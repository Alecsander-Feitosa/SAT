# gamification/medalhas.py
"""
Catálogo de medalhas e as regras para ganhar cada uma.
As medalhas aparecem embaixo do nome no Perfil e no Perfil Público.

Para trocar o catálogo, edite a lista MEDALHAS: cada medalha tem um código fixo (não mude o código
de uma medalha que já foi distribuída), nome, descrição, ícone do Bootstrap Icons, cor e a regra.
"""
from django.db.models import Count


def _registros(user, acao):
    from .models import RegistroXP
    return RegistroXP.objects.filter(user=user, acao=acao).count()


def _posts(user):
    from social.models import Post
    return Post.objects.filter(autor_s=user).count()


def _curtidas_recebidas(user):
    from social.models import Post
    return Post.objects.filter(autor_s=user).aggregate(t=Count('curtidas'))['t'] or 0


def _seguidores(user):
    perfil = getattr(user, 'perfil', None)
    return perfil.seguidores.count() if perfil else 0


def _amigos(user):
    from social.permissoes import amigos_ids
    return len(amigos_ids(user))


def _nivel(user):
    from .models import PerfilGamificacao
    jogo = PerfilGamificacao.objects.filter(user=user).first()
    return jogo.nivel_numero if jogo else 1


def _plano(user):
    perfil = getattr(user, 'perfil', None)
    return perfil.nivel_plano if perfil else 'gratis'


def _docs(user):
    perfil = getattr(user, 'perfil', None)
    return perfil.docs_status if perfil else ''


MEDALHAS = [
    {'codigo': 'primeira_voz', 'nome': 'Primeira Voz', 'descricao': 'Fez a primeira publicação', 'icone': 'bi-megaphone-fill', 'cor': '#3b82f6',
     'regra': lambda u: _posts(u) >= 1},
    {'codigo': 'comentarista', 'nome': 'Comentarista', 'descricao': 'Comentou em 50 publicações', 'icone': 'bi-chat-quote-fill', 'cor': '#06b6d4',
     'regra': lambda u: _registros(u, 'comentar') >= 50},
    {'codigo': 'popular', 'nome': 'Popular', 'descricao': 'Recebeu 100 curtidas', 'icone': 'bi-heart-fill', 'cor': '#ef4444',
     'regra': lambda u: _curtidas_recebidas(u) >= 100},
    {'codigo': 'presenca', 'nome': 'Presença Confirmada', 'descricao': 'Participou do primeiro evento', 'icone': 'bi-ticket-perforated-fill', 'cor': '#f59e0b',
     'regra': lambda u: _registros(u, 'evento') >= 1},
    {'codigo': 'fiel', 'nome': 'Fiel', 'descricao': 'Participou de 10 eventos', 'icone': 'bi-shield-fill-check', 'cor': '#d97706',
     'regra': lambda u: _registros(u, 'evento') >= 10},
    {'codigo': 'viajante', 'nome': 'Viajante', 'descricao': 'Foi em 3 caravanas', 'icone': 'bi-bus-front-fill', 'cor': '#16a34a',
     'regra': lambda u: _registros(u, 'caravana') >= 3},
    {'codigo': 'assiduo', 'nome': 'Assíduo', 'descricao': '30 dias de check-in no app', 'icone': 'bi-calendar-check-fill', 'cor': '#8b5cf6',
     'regra': lambda u: _registros(u, 'checkin_diario') >= 30},
    {'codigo': 'resenha', 'nome': 'Resenha', 'descricao': 'Tem 10 amigos', 'icone': 'bi-people-fill', 'cor': '#14b8a6',
     'regra': lambda u: _amigos(u) >= 10},
    {'codigo': 'influente', 'nome': 'Influente', 'descricao': 'Chegou a 50 seguidores', 'icone': 'bi-broadcast', 'cor': '#ec4899',
     'regra': lambda u: _seguidores(u) >= 50},
    {'codigo': 'veterano', 'nome': 'Veterano', 'descricao': 'Alcançou o nível 31', 'icone': 'bi-star-fill', 'cor': '#eab308',
     'regra': lambda u: _nivel(u) >= 31},
    {'codigo': 'lenda', 'nome': 'Lenda', 'descricao': 'Alcançou o nível 100', 'icone': 'bi-trophy-fill', 'cor': '#ca8a04',
     'regra': lambda u: _nivel(u) >= 100},
    {'codigo': 'socio_ouro', 'nome': 'Sócio Ouro', 'descricao': 'Assinante do plano Ouro', 'icone': 'bi-gem', 'cor': '#b8860b',
     'regra': lambda u: _plano(u) == 'ouro'},
    {'codigo': 'verificado', 'nome': 'Verificado', 'descricao': 'Documentos verificados pela torcida', 'icone': 'bi-patch-check-fill', 'cor': '#0ea5e9',
     'regra': lambda u: _docs(u) == 'verificado'},
]
POR_CODIGO = {m['codigo']: m for m in MEDALHAS}


def verificar_medalhas(user):
    """Concede as medalhas que o usuário passou a merecer. Retorna as novas."""
    from .models import MedalhaUsuario
    ja_tem = set(MedalhaUsuario.objects.filter(user=user).values_list('codigo', flat=True))
    novas = []
    for medalha in MEDALHAS:
        if medalha['codigo'] in ja_tem:
            continue
        try:
            ganhou = medalha['regra'](user)
        except Exception:
            ganhou = False
        if ganhou:
            _, criada = MedalhaUsuario.objects.get_or_create(user=user, codigo=medalha['codigo'])
            if criada:
                novas.append(medalha)
    if novas:
        from social.notificacoes import notificar
        for m in novas:
            notificar(user, 'nivel', f'🏅 Nova medalha: {m["nome"]} — {m["descricao"]}', link=f'/social/perfil/{user.id}/')
    return novas


def medalhas_do_usuario(user):
    """Lista (na ordem do catálogo) das medalhas conquistadas, com os dados de exibição."""
    from .models import MedalhaUsuario
    conquistas = {m.codigo: m.conquistada_em for m in MedalhaUsuario.objects.filter(user=user)}
    return [dict(m, conquistada_em=conquistas[m['codigo']]) for m in MEDALHAS if m['codigo'] in conquistas]
