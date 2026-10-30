# social/notificacoes.py
"""Criação das notificações do app (sininho no topo)."""
from django.urls import reverse


def notificar(usuario, tipo, texto, ator=None, post=None, link=''):
    from .models import Notificacao
    if ator and ator.id == usuario.id:
        return None  # ninguém é notificado das próprias ações
    if post and not link:
        link = reverse('ver_post', args=[post.id])
    return Notificacao.objects.create(usuario=usuario, ator=ator, tipo=tipo, texto=texto[:255], post=post, link=link)


def notificar_unico(usuario, tipo, texto, ator, post):
    """Evita repetir (ex: curtir, descurtir e curtir de novo não gera 3 avisos)."""
    from .models import Notificacao
    if ator and ator.id == usuario.id:
        return None
    if Notificacao.objects.filter(usuario=usuario, tipo=tipo, ator=ator, post=post).exists():
        return None
    return notificar(usuario, tipo, texto, ator=ator, post=post)


def notificar_muitos(usuarios, tipo, texto, ator=None, post=None, link=''):
    from .models import Notificacao
    if post and not link:
        link = reverse('ver_post', args=[post.id])
    Notificacao.objects.bulk_create([
        Notificacao(usuario=u, ator=ator, tipo=tipo, texto=texto[:255], post=post, link=link)
        for u in usuarios if not ator or u.id != ator.id
    ])


def nome(user):
    perfil = getattr(user, 'perfil', None)
    if perfil and perfil.vulgo:
        return perfil.vulgo
    return user.get_full_name() or user.username
