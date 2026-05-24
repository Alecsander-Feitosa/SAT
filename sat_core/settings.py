from pathlib import Path
from dotenv import load_dotenv
import os
import dj_database_url


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-chave-dev-123')

DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

# --- Configurações do Efí Bank (PIX) ---
EFI_CLIENT_ID = os.getenv('EFI_CLIENT_ID', '')
EFI_CLIENT_SECRET = os.getenv('EFI_CLIENT_SECRET', '')
EFI_SANDBOX = os.getenv('EFI_SANDBOX', 'True') == 'True'
EFI_CHAVE_PIX = os.getenv('EFI_CHAVE_PIX', 'sua_chave_pix_aqui@gmail.com')
EFI_CONTA_ID = os.getenv('EFI_CONTA_ID', '')  # ID da conta Efí (necessário para pagamento com cartão)

# Certificado: prioriza Base64 (para Render/produção), depois caminho local
import base64 as _b64
_efi_cert_b64 = os.getenv('EFI_CERT_BASE64', '')
if _efi_cert_b64:
    # No Render: recria o arquivo .pem a partir do Base64
    _cert_dir = os.path.join(BASE_DIR, 'certs')
    os.makedirs(_cert_dir, exist_ok=True)
    _cert_file = os.path.join(_cert_dir, 'certificado.pem')
    with open(_cert_file, 'wb') as f:
        f.write(_b64.b64decode(_efi_cert_b64))
    EFI_CERTIFICADO = _cert_file
else:
    # Local: usa o caminho relativo do .env
    _efi_cert_path = os.getenv('EFI_CERTIFICADO', '')
    EFI_CERTIFICADO = os.path.join(BASE_DIR, _efi_cert_path) if _efi_cert_path else ''

# --- NOVO: Obrigatório para o Render permitir logins e formulários via HTTPS ---
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    
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
    'accounts.backends.EmailBackend',
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
                'accounts.context_processors.carrinho_global',  # <-- Carrinho em todas as páginas
            ],
        },
    },
]

WSGI_APPLICATION = 'sat_core.wsgi.application'

# Configuração do Banco de Dados (Suporta DATABASE_URL ou variáveis individuais)
if os.getenv('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'postgres'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '6543'),
            'OPTIONS': {
                'sslmode': 'require',
            },
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True # Essencial para o Supabase
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

# Variável antiga mantida EXCLUSIVAMENTE para evitar crash da biblioteca django-cloudinary-storage no Django 5
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# --- Arquivos de Mídia (Uploads de Notícias/Produtos/Avatar) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configuração de Armazenamento (STORAGES) - Obrigatório para Django 4.2+ e 5.0+
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# --- Cloudinary: Armazenamento permanente de imagens (Render apaga arquivos locais a cada deploy) ---
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
}

# Só usa Cloudinary se as credenciais estiverem configuradas (produção)
if os.getenv('CLOUDINARY_CLOUD_NAME'):
    STORAGES["default"]["BACKEND"] = "cloudinary_storage.storage.MediaCloudinaryStorage"

# --- CORS (Permite que o App Android acesse a API) ---
CORS_ALLOW_ALL_ORIGINS = True # Em produção, mudaremos para domínios específicos

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = 'dashboard'

LOGOUT_REDIRECT_URL = 'login'


# Configurações opcionais do Allauth para capturar o email
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
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