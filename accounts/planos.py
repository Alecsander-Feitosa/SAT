# accounts/planos.py
"""Regras dos planos oficiais SAT (Grátis, Bronze, Prata, Ouro) e seus benefícios."""
from datetime import timedelta

from django.utils import timezone

from . import clube_ben
from .models import PlanoSocio, BeneficioTorcida, Assinatura, NIVEIS_PLANO, ORDEM_NIVEL

DIAS_VALIDADE = 30


def planos_oficiais():
    return PlanoSocio.objects.filter(torcida__isnull=True, nivel__isnull=False, ativo=True).order_by('preco')


def nivel_libera(nivel_usuario, nivel_minimo):
    return ORDEM_NIVEL.get(nivel_usuario, 0) >= ORDEM_NIVEL.get(nivel_minimo, 0)


def beneficios_por_nivel(torcida=None):
    """
    Lista de benefícios agrupada por nível, já cumulativa (o Ouro inclui tudo dos anteriores).
    Retorna: [{'nivel', 'nome', 'plano', 'oficiais': [...], 'torcida': [BeneficioTorcida...]}]
    """
    planos = {p.nivel: p for p in planos_oficiais()}
    extras = list(BeneficioTorcida.objects.filter(torcida=torcida, ativo=True)) if torcida else []
    resultado = []
    for nivel, nome in NIVEIS_PLANO:
        plano = planos.get(nivel)
        resultado.append({
            'nivel': nivel,
            'nome': nome,
            'plano': plano,
            'oficiais': plano.get_beneficios_lista() if plano else [],
            'torcida': [b for b in extras if b.nivel_minimo == nivel],
        })
    return resultado


def ativar_assinatura(assinatura):
    """
    Chamado quando o pagamento é confirmado (ou na hora, para o plano grátis).
    Encerra as outras assinaturas do sócio, define a validade e sincroniza com o club_ben.
    """
    perfil = assinatura.perfil
    Assinatura.objects.filter(perfil=perfil, ativa=True).exclude(id=assinatura.id).update(ativa=False)

    if assinatura.plano.gratuito:
        assinatura.valida_ate = None
    else:
        # Renovação antes de vencer soma os dias ao período atual
        base = max(assinatura.valida_ate or timezone.localdate(), timezone.localdate())
        assinatura.valida_ate = base + timedelta(days=DIAS_VALIDADE)
    assinatura.ativa = True
    assinatura.save()

    if hasattr(perfil, '_assinatura_vigente'):
        del perfil._assinatura_vigente
    clube_ben.sincronizar_membro(perfil)
    return assinatura


def confirmar_pagamento_fatura(fatura, metodo='PIX'):
    """Marca a fatura como paga e ativa/renova a assinatura. Idempotente."""
    if fatura.status == 'pago':
        return False
    fatura.status = 'pago'
    fatura.metodo_pagamento = metodo
    fatura.data_pagamento = timezone.now()
    fatura.save()
    ativar_assinatura(fatura.assinatura)
    return True
