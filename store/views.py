from django.shortcuts import render, get_object_or_404
from .models import Produto, Categoria

def loja_home(request):
    # Traz apenas produtos ativos
    produtos = Produto.objects.filter(ativo=True)
    return render(request, 'store.html', {'produtos': produtos})

def produto_detalhe(request, produto_id):
    # Página interna do produto para escolher tamanho
    produto = get_object_or_404(Produto, id=produto_id)
    return render(request, 'produto_detalhe.html', {'produto': produto})