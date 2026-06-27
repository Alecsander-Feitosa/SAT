from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Post, Comentario, PostMedia
from organizadas.models import Evento, Caravana

@login_required
def mural_social(request):
    # LÓGICA DE BUSCA
    query = request.GET.get('q', '').strip()
    usuarios_encontrados = None
    if query:
        from django.db.models import Q
        usuarios_encontrados = User.objects.filter(
            Q(first_name__icontains=query) | Q(username__icontains=query)
        ).exclude(id=request.user.id).select_related('perfil', 'perfil__torcida')[:30]

    # LÓGICA DAS ABAS (Filtro do Feed)
    aba = request.GET.get('aba', 'global')
    lembretes = []
    
    if aba == 'torcida' and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        # Mostra apenas posts direcionados à torcida do usuário
        posts = Post.objects.filter(
            torcida=request.user.perfil.torcida
        ).select_related('autor_s', 'autor_s__perfil', 'evento_relacionado').prefetch_related(
            'midias', 'curtidas', 'comentarios', 'comentarios__autor', 'comentarios__autor__perfil'
        ).order_by('-data_criacao')[:30]
        
        # LEMBRETES DE EVENTOS/CARAVANAS/REUNIÕES DA TORCIDA
        agora = timezone.now()
        torcida_usuario = request.user.perfil.torcida
        eventos = list(Evento.objects.filter(torcida=torcida_usuario, data__gte=agora).order_by('data')[:5])
        caravanas = list(Caravana.objects.filter(torcida=torcida_usuario, saida_horario__gte=agora).order_by('saida_horario')[:5])
        
        lembretes = eventos + caravanas
        lembretes.sort(key=lambda x: getattr(x, 'data', getattr(x, 'saida_horario', agora)))
        lembretes = lembretes[:5]
        
    else:
        # Mostra os posts globais (onde torcida é vazia).
        posts = Post.objects.filter(
            torcida__isnull=True
        ).select_related('autor_s', 'autor_s__perfil', 'evento_relacionado').prefetch_related(
            'midias', 'curtidas', 'comentarios', 'comentarios__autor', 'comentarios__autor__perfil'
        ).order_by('-data_criacao')[:30]
    
    # LÓGICA DE CRIAR NOVO POST
    if request.method == 'POST':
        texto = request.POST.get('texto', '')
        midias = request.FILES.getlist('midias')
        
        # NOVA LÓGICA: Captura a visibilidade escolhida
        visibilidade = request.POST.get('visibilidade', 'global')
        
        if texto or midias:
            titulo_gerado = texto[:50] + "..." if texto else "Nova Publicação"
            
            try:
                novo_post = Post(
                    autor_s=request.user, 
                    titulo=titulo_gerado,
                    texto=texto,
                )
                
                # Salva vinculado à torcida APENAS se ele selecionou a aba da torcida
                if visibilidade == 'torcida' and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                    novo_post.torcida = request.user.perfil.torcida
                else:
                    # Se for global, a torcida fica vazia (null)
                    novo_post.torcida = None
                    
                novo_post.save()

                # Processa os arquivos enviados (imagens/vídeos)
                for index, arquivo in enumerate(midias):
                    is_video = arquivo.name.lower().endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv'))
                    PostMedia.objects.create(post=novo_post, arquivo=arquivo, is_video=is_video)
                    
                    # Salva a primeira imagem no campo antigo por compatibilidade (opcional)
                    if index == 0 and not is_video:
                        novo_post.imagem = arquivo
                        novo_post.save()

                messages.success(request, 'Publicação criada com sucesso!')
            except Exception as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
                
            return redirect(f"/social/mural/?aba={visibilidade}") # Redireciona para a aba que ele postou
            
    context = {
        'posts': posts,
        'aba_atual': aba,
        'lembretes': lembretes,
        'query': query,
        'usuarios_encontrados': usuarios_encontrados,
    }
    return render(request, 'mural.html', context)

