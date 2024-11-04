import os
import tensorflow as tf

# Отключаем предупреждения TensorFlow
tf.get_logger().setLevel('ERROR')

# Настройки Gunicorn
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1
threads = 2
timeout = 300
worker_class = 'gthread'

# Логирование
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Предзагрузка
preload_app = True

def on_starting(server):
    """Инициализация при запуске"""
    tf.config.set_visible_devices([], 'GPU')
    tf.keras.backend.clear_session()
