from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from gamification.xp import conceder_xp
from organizadas.models import Evento, Caravana
from .models import Post, Comentario, PostMedia, DenunciaPost, Notificacao, Penalidade, CPFBloqueado
from .notificacoes import notificar, notificar_unico, notificar_muitos, nome
from .permissoes import (
    LIMITE_DENUNCIAS, amigos_ids, banimento, filtro_visiveis, is_admin_sat, is_desenvolvedor, is_presidente,
    pode_excluir_post, pode_moderar_torcida, pode_publicar, pode_ver_post, seguindo_ids,
)


def _ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _voltar(request, padrao='mural'):
    return redirect(request.META.get('HTTP_REFERER') or padrao)


def social_liberado(view):
    """Banidos (ou com CPF na lista negra) não acessam a SAT Social."""
    @wraps(view)
    def _view(request, *args, **kwargs):
        ban = banimento(request.user)
        if ban:
            if _ajax(request):
                return JsonResponse({'sucesso': False, 'erro': 'Conta banida da SAT Social.'}, status=403)
            return render(request, 'social/banido.html', {'ban': ban}, status=403)
        return view(request, *args, **kwargs)
    return _view


def _posts_com_relacoes(qs):
    return qs.select_related(
        'autor_s', 'autor_s__perfil', 'autor_s__perfil__torcida', 'autor_s__perfil_game', 'torcida',
        'evento_relacionado', 'caravana_relacionada', 'foto_relacionada',
    ).prefetch_related(
        'midias', 'curtidas',
        Prefetch('comentarios', queryset=Comentario.objects.select_related('autor', 'autor__perfil').order_by('data')),
    )


def _bonus_de_interacao(ator, post):
    """Toque do Mestre (Desenvolvedor) e Bênção do Líder (Presidente da mesma torcida) para o autor do post."""
    autor = post.autor_s
    if autor.id == ator.id:
        return
    if is_desenvolvedor(ator):
        ganho = conceder_xp(autor, 'toque_mestre', referencia=post.id)
        if ganho:
            notificar(autor, 'xp', f'Toque do Mestre! A equipe SAT notou seu post: +{ganho} EXP', ator=ator, post=post)
    elif is_presidente(ator) and getattr(autor, 'perfil', None) and autor.perfil.torcida_id == ator.perfil.torcida_id:
        ganho = conceder_xp(autor, 'bencao_lider', referencia=post.id)
        if ganho:
            notificar(autor, 'xp', f'Notado pelo Presidente! +{ganho} EXP', ator=ator, post=post)


