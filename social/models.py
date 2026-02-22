from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Torcida

User = get_user_model()

class Post(models.Model):
    autor_s = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts_redesocial'  # Nome único para o app social
    )

    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    imagem = models.ImageField(upload_to='posts/', null=True, blank=True)
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='posts_noticias', null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    curtidas = models.ManyToManyField(User, related_name='post_curtidas', blank=True)
    

    def total_curtidas(self):
        return self.curtidas.count()

class Comentario(models.Model):
    
    post = models.ForeignKey(Post, related_name='comentarios', on_delete=models.CASCADE)
    autor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comentarios_sociais' # <--- ADICIONE ISSO
    )
    texto = models.TextField()
    data = models.DateTimeField(auto_now_add=True)