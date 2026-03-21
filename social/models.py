# INICIO DA ATUALIZAÇÃO: Imports e Classe Post (Arquivo: social/models.py)
from django.db import models
from django.contrib.auth import get_user_model

# CORREÇÃO AQUI: A importação correta da Torcida é do app 'organizadas'
from organizadas.models import Torcida

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
    
    # Mantemos null=True e blank=True: Permite que torcedores comuns postem sem pertencer a organizadas
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='posts_noticias', null=True, blank=True)
    
    # ATUALIZAÇÃO AQUI: Novo campo de filtro principal da SAT Social
    # Herdaremos isso do autor do post para montar o feed segmentado do usuário
    time_relacionado = models.CharField("Time Relacionado", max_length=100, null=True, blank=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    curtidas = models.ManyToManyField(User, related_name='post_curtidas', blank=True)

    def total_curtidas(self):
        return self.curtidas.count()
# FIM DA ATUALIZAÇÃO: Imports e Classe Post

class Comentario(models.Model):
    
    post = models.ForeignKey(Post, related_name='comentarios', on_delete=models.CASCADE)
    autor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comentarios_sociais' # <--- ADICIONE ISSO
    )
    texto = models.TextField()
    data = models.DateTimeField(auto_now_add=True)