FROM python:3.9

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
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV CUDA_VISIBLE_DEVICES=-1
# Порт берем из переменных окружения Render
ENV PORT=${PORT:-10000}

# Открываем порт
EXPOSE ${PORT}

# Создаем gunicorn.conf.py
RUN echo "import os\n\
bind = f\"0.0.0.0:{os.environ.get('PORT', '10000')}\"\n\
workers = 4\n\
threads = 2\n\
timeout = 120\n\
capture_output = True\n\
enable_stdio_inheritance = True\n\
accesslog = '-'\n\
errorlog = '-'\n\
loglevel = 'info'" > /app/gunicorn.conf.py

# Запуск через gunicorn
CMD gunicorn -c gunicorn.conf.py web.app:app
