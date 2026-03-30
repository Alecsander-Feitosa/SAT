# loja/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from .models import Produto, ItemCarrinho, Pedido, ItemPedido, Variacao
# loja/views.py (substitua a função loja_view)

@login_required
def loja_view(request):
    total_itens = 0
    torcida_usuario = None
    
    # 1. Definir a base de produtos (para a torcida atual ou geral)
    if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        torcida_usuario = request.user.perfil.torcida
        base_produtos = Produto.objects.filter(torcida=torcida_usuario)
    else:
        base_produtos = Produto.objects.filter(torcida__isnull=True)
        
    produtos = base_produtos

    # 2. Aplicar o filtro de categoria se o usuário clicou em alguma
    categoria_atual = request.GET.get('categoria')
    if categoria_atual:
        produtos = produtos.filter(categoria=categoria_atual)
        
    # 3. Calcular os itens do carrinho
    total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    # 4. Puxar categorias da 'base_produtos' (assim os botões não somem quando filtramos)
    categorias = base_produtos.exclude(categoria__isnull=True).exclude(categoria__exact='').values_list('categoria', flat=True).distinct()

    context = {
        'produtos': produtos,
        'total_itens_carrinho': total_itens,
        'torcida': torcida_usuario,
        'categorias': categorias,
        'categoria_atual': categoria_atual, # Para marcar o botão ativo no HTML
    }
    return render(request, 'store.html', context)

@login_required
def adicionar_ao_carrinho(request, produto_id):
    # Proteção: Garantir que ele só adiciona produtos exclusivos da sua torcida
    if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida)
    else:
        produto = get_object_or_404(Produto, id=produto_id, torcida__isnull=True)

    variacao_id = request.POST.get('variacao_id')
    variacao = None
    
    if variacao_id:
        variacao = get_object_or_404(Variacao, id=variacao_id)
    
    if produto.estoque > 0:
        item, created = ItemCarrinho.objects.get_or_create(
            usuario=request.user, 
            produto=produto,
            variacao=variacao
        )
        
        if not created:
            item.quantidade += 1
            item.save()
            
    return redirect('loja')

@login_required
def detalhe_produto(request, produto_id):
    # Proteção na visualização do detalhe do produto
    if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida)
    else:
        produto = get_object_or_404(Produto, id=produto_id, torcida__isnull=True)
        
    return render(request, 'loja/detalhe_produto.html', {'produto': produto})



@login_required
def ver_carrinho(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco * item.quantidade for item in itens)
    return render(request, 'loja/carrinho.html', {'itens': itens, 'total_geral': total_geral})

@login_required
def remover_do_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    item.delete()
    return redirect('ver_carrinho')

@login_required
def finalizar_checkout(request):
    itens_carrinho = ItemCarrinho.objects.filter(usuario=request.user)
    if not itens_carrinho.exists():
        return redirect('loja')
    
    total_geral = sum(item.produto.preco * item.quantidade for item in itens_carrinho)
    
    with transaction.atomic():
        pedido = Pedido.objects.create(usuario=request.user, total=total_geral, status='pendente')
        for item in itens_carrinho:
            ItemPedido.objects.create(pedido=pedido, produto=item.produto, quantidade=item.quantidade, preco_unitario=item.produto.preco)
            item.produto.estoque -= item.quantidade
            item.produto.save()
        itens_carrinho.delete()
        
    return render(request, 'loja/sucesso.html', {'pedido': pedido})
    

@login_required
def checkout_exemplo_view(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco * item.quantidade for item in itens)
    
    return render(request, 'loja/checkout_exemplo.html', {
        'itens': itens,
        'total_geral': total_geral
    })