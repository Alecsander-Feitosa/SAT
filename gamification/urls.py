from django.urls import path, include
from . import views

urlpatterns = [
    path('', include('accounts.urls')),  
    path('noticias/', views.noticias, name='noticias'),
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('perfil/', views.perfil, name='perfil_gamificacao'),
    path('validar-checkin/', views.validar_checkin_estadio, name='validar_checkin'),
]