# ==========================================================
# FEED
# ==========================================================
@login_required
@social_liberado
def mural_social(request):
    user = request.user
    perfil = user.perfil

    # BUSCA DE PERFIS
    query = request.GET.get('q', '').strip()
    usuarios_encontrados = None
    if query:
        usuarios_encontrados = User.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) |
            Q(username__icontains=query) | Q(perfil__vulgo__icontains=query)
        ).exclude(id=user.id).select_related('perfil', 'perfil__torcida')[:30]

    # PUBLICAR
    if request.method == 'POST':
        ok, motivo = pode_publicar(user)
        if not ok:
            messages.error(request, motivo)
            return redirect('mural')

        texto = request.POST.get('texto', '').strip()
        midias = request.FILES.getlist('midias')
        visibilidade = request.POST.get('visibilidade', 'global')
        tipo = request.POST.get('tipo', 'normal')
        if not (texto or midias):
            return redirect('mural')

        if visibilidade not in ('global', 'torcida', 'amigos'):
            visibilidade = 'global'
        if visibilidade == 'torcida' and not perfil.torcida_id:
            visibilidade = 'global'
        # Tipos especiais
        if tipo == 'anuncio' and is_desenvolvedor(user):
            visibilidade = 'global'
        elif tipo == 'convocacao' and is_presidente(user):
            visibilidade = 'torcida'
        else:
            tipo = 'normal'

        novo_post = Post.objects.create(
            autor_s=user, titulo=(texto[:50] + '...') if texto else 'Nova Publicação', texto=texto,
            visibilidade=visibilidade, tipo=tipo,
            torcida=perfil.torcida if visibilidade == 'torcida' else None,
        )
        for index, arquivo in enumerate(midias):
            is_video = arquivo.name.lower().endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv'))
            midia = PostMedia.objects.create(post=novo_post, arquivo=arquivo, is_video=is_video)
            if index == 0 and not is_video:
                # Reaproveita o arquivo já enviado: reenviar o upload (já lido até o fim) quebra no Cloudinary
                novo_post.imagem = midia.arquivo.name
                novo_post.save(update_fields=['imagem'])

        ganho = conceder_xp(user, 'postar', referencia=novo_post.id)
        if tipo == 'convocacao':
            membros = User.objects.filter(perfil__torcida=perfil.torcida)
            notificar_muitos(membros, 'convocacao', f'📣 Convocação de {nome(user)}: {texto[:120]}', ator=user, post=novo_post)
            messages.success(request, f'Convocação enviada para todos da {perfil.torcida.nome}!')
        else:
            messages.success(request, f'Publicação criada! +{ganho} EXP' if ganho else 'Publicação criada!')
        return redirect(f"/social/mural/?aba={'torcida' if visibilidade == 'torcida' else 'global'}")

    # ABAS
    aba = request.GET.get('aba', 'global')
    lembretes = []
    visiveis = filtro_visiveis(user)
    anuncios = Post.objects.none()

    if aba == 'torcida' and perfil.torcida_id:
        posts = Post.objects.filter(visiveis, visibilidade='torcida', torcida_id=perfil.torcida_id)
        agora = timezone.now()
        eventos = list(Evento.objects.filter(torcida=perfil.torcida, data__gte=agora).order_by('data')[:5])
        caravanas = list(Caravana.objects.filter(torcida=perfil.torcida, saida_horario__gte=agora).order_by('saida_horario')[:5])
        lembretes = sorted(eventos + caravanas, key=lambda x: getattr(x, 'data', None) or x.saida_horario)[:5]
    else:
        aba = 'global'
        # Global = posts globais + posts "só amigos" de quem é seu amigo
        posts = Post.objects.filter(visiveis, Q(visibilidade='global') | Q(visibilidade='amigos'))
        # Anúncios oficiais dos Desenvolvedores ficam fixados no topo
        anuncios = _posts_com_relacoes(posts.filter(tipo='anuncio').order_by('-data_criacao'))[:3]
        posts = posts.exclude(id__in=[a.id for a in anuncios])

    posts = _posts_com_relacoes(posts.order_by('-data_criacao'))[:30]

    return render(request, 'mural.html', {
        'posts': posts,
        'anuncios': anuncios,
        'aba_atual': aba,
        'lembretes': lembretes,
        'query': query,
        'usuarios_encontrados': usuarios_encontrados,
        'eh_desenvolvedor': is_desenvolvedor(user),
        'eh_presidente': is_presidente(user),
    })


@login_required
@social_liberado
def ver_post(request, post_id):
    post = get_object_or_404(_posts_com_relacoes(Post.objects.all()), id=post_id)
    if not pode_ver_post(request.user, post):
        messages.error(request, 'Você não tem acesso a esta publicação.')
        return redirect('mural')
    return render(request, 'social/post_detalhe.html', {'post': post})


# ==========================================================
# INTERAÇÕES
# ==========================================================
@login_required
@social_liberado
@require_POST
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if not pode_ver_post(request.user, post):
        return JsonResponse({'sucesso': False}, status=403) if _ajax(request) else redirect('mural')

    if post.curtidas.filter(id=request.user.id).exists():
        post.curtidas.remove(request.user)
        liked = False
    else:
        post.curtidas.add(request.user)
        liked = True
        if post.autor_s_id != request.user.id:
            conceder_xp(request.user, 'curtir', referencia=post.id)
            notificar_unico(post.autor_s, 'curtida', f'{nome(request.user)} curtiu sua publicação', request.user, post)
            _bonus_de_interacao(request.user, post)

    if _ajax(request):
        return JsonResponse({'likes_count': post.curtidas.count(), 'liked': liked})
    return _voltar(request)


