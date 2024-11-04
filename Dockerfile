FROM python:3.9

WORKDIR /app

# Оптимизация установки системных зависимостей и очистки кэша
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Оптимизация установки Python пакетов
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    rm -rf ~/.cache/pip/* && \
    find /usr/local -type d -name __pycache__ -exec rm -rf {} +

COPY . .
RUN pip install -e . && \
    pip cache purge && \
    rm -rf ~/.cache/pip/* && \
    find /usr/local -type d -name __pycache__ -exec rm -rf {} +

RUN mkdir -p /app/logs /app/data
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["gunicorn", "-c", "gunicorn_config.py", "web.app:app"]

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1
