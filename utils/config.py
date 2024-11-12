import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import logging
from datetime import datetime

class Config:
    """Класс для работы с конфигурацией"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.getenv('RLOFC_CONFIG', 'config.yml')
        self.config = self._load_config()
        self._validate_and_update()
        
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        path = Path(self.config_path)
        
        if not path.exists():
            config = self._get_default_config()
            self._save_config(config)
            return config
            
        try:
            with open(path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            'game': {
                'seed': None,
                'num_games': 1000,
                'save_replays': False,
                'fantasy_mode': True,
                'progressive_fantasy': False,
                'think_time': 1000,  # миллисекунды
                'max_players': 3,
                'default_player_mode': 'single',
                'ai_vs_ai_enabled': True,
                'mobile_support': True
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
                'checkpoint_interval': 100,
                'save_best_only': True,
                'early_stopping_patience': 5,
                'max_training_time': 3600  # seconds
            },
            'agents': {
                'dqn': {
                    'hidden_layers': [256, 256, 128],
                    'dropout_rate': 0.2,
                    'target_update_freq': 1000,
                    'min_replay_size': 1000,
                    'double_dqn': True,
                    'dueling_dqn': True
                },
                'a3c': {
                    'num_workers': 4,
                    'value_loss_coef': 0.5,
                    'entropy_coef': 0.01,
                    'max_grad_norm': 40,
                    'lstm_size': 128
                },
                'ppo': {
                    'clip_ratio': 0.2,
                    'policy_epochs': 10,
                    'value_epochs': 10,
                    'target_kl': 0.01,
                    'value_loss_coef': 0.5,
                    'gae_lambda': 0.95,
                    'advantage_normalization': True
                }
            },
            'state': {
                'size': 364,
                'card_encoding_size': 52,
                'street_encoding_size': 3,
                'history_length': 10,
                'normalize_input': True
            },
            'action': {
                'size': 65,
                'legal_actions_only': True,
                'action_masking': True
            },
            'paths': {
                'models': 'models',
                'logs': 'logs',
                'replays': 'replays',
                'checkpoints': 'checkpoints',
                'tensorboard': 'runs',
                'exports': 'exports'
            },
            'logging': {
                'level': 'INFO',
                'file': 'rlofc.log',
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                'rotation': '1 day',
                'backup_count': 7,
                'log_to_file': True,
                'log_to_console': True
            },
            'web': {
                'host': '0.0.0.0',
                'port': int(os.getenv('PORT', 5000)),
                'debug': False,
                'static_folder': 'web/static',  # Исправленный путь для статических файлов
                'template_folder': 'web/templates',  # Исправленный путь для шаблонов
                'session_lifetime': 3600,
                'max_content_length': 16 * 1024 * 1024,
                'cors_enabled': True,
                'cors_origins': '*'
            },
            'metrics': {
                'enabled': True,
                'prometheus_port': 9090,
                'update_interval': 5,
                'custom_metrics': True,
                'export_metrics': True
            },
            'security': {
                'secret_key': os.urandom(24).hex(),
                'session_protection': 'strong',
                'csrf_enabled': True,
                'rate_limiting': True,
                'max_requests_per_minute': 100
            },
            'optimization': {
                'cache_enabled': True,
                'cache_timeout': 300,
                'compression_enabled': True,
                'minify_response': True
            }
        }
        
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Сохраняет конфигурацию в файл"""
        try:
            path = Path(self.config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def _validate_and_update(self) -> None:
        """Проверяет и обновляет конфигурацию"""
        default_config = self._get_default_config()
        
        def update_missing(current: dict, default: dict) -> dict:
            for key, value in default.items():
                if key not in current:
                    current[key] = value
                elif isinstance(value, dict) and isinstance(current[key], dict):
                    current[key] = update_missing(current[key], value)
            return current
            
        self.config = update_missing(self.config, default_config)
        self._save_config(self.config)

    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение из конфигурации по ключу"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Устанавливает значение в конфигурации"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            config = config.setdefault(k, {})
            
        config[keys[-1]] = value
        self._save_config(self.config)

    def update(self, updates: Dict[str, Any]) -> None:
        """Обновляет конфигурацию"""
        def deep_update(d: dict, u: dict) -> dict:
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    d[k] = deep_update(d[k], v)
                else:
                    d[k] = v
            return d
                    
        deep_update(self.config, updates)
        self._save_config(self.config)
        
    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Получает конфигурацию для конкретного агента"""
        base_config = {
            'learning_rate': self.get('training.learning_rate'),
            'gamma': self.get('training.gamma'),
            'batch_size': self.get('training.batch_size'),
            'memory_size': self.get('training.memory_size'),
            'checkpoint_interval': self.get('training.checkpoint_interval'),
            'save_best_only': self.get('training.save_best_only')
        }
        
        agent_specific = self.get(f'agents.{agent_type}', {})
        return {**base_config, **agent_specific}
        
    def validate(self) -> bool:
        """Проверяет валидность конфигурации"""
        try:
            required_keys = [
                'game', 'training', 'agents', 'paths', 'logging',
                'web', 'metrics', 'security', 'optimization'
            ]
            
            for key in required_keys:
                if key not in self.config:
                    logging.error(f"Missing required config section: {key}")
                    return False
                    
            # Проверка критических значений
            if self.get('web.port') <= 0:
                logging.error("Invalid web port")
                return False
                
            if self.get('training.batch_size') <= 0:
                logging.error("Invalid batch size")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Config validation error: {e}")
            return False
            
    def export_config(self, path: Optional[str] = None) -> None:
        """Экспортирует текущую конфигурацию"""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.get('paths.exports') + f"/config_export_{timestamp}.yml"
            
        try:
            export_path = Path(path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
                
            logging.info(f"Config exported to {path}")
            
        except Exception as e:
            logging.error(f"Error exporting config: {e}")
            
    def import_config(self, path: str) -> bool:
        """Импортирует конфигурацию из файла"""
        try:
            with open(path) as f:
                new_config = yaml.safe_load(f)
                
            if not isinstance(new_config, dict):
                logging.error("Invalid config format")
                return False
                
            self.config = new_config
            self._validate_and_update()
            self._save_config(self.config)
            
            logging.info(f"Config imported from {path}")
            return True
            
        except Exception as e:
            logging.error(f"Error importing config: {e}")
            return False
            
    def reset_to_default(self) -> None:
        """Сбрасывает конфигурацию к значениям по умолчанию"""
        self.config = self._get_default_config()
        self._save_config(self.config)
        logging.info("Config reset to default values")
        
    def get_all(self) -> Dict[str, Any]:
        """Возвращает всю конфигурацию"""
        return self.config.copy()
        
    def __str__(self) -> str:
        """Строковое представление конфигурации"""
        return f"Config(path={self.config_path})"
        
    def __repr__(self) -> str:
        """Подробное строковое представление"""
        return f"Config(path={self.config_path}, sections={list(self.config.keys())})"

