# CLARA API — Dockerfile for Railway/Render/Fly.io
FROM python:3.13-slim

WORKDIR /app

# Install system deps for psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject and install deps first (cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy app code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
