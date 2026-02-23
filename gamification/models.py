from django.db import models
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Partida(models.Model):
    time_casa = models.CharField(max_length=100)
    time_visitante = models.CharField(max_length=100)
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
        proximo = Nivel.objects.filter(xp_minimo__gt=self.xp_total).order_by('xp_minimo').first()
        if not proximo: return 100
        inicio = self.nivel.xp_minimo if self.nivel else 0
        total_necessario = proximo.xp_minimo - inicio
        atual_no_nivel = self.xp_total - inicio
        porcentagem = (atual_no_nivel / total_necessario) * 100
        return min(max(porcentagem, 5), 100)

    def __str__(self):
        return f"XP de {self.user.username}"

