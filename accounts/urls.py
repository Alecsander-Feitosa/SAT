from django.urls import path
from django.contrib.auth import views as auth_views # Importe as views de login
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('perfil/', views.editar_perfil, name='perfil'),
    path('carteirinha/', views.carteirinha, name='carteirinha'),
    path('noticias/', views.noticias, name='noticias'),
    path('torcidas/', views.torcidas, name='torcida'),
    path('vincular-torcida/<int:torcida_id>/', views.vincular_torcida, name='vincular_torcida'),
    path('minha-torcida/', views.mural_torcida, name='mural_torcida'),
    path('regras/', views.regras_view, name='regras'),
    
    # Rota corrigida para bater com a função na views.py
    path('seja-socio/', views.seja_socio, name='seja_socio'),
    
    path('evento/<int:evento_id>/', views.detalhe_evento, name='detalhe_evento'),
    path('confirmar-presenca/<int:evento_id>/', views.confirmar_presenca, name='confirmar_presenca'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('bet/', views.bet_view, name='bet'),
    path('beneficios/', views.beneficios_view, name='beneficios'),
]