from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView  # 1. ADICIONADO AQUI: Importação para rotas visuais rápidas
from gamification import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('gamification/', include('gamification.urls')),
    path('loja/', include('loja.urls')),
    
    path('social/', include('social.urls')),
    path('organizadas/', include('organizadas.urls')), 
    
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
    
    # 2. ADICIONADO AQUI: A rota para a área financeira
    path('financeiro/', TemplateView.as_view(template_name='financeiro.html'), name='financeiro'),
    
    path('admin-financeiro/', TemplateView.as_view(template_name='admin_financeiro.html'), name='admin_financeiro'),

    path('accounts/', include('allauth.urls')),
]

# --- A MÁGICA DO CSS ACONTECE AQUI ---
# Adicionamos tanto o MEDIA (fotos) quanto o STATIC (design/css)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)