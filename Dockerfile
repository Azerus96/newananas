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

# Копирование исходного кода
COPY . .

# Установка пакета в development mode
RUN pip install -e .

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/data

# Копирование gunicorn конфига
COPY gunicorn_config.py /app/gunicorn_config.py

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
