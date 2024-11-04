import os
import tensorflow as tf

# Настройка TensorFlow
tf.get_logger().setLevel("ERROR")
tf.config.set_visible_devices([], "GPU")

# Базовые настройки
port = os.getenv("PORT", "10000")
bind = "0.0.0.0:" + port
workers = int(os.getenv("WORKERS", "1"))
threads = 2
timeout = int(os.getenv("TIMEOUT", "300"))

# Настройки воркера
worker_class = "gthread"
worker_connections = 1000
keepalive = 2

# Логирование
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Предзагрузка приложения
preload_app = True

def on_starting(server):
    import tensorflow as tf
    tf.keras.backend.clear_session()

def post_fork(server, worker):
    import tensorflow as tf
    tf.keras.backend.clear_session()

def on_exit(server):
    import tensorflow as tf
    tf.keras.backend.clear_session()
