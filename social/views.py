from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Post, Comentario
from accounts.decorators import torcida_required
from django.views.decorators.http import require_POST




@login_required
def mural_social(request):
    aba = request.GET.get('aba', 'sat')
    
    # Usamos getattr para evitar erros caso o utilizador recém-criado ainda não tenha perfil
    perfil = getattr(request.user, 'perfil', None)
    
    # Define se o utilizador tem o Nível 2 desbloqueado (Torcida ativa E aprovada)
    tem_torcida_ativa = bool(perfil and perfil.torcida and getattr(perfil, 'aprovado', False))

    # BLOQUEIO DE SEGURANÇA: Se tentar aceder à aba da torcida sem permissão, é redirecionado para o feed geral
    if aba == 'torcida' and not tem_torcida_ativa:
        aba = 'sat'

    # LÓGICA DE CRIAÇÃO DE POSTS
    if request.method == 'POST':
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        
        if texto or imagem: 
            Post.objects.create(
                autor_s=request.user,
                texto=texto,
                imagem=imagem,
                torcida=perfil.torcida if (aba == 'torcida' and tem_torcida_ativa) else None,
                time_relacionado=perfil.time_coracao if perfil else None 
            )
            return redirect(f'/social/mural/?aba={aba}')

    if aba == 'sat':
        if perfil and getattr(perfil, 'time_coracao', None):
            posts = Post.objects.filter(
                Q(time_relacionado=perfil.time_coracao) | Q(time_relacionado__isnull=True)
            ).order_by('-data_criacao')
        else:
            posts = Post.objects.all().order_by('-data_criacao')
    else:
        posts = Post.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')

    context = {
        'posts': posts,
        'aba': aba,
        'tem_torcida_ativa': tem_torcida_ativa,
        'perfil': perfil
    }
    return render(request, 'mural.html', context)
# FIM DA ATUALIZAÇÃO: Função mural_social

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