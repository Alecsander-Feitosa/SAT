from django.urls import path
from . import views
urlpatterns = [
    path('', views.loja_home, name='loja'),
    path('produto/<int:produto_id>/', views.produto_detalhe, name='produto_detalhe'),
]