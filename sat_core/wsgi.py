"""
WSGI config for sat_core project.
"""

import os

from django.core.wsgi import get_wsgi_application

# Aponta para as configurações do nosso projeto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sat_core.settings')

# A variável que o erro diz que está faltando:
application = get_wsgi_application()