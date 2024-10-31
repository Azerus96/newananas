import os
from pathlib import Path
from typing import Any, Dict
import yaml

class Config:
    """Класс для работы с конфигурацией"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.getenv('RLOFC_CONFIG', 'config.yml')
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        path = Path(self.config_path)
        
        if not path.exists():
            return self._get_default_config()
            
        with open(path) as f:
            return yaml.safe_load(f)
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            'game': {
                'seed': None,
                'num_games': 1000,
                'save_replays': False
            },
            'training': {
                'batch_size': 32,
                'learning_rate': 0.001,
                'gamma': 0.99,
                'epsilon_start': 1.0,
                'epsilon_end': 0.01,
                'epsilon_decay': 0.995,
                'target_update': 10,
                'memory_size': 10000,
                'checkpoint_interval': 100
            },
            'paths': {
                'models': 'models',
                'logs': 'logs',
                'replays': 'replays'
            },
            'logging': {
                'level': 'INFO',
                'file': 'rlofc.log'
            }
        }
        
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение из конфигурации по ключу"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
                
        return value if value is not None else default
        
    def save(self) -> None:
        """Сохраняет текущую конфигурацию в файл"""
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.safe_dump(self.config, f)
