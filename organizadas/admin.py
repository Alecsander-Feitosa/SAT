from django.contrib import admin
from .models import Torcida, Caravana, Evento, Noticia, Post, Curtida
from .models import Parceiro
from .models import Publicidade 


@admin.register(Torcida)
class TorcidaAdmin(admin.ModelAdmin):
    # Removido 'cores' e adicionado 'sigla' e 'cor_primaria'
    list_display = ('nome', 'sigla', 'fundacao', 'cor_primaria')
    search_fields = ('nome', 'sigla', 'lema') 
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


@admin.register(Parceiro)
class ParceiroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'torcida', 'link')
    list_filter = ('torcida',)
    search_fields = ('nome',)


@admin.register(Publicidade)
class PublicidadeAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_inicio', 'data_fim', 'tempo_exibicao', 'ativo', 'torcida')
    list_filter = ('ativo', 'torcida', 'data_inicio', 'data_fim')
    search_fields = ('titulo',)