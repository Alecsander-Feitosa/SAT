from django.contrib import admin
from .models import Partida, Nivel, Badge, PerfilGamificacao, BadgeUsuario, CheckIn
from .models import Conquista

@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'xp_minimo', 'cor_tema')

# Remova o Nivel da lista abaixo para evitar conflitos
modelos = [Partida, Badge, PerfilGamificacao, BadgeUsuario, CheckIn]
for m in modelos:
    try:
        admin.site.register(m)
    except admin.sites.AlreadyRegistered:
        pass

admin.site.register(Conquista)