@login_required
@social_liberado
@require_POST
def adicionar_comentario(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    texto = (request.POST.get('comentario') or request.POST.get('texto') or '').strip()
    ok, motivo = pode_publicar(request.user)
    if not ok or not texto or not pode_ver_post(request.user, post):
        erro = motivo or 'Comentário inválido.'
        if _ajax(request):
            return JsonResponse({'sucesso': False, 'erro': erro}, status=403)
        messages.error(request, erro)
        return _voltar(request)

    comentario = Comentario.objects.create(post=post, autor=request.user, texto=texto)
    if post.autor_s_id != request.user.id:
        conceder_xp(request.user, 'comentar', referencia=post.id)
        notificar(post.autor_s, 'comentario', f'{nome(request.user)} comentou: "{texto[:80]}"', ator=request.user, post=post)
        _bonus_de_interacao(request.user, post)

    if _ajax(request):
        foto = request.user.perfil.foto.url if request.user.perfil.foto else ''
        return JsonResponse({
            'sucesso': True,
            'comentario_id': comentario.id,
            'total_comentarios': post.comentarios.filter(oculto=False).count(),
            'nome_autor': nome(request.user),
            'texto': comentario.texto,
            'foto_autor': foto,
        })
    return _voltar(request)


@login_required
@require_POST
def remover_comentario(request, comentario_id):
    """O autor apaga o próprio comentário; moderadores da torcida/admins ocultam."""
    comentario = get_object_or_404(Comentario.objects.select_related('post', 'post__torcida'), id=comentario_id)
    post = comentario.post
    if comentario.autor_id == request.user.id:
        comentario.delete()
    elif is_admin_sat(request.user) or (post.visibilidade == 'torcida' and pode_moderar_torcida(request.user, post.torcida)):
        comentario.oculto = True
        comentario.save(update_fields=['oculto'])
        notificar(comentario.autor, 'moderacao', 'Um comentário seu foi ocultado pela moderação.', post=post)
    else:
        messages.error(request, 'Sem permissão.')
    if _ajax(request):
        return JsonResponse({'sucesso': True})
    return _voltar(request)


@login_required
@require_POST
def excluir_post(request, post_id):
    post = get_object_or_404(Post.objects.select_related('torcida'), id=post_id)
    if not pode_excluir_post(request.user, post):
        messages.error(request, 'Você não tem permissão para excluir esta publicação.')
        return _voltar(request)
    if post.autor_s_id != request.user.id:
        notificar(post.autor_s, 'moderacao', 'Uma publicação sua foi removida pela moderação.')
    post.delete()
    messages.success(request, 'Publicação excluída.')
    return _voltar(request)


@login_required
@social_liberado
@require_POST
def denunciar_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    motivo = request.POST.get('motivo', 'outro')
    if motivo not in dict(DenunciaPost.MOTIVOS):
        motivo = 'outro'
    if post.autor_s_id == request.user.id or not pode_ver_post(request.user, post):
        messages.error(request, 'Não é possível denunciar esta publicação.')
        return _voltar(request)

    _, criada = DenunciaPost.objects.get_or_create(
        post=post, autor=request.user, defaults={'motivo': motivo, 'detalhe': request.POST.get('detalhe', '')[:300]}
    )
    if criada and not post.em_revisao and post.denuncias.count() >= LIMITE_DENUNCIAS:
        post.em_revisao = True
        post.save(update_fields=['em_revisao'])
        notificar_muitos(User.objects.filter(is_superuser=True), 'moderacao',
                         f'Post de {nome(post.autor_s)} atingiu {LIMITE_DENUNCIAS} denúncias e saiu do ar para revisão.',
                         post=post, link='/social/moderacao/')
    messages.success(request, 'Denúncia enviada. Obrigado por ajudar a manter a SAT Social segura.'
                     if criada else 'Você já denunciou esta publicação.')
    return _voltar(request)


@login_required
@social_liberado
@require_POST
def seguir_usuario(request, usuario_id):
    alvo = get_object_or_404(User.objects.select_related('perfil'), id=usuario_id)
    eu = request.user
    seguindo = False
    if eu != alvo and hasattr(alvo, 'perfil'):
        if alvo.perfil.seguidores.filter(id=eu.id).exists():
            alvo.perfil.seguidores.remove(eu)
        else:
            alvo.perfil.seguidores.add(eu)
            seguindo = True
            conceder_xp(eu, 'seguir', referencia=alvo.id)
            if eu.perfil.seguidores.filter(id=alvo.id).exists():  # seguem um ao outro: viraram amigos
                conceder_xp(eu, 'novo_amigo', referencia=alvo.id)
                conceder_xp(alvo, 'novo_amigo', referencia=eu.id)
                notificar(alvo, 'amigo', f'Você e {nome(eu)} agora são amigos!', ator=eu, link=f'/social/perfil/{eu.id}/')
            else:
                notificar(alvo, 'seguidor', f'{nome(eu)} começou a seguir você', ator=eu, link=f'/social/perfil/{eu.id}/')

    if _ajax(request):
        return JsonResponse({'seguindo': seguindo, 'seguidores': alvo.perfil.seguidores.count()})
    return _voltar(request)


@login_required
@social_liberado
def compartilhar_item(request, tipo_item, item_id):
    from organizadas.models import ConquistaTorcida, FotoGaleria

    if request.method != 'POST':
        return _voltar(request)
    ok, motivo = pode_publicar(request.user)
    if not ok:
        messages.error(request, motivo)
        return _voltar(request)

    visibilidade = request.POST.get('visibilidade', 'global')
    perfil = request.user.perfil
    if visibilidade not in ('global', 'torcida', 'amigos') or (visibilidade == 'torcida' and not perfil.torcida_id):
        visibilidade = 'global'
    novo_post = Post(
        autor_s=request.user, texto=request.POST.get('texto', ''),
        titulo=f"Compartilhou um(a) {tipo_item.capitalize()}",
        visibilidade=visibilidade, torcida=perfil.torcida if visibilidade == 'torcida' else None,
    )
    relacoes = {
        'evento': ('evento_relacionado', Evento), 'caravana': ('caravana_relacionada', Caravana),
        'conquista': ('conquista_relacionada', ConquistaTorcida), 'foto': ('foto_relacionada', FotoGaleria),
    }
    if tipo_item not in relacoes:
        messages.error(request, "Tipo de item inválido.")
        return _voltar(request)
    campo, modelo = relacoes[tipo_item]
    setattr(novo_post, campo, get_object_or_404(modelo, id=item_id))
    novo_post.save()
    conceder_xp(request.user, 'postar', referencia=novo_post.id)
    messages.success(request, f'{tipo_item.capitalize()} compartilhado(a) no mural com sucesso!')
    return redirect('mural')


# ==========================================================
# PERFIL PÚBLICO
# ==========================================================
def render_perfil(request, alvo):
    """
    Perfil e Perfil Público são a MESMA tela. Quando quem vê é o dono, aparecem também
    a carteirinha e as configurações da conta.
    """
    from gamification.medalhas import medalhas_do_usuario, verificar_medalhas
    from gamification.models import PerfilGamificacao
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=alvo)
    eh_dono = alvo.id == request.user.id
    if eh_dono:
        verificar_medalhas(alvo)  # garante medalhas de quem já cumpria as regras antes do sistema existir

    # Só os posts que QUEM ESTÁ VENDO pode ver (posts da torcida não vazam para outras torcidas)
    posts = _posts_com_relacoes(
        Post.objects.filter(filtro_visiveis(request.user), autor_s=alvo).order_by('-data_criacao')
    )
    eu_sigo = alvo.perfil.seguidores.filter(id=request.user.id).exists()
    me_segue = request.user.perfil.seguidores.filter(id=alvo.id).exists()

    contexto = {
        'usuario_alvo': alvo,
        'perfil_game': perfil_game,
        'medalhas': medalhas_do_usuario(alvo),
        'posts': posts,
        'total_posts': posts.count(),
        'total_seguidores': alvo.perfil.seguidores.count(),
        'total_seguindo': len(seguindo_ids(alvo)),
        'total_amigos': len(amigos_ids(alvo)),
        'eu_sigo': eu_sigo,
        'me_segue': me_segue,
        'amigos': eu_sigo and me_segue,
        'eh_dono': eh_dono,
    }
    if eh_dono:
        from django.conf import settings
        from accounts.views import contexto_carteirinha
        contexto.update(contexto_carteirinha(alvo.perfil, request))
        torcida = alvo.perfil.torcida
        contexto['whatsapp_suporte'] = ''.join(c for c in ((torcida.whatsapp_suporte if torcida else '') or
                                                         getattr(settings, 'SAT_WHATSAPP_SUPORTE', '')) if c.isdigit())
    return render(request, 'perfil_publico.html', contexto)


