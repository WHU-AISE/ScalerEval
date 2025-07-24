import asyncio
import threading
import queue
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, List, Optional
from fastapi import BackgroundTasks, WebSocket, WebSocketDisconnect
from datetime import datetime

import json
import os
import weakref


class TaskManager:
    def __init__(self):
        self.active_tasks = set()
        self.websocket_connections = weakref.WeakSet()
        
    def add_task(self, task):
        self.active_tasks.add(task)
        task.add_done_callback(self.active_tasks.discard)
    
    def add_websocket(self, ws):
        self.websocket_connections.add(ws)
    
    async def cleanup_all(self):
        for task in list(self.active_tasks):
            if not task.done():
                task.cancel()
        
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        
        for ws in list(self.websocket_connections):
            try:
                await ws.close()
            except:
                pass