from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Post, Comentario
from accounts.decorators import torcida_required
from django.views.decorators.http import require_POST
from django.db.models import Q



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
                autor_s=request.user, # Usa autor_s como no seu modelo!
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
    
    # Substituí post.total_curtidas() por post.curtidas.count() para ser 100% seguro
    return JsonResponse({
        'liked': liked,
        'likes_count': post.curtidas.count() 
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

@login_required
@require_POST
def seguir_usuario(request, usuario_id):
    from django.contrib.auth.models import User
    
    usuario_alvo = get_object_or_404(User, id=usuario_id)
    
    # Prevenção: o utilizador não pode seguir a si mesmo
    if request.user == usuario_alvo:
        return JsonResponse({'sucesso': False, 'erro': 'Não podes seguir a ti mesmo.'}, status=400)
    
    perfil_alvo = usuario_alvo.perfil
    meu_perfil = request.user.perfil # Pega o perfil de quem clicou
    
    # BLINDAGEM: O Django tenta guardar o Perfil. Se o model exigir User, ele usa o User.
    try:
        if meu_perfil in perfil_alvo.seguidores.all():
            perfil_alvo.seguidores.remove(meu_perfil)
            seguindo = False
        else:
            perfil_alvo.seguidores.add(meu_perfil)
            seguindo = True
    except TypeError:
        # Se der erro de tipo, é porque o seu model de seguidores exige o "User"
        if request.user in perfil_alvo.seguidores.all():
            perfil_alvo.seguidores.remove(request.user)
            seguindo = False
        else:
            perfil_alvo.seguidores.add(request.user)
            seguindo = True
            
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'sucesso': True,
            'seguindo': seguindo
        })
        
    return redirect(request.META.get('HTTP_REFERER', '/social/mural/'))