# social/permissoes.py
"""Quem vê, quem modera e quem está punido na SAT Social."""
from django.db.models import Q
from django.utils import timezone

LIMITE_DENUNCIAS = 5  # a partir daqui o post sai do ar e vai para revisão dos administradores


def _perfil(user):
    return getattr(user, 'perfil', None) if user and user.is_authenticated else None


def is_admin_sat(user):
    """Administradores da SAT: excluem qualquer post e aplicam penalidades."""
    return bool(user and user.is_authenticated and user.is_superuser)


def is_desenvolvedor(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.cargo_especial == 'desenvolvedor')


def is_presidente(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.cargo_especial == 'presidente' and perfil.torcida_id)


def pode_moderar_torcida(user, torcida):
    """Admin SAT, ou moderador/presidente DA PRÓPRIA torcida."""
    if not torcida:
        return False
    if is_admin_sat(user):
        return True
    perfil = _perfil(user)
    if not perfil or perfil.torcida_id != torcida.id:
        return False
    return user.is_staff or perfil.cargo_especial == 'presidente'


def pode_excluir_post(user, post):
    if post.autor_s_id == user.id or is_admin_sat(user):
        return True
    # Moderadores só apagam o que foi postado no feed da torcida deles
    return post.visibilidade == 'torcida' and pode_moderar_torcida(user, post.torcida)


# ---------- Amizade (seguir em mão dupla) ----------
def seguindo_ids(user):
    """IDs dos usuários que `user` segue (user está em perfil.seguidores deles)."""
    from accounts.models import Perfil
    return set(Perfil.objects.filter(seguidores=user).values_list('user_id', flat=True))


def amigos_ids(user):
    perfil = _perfil(user)
    if not perfil:
        return set()
    seguidores = set(perfil.seguidores.values_list('id', flat=True))
    return seguidores & seguindo_ids(user)


def sao_amigos(a, b):
    return a.id in amigos_ids(b)


# ---------- O que cada usuário pode ver ----------
def filtro_visiveis(user):
    """Q() com todos os posts que `user` pode ver (respeita torcida, amigos e revisão)."""
    perfil = _perfil(user)
    filtro = Q(visibilidade='global')
    filtro |= Q(visibilidade='amigos', autor_s_id__in=amigos_ids(user) | {user.id})
    if perfil and perfil.torcida_id:
        filtro |= Q(visibilidade='torcida', torcida_id=perfil.torcida_id)
    filtro |= Q(autor_s=user)  # o autor sempre vê os próprios posts
    # Em revisão: só o autor e os administradores enxergam
    if not is_admin_sat(user):
        filtro &= Q(em_revisao=False) | Q(autor_s=user)
    return filtro


def pode_ver_post(user, post):
    from .models import Post
    return Post.objects.filter(filtro_visiveis(user), pk=post.pk).exists()


# ---------- Penalidades e lista negra ----------
def _cpf_numeros(user):
    perfil = _perfil(user)
    return ''.join(c for c in (perfil.cpf or '') if c.isdigit()) if perfil else ''


def penalidade_ativa(user, tipo):
    from .models import Penalidade
    agora = timezone.now()
    return (Penalidade.objects.filter(user=user, tipo=tipo, revogada=False, inicio__lte=agora)
            .filter(Q(fim__isnull=True) | Q(fim__gt=agora)).order_by('-fim').first())


def banimento(user):
    """Penalidade de ban ativa, ou o registro do CPF na lista negra. None se liberado."""
    if not user.is_authenticated:
        return None
    ban = penalidade_ativa(user, 'ban')
    if ban:
        return ban
    from .models import CPFBloqueado
    cpf = _cpf_numeros(user)
    if cpf:
        bloqueio = CPFBloqueado.objects.filter(cpf=cpf).first()
        if bloqueio and bloqueio.ativo:
            return bloqueio
    return None


def suspensao(user):
    return penalidade_ativa(user, 'suspensao')


def pode_publicar(user):
    """(pode, motivo) — bloqueia banidos e suspensos de postar/comentar."""
    ban = banimento(user)
    if ban:
        return False, 'Sua conta está banida da SAT Social.'
    susp = suspensao(user)
    if susp:
        ate = f" até {timezone.localtime(susp.fim):%d/%m/%Y %H:%M}" if susp.fim else ''
        return False, f'Você está suspenso de publicar{ate}.'
    return True, ''
