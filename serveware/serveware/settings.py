"""
Django settings for the ServeWare project.

All environment-specific and secret values are read from environment variables.
Nothing secret is stored in this file.

Where the values come from:
  - Local development : serveware/serveware/.env  (next to manage.py, gitignored)
  - Staging container : deploy/.env.staging       (Jenkins secret file: serveware-env-staging)
  - Prod container    : deploy/.env.prod          (Jenkins secret file: serveware-env-prod)
  - Jenkins CI tests  : environment block in the Jenkinsfile

Environment variables used (placeholders -> put real values in the .env files, NOT here):

  DJANGO_ENV=development | staging | production
  DJANGO_DEBUG=True | False
  DJANGO_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(50))">
  DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<container-name e.g. serveware-prod-web>
  DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:<port>,http://127.0.0.1:<port>
  SITE_URL=http://localhost:<port>
  APP_VERSION=<set automatically by the Docker build / Jenkins>
  SQLITE_PATH=<path to db file; containers use /data/db.sqlite3>
  MEDIA_ROOT=<path to uploads; containers use /app/media>
  EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend | django.core.mail.backends.smtp.EmailBackend
  EMAIL_HOST=smtp.gmail.com
  EMAIL_PORT=587
  EMAIL_USE_TLS=True
  EMAIL_HOST_USER=serveware.in@gmail.com
  EMAIL_HOST_PASSWORD=<new Gmail App Password, no spaces>
  DEFAULT_FROM_EMAIL=ServeWare <serveware.in@gmail.com>
  OTP_TTL_SECONDS=600
  LOG_LEVEL=DEBUG | INFO | WARNING
  ENABLE_FAULT_INJECTION=True | False   (False in production)
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Optional local file for development; a missing file is fine (containers use env_file instead).
environ.Env.read_env(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DJANGO_ENV = env("DJANGO_ENV", default="development")

# Defaults to False so a missing variable can never accidentally enable debug in prod.
DEBUG = env.bool("DJANGO_DEBUG", default=False)

# The default only exists so tests and `collectstatic` during `docker build` can run.
# Production refuses to start with it.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key")
if DJANGO_ENV == "production" and SECRET_KEY.startswith("dev-only"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

APP_VERSION = env("APP_VERSION", default="dev")
SITE_URL = env("SITE_URL", default="http://localhost:8000")  # used in table QR codes
ENABLE_FAULT_INJECTION = env.bool("ENABLE_FAULT_INJECTION", default=False)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_prometheus',  # exposes /metrics for Prometheus

    'accounts',    # user authentication app
    'restaurant',  # restaurant app
    'customer',    # customer app
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',               # serves static files under gunicorn
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',   # must be last
]

ROOT_URLCONF = 'serveware.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'serveware.wsgi.application'
AUTH_USER_MODEL = 'accounts.CustomUser'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'sessionid'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        # django_prometheus wrapper around sqlite3 adds DB query metrics
        'ENGINE': 'django_prometheus.db.backends.sqlite3',
        'NAME': env("SQLITE_PATH", default=str(BASE_DIR / 'db.sqlite3')),
    }
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files & media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # target of `collectstatic` (was missing before)

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / 'media')))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Email (OTP password reset)
# Default is the console backend: emails are printed, never sent.
# Only production sets the SMTP backend + App Password in .env.prod.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="ServeWare <no-reply@serveware.local>")

OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=600)


# ---------------------------------------------------------------------------
# Security headers
# (HTTPS-only cookie flags are left off because this runs over plain HTTP locally.)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True


# ---------------------------------------------------------------------------
# Logging (replaces print() debugging)
# Use in code:  logger = logging.getLogger("serveware")
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "serveware": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}


# ---------------------------------------------------------------------------
# Tests: JUnit XML output so Jenkins can show results and trends
# ---------------------------------------------------------------------------
TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
TEST_OUTPUT_DIR = str(BASE_DIR / "test-reports")
TEST_OUTPUT_FILE_NAME = None
