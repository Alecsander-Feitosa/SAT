from django.urls import path, include
from . import views
from accounts import views as accounts_views
from loja import views as loja_views

urlpatterns = [
    path('', include('accounts.urls')),  
    path('noticias/', views.noticias, name='noticias'),
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('perfil/', views.perfil, name='perfil_gamificacao'),
    path('validar-checkin/', views.validar_checkin_estadio, name='validar_checkin'),
    path('confirmar-presenca/<int:evento_id>/', views.confirmar_presenca, name='confirmar_presenca'),
    path('mural/', views.mural_presenca, name='mural_torcida'),
    path('noticias/', views.noticias, name='noticias'),
    path('hub/', views.games_hub, name='games_menu'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
    path('evento/<int:evento_id>/', views.detalhe_evento, name='detalhe_evento'),
    path('loja/', loja_views.loja_view, name='loja_view'),
]