@login_required
@social_liberado
def perfil_publico(request, user_id):
    alvo = get_object_or_404(User.objects.select_related('perfil', 'perfil__torcida'), id=user_id)
    return render_perfil(request, alvo)


@login_required
@social_liberado
def conexoes(request, user_id):
    """Seguidores, seguindo e amigos de um perfil. O dono pode remover seguidores e seguir de volta."""
    alvo = get_object_or_404(User.objects.select_related('perfil'), id=user_id)
    aba = request.GET.get('aba', 'seguidores')
    seguidores = set(alvo.perfil.seguidores.values_list('id', flat=True))
    seguindo = seguindo_ids(alvo)
    ids = {'seguidores': seguidores, 'seguindo': seguindo, 'amigos': seguidores & seguindo}.get(aba, seguidores)
    meus_seguindo = seguindo_ids(request.user)
    pessoas = User.objects.filter(id__in=ids).select_related('perfil', 'perfil__torcida', 'perfil_game').order_by('first_name', 'username')
    return render(request, 'social/conexoes.html', {
        'usuario_alvo': alvo,
        'aba': aba,
        'pessoas': pessoas,
        'meus_seguindo': meus_seguindo,
        'eh_dono': alvo.id == request.user.id,
        'totais': {'seguidores': len(seguidores), 'seguindo': len(seguindo), 'amigos': len(seguidores & seguindo)},
    })


