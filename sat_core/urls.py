from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from gamification import views



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('gamification/', include('gamification.urls')),
    path('social/', include('social.urls')), # Módulo 4: Engajamento 
    path('loja/', include('loja.urls')),
    path('ranking/', views.ranking_torcida, name='ranking'),
    path('eventos/', views.lista_eventos, name='lista_eventos'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)