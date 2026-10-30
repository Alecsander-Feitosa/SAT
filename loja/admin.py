from django.contrib import admin
from .models import AvaliacaoProduto, ConfigLoja, ImagemProduto, Produto, Variacao, Pedido, ItemPedido

# Permite editar variações dentro da página do Produto
class VariacaoInline(admin.TabularInline):
    model = Variacao
    extra = 1  # Quantidade de campos vazios para novas variações

class ImagemProdutoInline(admin.TabularInline):
    model = ImagemProduto
    extra = 1

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'categoria', 'estoque', 'destaque')
    list_filter = ('categoria', 'destaque', 'torcida')
    search_fields = ('nome', 'descricao')
    inlines = [VariacaoInline, ImagemProdutoInline] # Variações e fotos extras

# Exibe os itens comprados dentro do detalhe do Pedido
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'variacao_descricao', 'quantidade', 'preco_unitario')

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'total', 'status', 'codigo_rastreio', 'retirada_sede', 'metodo_pagamento', 'data_pedido')
    list_filter = ('status', 'retirada_sede', 'metodo_pagamento', 'data_pedido')
    inlines = [ItemPedidoInline]

# Banner e CEP de envio por torcida. O registro SEM torcida é o da loja SAT Global.
@admin.register(ConfigLoja)
class ConfigLojaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'banner_titulo', 'cep_origem')

@admin.register(AvaliacaoProduto)
class AvaliacaoProdutoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'usuario', 'nota', 'data')
    list_filter = ('nota',)
    search_fields = ('produto__nome', 'comentario')
