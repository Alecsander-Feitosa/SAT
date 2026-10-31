from django.conf import settings

from .permissions import is_bepe, torcida_da_diretoria


def acesso_bepe(request):
    """Disponibiliza nos templates: acesso à Área BEPE, canal da diretoria e status da localização."""
    if not request.user.is_authenticated:
        return {'acesso_bepe': False, 'acesso_canal_diretoria': False}

    from .models import Denuncia, Mensagem, LocalizacaoTorcedor, DocumentoBEPE

    torcida_diretoria = torcida_da_diretoria(request.user)
    contexto = {
        'acesso_bepe': is_bepe(request.user),
        'acesso_canal_diretoria': torcida_diretoria is not None,
    }
    if contexto['acesso_bepe']:
        contexto['bepe_pendencias'] = (
            Denuncia.objects.filter(status='nova').count() +
            Mensagem.objects.filter(do_bepe=False, lida=False).count() +
            DocumentoBEPE.objects.filter(visto_em__isnull=True).count()
        )
    if torcida_diretoria:
        # Mensagens do BEPE ainda não lidas: viram bolinha piscando no menu e pop-up na tela
        nao_lidas = Mensagem.objects.filter(conversa__torcida=torcida_diretoria, do_bepe=True, lida=False)
        contexto['bepe_msgs_diretoria'] = nao_lidas.count()
        if contexto['bepe_msgs_diretoria']:
            contexto['bepe_msg_alerta'] = nao_lidas.select_related('conversa').order_by('-enviada_em').first()

    loc = LocalizacaoTorcedor.objects.filter(user=request.user).only('status').first()
    # None = nunca respondeu; 'ativo' ou 'recusado'
    contexto['localizacao_bepe'] = loc.status if loc else None
    contexto['bepe_intervalo_localizacao'] = getattr(settings, 'BEPE_INTERVALO_LOCALIZACAO', 60)
    return contexto
