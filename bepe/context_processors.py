from django.conf import settings

from .permissions import is_bepe, torcida_da_diretoria


def acesso_bepe(request):
    """Disponibiliza nos templates: acesso à Área BEPE, canal da diretoria e status da localização."""
    if not request.user.is_authenticated:
        return {'acesso_bepe': False, 'acesso_canal_diretoria': False}

    from .models import Denuncia, Mensagem, LocalizacaoTorcedor

    contexto = {
        'acesso_bepe': is_bepe(request.user),
        'acesso_canal_diretoria': torcida_da_diretoria(request.user) is not None,
    }
    if contexto['acesso_bepe']:
        contexto['bepe_pendencias'] = (
            Denuncia.objects.filter(status='nova').count() +
            Mensagem.objects.filter(do_bepe=False, lida=False).count()
        )

    loc = LocalizacaoTorcedor.objects.filter(user=request.user).only('status').first()
    # None = nunca respondeu; 'ativo' ou 'recusado'
    contexto['localizacao_bepe'] = loc.status if loc else None
    contexto['bepe_intervalo_localizacao'] = getattr(settings, 'BEPE_INTERVALO_LOCALIZACAO', 60)
    return contexto
