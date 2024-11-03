FROM python:3.8-slim

# Установить рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements/prod.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . /app

# Указываем переменную окружения
ENV FLASK_APP=web/app.py

# Запускаем Flask приложение
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
