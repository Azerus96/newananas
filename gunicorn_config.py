import os
import tensorflow as tf

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Базовые настройки
port = os.getenv('PORT')
if not port:
    raise ValueError('PORT environment variable is not set')
bind = f"0.0.0.0:{port}"

workers = int(os.getenv('WORKERS', '1'))
threads = int(os.getenv('THREADS', '2'))
timeout = int(os.getenv('TIMEOUT', '300'))

# Настройки воркера
worker_class = 'gthread'
worker_connections = 1000
keepalive = 2

# Логирование
accesslog = '-'
errorlog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True

# Предзагрузка приложения
preload_app = True

def _clear_tf_session():
    """Централизованная очистка сессии TensorFlow"""
    try:
        tf.keras.backend.clear_session()
    except:
        pass

def on_starting(server):
    _clear_tf_session()

def post_fork(server, worker):
    _clear_tf_session()

def on_exit(server):
    _clear_tf_session()
