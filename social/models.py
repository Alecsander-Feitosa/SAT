# INICIO DA ATUALIZAÇÃO: Imports e Classe Post (Arquivo: social/models.py)
from django.db import models
from django.contrib.auth import get_user_model
from organizadas.models import Torcida, Evento, Caravana, ConquistaTorcida, FotoGaleria
User = get_user_model()

class Post(models.Model):
    autor_s = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts_redesocial'
    )
    titulo = models.CharField(max_length=200)
    texto = models.TextField() 
    imagem = models.ImageField(upload_to='posts/', null=True, blank=True)
    
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='posts_noticias', null=True, blank=True)
    time_relacionado = models.CharField("Time Relacionado", max_length=100, null=True, blank=True)
    
    # --- NOVOS CAMPOS DE COMPARTILHAMENTO ---
    # Permitem anexar um item oficial da torcida à publicação do mural
    evento_relacionado = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    caravana_relacionada = models.ForeignKey(Caravana, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    conquista_relacionada = models.ForeignKey(ConquistaTorcida, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    foto_relacionada = models.ForeignKey(FotoGaleria, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    # ----------------------------------------

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