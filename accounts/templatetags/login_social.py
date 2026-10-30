from allauth.socialaccount.adapter import get_adapter
from django import template
from django.conf import settings

register = template.Library()

ORDEM = ['google', 'apple', 'facebook']

# Classes de cada tela onde os botões aparecem
VARIANTES = {
    'pre_login': {
        'grupo': 'flex justify-between w-full',
        'botao': 'w-24 h-16 flex items-center justify-center bg-white rounded-[20px] hover:scale-105 transition-all shadow-md',
        'logo': 'w-12 h-12 object-contain',
    },
    'torcida': {
        'divisor': 'w-full flex items-center justify-center mt-6 mb-4',
        'linha': 'h-px bg-gray-800 flex-grow',
        'texto': 'px-4 text-gray-500 font-black uppercase tracking-widest text-[10px]',
        'grupo': 'flex justify-between w-full gap-2',
        'form': 'flex-1',
        'botao': 'w-full h-14 flex items-center justify-center bg-[#0d1117] border border-gray-800 rounded-xl hover:scale-105 hover:border-[var(--tema-cor)] transition-all shadow-md',
        'logo': 'w-7 h-7 object-contain',
    },
    'padrao': {
        'divisor': 'w-full flex items-center justify-center mt-8 mb-6',
        'linha': 'h-px bg-[#D37129]/30 flex-grow',
        'texto': 'px-4 text-[#D37129]/60 font-black uppercase tracking-widest text-[10px]',
        'grupo': 'flex justify-between w-full gap-3 mb-8',
        'form': 'flex-1',
        'botao': 'w-full h-14 flex items-center justify-center bg-white border-2 border-[#D37129]/20 rounded-xl hover:scale-105 hover:border-[#D37129] transition-all shadow-sm',
        'logo': 'w-7 h-7 object-contain',
        'vazio': 'h-6',
    },
}


@register.inclusion_tag('includes/login_social.html', takes_context=True)
def botoes_login_social(context, variante='padrao'):
    request = context['request']
    provedores = [p for p in get_adapter().list_providers(request) if not p.app.settings.get('hidden')]
    provedores = sorted((p for p in provedores if p.id in ORDEM), key=lambda p: ORDEM.index(p.id))
    return {
        'request': request,
        'csrf_token': context.get('csrf_token'),
        'provedores': provedores,
        'v': VARIANTES[variante],
        # Usado pelo login nativo dentro do app (Capacitor)
        'config_app': {
            'googleWeb': settings.GOOGLE_CLIENT_ID,
            'googleIos': settings.GOOGLE_IOS_CLIENT_ID,
            'appleBundle': settings.APPLE_BUNDLE_ID,
            'appleClientId': next((p.app.client_id for p in provedores if p.id == 'apple'), ''),
        },
    }
