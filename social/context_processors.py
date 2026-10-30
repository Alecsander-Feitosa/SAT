def social(request):
    """Contador do sininho e, para admins, de posts em revisão."""
    if not request.user.is_authenticated:
        return {}
    from .models import Notificacao, Post
    contexto = {'notificacoes_nao_lidas': Notificacao.objects.filter(usuario=request.user, lida=False).count()}
    if request.user.is_superuser:
        contexto['denuncias_pendentes'] = Post.objects.filter(em_revisao=True).count()
    return contexto
