import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import os
import redis


load_dotenv(find_dotenv())

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-je%_l51vz1p_t-7h!n8xm+*fqg!v!xp^jcva3+6mfwkg3tbib_'
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!

ALLOWED_HOSTS = ["*"]

APPEND_SLASH = False
# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "knox",
    "channels",
    "channels_redis",
    "djangochannelsrestframework",
    "corsheaders",
    "storages",
    "user_account",
    "rides",
    "payment",
    "administrationApp",
    "chat",
    "ride_request",
    "mjml",
    "website",
    "tailwind",
    "theme",
    "django_browser_reload",
    "advertisement",
]

TAILWIND_APP_NAME = "theme"

INTERNAL_IPS = [
    "127.0.0.1",
]


MJML_BACKEND_MODE = "cmd"
MJML_EXEC_CMD = "node_modules/.bin/mjml"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
        "knox.auth.TokenAuthentication",
    ],
    "EXCEPTION_HANDLER": "mytaxi.customexceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "mytaxi.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mytaxi.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("dbname"),
        "USER": os.environ.get("dbuser"),
        "PASSWORD": os.environ.get("dbpassword"),
        "HOST": os.environ.get("dbhost"),
        "PORT": 5432,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://" + os.environ.get("REDIS_LOCATION"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis://" + os.environ.get("REDIS_LOCATION"))],
        },
    },
}

redis_pool = redis.ConnectionPool.from_url("redis://" + os.environ.get("REDIS_LOCATION"))
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

# AWS s3 Bucket Settings
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = "mytaxi-1"
AWS_S3_REGION_NAME = "ap-northeast-1"
AWS_S3_CUSTOM_DOMAIN = "%s.s3.amazonaws.com" % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_DEFAULT_ACL = None
AWS_LOCATION = "static"

# Static and Media Settings
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

STATIC_URL = "https://%s/%s/static/" % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, "media")
DEFAULT_FILE_STORAGE = "mytaxi.storages.MediaStorage"


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "user_account.User"

ASGI_APPLICATION = "mytaxi.routing.application"


CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Email Settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtpout.secureserver.net"
EMAIL_PORT = 465
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_HOST_USER")
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False

border_color = "\033[31m"  # ANSI escape code for red color
reset_color = "\033[0m"  # Reset color to default
teal_color = "\033[36m"  # ANSI escape code for teal color
yellow_color = "\033[33m"  # ANSI escape code for yellow color

# log_format = f"""
# {border_color}----------------------------------------------------
# {border_color}|{{levelname:^50}}|
# {border_color}----------------------------------------------------{reset_color}
# {teal_color}{{levelname}}{reset_color} {{asctime:s}} {{name}} {{module}} {{filename}} {{lineno:d}} {{name}} {{funcName}} {{process:d}} {{message}}
# """

log_format = """
{border_color}+-----------------------------------------------------------------------------------------------------------+
{border_color}|{reset_color}{levelname_color} : {yellow_color}{message:^100}{reset_color}{border_color}|{reset_color}
{border_color}+-----------------------------------------------------------------------------------------------------------+{reset_color}
{levelname_color} : {name} {module} {filename} {lineno} {funcName} {process} {yellow_color}{message}{reset_color}
"""

color_mapping = {
    "DEBUG": "\033[36m",  # Teal color for DEBUG levelname
    "INFO": "\033[32m",  # Green color for INFO levelname
    "WARNING": "\033[33m",  # Yellow color for WARNING levelname
    "ERROR": "\033[31m",  # Red color for ERROR levelname
    "CRITICAL": "\033[91m",  # Bright red color for CRITICAL levelname
}
reset_color = "\033[0m"  # Reset color to default


# Define a custom formatter that applies colors to levelnames
class ColoredFormatter(logging.Formatter):
    border_color = "\033[31m"
    yellow_color = "\033[33m"  # ANSI escape code for red color

    def format(self, record):
        levelname_color = color_mapping.get(record.levelname, "")
        record.levelname_color = f"{levelname_color}{record.levelname}{reset_color}"
        record.border_color = f"{self.border_color}"
        record.reset_color = f"{reset_color}"
        record.yellow_color = f"{self.yellow_color}"
        return super().format(record)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "()": ColoredFormatter,
            "format": log_format,
            # "format": "\033[31m\n----------------------------------------------------\n|{levelname:^50}|\n----------------------------------------------------\n  {levelname}  {name} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "info_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{BASE_DIR}/logs/mytaxi_info.log",
            "mode": "a",
            "encoding": "utf-8",
            "formatter": "verbose",
            "level": "INFO",
            "backupCount": 5,
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
        },
        "error_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{BASE_DIR}/logs/mytaxi_error.log",
            "mode": "a",
            "formatter": "verbose",
            "level": "WARNING",
            "backupCount": 5,
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "info_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.template": {
            "handlers": ["error_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.server": {
            "handlers": ["error_handler"],
            "level": "INFO",
            "propagate": True,
        },
        "daphne": {
            "handlers": ["console", "info_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
        "gunicorn": {
            "handlers": ["console", "info_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}
