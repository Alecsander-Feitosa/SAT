from django.urls import path
from . import views

urlpatterns = [
    # --- ROTAS PÚBLICAS E GERAIS ---
    path('', views.lista_torcidas, name='lista_torcidas'),
    
    # --- PAINEL DE MODERAÇÃO VISUAL (Substitui o sat-admin) ---
    path('moderacao/', views.painel_moderador, name='painel_moderador'), 

    # --- INTERAÇÕES DA REDE SOCIAL ---
    path('post/<int:post_id>/curtir/', views.curtir_post, name='curtir_post'),
    path('cancao/<int:cancao_id>/excluir/', views.excluir_cancao, name='excluir_cancao'),

    # --- ROTAS DA TORCIDA (HUB) ---
    path('hub/<slug:slug>/galeria/', views.galeria_fotos, name='galeria_fotos'),
    path('hub/<slug:slug>/cancoes/', views.cancoes, name='cancoes'),

    # --- A ROTA DO SLUG VAI PARA O FIM (A Armadilha desarmada) ---
    
    # CORREÇÃO AQUI: Renomeado de name='hub' para name='hub_organizadas' para não dar conflito
    path('hub/<slug:slug>/', views.hub_view, name='hub_organizadas'),
    
    path('hub/<slug:slug>/diretoria/', views.diretoria, name='diretoria'),
    path('hub/<slug:slug>/conquistas/', views.mural_conquistas, name='mural_conquistas'),
    path('hub/<slug:slug>/eventos/', views.lista_eventos, name='lista_eventos'),
    path('hub/<slug:slug>/regras/', views.regras, name='regras'),
    path('hub/<slug:slug>/aliadas/', views.aliadas, name='aliadas'),
    path('hub/<slug:slug>/viagens/', views.viagens, name='viagens'),
]