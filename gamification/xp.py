# gamification/xp.py
"""
Sistema de EXP da SAT: tabela de ações, multiplicador por plano, níveis numéricos e títulos.

Use sempre `conceder_xp(...)`: ele aplica o multiplicador do plano e grava um RegistroXP.
A mesma (ação, referência) nunca rende XP duas vezes — curtir/descurtir em loop não "farma" pontos.
"""
import math

from django.db import IntegrityError, transaction
from django.utils import timezone

# ---------- Tabela de EXP base por ação ----------
XP_ACOES = {
    'curtir': 5,
    'comentar': 15,
    'postar': 40,
    'checkin_diario': 20,
    'evento': 200,
    'caravana': 500,
    'seguir': 15,
    'novo_amigo': 20,
    'compra': 200,
    # Bônus especiais
    'toque_mestre': 100,     # Desenvolvedor curtiu/comentou seu post
    'bencao_lider': 50,      # Presidente da sua torcida curtiu/comentou seu post
}

# ---------- Multiplicador por plano ----------
MULTIPLICADOR_PLANO = {'gratis': 1.0, 'bronze': 1.2, 'prata': 1.5, 'ouro': 2.0}

# ---------- Níveis ----------
# XP total para chegar ao nível n = 25 · n · (n - 1)  →  nível 10 = 2.250 XP, nível 50 = 61.250, nível 100 = 247.500
FATOR_NIVEL = 25

TITULOS = [  # (nível mínimo, título)
    (100, 'Lenda'),
    (76, 'Visionário'),
    (51, 'Embaixador'),
    (31, 'Veterano'),
    (16, 'Desbravador'),
    (6, 'Explorador'),
    (1, 'Recruta'),
]


def xp_para_nivel(n):
    return FATOR_NIVEL * n * (n - 1)


NIVEL_MAXIMO = 100


def nivel_por_xp(xp):
    if xp <= 0:
        return 1
    return min(NIVEL_MAXIMO, max(1, int((1 + math.sqrt(1 + 4 * xp / FATOR_NIVEL)) // 2)))


def titulo_por_nivel(nivel):
    for minimo, titulo in TITULOS:
        if nivel >= minimo:
            return titulo
    return 'Recruta'


def titulo_do_usuario(user, nivel=None):
    """Desenvolvedor e Presidente têm título especial, acima do nível."""
    from social.permissoes import is_desenvolvedor, is_presidente
    if is_desenvolvedor(user):
        return 'Desenvolvedor'
    if is_presidente(user):
        return 'Presidente'
    return titulo_por_nivel(nivel if nivel is not None else nivel_por_xp(_perfil_game(user).xp_total))


def _perfil_game(user):
    from .models import PerfilGamificacao
    perfil, _ = PerfilGamificacao.objects.get_or_create(user=user)
    return perfil


def multiplicador(user):
    perfil = getattr(user, 'perfil', None)
    return MULTIPLICADOR_PLANO.get(perfil.nivel_plano if perfil else 'gratis', 1.0)


def conceder_xp(user, acao, referencia='', bonus=1.0, notificar=False):
    """
    Dá o XP da ação ao usuário (com multiplicador do plano e bônus extra, ex: 1.2 em evento do Presidente).
    Retorna o XP ganho, ou 0 se essa ação/referência já tinha rendido XP antes.
    """
    from .models import RegistroXP
    if not user or not getattr(user, 'is_authenticated', False):
        return 0
    base = XP_ACOES.get(acao, 0)
    if not base:
        return 0
    ganho = round(base * multiplicador(user) * bonus)
    try:
        with transaction.atomic():
            RegistroXP.objects.create(user=user, acao=acao, referencia=str(referencia)[:60], xp=ganho)
            perfil = _perfil_game(user)
            nivel_antes = perfil.nivel_numero
            perfil.xp_total += ganho
            perfil.save(update_fields=['xp_total'])
    except IntegrityError:
        return 0  # já ganhou XP por isso

    from .medalhas import verificar_medalhas
    verificar_medalhas(user)

    nivel_depois = nivel_por_xp(perfil.xp_total)
    if nivel_depois > nivel_antes:
        from social.notificacoes import notificar as enviar
        enviar(user, 'nivel', f'Você subiu para o nível {nivel_depois} — {titulo_por_nivel(nivel_depois)}!')
    elif notificar:
        from social.notificacoes import notificar as enviar
        enviar(user, 'xp', f'+{ganho} EXP: {notificar}')
    return ganho


def checkin_diario(user):
    """Primeiro acesso do dia ao app."""
    return conceder_xp(user, 'checkin_diario', referencia=timezone.localdate().isoformat())


def _bonus_atividade(atividade):
    """+20% se criada por um Presidente; x2 se a equipe SAT (Desenvolvedor) está presente (épico)."""
    from social.permissoes import is_presidente
    bonus = 1.0
    if atividade.criado_por_id and is_presidente(atividade.criado_por):
        bonus *= 1.2
    if atividade.epico:
        bonus *= 2
    return bonus


def _tornar_epico(atividade, desenvolvedor, participantes, nome_tipo, link):
    """Presença VIP: quando um Desenvolvedor participa, a atividade vira épica e todos são avisados."""
    from social.notificacoes import notificar_muitos
    if atividade.epico:
        return
    atividade.epico = True
    atividade.save(update_fields=['epico'])
    titulo = getattr(atividade, 'titulo', str(atividade))
    notificar_muitos(participantes, 'evento_epico',
                     f'⚡ A equipe oficial SAT está presente em "{titulo}"! {nome_tipo} ÉPICO: EXP em dobro.',
                     ator=desenvolvedor, link=link)


def xp_participacao_evento(user, evento):
    from django.contrib.auth.models import User
    from django.db.models import Q
    from django.urls import reverse
    from social.permissoes import is_desenvolvedor
    if is_desenvolvedor(user):
        # Quem confirmou presença ou fez check-in (o projeto tem dois modelos de check-in)
        participantes = User.objects.filter(
            Q(checkins__evento=evento) | Q(checkin__evento=evento) | Q(presenca__evento=evento)
        ).distinct()
        _tornar_epico(evento, user, participantes, 'Evento', reverse('detalhe_evento', args=[evento.id]))
    return conceder_xp(user, 'evento', referencia=evento.id, bonus=_bonus_atividade(evento))


def xp_participacao_caravana(user, caravana):
    from django.contrib.auth.models import User
    from django.urls import reverse
    from social.permissoes import is_desenvolvedor
    if is_desenvolvedor(user):
        participantes = User.objects.filter(presencacaravana__caravana=caravana).distinct()
        _tornar_epico(caravana, user, participantes, 'Caravana', reverse('viagens_view'))
    return conceder_xp(user, 'caravana', referencia=caravana.id, bonus=_bonus_atividade(caravana))
