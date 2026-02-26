from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


User = get_user_model()

class Partida(models.Model):
    time_casa = models.CharField(max_length=100)
    time_visitante = models.CharField(max_length=100)
    data_hora = models.DateTimeField()
    local = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.time_casa} x {self.time_visitante}"

class Nivel(models.Model):
    nome = models.CharField(max_length=50) # Corrigido aqui
    xp_minimo = models.IntegerField()
    cor_tema = models.CharField(max_length=7, default='#D37129') 
    icone = models.ImageField(upload_to='niveis/', null=True, blank=True)

    def __str__(self):
        return self.nome

class Badge(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True) # Adicionado para lógica de sinais
    requisito_checkins = models.PositiveIntegerField(default=1)
    imagem = models.ImageField(upload_to='badges/', default='badges/default.png')

    def __str__(self):
        return self.nome



class BadgeUsuario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    data_ganha = models.DateTimeField(auto_now_add=True)

class CheckIn(models.Model):
    # Null=True permite que pessoas sem cadastro (não-sócios) façam check-in
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkins', null=True, blank=True)
    nome_visitante = models.CharField(max_length=100, null=True, blank=True) # Para quem não logou
    evento = models.ForeignKey('organizadas.Evento', on_delete=models.CASCADE)
    data = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    foto = models.ImageField(upload_to='checkins/fotos/', null=True, blank=True) # O NOVO CAMPO
    validado = models.BooleanField(default=False)

class PerfilGamificacao(models.Model):
    user = models.OneToOneField(User, related_name='perfil_game', on_delete=models.CASCADE)
    xp_total = models.IntegerField(default=0)
    nivel = models.ForeignKey('Nivel', on_delete=models.SET_NULL, null=True, blank=True)


    def progresso_nivel(self):
        from .models import Nivel
        
        # 1. Pega o nível atual do usuário (se não tiver, assume o menor nível do sistema)
        nivel_atual = self.nivel
        if not nivel_atual:
            nivel_atual = Nivel.objects.order_by('xp_minimo').first()
        
        # 2. Pega o PRÓXIMO nível (o primeiro que tem XP estritamente maior que o atual)
        proximo_nivel = Nivel.objects.filter(xp_minimo__gt=self.xp_total).order_by('xp_minimo').first()
        
        # Se não existe próximo nível, ele é nível máximo (Lenda) -> Barra 100%
        if not proximo_nivel:
            return 100

        # 3. Cálculo matemático do progresso
        xp_inicio = nivel_atual.xp_minimo if nivel_atual else 0
        xp_objetivo = proximo_nivel.xp_minimo
        
        # Quanto XP ele precisa ganhar NO TOTAL para atravessar este nível específico
        largura_do_nivel = xp_objetivo - xp_inicio
        
        # Quanto XP ele já ganhou ALÉM do mínimo do nível atual
        xp_ganho_neste_nivel = self.xp_total - xp_inicio
        
        if largura_do_nivel > 0:
            progresso = (xp_ganho_neste_nivel / largura_do_nivel) * 100
            # Garante que a barra não fique negativa nem passe de 100
            return min(max(progresso, 0), 100)
        
        return 0

    def __str__(self):
        return f"XP de {self.user.username}"

@receiver(post_save, sender=CheckIn)
def atribuir_xp_checkin(sender, instance, created, **kwargs):
    if created and instance.user:
        # Busca ou cria o perfil de gamificação do usuário
        perfil, _ = PerfilGamificacao.objects.get_or_create(user=instance.user)
        
        # Atribui 50 XP por check-in
        perfil.xp_total += 50
        
        # Lógica automática para subir de nível
        novo_nivel = Nivel.objects.filter(xp_minimo__lte=perfil.xp_total).order_by('-xp_minimo').first()
        if novo_nivel:
            perfil.nivel = novo_nivel
            
        perfil.save()


@receiver(post_save, sender=CheckIn)
def processar_gamificacao_estadio(sender, instance, created, **kwargs):
    if created and instance.user:
        # 1. Credita o XP (50 pontos por presença no estádio)
        perfil, _ = PerfilGamificacao.objects.get_or_create(user=instance.user)
        perfil.xp_total += 50
        
        # 2. Lógica de Level Up: Busca o maior nível que o XP atual alcança
        novo_nivel = Nivel.objects.filter(xp_minimo__lte=perfil.xp_total).order_by('-xp_minimo').first()
        if novo_nivel:
            perfil.nivel = novo_nivel
        
        perfil.save()

        # 3. Verificação de Medalhas (Badges) por recorrência
        total_checkins = CheckIn.objects.filter(user=instance.user).count()
        
        # Exemplo: Se completou 5 check-ins, ganha a medalha "Fiel Escudeiro"
        badge_fiel = Badge.objects.filter(requisito_checkins=5).first()
        if badge_fiel and total_checkins >= 5:
            BadgeUsuario.objects.get_or_create(user=instance.user, badge=badge_fiel)


class Conquista(models.Model):
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, help_text="Nome do ícone do Bootstrap (ex: bi-award)")
    xp_necessario = models.IntegerField(default=0)
    cor_hex = models.CharField(max_length=7, default="#D37129")

    def __str__(self):
        return self.titulo