@login_required
@require_POST
def remover_seguidor(request, usuario_id):
    """Tira alguém da lista dos MEUS seguidores (a amizade também se desfaz)."""
    request.user.perfil.seguidores.remove(usuario_id)
    messages.success(request, 'Seguidor removido.')
    return _voltar(request)


# ==========================================================
# NOTIFICAÇÕES
# ==========================================================
@login_required
def notificacoes(request):
    lista = Notificacao.objects.filter(usuario=request.user).select_related('ator', 'ator__perfil')[:60]
    resposta = render(request, 'social/notificacoes.html', {'notificacoes': lista})
    Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
    return resposta


# ==========================================================
# MODERAÇÃO (administradores da SAT)
# ==========================================================
@login_required
def moderacao(request):
    if not is_admin_sat(request.user):
        messages.error(request, 'Acesso restrito aos administradores da SAT.')
        return redirect('mural')

    if request.method == 'POST':
        _aplicar_moderacao(request)
        return redirect('moderacao_social')

    denunciados = _posts_com_relacoes(
        Post.objects.annotate(total_denuncias=Count('denuncias')).filter(Q(total_denuncias__gt=0) | Q(em_revisao=True))
        .order_by('-em_revisao', '-total_denuncias')
    ).prefetch_related('denuncias__autor')[:50]
    agora = timezone.now()
    penalidades = Penalidade.objects.filter(revogada=False).filter(Q(fim__isnull=True) | Q(fim__gt=agora)).select_related('user')
    return render(request, 'social/moderacao.html', {
        'denunciados': denunciados,
        'penalidades': penalidades,
        'cpfs': CPFBloqueado.objects.order_by('-criado_em')[:50],
        'limite': LIMITE_DENUNCIAS,
    })


def _aplicar_moderacao(request):
    acao = request.POST.get('acao')
    admin = request.user

    if acao == 'revogar':
        pen = get_object_or_404(Penalidade, id=request.POST.get('penalidade_id'))
        pen.revogada = True
        pen.save(update_fields=['revogada'])
        if pen.tipo == 'ban':
            cpf = ''.join(c for c in (pen.user.perfil.cpf or '') if c.isdigit())
            CPFBloqueado.objects.filter(cpf=cpf).delete()
        notificar(pen.user, 'moderacao', f'Sua penalidade ({pen.get_tipo_display().lower()}) foi revogada.')
        messages.success(request, 'Penalidade revogada.')
        return

    post = get_object_or_404(Post, id=request.POST.get('post_id'))
    autor = post.autor_s

    if acao == 'manter':
        post.denuncias.all().delete()
        post.em_revisao = False
        post.save(update_fields=['em_revisao'])
        messages.success(request, 'Post mantido e denúncias arquivadas.')
        return

    # Daqui pra baixo o post é removido; opcionalmente o autor é penalizado
    motivo = request.POST.get('motivo', '').strip() or 'Violação das regras da SAT Social'
    dias = request.POST.get('dias', '')
    fim = timezone.now() + timedelta(days=int(dias)) if dias.isdigit() and int(dias) > 0 else None
    post.delete()

    if acao == 'excluir':
        notificar(autor, 'moderacao', f'Sua publicação foi removida: {motivo}')
        messages.success(request, 'Post excluído.')
    elif acao == 'suspender':
        fim = fim or timezone.now() + timedelta(days=7)
        Penalidade.objects.create(user=autor, tipo='suspensao', motivo=motivo, fim=fim, aplicada_por=admin)
        notificar(autor, 'moderacao', f'Post removido e você está suspenso de publicar até {timezone.localtime(fim):%d/%m/%Y}. Motivo: {motivo}')
        messages.success(request, f'Post excluído e {nome(autor)} suspenso até {timezone.localtime(fim):%d/%m/%Y}.')
    elif acao == 'banir':
        Penalidade.objects.create(user=autor, tipo='ban', motivo=motivo, fim=fim, aplicada_por=admin)
        cpf = ''.join(c for c in (autor.perfil.cpf or '') if c.isdigit())
        if cpf:
            CPFBloqueado.objects.update_or_create(cpf=cpf, defaults={'motivo': motivo, 'ate': fim, 'criado_por': admin})
        quando = f'até {timezone.localtime(fim):%d/%m/%Y}' if fim else 'permanentemente'
        notificar(autor, 'moderacao', f'Sua conta foi banida da SAT Social {quando}. Motivo: {motivo}')
        messages.success(request, f'{nome(autor)} banido {quando}' + (' (CPF na lista negra).' if cpf else '.'))
