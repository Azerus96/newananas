# Build stage
FROM python:3.9-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.9-slim

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application code
COPY . .

# Create non-privileged user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app/data /app/logs

USER appuser

# Environment variables
ENV PYTHONPATH="${PYTHONPATH}:/app" \
    FLASK_APP=web.app \
    FLASK_ENV=production \
    WORKERS=4 \
    PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Expose port
EXPOSE ${PORT}

# Start application
CMD ["sh", "-c", "gunicorn \
    --bind 0.0.0.0:${PORT} \
    --worker-class gevent \
    --workers ${WORKERS} \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    web.app:app"]
