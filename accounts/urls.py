
from django.contrib.auth import views as auth_views
from . import views
from django.urls import path



urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('perfil/', views.editar_perfil, name='perfil'),
    path('noticias/', views.noticias, name='noticias'),
    
    # REDE SOCIAL (SAT Social - Fotos)
    path('social/', views.mural_social, name='mural'),
    path('hub/', views.area_hub, name='hub_torcida'), # Link para o design antigo (cartão)
    path('mural/', views.mural_social, name='mural_social'),
    # accounts/urls.py
    path('moderacao/', views.moderacao_torcida, name='moderacao_torcida'),
    path('aprovar/<int:perfil_id>/', views.aprovar_membro, name='aprovar_membro'),
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
    path('viagens/', views.viagens_view, name='viagens_view'),

    # LINKS DE SEGURANÇA
    path('store', views.dashboard, name='loja'),
    path('games/', views.hub_games_view, name='games_hub'),
    path('bet/', views.dashboard, name='bet_view'),
    path('seja-socio/', views.seja_socio, name='seja_socio'),
    path('vincular/<int:torcida_id>/', views.vincular_torcida, name='vincular_torcida'),
    path('curtir/<int:post_id>/', views.curtir_post, name='curtir_post'),
    
]