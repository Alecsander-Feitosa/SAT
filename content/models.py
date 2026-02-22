# content/models.py
from django.db import models
from accounts.models import User
from django.contrib.auth.models import User
from accounts.models import Torcida



class Postagem(models.Model):
    autor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts_noticias'  # Nome único para o app de conteúdo
    )
    texto = models.TextField()
    imagem = models.ImageField(upload_to='feed/', null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    # Sistema de curtidas para engajamento
    curtidas = models.ManyToManyField(User, related_name='posts_curtidos', blank=True)

    class Meta:
        ordering = ['-data_criacao']

class Comentario(models.Model):
    postagem = models.ForeignKey(Postagem, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comentarios_noticias' # <--- ADICIONE ISSO
    )
    texto = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

class Notificacao(models.Model):
    TIPOS = [
        ('INFO', 'Informativo'),
        ('URGENTE', 'Urgente'),
        ('CONQUISTA', 'Nova Medalha'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    titulo = models.CharField(max_length=100)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='INFO')
    lida = models.BooleanField(default=False)
    data_envio = models.DateTimeField(auto_now_add=True)

class Post(models.Model):
    titulo = models.CharField(max_length=200)
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='noticias', null=True, blank=True)
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)

    torcida = models.ForeignKey(
        Torcida, 
        on_delete=models.CASCADE, 
        related_name='noticias', 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return self.titulo