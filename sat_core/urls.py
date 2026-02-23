from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from gamification import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('accounts.urls')),      # Centraliza dashboard e perfil
    path('loja/', include('store.urls')),    # Módulo 3: E-commerce 
    path('social/', include('social.urls')), # Módulo 4: Engajamento 
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('gamification/', include('gamification.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)