@login_required
def excluir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Validação de Segurança: Apenas o dono do post ou um Admin (staff) pode apagar
    if request.user == post.autor_s or request.user.is_staff:
        post.delete()
        messages.success(request, 'Publicação excluída com sucesso.')
    else:
        messages.error(request, 'Você não tem permissão para excluir esta publicação.')
        
    return redirect(request.META.get('HTTP_REFERER', 'mural'))

@login_required
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    
    try:
        if request.user in post.curtidas.all():
            post.curtidas.remove(request.user)
            liked = False
        else:
            post.curtidas.add(request.user)
            liked = True
            
        if is_ajax:
            return JsonResponse({
                'likes_count': post.curtidas.count(),
                'liked': liked
            })
    except Exception as e:
        if is_ajax:
            return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)
            
    return redirect('mural')

@login_required
def adicionar_comentario(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        texto = request.POST.get('comentario') or request.POST.get('texto') 
        
        if texto:
            try:
                comentario = Comentario.objects.create(
                    post=post,
                    autor=request.user,
                    texto=texto
                )
                
                if is_ajax:
                    foto_url = ""
                    try:
                        if hasattr(request.user, 'perfil') and request.user.perfil.foto:
                            foto_url = request.user.perfil.foto.url
                    except ValueError:
                        foto_url = "" 
                        
                    return JsonResponse({
                        'sucesso': True,
                        'total_comentarios': post.comentarios.count(),
                        'nome_autor': request.user.get_full_name() or request.user.username,
                        'texto': comentario.texto,
                        'foto_autor': foto_url
                    })
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)
                
    return redirect('mural')

@login_required
def seguir_usuario(request, usuario_id):
    usuario_alvo = get_object_or_404(User, id=usuario_id)
    
    if request.user != usuario_alvo and hasattr(usuario_alvo, 'perfil'):
        if request.user in usuario_alvo.perfil.seguidores.all():
            usuario_alvo.perfil.seguidores.remove(request.user)
        else:
            usuario_alvo.perfil.seguidores.add(request.user)
            
    return redirect(request.META.get('HTTP_REFERER', 'mural'))

@login_required
def compartilhar_item(request, tipo_item, item_id):
    # Importação local para evitar importações circulares
    from organizadas.models import Evento, Caravana, ConquistaTorcida, FotoGaleria
    
    if request.method == 'POST':
        texto_usuario = request.POST.get('texto', '')
        visibilidade = request.POST.get('visibilidade', 'global')
        
        # Cria a base da publicação
        novo_post = Post(
            autor_s=request.user,
            texto=texto_usuario,
            titulo=f"Compartilhou um(a) {tipo_item.capitalize()}"
        )
        
        # Define se é global ou apenas para a torcida
        if visibilidade == 'torcida' and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            novo_post.torcida = request.user.perfil.torcida
            
        # Anexa o item correspondente baseado no tipo
        if tipo_item == 'evento':
            novo_post.evento_relacionado = get_object_or_404(Evento, id=item_id)
        elif tipo_item == 'caravana':
            novo_post.caravana_relacionada = get_object_or_404(Caravana, id=item_id)
        elif tipo_item == 'conquista':
            novo_post.conquista_relacionada = get_object_or_404(ConquistaTorcida, id=item_id)
        elif tipo_item == 'foto':
            novo_post.foto_relacionada = get_object_or_404(FotoGaleria, id=item_id)
        else:
            messages.error(request, "Tipo de item inválido.")
            return redirect(request.META.get('HTTP_REFERER', 'mural'))

        novo_post.save()
        messages.success(request, f'{tipo_item.capitalize()} compartilhado(a) no mural com sucesso!')
        return redirect('mural') # Redireciona para o mural
        
    return redirect(request.META.get('HTTP_REFERER', 'mural'))

@login_required
def perfil_publico(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    
    # Busca apenas os posts na timeline que esse usuário é o autor
    posts = Post.objects.filter(autor_s=usuario_alvo).order_by('-data_criacao')
    
    context = {
        'usuario_alvo': usuario_alvo,
        'posts': posts,
    }
    return render(request, 'perfil_publico.html', context)