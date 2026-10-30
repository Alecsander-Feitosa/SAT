# loja/models.py
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Avg
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

    # Variação dupla: cada Variacao combina uma opção de cada eixo (ex: Tamanho P + Cor Preta)
    rotulo_opcao1 = models.CharField("Nome da 1ª variação", max_length=30, default='Tamanho', blank=True)
    rotulo_opcao2 = models.CharField("Nome da 2ª variação", max_length=30, blank=True, help_text="Ex: Cor, Tipo. Vazio = só uma variação")

    tabela_medidas = models.ImageField("Tabela de medidas (imagem)", upload_to='produtos/medidas/', null=True, blank=True)
    tabela_medidas_texto = models.TextField("Tabela de medidas (texto)", blank=True, help_text="Uma linha por tamanho. Ex: P | 50 cm | 70 cm")

    def preco_atual(self):
        if self.preco_promocional and self.preco_promocional < self.preco:
            return self.preco_promocional
        return self.preco

    @property
    def vendedor(self):
        """Quem vende o item: a torcida dona do produto ou a própria SAT."""
        return self.torcida.sigla or self.torcida.nome if self.torcida_id else 'SAT Oficial'

    def media_avaliacoes(self):
        return self.avaliacoes.aggregate(m=Avg('nota'))['m']

    def __str__(self):
        return self.nome
    

# --- NOVO: Múltiplas Imagens do Produto ---
class ImagemProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='imagens_extra')
    imagem = models.ImageField(upload_to='produtos/galeria/')

class Variacao(models.Model):
    produto = models.ForeignKey(Produto, related_name='variacoes', on_delete=models.CASCADE)
    nome = models.CharField("Variação", max_length=50, help_text="1ª opção. Ex: P")
    opcao2 = models.CharField("2ª opção", max_length=50, blank=True, help_text="Ex: Preta")
    estoque = models.PositiveIntegerField(default=0)

    @property
    def descricao(self):
        return f"{self.nome} / {self.opcao2}" if self.opcao2 else self.nome

    def __str__(self):
        return f"{self.produto.nome} - {self.descricao}"


class ItemCarrinho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    adicionado_em = models.DateTimeField(auto_now_add=True)
    variacao = models.ForeignKey(Variacao, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def subtotal(self):
        return self.produto.preco_atual() * self.quantidade

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

    # --- Acompanhamento pelo cliente (Perfil > Meus pedidos) ---
    codigo_rastreio = models.CharField("Código de rastreio", max_length=40, blank=True)
    nota_fiscal = models.FileField("Nota fiscal (PDF)", upload_to='notas_fiscais/', blank=True, null=True)

    # --- Status separados para o cliente: pagamento x entrega ---
    @property
    def status_pagamento(self):
        """(rótulo, cor)"""
        if self.status == 'cancelado':
            return ('Cancelado', 'red')
        if self.status == 'pendente':
            return ('Pagar na sede', 'blue') if self.metodo_pagamento == 'sede' else ('Aguardando pagamento', 'yellow')
        return ('Pago', 'green')

    @property
    def etapas_entrega(self):
        """Linha do tempo: lista de (rótulo, concluída?)."""
        final = 'Retirado na sede' if self.retirada_sede else 'Entregue'
        meio = 'Pronto para retirada' if self.retirada_sede else 'Enviado'
        etapas = ['Pedido realizado', 'Pagamento confirmado', meio, final]
        atual = {'pendente': 0, 'pago': 1, 'enviado': 2, 'aguardando_retirada': 2, 'concluido': 3}.get(self.status, -1)
        return [(rotulo, i <= atual) for i, rotulo in enumerate(etapas)]
    
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
    variacao = models.ForeignKey(Variacao, on_delete=models.SET_NULL, null=True, blank=True)
    variacao_descricao = models.CharField(max_length=110, blank=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario


class AvaliacaoProduto(models.Model):
    produto = models.ForeignKey(Produto, related_name='avaliacoes', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField(validators=[MaxValueValidator(5)])
    comentario = models.CharField(max_length=300, blank=True)
    foto = models.ImageField(upload_to='produtos/avaliacoes/', null=True, blank=True)
    data = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data']
        constraints = [models.UniqueConstraint(fields=['produto', 'usuario'], name='avaliacao_unica_por_usuario')]


class ConfigLoja(models.Model):
    """Banner e dados de envio da loja de cada torcida (torcida vazia = loja SAT Global)."""
    torcida = models.OneToOneField('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True, related_name='config_loja')
    banner_imagem = models.ImageField("Imagem do banner", upload_to='loja/banners/', null=True, blank=True)
    banner_selo = models.CharField("Selo do banner", max_length=30, blank=True, default='Novo Manto')
    banner_titulo = models.CharField("Título do banner", max_length=80, blank=True, default='Linha Arquibancada')
    banner_subtitulo = models.CharField("Subtítulo do banner", max_length=120, blank=True, default='Garanta já com desconto de sócio.')
    banner_link = models.CharField("Link do banner", max_length=255, blank=True, help_text="Opcional. Ex: /loja/produto/12/")
    cep_origem = models.CharField("CEP de onde os produtos são enviados", max_length=9, blank=True)

    def __str__(self):
        return f"Loja {self.torcida or 'SAT Global'}"

