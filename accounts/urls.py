from django.urls import path
from . import views

urlpatterns = [
    # A página inicial agora é o Pré-Login
    path('', views.pre_login, name='pre_login'),
    
    # NOVAS ROTAS PARA O FLUXO DA TORCIDA (WHITE LABEL)
    path('escolher-torcida/', views.escolher_torcida_publico, name='escolher_torcida_publico'),
    path('entrar/<int:torcida_id>/', views.entrada_torcida, name='entrada_torcida'),
    
    # O Dashboard ganha uma URL própria (ex: seusite.com/dashboard/)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # LOGIN PERSONALIZADO (A Mágica acontece aqui!)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    
    path('cadastro/', views.cadastro, name='cadastro'),
    path('cadastro_etapa2/', views.cadastro_etapa2, name='cadastro_etapa2'),
    path('perfil/', views.editar_perfil, name='perfil'),
    path('noticias/', views.noticias, name='noticias'),
    
    # REDE SOCIAL (SAT Social - Fotos)
    path('social/', views.mural_social, name='mural'),
    path('hub/', views.area_hub, name='hub'), # Link para o design antigo (cartão)
    path('mural/', views.mural_social, name='mural_social'),
    
    # MODERAÇÃO
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