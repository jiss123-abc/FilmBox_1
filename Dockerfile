FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any needed (sqlite is built-in)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Set environment variable to ensure logs are visible
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
