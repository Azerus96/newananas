FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Установка CUDA (если нужно)
# RUN curl -O https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
# RUN mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
# RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub
# RUN add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"
# RUN apt-get update && apt-get install -y cuda

# Создание рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . /app/

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements/prod.txt

# Для разработки можно установить дополнительные зависимости
RUN if [ "$FLASK_ENV" = "development" ] ; then pip install --no-cache-dir -r requirements/dev.txt ; fi

# Порт для веб-сервера
EXPOSE 5000

# Порт для Jupyter
EXPOSE 8888

# Запуск по умолчанию
CMD ["python", "-m", "rlofc.web.app"]
