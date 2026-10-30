
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import CheckIn, Badge, BadgeUsuario, Nivel, PerfilGamificacao
from accounts.models import Perfil 
from content.models import Notificacao

@receiver(post_save, sender=User)
def configurar_novo_torcedor(sender, instance, created, **kwargs):
    if created:
        # MANTENHA esta linha: ela cria apenas a parte de pontos/XP
        PerfilGamificacao.objects.get_or_create(user=instance)
