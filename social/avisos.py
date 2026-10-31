# social/avisos.py
"""Pop-ups de aviso, faixa do cabeçalho e avisos automáticos (vencimento do plano)."""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Popup, AvisoCabecalho

DIAS_AVISO_VENCIMENTO = 5   # avisa a partir de 5 dias antes de vencer
DIAS_AVISO_VENCIDO = 7      # e por até 7 dias depois de vencido


def aviso_cabecalho():
    return AvisoCabecalho.objects.filter(ativo=True).first()


def popups_visiveis(user):
    """Pop-ups no ar para este usuário: os da SAT e, se for membro aprovado, os da torcida dele."""
    agora = timezone.now()
    perfil = getattr(user, 'perfil', None)
    alvo = Q(torcida__isnull=True)
    if perfil and perfil.torcida_id and perfil.aprovado:
        alvo |= Q(torcida_id=perfil.torcida_id)
    return (Popup.objects.filter(alvo, ativo=True, exibir_em__lte=agora)
            .filter(Q(exibir_ate__isnull=True) | Q(exibir_ate__gte=agora)))


def proximo_popup(user):
    """O pop-up mais antigo que o usuário ainda não viu (um por vez)."""
    return (popups_visiveis(user).exclude(vistos__usuario=user)
            .select_related('torcida').order_by('exibir_em').first())


def popups_no_dia(torcida, dia, ignorar_id=None):
    """Quantos pop-ups a torcida já programou para aparecer nesse dia (limite de 3)."""
    inicio = timezone.make_aware(datetime.combine(dia, time.min))
    qs = Popup.objects.filter(torcida=torcida, ativo=True, exibir_em__gte=inicio, exibir_em__lt=inicio + timedelta(days=1))
    if ignorar_id:
        qs = qs.exclude(id=ignorar_id)
    return qs.count()


def aviso_vencimento(perfil):
    """{'dias': n, 'plano': nome, 'vencido': bool} quando o plano pago está para vencer ou acabou de vencer."""
    if not perfil:
        return None
    hoje = timezone.localdate()
    vigente = perfil.assinatura_vigente
    if vigente:
        if vigente.valida_ate and (vigente.valida_ate - hoje).days <= DIAS_AVISO_VENCIMENTO:
            return {'dias': (vigente.valida_ate - hoje).days, 'plano': vigente.plano.nome,
                    'data': vigente.valida_ate, 'vencido': False}
        return None
    vencida = (perfil.assinaturas.filter(valida_ate__lt=hoje, valida_ate__gte=hoje - timedelta(days=DIAS_AVISO_VENCIDO))
               .select_related('plano').order_by('-valida_ate').first())
    if vencida:
        return {'dias': (hoje - vencida.valida_ate).days, 'plano': vencida.plano.nome,
                'data': vencida.valida_ate, 'vencido': True}
    return None
