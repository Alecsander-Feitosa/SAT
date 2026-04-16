# loja/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.loja_view, name='loja'),
    path('adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('remover/<int:item_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('checkout/', views.finalizar_checkout, name='finalizar_checkout'),
    path('produto/<int:produto_id>/', views.detalhe_produto, name='detalhe_produto'),
    path('checkout/exemplo/', views.checkout_exemplo_view, name='checkout_exemplo'),
    path('painel/', views.painel_loja, name='painel_loja'),
    path('painel/novo/', views.form_produto, name='novo_produto'),
    path('painel/editar/<int:produto_id>/', views.form_produto, name='editar_produto'),
    path('painel/excluir/<int:produto_id>/', views.excluir_produto, name='excluir_produto'),
]