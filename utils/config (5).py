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
                'save_replays': False,
                'fantasy_mode': True,
                'progressive_fantasy': False,
                'think_time': 1000  # миллисекунды
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
            'agents': {
                'dqn': {
                    'hidden_layers': [256, 256, 128],
                    'dropout_rate': 0.2,
                    'target_update_freq': 1000,
                    'min_replay_size': 1000
                },
                'a3c': {
                    'num_workers': 4,
                    'value_loss_coef': 0.5,
                    'entropy_coef': 0.01,
                    'max_grad_norm': 40
                },
                'ppo': {
                    'clip_ratio': 0.2,
                    'policy_epochs': 10,
                    'value_epochs': 10,
                    'target_kl': 0.01,
                    'value_loss_coef': 0.5,
                    'gae_lambda': 0.95
                }
            },
            'state': {
                'size': 364,  # Размер вектора состояния
                'card_encoding_size': 52,
                'street_encoding_size': 3
            },
            'action': {
                'size': 65  # Размер пространства действий
            },
            'paths': {
                'models': 'models',
                'logs': 'logs',
                'replays': 'replays',
                'checkpoints': 'checkpoints'
            },
            'logging': {
                'level': 'INFO',
                'file': 'rlofc.log',
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            },
            'web': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'static_folder': 'static',
                'template_folder': 'templates'
            },
            'metrics': {
                'enabled': True,
                'prometheus_port': 9090,
                'update_interval': 5
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
            
    def update(self, updates: Dict[str, Any]) -> None:
        """Обновляет конфигурацию"""
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    deep_update(d[k], v)
                else:
                    d[k] = v
                    
        deep_update(self.config, updates)
        
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Получает конфигурацию для конкретного агента"""
        base_config = {
            'learning_rate': self.get('training.learning_rate'),
            'gamma': self.get('training.gamma'),
            'batch_size': self.get('training.batch_size'),
            'memory_size': self.get('training.memory_size')
        }
        
        agent_specific = self.get(f'agents.{agent_type}', {})
        return {**base_config, **agent_specific}
        
    def validate(self) -> bool:
        """Проверяет валидность конфигурации"""
        required_keys = [
            'game', 'training', 'agents', 'paths', 'logging'
        ]
        
        for key in required_keys:
            if key not in self.config:
                return False
                
        return True
