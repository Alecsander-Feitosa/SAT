from django.urls import path
from . import views

app_name = 'bepe'

urlpatterns = [
    # ÁREA RESTRITA (grupo BEPE + admins)
    path('', views.painel, name='painel'),
    path('cadastrados/', views.cadastrados, name='cadastrados'),
    path('cadastrados/<int:perfil_id>/', views.cadastrado_detalhe, name='cadastrado_detalhe'),
    path('mapa/', views.mapa, name='mapa'),
    path('mapa/dados/', views.mapa_dados, name='mapa_dados'),
    path('jogos/', views.jogos, name='jogos'),
    path('rotas/', views.rotas, name='rotas'),
    path('rotas/nova/', views.rota_planejar, name='rota_nova'),
    path('rotas/<int:plano_id>/', views.rota_planejar, name='rota_editar'),
    path('rotas/<int:plano_id>/enviar/', views.rota_enviar, name='rota_enviar'),
    path('rotas/<int:plano_id>/excluir/', views.rota_excluir, name='rota_excluir'),
    path('rotas/torcedores/', views.rota_torcedores, name='rota_torcedores'),
    path('reunioes/', views.reunioes, name='reunioes'),
    path('reunioes/<int:reuniao_id>/cancelar/', views.reuniao_cancelar, name='reuniao_cancelar'),
    path('canal/', views.conversas, name='conversas'),
    path('canal/nova/', views.nova_conversa, name='nova_conversa'),
    path('canal/<int:conversa_id>/', views.conversa, name='conversa'),
    path('denuncias/', views.denuncias, name='denuncias'),
    path('denuncias/<int:denuncia_id>/', views.denuncia_detalhe, name='denuncia_detalhe'),
    path('documentos/', views.documentos, name='documentos'),
    path('documentos/<int:documento_id>/', views.documento_abrir, name='documento_abrir'),

    # LADO DA DIRETORIA DAS TORCIDAS
    path('diretoria/', views.diretoria_conversas, name='diretoria_conversas'),
    path('diretoria/nova/', views.diretoria_nova_conversa, name='diretoria_nova_conversa'),
    path('diretoria/<int:conversa_id>/', views.diretoria_conversa, name='diretoria_conversa'),
    path('diretoria/reunioes/', views.diretoria_reunioes, name='diretoria_reunioes'),
    path('diretoria/documentos/', views.diretoria_documentos, name='diretoria_documentos'),
    path('diretoria/documentos/<int:documento_id>/excluir/', views.diretoria_documento_excluir, name='diretoria_documento_excluir'),
    path('diretoria/presenca/<str:tipo>/<int:alvo_id>/', views.diretoria_lista_presenca, name='diretoria_lista_presenca'),

    # TORCEDOR: COMPARTILHAR LOCALIZAÇÃO
    path('localizacao/', views.localizacao, name='localizacao'),

    # PÚBLICO: FALE COM O BEPE
    path('fale/', views.fale_com_bepe, name='fale_com_bepe'),
    path('fale/acompanhar/', views.acompanhar_denuncia, name='acompanhar_denuncia'),
]
