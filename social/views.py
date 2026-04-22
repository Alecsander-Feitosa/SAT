from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Post, Comentario

@login_required
def mural_social(request):
    # LÓGICA DAS ABAS (Filtro do Feed)
    aba = request.GET.get('aba', 'global')
    
    if aba == 'torcida' and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        # Mostra apenas posts direcionados à torcida do usuário
        posts = Post.objects.filter(torcida=request.user.perfil.torcida).order_by('-data_criacao')
    else:
        # Mostra os posts globais (onde torcida é vazia) OU todos. 
        # Aqui deixaremos exibir todos no global para a timeline ficar movimentada.
        posts = Post.objects.all().order_by('-data_criacao')
    
    # LÓGICA DE CRIAR NOVO POST
    if request.method == 'POST':
        texto = request.POST.get('texto', '')
        imagem = request.FILES.get('imagem')
        
        # NOVA LÓGICA: Captura a visibilidade escolhida
        visibilidade = request.POST.get('visibilidade', 'global')
        
        if texto or imagem:
            titulo_gerado = texto[:50] + "..." if texto else "Publicação com Imagem"
            
            try:
                novo_post = Post(
                    autor_s=request.user, 
                    titulo=titulo_gerado,
                    texto=texto, 
                    imagem=imagem
                )
                
                # Salva vinculado à torcida APENAS se ele selecionou a aba da torcida
                if visibilidade == 'torcida' and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                    novo_post.torcida = request.user.perfil.torcida
                else:
                    # Se for global, a torcida fica vazia (null)
                    novo_post.torcida = None
                    
                novo_post.save()
                messages.success(request, 'Publicação criada com sucesso!')
            except Exception as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
                
            return redirect(f"/social/mural/?aba={visibilidade}") # Redireciona para a aba que ele postou
            
    context = {
        'posts': posts,
        'aba_atual': aba 
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