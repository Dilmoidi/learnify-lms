# Dockerfile for Learnify LMS - Production Daphne ASGI Server

# 1. Base Image
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=learnify.prod_settings

# 3. Set work directory
WORKDIR /app

# 4. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy project files
COPY . /app/

# 7. Collect static files
# We temporarily stub database connection config to collect static files without DB availability
RUN DJANGO_SECRET_KEY="temporary-secret-key-for-collectstatic" \
    python manage.py collectstatic --noinput --clear

# 8. Expose ASGI port
EXPOSE 8000

# 9. Start Daphne ASGI server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "learnify.asgi:application"]
