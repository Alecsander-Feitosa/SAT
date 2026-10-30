from django.urls import path
from . import views

urlpatterns = [
    path('mural/', views.mural_social, name='mural'),
    path('post/<int:post_id>/', views.ver_post, name='ver_post'),
    path('curtir/<int:post_id>/', views.curtir_post, name='social_curtir_post'),
    path('comentar/<int:post_id>/', views.adicionar_comentario, name='social_comentar_post'),
    path('comentario/<int:comentario_id>/remover/', views.remover_comentario, name='social_remover_comentario'),
    path('denunciar/<int:post_id>/', views.denunciar_post, name='social_denunciar_post'),
    path('usuario/<int:usuario_id>/seguir/', views.seguir_usuario, name='seguir_usuario'),
    path('excluir/<int:post_id>/', views.excluir_post, name='social_excluir_post'),
    path('compartilhar/<str:tipo_item>/<int:item_id>/', views.compartilhar_item, name='social_compartilhar'),
    path('perfil/<int:user_id>/', views.perfil_publico, name='perfil_publico'),
    path('perfil/<int:user_id>/conexoes/', views.conexoes, name='conexoes'),
    path('seguidor/<int:usuario_id>/remover/', views.remover_seguidor, name='remover_seguidor'),
    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('moderacao/', views.moderacao, name='moderacao_social'),
]
