from typing import Type, Dict
from baselines.scaler_config_template import ScalerConfig
from baselines.NoneScaler.cfg import NoneConfig
from baselines.KHPA.cfg import KHPAConfig
from baselines.Showar.cfg import ShowarConfig
from baselines.PBScaler.cfg import PBScalerConfig
from baselines.scaler_template import ScalerTemplate
from baselines.NoneScaler.scaler import NoneScaler
from baselines.KHPA.scaler import KHPAScaler
from baselines.Showar.scaler import ShowarScaler
from baselines.PBScaler.scaler import PBScaler
from config.exp_config import Config

class ScalerFactory:
    CONFIG_CLASSES: Dict[str, Type[ScalerConfig]] = {
        'None': NoneConfig,
        'KHPA': KHPAConfig,
        'Showar': ShowarConfig,
        'PBScaler': PBScalerConfig,
    }
    SCALER_CLASSES: Dict[str, Type[ScalerTemplate]] = {
        'None': NoneScaler,
        'KHPA': KHPAScaler,
        'Showar': ShowarScaler,
        'PBScaler': PBScaler,
    }

    @classmethod
    def create_scaler(cls, name: str, exp_config: Config) -> ScalerTemplate:
        if 'KHPA' in name:
            CPU_thred = int(name.split('-')[1])
            config = KHPAConfig(exp_config)
            config.set_cpu_threshold(CPU_thred)
            scaler = KHPAScaler(config, name)
            return scaler
        else:
            config_class = cls.CONFIG_CLASSES.get(name)
            if not config_class:
                raise ValueError(f"Unknown scaler/config name: {name}")
            
            scaler_class = cls.SCALER_CLASSES.get(name)
            if not scaler_class:
                raise ValueError(f"Unknown scaler name: {name}")
            
            config = config_class(exp_config)
        
            scaler = scaler_class(config, name)
            
            return scaler