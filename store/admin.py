from django.contrib import admin
from .models import Categoria, Produto, VariacaoProduto, Pedido

class VariacaoInline(admin.TabularInline):
    model = VariacaoProduto
    extra = 1

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco', 'ativo')
    inlines = [VariacaoInline]

admin.site.register(Categoria)
admin.site.register(Pedido)