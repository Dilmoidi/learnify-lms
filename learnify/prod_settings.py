from .settings import *
import os
import dj_database_url

# Production settings for Learnify LMS
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-prod-key-change-me-in-env')

# ALLOWED_HOSTS & CSRF_TRUSTED_ORIGINS
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Configure CSRF trusted origins for secure form submissions in production
csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = csrf_origins.split(',')
else:
    CSRF_TRUSTED_ORIGINS = []

# Database configuration - using PostgreSQL for production
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=False
        )
    }

# Channel Layers - using Redis for production WebSockets coordination
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/1')
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [REDIS_URL],
        },
    },
}

# Security headers for reverse proxy configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Add WhiteNoise to middleware (must be right after SecurityMiddleware)
MIDDLEWARE = list(MIDDLEWARE)
try:
    security_index = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(security_index + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
except ValueError:
    MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Configure WhiteNoise storage for static file compression and caching (Django 4.2+ format)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Optional SSL/HTTPS security settings (can be enabled via environment variables)
if os.environ.get('DJANGO_SECURE_SSL', 'False') == 'True':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
