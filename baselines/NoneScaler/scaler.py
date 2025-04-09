import time
from baselines.NoneScaler.cfg import NoneConfig
from baselines.scaler_template import ScalerTemplate
from utils.logger import get_logger

class NoneScaler(ScalerTemplate):
    def __init__(self, cfg: NoneConfig, name: str):
        super().__init__(cfg, name)
        self.logger = get_logger('./logs', 'None')

    async def register(self):
        self.logger.info('Register NoneController...')
            

    def cancel(self):
        self.logger.info('Remove NoneController...')