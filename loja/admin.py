from django.contrib import admin
from .models import Produto, Variacao, Pedido, ItemPedido

# Permite editar variações dentro da página do Produto
class VariacaoInline(admin.TabularInline):
    model = Variacao
    extra = 1  # Quantidade de campos vazios para novas variações

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'categoria', 'estoque', 'destaque')
    list_filter = ('categoria', 'destaque', 'torcida')
    search_fields = ('nome', 'descricao')
    inlines = [VariacaoInline] # Adiciona a edição de tamanhos/cores aqui

# Exibe os itens comprados dentro do detalhe do Pedido
class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'quantidade', 'preco_unitario')

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'total', 'status', 'data_pedido')
    list_filter = ('status', 'data_pedido')
    inlines = [ItemPedidoInline]