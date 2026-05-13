# loja/models.py
from django.db import models
from django.contrib.auth.models import User

## --- NOVO: Categoria de Produto ---
class CategoriaProduto(models.Model):
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

# --- ATUALIZADO: Produto ---
class Produto(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField("Descrição", blank=True, null=True)
    categoria = models.ForeignKey(CategoriaProduto, on_delete=models.SET_NULL, null=True, blank=True)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True)
    
    preco = models.DecimalField("Preço Original", max_digits=10, decimal_places=2)
    preco_promocional = models.DecimalField("Preço Promocional", max_digits=10, decimal_places=2, null=True, blank=True)
    
    estoque = models.PositiveIntegerField(default=0)
    peso = models.DecimalField("Peso (kg)", max_digits=5, decimal_places=3, default=0.500)
    imagem = models.ImageField("Imagem Principal", upload_to='produtos/', null=True, blank=True)
    destaque = models.BooleanField(default=False)

    def preco_atual(self):
        if self.preco_promocional and self.preco_promocional < self.preco:
            return self.preco_promocional
        return self.preco

    def __str__(self):
        return self.nome
    

# --- NOVO: Múltiplas Imagens do Produto ---
class ImagemProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='imagens_extra')
    imagem = models.ImageField(upload_to='produtos/galeria/')

class Variacao(models.Model):
    produto = models.ForeignKey(Produto, related_name='variacoes', on_delete=models.CASCADE)
    nome = models.CharField("Variação", max_length=50, help_text="Ex: Tamanho P, Cor Preta")
    estoque = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.produto.nome} - {self.nome}"


class ItemCarrinho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    adicionado_em = models.DateTimeField(auto_now_add=True)
    variacao = models.ForeignKey(Variacao, on_delete=models.SET_NULL, null=True, blank=True)

class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('enviado', 'Enviado'),
        ('aguardando_retirada', 'Aguardando Retirada'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    PAGAMENTO_CHOICES = [
        ('pix', 'PIX'),
        ('boleto', 'Boleto Bancário'),
        ('cartao', 'Cartão de Crédito'),
        ('sede', 'Pagar na Sede'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_pedido = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente')
    
    # --- Tipo de Entrega ---
    retirada_sede = models.BooleanField("Retirar na Sede?", default=False)
    
    # --- Dados de Entrega e Frete (só para envio) ---
    cep = models.CharField(max_length=9, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    
    valor_frete = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    modalidade_frete = models.CharField(max_length=50, blank=True, null=True)
    
    # --- Método de Pagamento ---
    metodo_pagamento = models.CharField(max_length=20, choices=PAGAMENTO_CHOICES, default='pix')
    
    # --- Integração Efí Bank (PIX) ---
    txid = models.CharField(max_length=35, blank=True, null=True, help_text="ID da transação na Efí Bank")
    loc_id = models.IntegerField(blank=True, null=True, help_text="ID da location (Payload do PIX)")
    pix_copia_e_cola = models.TextField(blank=True, null=True)
    pix_qrcode = models.TextField(blank=True, null=True, help_text="URL ou base64 da imagem do QR Code")

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='itens', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)