import os
import tensorflow as tf

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Базовые настройки
port = os.getenv('PORT', '10000')
bind = '0.0.0.0:' + port
workers = 1
threads = 2
timeout = 120

# Настройки воркера
worker_class = 'gthread'
worker_connections = 1000
keepalive = 2

# Логирование
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Предзагрузка приложения
preload_app = True

def on_starting(server):
    """Инициализация при запуске"""
    tf.keras.backend.clear_session()

def post_fork(server, worker):
    """После создания воркера"""
    tf.keras.backend.clear_session()

def on_exit(server):
    """При завершении"""
    tf.keras.backend.clear_session()
