from django.contrib import admin
from .models import Partida, Nivel, Badge, PerfilGamificacao, BadgeUsuario, CheckIn

# Registro direto para evitar erro de duplicidade
admin.site.register(Partida)
admin.site.register(Nivel)
admin.site.register(Badge)
admin.site.register(PerfilGamificacao)
admin.site.register(BadgeUsuario)
admin.site.register(CheckIn)