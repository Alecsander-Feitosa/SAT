
from django.contrib.auth import views as auth_views
from . import views
from django.urls import path



urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('perfil/', views.editar_perfil, name='perfil'),
    path('noticias/', views.noticias, name='noticias'),
    
    # REDE SOCIAL (SAT Social - Fotos)
    path('social/', views.mural_torcida, name='mural_social'), 
    
    # HUB DA TORCIDA (Onde tem o cartão e os ícones)
    # MUDAMOS O NAME PARA 'torcida' PARA ACABAR COM O ERRO
    path('torcida/', views.area_torcida, name='torcida'),
    
    # EVENTOS
    path('eventos/', views.lista_eventos, name='lista_eventos'),
    
    # MANUTENÇÃO BET
    path('bet/manutencao/', views.bet_manutencao, name='bet_manutencao'),

    # SUB-PÁGINAS
    path('torcida/galeria/', views.galeria_fotos, name='galeria_fotos'),
    path('torcida/diretoria/', views.diretoria_view, name='diretoria'),
    path('torcida/conquistas/', views.mural_conquistas, name='mural_conquistas'),
    path('torcida/cancoes/', views.cancoes_torcida, name='cancoes'),
    path('torcida/regras/', views.regras_view, name='regras'),
    path('torcida/aliadas/', views.aliadas_view, name='aliadas'),
    path('torcida/viagens/', views.viagens_view, name='viagens'),

    # LINKS DE SEGURANÇA
    path('store', views.dashboard, name='loja'),
    path('games/', views.dashboard, name='games_menu'),
    path('bet/', views.dashboard, name='bet_view'),
    path('seja-socio/', views.seja_socio, name='seja_socio'),
]