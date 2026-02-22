# organizadas/admin.py
from django.contrib import admin
from .models import Torcida, Evento

@admin.register(Torcida)
class TorcidaAdmin(admin.ModelAdmin):
    list_display = ('nome',)

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    # Campos que aparecem na lista
    list_display = ('titulo', 'torcida', 'data_evento', 'local')
    # Filtros e buscas
    list_filter = ('torcida', 'data_evento')
    search_fields = ('titulo', 'local')
    # Campos dentro do formulário de edição (incluindo os novos)
    fields = ('torcida', 'titulo', 'data_evento', 'local', 'imagem_capa', 'informativo')