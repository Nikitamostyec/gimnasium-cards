import sys
from pathlib import Path
import environ

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Добавляем папку apps в PYTHONPATH, чтобы импортировать приложения напрямую
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Инициализация чтения .env
env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние библиотеки
    'bootstrap',
    'simple_history',

    # Наши приложения (из папки apps/)
    'core',
    'users',
    'cards',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware для фиксации пользователя в журнале аудита
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Общая папка шаблонов
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

WSGI_APPLICATION = 'config.wsgi.application'

# База данных читается автоматически из .env (SQLite или PostgreSQL)
DATABASES = {
    'default': env.db('DATABASE_URL',
                      default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# Указываем нашу кастомную модель пользователя (Учителя и Завучи)
AUTH_USER_MODEL = 'users.User'

# Настройки сессий для учеников (сессия живет 2 недели, если не нажали "Выйти")
SESSION_COOKIE_AGE = 1209600

# Локализация под РФ (важно для валидации дат и админки)
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Статические файлы
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_USE_FINDERS = True


if not DEBUG:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Куда перенаправлять учителей при входе/выходе
LOGIN_URL = '/staff/login/'
LOGIN_REDIRECT_URL = '/staff/dashboard/'
LOGOUT_REDIRECT_URL = '/'

TEACHER_INVITE_CODE = 'GIM16-2026-TEACH'
