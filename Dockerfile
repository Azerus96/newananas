# Dockerfile
FROM python:3.9

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    TF_CPP_MIN_LOG_LEVEL=3 \
    CUDA_VISIBLE_DEVICES=-1 \
    PORT=10000 \
    PYTHONPATH=/app \
    WORKERS=1 \
    TIMEOUT=300

# Обновление pip
RUN pip install --no-cache-dir --upgrade pip

# Копирование requirements
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Установка gunicorn
RUN pip install gunicorn

# Копирование исходного кода
COPY . .

# Установка пакета в development mode
RUN pip install -e .

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/data

# Создание gunicorn конфига
RUN echo 'import os\n\
import tensorflow as tf\n\
\n\
# Настройка TensorFlow\n\
tf.get_logger().setLevel("ERROR")\n\
tf.config.set_visible_devices([], "GPU")\n\
\n\
# Базовые настройки\n\
bind = f"0.0.0.0:{os.getenv("PORT", "10000")}"\n\
workers = int(os.getenv("WORKERS", "1"))\n\
threads = 2\n\
timeout = int(os.getenv("TIMEOUT", "300"))\n\
\n\
# Настройки воркера\n\
worker_class = "gthread"\n\
worker_connections = 1000\n\
keepalive = 2\n\
\n\
# Логирование\n\
accesslog = "-"\n\
errorlog = "-"\n\
loglevel = "info"\n\
\n\
# Предзагрузка приложения\n\
preload_app = True\n\
\n\
def on_starting(server):\n\
    tf.keras.backend.clear_session()\n\
\n\
def post_fork(server, worker):\n\
    tf.keras.backend.clear_session()\n\
\n\
def on_exit(server):\n\
    tf.keras.backend.clear_session()' > /app/gunicorn_config.py

# Проверка конфигурации при сборке
RUN python -c "import tensorflow as tf; tf.keras.backend.clear_session()"

# Создание непривилегированного пользователя
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Открываем порт
EXPOSE $PORT

# Запуск приложения
CMD ["gunicorn", "-c", "gunicorn_config.py", "web.app:app"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/health || exit 1
