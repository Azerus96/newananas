import os
import tensorflow as tf

# Настройка TensorFlow
tf.get_logger().setLevel('ERROR')
tf.config.set_visible_devices([], 'GPU')

# Базовые настройки
port = os.getenv('PORT', '8000')
bind = f"0.0.0.0:{port}"

# WebSocket настройки
workers = 1
threads = int(os.getenv('THREADS', '4'))
timeout = int(os.getenv('TIMEOUT', '300'))
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'
worker_connections = 1000
keepalive = 2

# WebSocket специфичные настройки
websocket_ping_interval = 25
websocket_ping_timeout = 60
websocket_max_message_size = 1024 * 1024

# Логирование
accesslog = '-'
errorlog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True

# Отключаем предзагрузку для WebSocket
preload_app = False

def _clear_tf_session():
    try:
        tf.keras.backend.clear_session()
    except Exception as e:
        print(f"Error clearing TensorFlow session: {e}")

def on_starting(server):
    _clear_tf_session()

def post_fork(server, worker):
    _clear_tf_session()

def on_exit(server):
    _clear_tf_session()

def when_ready(server):
    print("WebSocket server is ready to accept connections")
