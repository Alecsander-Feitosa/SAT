from django.contrib import admin
from .models import Partida, Nivel, Badge, PerfilGamificacao, BadgeUsuario, CheckIn, Conquista

@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'xp_minimo', 'cor_tema')
    # Removido o search_fields('user__username') daqui, pois Nivel não tem campo user.

@admin.register(PerfilGamificacao)
class PerfilGamificacaoAdmin(admin.ModelAdmin):
    list_display = ('user', 'xp_total', 'nivel')
    search_fields = ('user__username',) # Aqui sim funciona!

@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'xp_necessario')
    search_fields = ('titulo',)

# Registra o restante dos modelos simples de uma vez
modelos = [Partida, Badge, BadgeUsuario, CheckIn]
for m in modelos:
    try:
        admin.site.register(m)
    except admin.sites.AlreadyRegistered:
        pass