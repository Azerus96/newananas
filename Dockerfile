# Dockerfile

# Используем многоэтапную сборку для оптимизации
FROM python:3.9-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

# Финальный образ
FROM python:3.9-slim

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . /app/

# Создание непривилегированного пользователя
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Настройка переменных окружения
ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV FLASK_APP=web.app
ENV FLASK_ENV=production

# Порт для веб-сервера
EXPOSE 5000

# Запуск через gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--workers", "4", "web.app:app"]
