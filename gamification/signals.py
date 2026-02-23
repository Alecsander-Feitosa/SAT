
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import CheckIn, Badge, BadgeUsuario, Nivel, PerfilGamificacao
from accounts.models import Perfil 
from content.models import Notificacao

@receiver(post_save, sender=User)
def configurar_novo_torcedor(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.get_or_create(user=instance)
        PerfilGamificacao.objects.get_or_create(user=instance)
        Notificacao.objects.create(
            user=instance, 
            titulo="Bem-vindo ao SAT!",
            mensagem="Complete seu perfil para liberar sua carteirinha virtual."
        )


@receiver(post_save, sender=CheckIn)
def processar_conquistas(sender, instance, created, **kwargs):
    if created and instance.validado:
        perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=instance.user)
        
        # Adiciona 50 XP por presença confirmada
        perfil_game.xp_total += 50
        
        # Lógica de atualização de nível
        novo_nivel = Nivel.objects.filter(xp_minimo__lte=perfil_game.xp_total).order_by('-xp_minimo').first()
        if novo_nivel:
            perfil_game.nivel = novo_nivel
        perfil_game.save()
