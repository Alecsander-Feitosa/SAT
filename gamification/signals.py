
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User # Importação que faltava
from .models import CheckIn, Badge, BadgeUsuario

# Importe os modelos dos outros apps
from accounts.models import Perfil 
from gamification.models import PerfilGamificacao
from content.models import Notificacao


@receiver(post_save, sender=User)
def configurar_novo_torcedor(sender, instance, created, **kwargs):
    if created:
        # Agora as chamadas abaixo funcionarão corretamente
        Perfil.objects.create(user=instance)
        PerfilGamificacao.objects.create(user=instance)
        Notificacao.objects.create(
            user=instance, 
            titulo="Bem-vindo ao SAT!",
            mensagem="Complete seu perfil para liberar sua carteirinha virtual."
        )


@receiver(post_save, sender=CheckIn)
def processar_conquistas(sender, instance, created, **kwargs):
    if created and instance.validado:
        perfil_game = PerfilGamificacao.objects.get(user=instance.user)
        
        # 1. Adiciona XP por presença [cite: 92]
        perfil_game.xp_total += 50
        perfil_game.save()
        
        # 2. Lógica para Badge "Viajante" 
        if instance.evento.tipo == 'FORA':
            badge_viajante = Badge.objects.get(slug='viajante')
            BadgeUsuario.objects.get_or_create(user=instance.user, badge=badge_viajante)
            
        # 3. Lógica para "Invicto" (10 jogos seguidos) 
        total_seguidos = CheckIn.objects.filter(user=instance.user, validado=True).count()
        if total_seguidos >= 10:
            badge_invicto = Badge.objects.get(slug='invicto')
            BadgeUsuario.objects.get_or_create(user=instance.user, badge=badge_invicto)