from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Post, Comentario
from accounts.decorators import torcida_required
from django.views.decorators.http import require_POST




@login_required
@torcida_required
def mural_social(request):
    aba = request.GET.get('aba', 'sat')
    perfil = request.user.perfil
    
    if aba == 'sat':
        # Posts oficiais (geralmente sem torcida vinculada ou da administração)
        posts = Post.objects.filter(torcida__isnull=True).order_by('-data_criacao')
    else:
        # Posts específicos da torcida do utilizador
        posts = Post.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')

    if request.method == 'POST':
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        if texto:
            Post.objects.create(
                autor_s=request.user,
                texto=texto,
                imagem=imagem,
                torcida=perfil.torcida if aba == 'torcida' else None
            )
            return redirect(f'/social/mural/?aba={aba}')

    context = {
        'posts': posts,
        'aba': aba,
        'tem_torcida_ativa': True if perfil.torcida else False
    }
    return render(request, 'mural.html', context)

@login_required
@require_POST 
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.user in post.curtidas.all():
        post.curtidas.remove(request.user)
        liked = False
    else:
        post.curtidas.add(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': post.total_curtidas()
    })



@login_required
@require_POST
def adicionar_comentario(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    texto = request.POST.get('comentario')
    
    if texto:
        comentario = Comentario.objects.create(
            post=post,
            autor=request.user,
            texto=texto
        )
        
        # Pega a foto de perfil se existir, senão usa o avatar gerado
        foto_url = f"https://ui-avatars.com/api/?name={request.user.username}&background=random&color=fff"
        if hasattr(request.user, 'perfil') and request.user.perfil.foto:
            foto_url = request.user.perfil.foto.url

        # Se for requisição do JavaScript (AJAX), devolvemos os dados em JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'sucesso': True,
                'texto': comentario.texto,
                'nome_autor': request.user.username,
                'foto_autor': foto_url,
                'total_comentarios': post.comentarios.count()
            })

    return redirect(request.META.get('HTTP_REFERER', '/social/mural/'))