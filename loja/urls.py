from django.urls import path
from . import views

urlpatterns = [
    path('', views.loja_view, name='store'),
    path('adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='add_carrinho'),
    path('meu-carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('remover/<int:item_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
]