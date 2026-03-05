from django.contrib import admin
# Aqui sim funciona, pois esses modelos estão em accounts/models.py
from .models import Perfil, Evento, CheckIn, Conquista 

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'whatsapp', 'torcida', 'aprovado')
    list_filter = ('aprovado', 'torcida')
    search_fields = ('user__username', 'cpf', 'whatsapp', 'user__first_name')
    list_editable = ('aprovado',) 

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'local', 'torcida', 'ativo')
    list_filter = ('ativo', 'torcida')
    search_fields = ('nome', 'local')
    list_editable = ('ativo',)

@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'evento', 'data_criacao', 'validado')
    list_filter = ('validado', 'evento')
    search_fields = ('user__username', 'evento__nome')
    
@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'xp_necessario')
    search_fields = ('titulo',)