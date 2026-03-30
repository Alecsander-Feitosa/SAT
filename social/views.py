from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Post, Comentario

@login_required
def mural_social(request):
    # Puxa os posts ordenados do mais recente para o mais antigo
    posts = Post.objects.all().order_by('-data_criacao')
    
    if request.method == 'POST':
        texto = request.POST.get('texto', '')
        imagem = request.FILES.get('imagem')
        
        if texto or imagem:
            # 1. SOLUÇÃO DO TÍTULO: Cria um título automático usando as 50 primeiras letras do texto
            titulo_gerado = texto[:50] + "..." if texto else "Publicação com Imagem"
            
            try:
                novo_post = Post(
                    autor_s=request.user, 
                    titulo=titulo_gerado, # Preenche o campo obrigatório do banco de dados!
                    texto=texto, 
                    imagem=imagem
                )
                
                # Associa a torcida se existir
                if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                    novo_post.torcida = request.user.perfil.torcida
                    
                novo_post.save()
                messages.success(request, 'Publicação criada com sucesso!')
            except Exception as e:
                # Se falhar, não crasha a tela inteira, apenas avisa
                messages.error(request, f'Erro ao salvar: {str(e)}')
                
            return redirect('mural')
            
    context = {'posts': posts}
    return render(request, 'mural.html', context)

@login_required
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    
    try:
        # Lógica de curtir / descurtir
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
                    # 2. SOLUÇÃO DA FOTO: Tenta pegar a url da foto. Se ela não existir, captura o erro e envia vazio.
                    try:
                        if hasattr(request.user, 'perfil') and request.user.perfil.foto:
                            foto_url = request.user.perfil.foto.url
                    except ValueError:
                        foto_url = "" # Contorna o erro de quando a foto está em branco
                        
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