from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_torcidas, name='lista_torcidas'),
    path('<slug:slug>/', views.perfil_torcida, name='perfil_torcida'),
    path('evento/<int:evento_id>/confirmar/', views.confirmar_presenca, name='confirmar_presenca'),
    path('caravana/<int:caravana_id>/reservar/', views.reservar_caravana, name='reservar_caravana'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
]