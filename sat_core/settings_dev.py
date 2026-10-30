# Configuração para testar no seu computador, sem tocar no banco/arquivos de produção.
# Uso: python manage.py runserver --settings=sat_core.settings_dev
from .settings import *  # noqa: F401,F403

DEBUG = True

# Banco local (cópia do db.sqlite3), ignorado pelo git
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_dev.sqlite3',
    }
}

# Uploads ficam na pasta media/ local, nunca no Cloudinary
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Demonstração da geolocalização em tempo real: envia a cada 15 s
BEPE_INTERVALO_LOCALIZACAO = 15

# Celulares só liberam o GPS em HTTPS: permite os túneis de teste (cloudflared / ngrok)
CSRF_TRUSTED_ORIGINS = ['https://*.trycloudflare.com', 'https://*.ngrok-free.app', 'https://*.ngrok.app']
