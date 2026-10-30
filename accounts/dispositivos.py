# accounts/dispositivos.py
"""Registro dos aparelhos conectados (Perfil > Segurança > Dispositivos conectados)."""
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone

INTERVALO_ATUALIZACAO = 300  # segundos entre atualizações do "último acesso"


def _ip(request):
    encaminhado = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (encaminhado.split(',')[0].strip() if encaminhado else request.META.get('REMOTE_ADDR')) or None


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    from .models import DispositivoSessao
    if not request.session.session_key:
        request.session.save()
    DispositivoSessao.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={'user': user, 'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300], 'ip': _ip(request),
                  'ultimo_acesso': timezone.now()},
    )


class DispositivoMiddleware:
    """Mantém o 'último acesso' do aparelho atualizado (no máximo a cada 5 min)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and request.session.session_key:
            agora = timezone.now().timestamp()
            chave = request.session.session_key
            # Atualiza a cada 5 min, ou na hora se a chave da sessão mudou (ex: depois de trocar a senha)
            if (agora - request.session.get('dispositivo_ts', 0) > INTERVALO_ATUALIZACAO
                    or request.session.get('dispositivo_chave') != chave):
                from .models import DispositivoSessao
                DispositivoSessao.objects.update_or_create(
                    session_key=request.session.session_key,
                    defaults={'user': user, 'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300],
                              'ip': _ip(request), 'ultimo_acesso': timezone.now()},
                )
                request.session['dispositivo_ts'] = agora
                request.session['dispositivo_chave'] = chave
        return self.get_response(request)


def dispositivos_ativos(user):
    """Aparelhos com sessão ainda válida (limpa os registros de sessões que já expiraram)."""
    from .models import DispositivoSessao
    validas = set(Session.objects.filter(expire_date__gt=timezone.now()).values_list('session_key', flat=True))
    registros = list(DispositivoSessao.objects.filter(user=user))
    expirados = [d.id for d in registros if d.session_key not in validas]
    if expirados:
        DispositivoSessao.objects.filter(id__in=expirados).delete()
    return [d for d in registros if d.session_key in validas]


def encerrar(user, session_keys):
    from .models import DispositivoSessao
    Session.objects.filter(session_key__in=session_keys).delete()
    DispositivoSessao.objects.filter(user=user, session_key__in=session_keys).delete()
