# loja/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from .models import Produto, ItemCarrinho, Pedido, ItemPedido, Variacao
from django.contrib import messages
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


# ==========================================
# PAINEL DO MODERADOR DA LOJA
# ==========================================

@login_required
def painel_loja(request):
    # REGRA DE OURO: Só staff com torcida entra
    if not request.user.is_staff or not hasattr(request.user, 'perfil') or not request.user.perfil.torcida:
        messages.error(request, "Acesso negado. Apenas moderadores autorizados.")
        return redirect('loja')

    # Mostra apenas os produtos da torcida deste moderador
    produtos = Produto.objects.filter(torcida=request.user.perfil.torcida).order_by('-id')
    return render(request, 'loja/painel.html', {'produtos': produtos})

@login_required
def form_produto(request, produto_id=None):
    if not (request.user.is_staff and hasattr(request.user, 'perfil') and request.user.perfil.torcida):
        return redirect('loja')
        
    # Se houver ID, é edição. Se não, é criação.
    produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida) if produto_id else None
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        preco = request.POST.get('preco').replace(',', '.') # Garante formato decimal
        categoria = request.POST.get('categoria')
        estoque = request.POST.get('estoque')
        descricao = request.POST.get('descricao')
        destaque = request.POST.get('destaque') == 'on'
        imagem = request.FILES.get('imagem')
        
        if produto:
            produto.nome = nome
            produto.preco = preco
            produto.categoria = categoria
            produto.estoque = estoque
            produto.descricao = descricao
            produto.destaque = destaque
            if imagem:
                produto.imagem = imagem
            produto.save()
            messages.success(request, 'Produto atualizado!')
        else:
            Produto.objects.create(
                nome=nome, preco=preco, categoria=categoria,
                estoque=estoque, descricao=descricao, destaque=destaque,
                imagem=imagem, torcida=request.user.perfil.torcida
            )
            messages.success(request, 'Produto criado com sucesso!')
        return redirect('painel_loja')
        
    return render(request, 'loja/form_produto.html', {'produto': produto})

@login_required
def excluir_produto(request, produto_id):
    if request.user.is_staff:
        # Garante que o moderador só apaga produtos da SUA torcida
        produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida)
        produto.delete()
        messages.success(request, 'Produto removido com sucesso.')
    return redirect('painel_loja')