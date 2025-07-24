import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from fastapi import WebSocket
from typing import Dict, List, Optional, TextIO, Tuple, Callable


class SmartLogStream:
    def __init__(self, file_stream, filter_patterns=None):
        self.file_stream = file_stream
        self.filter_patterns = filter_patterns or [
            "[LogFileReader]",
            "Processing log line:",
            "Log entry created:",
            "Broadcasting to",
            "WebSocket send failed:",
            "Added environment websocket",
            "Removed environment websocket",
            "Added evaluation websocket", 
            "Removed evaluation websocket",
            "Processing...", # 过滤进度日志
        ]
    
    def write(self, data):
        data_str = str(data)
        should_filter = any(pattern in data_str for pattern in self.filter_patterns)
        
        if not should_filter:
            self.file_stream.write(data)
            self.file_stream.flush()
    
    def flush(self):
        self.file_stream.flush()
    
    def __getattr__(self, attr):
        return getattr(self.file_stream, attr)


def setup_smart_logging(log_file_path: str = "logs/output.log") -> Tuple[TextIO, TextIO, TextIO]:
    log_file = open(log_file_path, "w", encoding='utf-8')
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    sys.stdout = SmartLogStream(log_file)
    sys.stderr = SmartLogStream(log_file)
    
    return original_stdout, original_stderr, log_file


def get_debug_logger(name: str = 'debug') -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.WARNING)  # 只显示 WARNING 和 ERROR
        handler = logging.StreamHandler(sys.__stdout__)
        formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger


class SmartLogFileReader:
    
    def __init__(self, log_file_path="logs/output.log", status_callback=None):
        self.log_file_path = os.path.abspath(log_file_path)
        self.last_position = 0
        self.connected_websockets = {
            'environment': [],
            'evaluation': []
        }
        self.monitoring = False
        self.processed_lines = set()  
        self.status_callback = status_callback

        self.debug_logger = get_debug_logger('LogFileReader')
    
    def set_status_callback(self, callback: Callable):
        self.status_callback = callback
    
    async def start_monitoring(self):
        self.monitoring = True
        
        if not os.path.exists(self.log_file_path):
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write("")
        else:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(0, 2)  # 跳到文件末尾
                self.last_position = f.tell()
        
        while self.monitoring:
            try:
                if os.path.exists(self.log_file_path):
                    with open(self.log_file_path, 'r', encoding='utf-8') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        
                        if new_lines:
                            self.last_position = f.tell()
                            
                            for line in new_lines:
                                line = line.strip()
                                if line and not self._should_skip_line(line):
                                    await self.process_log_line(line)
                
            except Exception as e:
                self.debug_logger.error(f"Error reading log file: {e}")
            
            await asyncio.sleep(0.1)
    
    def _should_skip_line(self, line: str) -> bool:
        skip_patterns = [
            "[LogFileReader]",
            "Processing log line:",
            "Log entry created:",
            "Broadcasting to",
            "Added environment websocket",
            "Removed environment websocket",
            "HTTPError('500 Server Error:",
            "HTTPError('404 Not Found:",
            "HTTPError('503 Service Unavailable:",
            "Processing... (",
        ]
        
        if not line or line in self.processed_lines:
            return True
        
        return any(pattern in line for pattern in skip_patterns)
    
    def stop_monitoring(self):
        self.monitoring = False
    
    async def process_log_line(self, line: str):
        if not line:
            return
        
        if line in self.processed_lines:
            return
        self.processed_lines.add(line)
        
        if len(self.processed_lines) > 10000:
            self.processed_lines.clear()
        
        # 🔧 移除处理日志的调试信息
        
        stage = self.determine_stage(line)
        level = self.determine_level(line)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": line,
            "level": level,
            "stage": stage
        }
        
        await self.broadcast_to_websockets(stage, log_entry)
        
        if self.status_callback:
            try:
                self.status_callback(stage, log_entry)
            except Exception as e:
                self.debug_logger.error(f"Error in status callback: {e}")
    
    def determine_stage(self, line: str) -> str:
        env_keywords = [
            'init_env', 'create namespace', 'create deployments', 
            'microservices are avaliable', 'Pre-cleaning environment',
            'Environment preparation', 'Initializing',
            'Step 1:', 'Step 2:', 'Step 3:',
            'Starting environment preparation', 'Pre-cleaning',
            'Environment initialization', 'Verifying environment',
            'all services in', 'are avaliable', '[ENVIRONMENT]'
        ]
        
        eval_keywords = [
            '[Locust]', '[LoadInjector]', '[Scaler]', 
            'SLO violation', 'Success rate', 'CPU usage', 'Memory usage',
            'Injecting workload', 'Step 4:', 'Step 5:', 'Step 6:',
            'Starting evaluation', 'Registering scaler',
            'Starting workload', 'Collecting performance', 'Calculating results',
            '[EVALUATION]', '[LOCUST]', 'Workload injection completed',
            'Metrics collection completed'
        ]
        
        line_lower = line.lower()
        
        for keyword in env_keywords:
            if keyword.lower() in line_lower:
                return "environment"
        
        for keyword in eval_keywords:
            if keyword.lower() in line_lower:
                return "evaluation"
        
        return "environment"
    
    def determine_level(self, line: str) -> str:
        line_upper = line.upper()
        
        if any(word in line_upper for word in ['ERROR', 'FAILED', 'EXCEPTION', 'TRACEBACK']):
            return "error"
        elif any(word in line_upper for word in ['WARNING', 'WARN']):
            return "warning"
        elif any(word in line_upper for word in ['SUCCESS', 'COMPLETED', 'READY', 'AVALIABLE']):
            return "success"
        else:
            return "info"
    
    async def broadcast_to_websockets(self, log_type: str, log_entry: dict):
        if log_type in self.connected_websockets:
            websockets = self.connected_websockets[log_type].copy()
                
            disconnected = []
            for websocket in websockets:
                try:
                    await websocket.send_text(json.dumps(log_entry))
                except Exception as e:
                    self.debug_logger.warning(f"WebSocket send failed: {e}")
                    disconnected.append(websocket)
            
            for ws in disconnected:
                if ws in self.connected_websockets[log_type]:
                    self.connected_websockets[log_type].remove(ws)
    
    def add_websocket(self, log_type: str, websocket: WebSocket):
        if log_type in self.connected_websockets:
            self.connected_websockets[log_type].append(websocket)
    
    def remove_websocket(self, log_type: str, websocket: WebSocket):
        if log_type in self.connected_websockets:
            if websocket in self.connected_websockets[log_type]:
                self.connected_websockets[log_type].remove(websocket)


def log_business_info(message: str, stage: str = "general"):
    print(f"[{stage.upper()}] {message}")

def log_business_success(message: str, stage: str = "general"):
    print(f"[{stage.upper()}] SUCCESS: {message}")

def log_business_error(message: str, stage: str = "general"):
    print(f"[{stage.upper()}] ERROR: {message}")

def log_business_warning(message: str, stage: str = "general"):
    print(f"[{stage.upper()}] WARNING: {message}")

def restore_logging(original_stdout: TextIO, original_stderr: TextIO, log_file: TextIO):
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    if log_file and not log_file.closed:
        log_file.close()