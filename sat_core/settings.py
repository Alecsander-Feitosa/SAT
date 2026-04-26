from pathlib import Path
from dotenv import load_dotenv
import os
import dj_database_url


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-chave-dev-123')

DEBUG = True
ALLOWED_HOSTS = ['*']

# --- NOVO: Obrigatório para o Render permitir logins e formulários via HTTPS ---
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 1. ESTE APP NATIVO É OBRIGATÓRIO PARA O ALLAUTH
    'django.contrib.sites', 

    # 2. AS APPS DO ALLAUTH QUE FALTAM
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    # 3. OS SEUS PROVEDORES SOCIAIS
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.apple',
    'allauth.socialaccount.providers.facebook',

    # --- Frameworks para API (Android/iOS) ---
    'rest_framework',   # Cria a API
    'corsheaders',      # Permite conexão externa (App/React)

    # --- Meus Aplicativos SAT ---
    'accounts.apps.AccountsConfig',
    'gamification',  # Check-in, Pontos e Ranking
    'content',       # Notícias e Avisos
    'organizadas',   # Torcidas
    'social',
    'loja',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend', # Autenticação do Allauth
]



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # <--- NOVO: Obrigatório para Apps
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'sat_core.urls'

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
                'accounts.context_processors.tema_torcida',
                'accounts.context_processors.torcida_branding', # <-- Adicionado aqui corretamente
            ],
        },
    },
]

WSGI_APPLICATION = 'sat_core.wsgi.application'

# O Render vai injetar a URL do PostgreSQL automaticamente
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600
    )
}

# --- Configuração da API REST ---
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}

# --- Configuração de Usuário ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internacionalização ---
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'

# Diz ao Django onde estão os teus ficheiros de desenvolvimento
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Diz ao Django para onde enviar os ficheiros quando fazes o deploy no Render
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Ativa a compressão e o cache do WhiteNoise (opcional mas muito recomendado)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- Arquivos de Mídia (Uploads de Notícias/Produtos/Avatar) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- CORS (Permite que o App Android acesse a API) ---
CORS_ALLOW_ALL_ORIGINS = True # Em produção, mudaremos para domínios específicos

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = 'dashboard'

LOGOUT_REDIRECT_URL = 'login'


# Configurações opcionais do Allauth para capturar o email
ACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True




# ==========================================
# CONFIGURAÇÕES DO PAINEL ADMIN (JAZZMIN)
# ==========================================
JAZZMIN_SETTINGS = {
    "site_title": "SAT Admin",
    "site_header": "Plataforma SAT",
    "site_brand": "Gestão SAT",
    "welcome_sign": "Bem-vindo ao Painel de Moderação",
    "search_model": ["auth.User", "organizadas.Torcida"], # Permite pesquisar rápido
    "show_sidebar": True,
    "navigation_expanded": False, # Mantém o menu recolhido no telemóvel
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        # Pode adicionar ícones para as suas apps depois
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly", # Um tema escuro e elegante
    "dark_mode_theme": "darkly",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-primary",
}