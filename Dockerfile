FROM python:3.8-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Обновление pip
RUN pip install --upgrade pip

# Копирование requirements
COPY requirements/prod.txt /app/requirements.txt

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка gunicorn
RUN pip install gunicorn

# Копирование всего проекта
COPY . /app

# Установка нашего пакета
RUN pip install -e .

# Создание необходимых директорий
RUN mkdir -p /app/logs

# Установка переменных окружения
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PORT=10000

# Открываем порт
EXPOSE $PORT

# Запуск через gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    web.app:app
