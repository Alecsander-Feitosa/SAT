from django.urls import path
from . import views

urlpatterns = [
    path('mural/', views.mural_social, name='mural'),
    path('curtir/<int:post_id>/', views.curtir_post, name='social_curtir_post'),
    path('comentar/<int:post_id>/', views.adicionar_comentario, name='social_comentar_post'),
    path('usuario/<int:usuario_id>/seguir/', views.seguir_usuario, name='seguir_usuario'),
    path('excluir/<int:post_id>/', views.excluir_post, name='social_excluir_post'),
]