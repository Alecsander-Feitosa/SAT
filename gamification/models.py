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
        """Percentual (0-100) do caminho entre o nível atual e o próximo."""
        from .xp import xp_para_nivel
        inicio = xp_para_nivel(self.nivel_numero)
        fim = xp_para_nivel(self.nivel_numero + 1)
        if fim <= inicio:
            return 100
        return min(max((self.xp_total - inicio) / (fim - inicio) * 100, 0), 100)

    # --- Níveis numéricos (1 a 100+) com títulos: ver gamification/xp.py ---
    @property
    def nivel_numero(self):
        from .xp import nivel_por_xp
        return nivel_por_xp(self.xp_total)

    @property
    def titulo(self):
        from .xp import titulo_do_usuario
        return titulo_do_usuario(self.user, self.nivel_numero)

    @property
    def xp_proximo_nivel(self):
        from .xp import xp_para_nivel
        return xp_para_nivel(self.nivel_numero + 1)

    def __str__(self):
        return f"XP de {self.user.username}"


class RegistroXP(models.Model):
    """Histórico de cada ganho de XP. A combinação (usuário, ação, referência) só rende XP uma vez."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_xp')
    acao = models.CharField(max_length=30)
    referencia = models.CharField(max_length=60, blank=True, help_text="Ex: id do post, data do check-in diário")
    xp = models.IntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        constraints = [models.UniqueConstraint(fields=['user', 'acao', 'referencia'], name='xp_unico_por_acao')]

    def __str__(self):
        return f"{self.user.username} +{self.xp} ({self.acao})"

@receiver(post_save, sender=CheckIn)
def processar_gamificacao_estadio(sender, instance, created, **kwargs):
    if created and instance.user:
        # EXP de participação no evento (tabela, plano, bônus do Presidente e evento épico) — gamification/xp.py
        from .xp import xp_participacao_evento
        xp_participacao_evento(instance.user, instance.evento)

        # Medalhas (Badges) por recorrência
        total_checkins = CheckIn.objects.filter(user=instance.user).count()
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

class MedalhaUsuario(models.Model):
    """Medalha conquistada (o catálogo e as regras ficam em gamification/medalhas.py)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medalhas')
    codigo = models.CharField(max_length=30)
    conquistada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['conquistada_em']
        constraints = [models.UniqueConstraint(fields=['user', 'codigo'], name='medalha_unica')]

    def __str__(self):
        return f"{self.user.username} - {self.codigo}"
