# loja/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from .models import Produto, ItemCarrinho, Pedido, ItemPedido, Variacao

def loja_view(request):
    total_itens = 0
    
    if request.user.is_authenticated:
        # Se o utilizador tem uma torcida vinculada ao perfil
        if request.user.perfil.torcida:
            produtos = Produto.objects.filter(
                Q(torcida=request.user.perfil.torcida) | Q(torcida__isnull=True)
            )
        else:
            # Se for apenas um membro SAT sem torcida
            produtos = Produto.objects.filter(torcida__isnull=True)
            
        total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    else:
        # Visitantes não logados veem apenas produtos gerais
        produtos = Produto.objects.filter(torcida__isnull=True)

    return render(request, 'store.html', {'produtos': produtos, 'total_itens_carrinho': total_itens})

@login_required
def adicionar_ao_carrinho(request, produto_id):
    # Proteção de segurança: Garantir que ele só adiciona produtos permitidos
    if request.user.perfil.torcida:
        produto = get_object_or_404(Produto, id=produto_id, torcida__in=[request.user.perfil.torcida, None])
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
    # Proteção na visualização do detalhe do produto
    if request.user.is_authenticated and request.user.perfil.torcida:
        produto = get_object_or_404(Produto, id=produto_id, torcida__in=[request.user.perfil.torcida, None])
    else:
        produto = get_object_or_404(Produto, id=produto_id, torcida__isnull=True)
        
    return render(request, 'loja/detalhe_produto.html', {'produto': produto})

@login_required
def checkout_exemplo_view(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco * item.quantidade for item in itens)
    
    return render(request, 'loja/checkout_exemplo.html', {
        'itens': itens,
        'total_geral': total_geral
    })