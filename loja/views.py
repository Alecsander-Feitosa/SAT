from django.shortcuts import render
from .models import Produto
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Produto, ItemCarrinho

def loja_view(request):
    perfil = request.user.perfil_game
    # Verifica se o usuário tem uma torcida vinculada
    torcida_usuario = perfil.torcida_filiada if hasattr(perfil, 'torcida_filiada') else None
    
    if torcida_usuario:
        produtos = Produto.objects.filter(torcida=torcida_usuario)
        # Se a torcida dele não tiver produtos, pega outros aleatórios
        if not produtos.exists():
            produtos = Produto.objects.order_by('?')[:4]
    else:
        # Sem torcida? Mostra produtos aleatórios
        produtos = Produto.objects.order_by('?')[:4]

    context = {
        'produtos': produtos,
        'torcida': torcida_usuario,
    }
    return render(request, 'store.html', context)



def loja_view(request):
    perfil = request.user.perfil_game
    torcida_usuario = getattr(perfil, 'torcida_filiada', None)
    
    # Filtro: Torcida do usuário ou Aleatórios
    if torcida_usuario:
        produtos = Produto.objects.filter(torcida=torcida_usuario)
        if not produtos.exists():
            produtos = Produto.objects.order_by('?')[:6]
    else:
        produtos = Produto.objects.order_by('?')[:6]

    # Contador do carrinho
    carrinho_count = ItemCarrinho.objects.filter(usuario=request.user).count()

    return render(request, 'store.html', {
        'produtos': produtos,
        'torcida': torcida_usuario,
        'carrinho_count': carrinho_count
    })

def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    item, created = ItemCarrinho.objects.get_or_create(usuario=request.user, produto=produto)
    if not created:
        item.quantidade += 1
        item.save()
    return JsonResponse({'status': 'sucesso', 'carrinho_count': ItemCarrinho.objects.filter(usuario=request.user).count()})

def ver_carrinho(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total = sum(item.produto.preco * item.quantidade for item in itens)
    
    return render(request, 'loja/carrinho.html', {
        'itens': itens,
        'total': total
    })

def remover_do_carrinho(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
        item.delete()
        
        # Recalcula o total após excluir
        itens = ItemCarrinho.objects.filter(usuario=request.user)
        novo_total = sum(i.produto.preco * i.quantidade for i in itens)
        
        return JsonResponse({
            'status': 'sucesso', 
            'novo_total': f"{novo_total:.2f}",
            'carrinho_vazio': not itens.exists()
        })
    return JsonResponse({'status': 'erro'}, status=400)