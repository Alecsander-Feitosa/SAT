from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_torcidas, name='lista_torcidas'),
    
    # --- ROTAS DO PAINEL ADMIN (Devem vir sempre antes do slug!) ---
    path('sat-admin/', views.admin_dashboard, name='admin_dashboard'),
    path('sat-admin/nova-torcida/', views.nova_torcida, name='nova_torcida'), 
    path('sat-admin/utilizadores/', views.gerir_utilizadores, name='gerir_utilizadores'), 
    path('sat-admin/torcidas/', views.gerenciar_torcidas, name='gerenciar_torcidas'),   
    path('sat-admin/torcida/<int:id>/editar/', views.editar_torcida, name='editar_torcida'),
    path('sat-admin/utilizador/<int:perfil_id>/status/', views.alternar_status_utilizador, name='alternar_status_utilizador'),

    
    path('<slug:slug>/', views.perfil_torcida, name='perfil_torcida'),
    path('evento/<int:evento_id>/confirmar/', views.confirmar_presenca, name='confirmar_presenca'),
    path('caravana/<int:caravana_id>/reservar/', views.reservar_caravana, name='reservar_caravana'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
    path('hub/', views.hub_view, name='hub'),
]