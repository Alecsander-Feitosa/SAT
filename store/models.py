from django.db import models
from django.conf import settings

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    def __str__(self): return self.nome
    class Meta: verbose_name_plural = "Categorias"

class Produto(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='produtos', on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.nome

class VariacaoProduto(models.Model):
    produto = models.ForeignKey(Produto, related_name='variacoes', on_delete=models.CASCADE)
    nome = models.CharField("Tamanho/Cor", max_length=50) # Ex: P, M, G
    estoque = models.IntegerField(default=0)

class Pedido(models.Model):
    STATUS_CHOICES = (('P', 'Pendente'), ('A', 'Aprovado'), ('E', 'Enviado'), ('C', 'Cancelado'))
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data_pedido = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)