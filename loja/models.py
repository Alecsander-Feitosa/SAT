from django.db import models
from django.contrib.auth.models import User

class Produto(models.Model):
    nome = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to='produtos/')
    categoria = models.CharField(max_length=100)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True)
    estoque = models.IntegerField(default=10)
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True)
    destaque = models.BooleanField(default=False)
    estoque = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.nome

class ItemCarrinho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    adicionado_em = models.DateTimeField(auto_now_add=True)