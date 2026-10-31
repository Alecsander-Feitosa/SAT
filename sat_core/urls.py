from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from gamification import views
from accounts import views as accounts_views
from sat_core import pwa


urlpatterns = [
    # PWA / app (manifest e service worker precisam ficar na raiz)
    path('manifest.webmanifest', pwa.manifest, name='pwa_manifest'),
    path('sw.js', pwa.service_worker, name='pwa_sw'),
    path('offline/', pwa.offline, name='pwa_offline'),

    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('gamification/', include('gamification.urls')),
    path('loja/', include('loja.urls')),
    
    path('social/', include('social.urls')),
    path('organizadas/', include('organizadas.urls')), 
    path('bepe/', include('bepe.urls')),
    
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
    
    # Área financeira
    path('financeiro/', accounts_views.financeiro, name='financeiro'),
    
    # ROTAS DE ADMINISTRAÇÃO DA SAT
    # (o financeiro do moderador fica em organizadas/urls.py: admin_financeiro)
    path('admin-master/', TemplateView.as_view(template_name='admin_master.html'), name='admin_master'),
    
    path('admin-dashboard/', TemplateView.as_view(template_name='admin_master.html'), name='admin_dashboard'),
    # ---> ADICIONE ESTAS TRÊS LINHAS PARA OS BOTÕES DO PAINEL ADMIN <---
    path('admin-master/utilizadores/', TemplateView.as_view(template_name='admin_utilizadores.html'), name='gerir_utilizadores'),
    path('admin-master/nova-torcida/', TemplateView.as_view(template_name='admin_nova_torcida.html'), name='nova_torcida'),
    path('admin-master/torcidas/', TemplateView.as_view(template_name='admin_torcidas.html'), name='gerenciar_torcidas'),
    
    path('admin-painel/utilizador/<int:perfil_id>/editar/', accounts_views.admin_editar_utilizador, name='admin_editar_utilizador'),    
    path('accounts/', include('allauth.urls')),
    path('_allauth/', include('allauth.headless.urls')),  # login nativo do app
]

# --- A MÁGICA DO CSS ACONTECE AQUI ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)