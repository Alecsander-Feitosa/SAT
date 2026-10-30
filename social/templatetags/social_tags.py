from django import template

from social import permissoes

register = template.Library()


@register.filter
def pode_excluir(post, user):
    return permissoes.pode_excluir_post(user, post)


@register.filter
def pode_moderar_post(post, user):
    """Pode ocultar comentários deste post (admin, ou moderador/presidente da torcida no feed da torcida)."""
    return permissoes.is_admin_sat(user) or (
        post.visibilidade == 'torcida' and permissoes.pode_moderar_torcida(user, post.torcida))


@register.filter
def curtiu(post, user):
    return any(u.id == user.id for u in post.curtidas.all())


@register.filter
def comentarios_visiveis(post):
    return [c for c in post.comentarios.all() if not c.oculto]


@register.inclusion_tag('social/_selo_autor.html')
def selo_autor(user, tamanho='normal'):
    perfil = getattr(user, 'perfil', None)
    jogo = getattr(user, 'perfil_game', None)
    return {
        'u': user,
        'perfil': perfil,
        'nome': (perfil.vulgo if perfil and perfil.vulgo else None) or user.get_full_name() or user.username,
        'nome_completo': user.get_full_name() or user.username,
        'dev': permissoes.is_desenvolvedor(user),
        'presidente': permissoes.is_presidente(user),
        'nivel': jogo.nivel_numero if jogo else 1,
        'tamanho': tamanho,
    }
