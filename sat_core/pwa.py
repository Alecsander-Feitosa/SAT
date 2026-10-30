"""
PWA do SAT: manifest, service worker e página offline.

O service worker precisa ser servido na raiz (/sw.js) para controlar o site
inteiro, por isso ele sai daqui e não de /static/.
"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

# Suba este número sempre que mudar o sw.js ou os arquivos pré-carregados,
# para os aparelhos descartarem o cache antigo.
VERSAO_CACHE = 'sat-v1'


@cache_control(max_age=86400, public=True)
def manifest(request):
    dados = {
        'name': 'SAT - Sócio Torcedor',
        'short_name': 'SAT',
        'id': '/',
        'start_url': '/?origem=app',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'lang': 'pt-BR',
        'background_color': '#1A1A1A',
        'theme_color': '#D37129',
        'icons': [
            {'src': static('img/app/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('img/app/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': static('img/app/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return JsonResponse(dados, content_type='application/manifest+json')


@cache_control(no_cache=True)
def service_worker(request):
    contexto = {
        'versao': VERSAO_CACHE,
        'static_url': settings.STATIC_URL,
        'precache': [
            '/offline/',
            static('img/app/icon-192.png'),
            static('img/logo-shield.png'),
        ],
    }
    resposta = render(request, 'pwa/sw.js', contexto, content_type='application/javascript')
    resposta['Service-Worker-Allowed'] = '/'
    return resposta


def offline(request):
    return render(request, 'pwa/offline.html')
