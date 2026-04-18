from django.urls import path
from . import views

urlpatterns = [
    # --- ROTAS PÚBLICAS E GERAIS ---
    path('', views.lista_torcidas, name='lista_torcidas'),
    
    # --- PAINEL DE MODERAÇÃO VISUAL (Substitui o sat-admin) ---
    path('moderacao/', views.painel_moderador, name='painel_moderador'), 

    # --- INTERAÇÕES DA REDE SOCIAL ---
    path('post/<int:post_id>/curtir/', views.curtir_post, name='curtir_post'),
    path('cancao/<int:cancao_id>/excluir/', views.excluir_cancao, name='excluir_cancao'),

    # --- ROTAS DA TORCIDA (HUB) ---
    # Coloquei o <slug:slug> nas rotas do HUB para que o Django saiba de qual torcida são as fotos/canções
    path('hub/<slug:slug>/', views.hub_view, name='hub_organizadas'), 
    path('hub/<slug:slug>/galeria/', views.galeria_fotos, name='galeria_fotos'),
    path('hub/<slug:slug>/cancoes/', views.cancoes, name='cancoes'),

    # --- A ROTA DO SLUG VAI PARA O FIM (A Armadilha desarmada) ---
    # Atualizado o nome da view de perfil_torcida para detalhes_torcida (que é o nome correto na sua views.py)
    path('<slug:slug>/', views.detalhes_torcida, name='perfil_torcida'),
]