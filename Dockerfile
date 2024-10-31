FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . /app/

# Установка пакета в режиме разработки
RUN pip install -e .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements/prod.txt

# Для разработки можно установить дополнительные зависимости
RUN if [ "$FLASK_ENV" = "development" ] ; then pip install --no-cache-dir -r requirements/dev.txt ; fi

# Установка PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Порт для веб-сервера
EXPOSE 5000

# Запуск приложения
CMD ["python", "web/app.py"]
