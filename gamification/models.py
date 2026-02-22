from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Partida(models.Model):
    time_casa = models.CharField(max_length=100) # O Django exige um valor aqui
    time_visitante = models.CharField(max_length=100) # E aqui também
    data_hora = models.DateTimeField()
    local = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.time_casa} x {self.time_visitante}"

class Nivel(models.Model):
    nome = models.CharField(max_length=50) # Bronze, Prata, Ouro, Diamante
    xp_minimo = models.PositiveIntegerField()
    cor_tema = models.CharField(max_length=7, default="#e67e22")

    def __str__(self):
        return self.nome

class Badge(models.Model):
    nome = models.CharField(max_length=100)
    requisito_checkins = models.PositiveIntegerField(default=1)
    imagem = models.ImageField(upload_to='badges/', default='badges/default.png')

    def __str__(self):
        return self.nome

class PerfilGamificacao(models.Model):
    user = models.OneToOneField(User, related_name='perfil_game', on_delete=models.CASCADE)
    xp_total = models.IntegerField(default=0)
    nivel = models.ForeignKey('Nivel', on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"XP de {self.user.username}"

class BadgeUsuario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    data_ganha = models.DateTimeField(auto_now_add=True)

class CheckIn(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkins')
    data = models.DateTimeField(auto_now_add=True) # Este campo não aceita "vazio"
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    def __str__(self):
        return f"Check-in de {self.user.username} em {self.data}"