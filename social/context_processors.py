def social(request):
    """Contador do sininho, faixa do cabeçalho, pop-up pendente e, para admins, posts em revisão."""
    from .avisos import aviso_cabecalho, proximo_popup, aviso_vencimento
    contexto = {}
    try:
        contexto['aviso_cabecalho'] = aviso_cabecalho()
    except Exception:
        pass
    if not request.user.is_authenticated:
        return contexto
    from .models import Notificacao, Post
    contexto['notificacoes_nao_lidas'] = Notificacao.objects.filter(usuario=request.user, lida=False).count()
    if request.user.is_superuser:
        contexto['denuncias_pendentes'] = Post.objects.filter(em_revisao=True).count()
    # Pop-ups só em páginas normais (não em chamadas AJAX nem no painel do moderador)
    if request.headers.get('x-requested-with') != 'XMLHttpRequest' and '/moderacao/' not in request.path:
        try:
            contexto['popup_pendente'] = proximo_popup(request.user)
            contexto['aviso_vencimento'] = aviso_vencimento(getattr(request.user, 'perfil', None))
        except Exception:
            pass
    return contexto
