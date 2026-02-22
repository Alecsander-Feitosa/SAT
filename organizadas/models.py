from django.db import models
from django.conf import settings
from gamification.models import Partida


class Torcida(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True)
    fundacao = models.DateField("Data de Fundação")
    mascote = models.CharField(max_length=100, blank=True)
    cores = models.CharField("Cores", max_length=100)
    logo = models.ImageField(upload_to='logos_torcida/', blank=True)
    historia = models.TextField("Histórico", blank=True)
    
    def __str__(self):
        return self.nome



class Caravana(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='caravanas')
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, verbose_name="Jogo Alvo")
    titulo = models.CharField(max_length=200, help_text="Ex: Invasão do Maracanã")
    
    saida_local = models.CharField("Local de Saída", max_length=200)
    saida_horario = models.DateTimeField("Horário de Saída")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vagas_totais = models.IntegerField()
    
    passageiros = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='caravanas_inscritas', blank=True)

    def vagas_restantes(self):
        return self.vagas_totais - self.passageiros.count()

    def __str__(self):
        return f"Caravana: {self.titulo}"
     
class Evento(models.Model):
    torcida = models.ForeignKey('Torcida', on_delete=models.CASCADE, related_name='torcida_eventos')
    titulo = models.CharField(max_length=100)
    data_evento = models.DateTimeField()
    local = models.CharField(max_length=255)
    
    # NOVOS CAMPOS
    imagem_capa = models.ImageField(upload_to='eventos/', null=True, blank=True)
    informativo = models.TextField(help_text="Texto detalhado sobre o evento", blank=True)
    
    def __str__(self):
        return self.titulo