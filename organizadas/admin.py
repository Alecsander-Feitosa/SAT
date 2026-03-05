from django.contrib import admin
# Importamos APENAS os modelos que estão dentro de organizadas/models.py
from .models import Torcida, Caravana, Evento, Noticia, Post, Curtida

@admin.register(Torcida)
class TorcidaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'fundacao', 'cores')
    search_fields = ('nome', 'cores')
    prepopulated_fields = {'slug': ('nome',)} # Preenche o slug automaticamente

@admin.register(Caravana)
class CaravanaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'torcida', 'saida_local', 'saida_horario', 'vagas_totais')
    list_filter = ('torcida',)
    search_fields = ('titulo', 'saida_local')

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'torcida', 'data', 'local', 'ativo')
    list_filter = ('ativo', 'torcida')
    search_fields = ('titulo', 'local')
    list_editable = ('ativo',)

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_publicacao', 'autor')
    search_fields = ('titulo', 'autor')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('autor', 'torcida', 'data_criacao')
    list_filter = ('torcida',)
    search_fields = ('autor__username', 'texto')

@admin.register(Curtida)
class CurtidaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'post', 'data_curtida')