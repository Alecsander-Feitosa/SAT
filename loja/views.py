# loja/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from .models import Produto, ItemCarrinho, Pedido, ItemPedido

def loja_view(request):
    produtos = Produto.objects.all()
    total_itens = 0
    if request.user.is_authenticated:
        total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    return render(request, 'store.html', {'produtos': produtos, 'total_itens_carrinho': total_itens})

@login_required
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    variacao_id = request.POST.get('variacao_id')
    variacao = None
    
    if variacao_id:
        variacao = get_object_or_404(Variacao, id=variacao_id)
    
    # Verifica se há estoque antes de processar
    if produto.estoque > 0:
        # Tenta buscar um item existente com a mesma variação, ou cria um novo
        item, created = ItemCarrinho.objects.get_or_create(
            usuario=request.user, 
            produto=produto,
            variacao=variacao
        )
        
        # Se o item já existia no carrinho, apenas aumenta a quantidade
        if not created:
            item.quantidade += 1
            item.save()
            
    return redirect('loja')

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
    


def detalhe_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    return render(request, 'loja/detalhe_produto.html', {'produto': produto})

@login_required
def checkout_exemplo_view(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco * item.quantidade for item in itens)
    
    return render(request, 'loja/checkout_exemplo.html', {
        'itens': itens,
        'total_geral': total_geral
    })