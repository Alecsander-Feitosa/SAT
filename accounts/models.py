from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from organizadas.models import Torcida
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta


# INICIO DA ATUALIZAÇÃO: Classe Perfil (Arquivo: accounts/models.py)
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to='perfil_fotos/', null=True, blank=True)
    time_coracao = models.CharField("Time do Coração", max_length=100, null=True, blank=True)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True)    
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    aprovado = models.BooleanField(default=False)
    
    # Dados Pessoais
    data_nascimento = models.DateField(null=True, blank=True)
    nome_mae = models.CharField("Nome da Mãe", max_length=150, blank=True) # <- ADICIONAR ESTA LINHA
    nome_pai = models.CharField("Nome do Pai", max_length=150, blank=True) # <- ADICIONAR ESTA LINHA
    rg_cnh = models.CharField("RG ou CNH", max_length=20, blank=True)
    orgao_expedidor = models.CharField(max_length=20, blank=True)
    
    # Endereço
    cep = models.CharField(max_length=9, blank=True)
    rua = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=10, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    
    # Documentos
    doc_frente = models.ImageField(upload_to='documentos/frente/', blank=True, null=True)
    doc_verso = models.ImageField(upload_to='documentos/verso/', blank=True, null=True)
    doc_selfie = models.ImageField(upload_to='documentos/selfie/', blank=True, null=True)
    
    # Informações da Torcida
    vulgo = models.CharField(max_length=50, blank=True)
    pelotao = models.CharField(max_length=50, blank=True)
    rede_social = models.CharField(max_length=100, blank=True)
    seguidores = models.ManyToManyField(User, related_name='seguindo', blank=True)
    
    # NOVOS CAMPOS PARA FAVORITAR (SALVAR)
    eventos_salvos = models.ManyToManyField('organizadas.Evento', related_name='salvo_por', blank=True)
    caravanas_salvas = models.ManyToManyField('organizadas.Caravana', related_name='salvo_por', blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

# NOVO MODELO (Coloque no final do arquivo)
class PresencaCaravana(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    caravana = models.ForeignKey('organizadas.Caravana', on_delete=models.CASCADE, related_name='presencas_caravana')
    data_confirmacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'caravana') # Impede que o usuário confirme 2 vezes na mesma caravana




# --- NOVO: Histórico KYC (Veiculação/Aprovações) ---
class HistoricoSocio(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='historico_kyc')
    data_acao = models.DateTimeField(auto_now_add=True)
    acao = models.CharField(max_length=100, help_text="Ex: Aprovado, Rejeitado, Documentos Enviados")
    observacao = models.TextField(blank=True)
    moderador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

# --- NOVO: Campos Personalizados ---
class CampoPersonalizado(models.Model):
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, related_name='campos_personalizados')
    nome_campo = models.CharField(max_length=100, help_text="Ex: Qual o seu tamanho de camisa?")
    obrigatorio = models.BooleanField(default=False)

class RespostaCampo(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='respostas_customizadas')
    campo = models.ForeignKey(CampoPersonalizado, on_delete=models.CASCADE)
    resposta = models.CharField(max_length=255)

# --- ATUALIZADO: Convites de Aliadas ---
class Aliada(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceito', 'Aceito'),
        ('recusado', 'Recusado')
    ]
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='aliadas_enviadas')
    torcida_convidada = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='convites_recebidos', null=True, blank=True)
    nome_organizada = models.CharField(max_length=100) # Caso seja uma torcida fora do SAT
    clube = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='torcidas/aliadas/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    def __str__(self):
        return f"{self.nome_organizada} ({self.clube})"

# --- ATUALIZADO: Canções ---
class Cancao(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='cancoes')
    titulo = models.CharField(max_length=100)
    descricao = models.TextField("Descrição/Contexto", blank=True)
    letra = models.TextField(blank=True, null=True, help_text="Letra completa da música")
    video_url = models.URLField(blank=True, null=True, help_text="Link embed do vídeo")
    arquivo_audio = models.FileField(upload_to='cancoes/audio/', blank=True, null=True)

    def __str__(self):
        return self.titulo
    

class Presenca(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # CORREÇÃO: Adicione 'organizadas.Evento' como o primeiro argumento
    evento = models.ForeignKey('organizadas.Evento', on_delete=models.CASCADE, related_name='presencas')
    data_confirmacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.evento.titulo}"

class Conquista(models.Model):
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    icone = models.CharField(max_length=50, help_text="Nome do ícone do Bootstrap (ex: bi-award)")
    xp_necessario = models.IntegerField(default=0)
    cor_hex = models.CharField(max_length=7, default="#D37129")

    def __str__(self):
        return self.titulo
    

class CheckIn(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Adicionamos o related_name='checkins_accounts' para diferenciar do outro app
    evento = models.ForeignKey(
        'organizadas.Evento', 
        on_delete=models.CASCADE, 
        related_name='checkins_accounts'
    )
    foto = models.ImageField(upload_to='checkins/', null=True, blank=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    validado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'evento')


class Evento(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    local = models.CharField(max_length=255) # Ex: Arena Castelão
    data = models.DateTimeField()
    xp_recompensa = models.IntegerField(default=50)
    ativo = models.BooleanField(default=True)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True)
    data = models.DateTimeField()
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    raio_checkin = models.IntegerField(default=500, help_text="Raio em metros para permitir check-in")
   
    def __str__(self):
        return self.nome
    

# accounts/models.py

class PlanoSocio(models.Model):
    ativo = models.BooleanField("Plano Ativo?", default=True)
    nome = models.CharField("Nome do Plano", max_length=100)
    preco = models.DecimalField("Preço Mensal", max_digits=7, decimal_places=2)
    beneficios = models.TextField("Benefícios (um por linha)")
    destaque = models.BooleanField("Plano Destaque?", default=False)
    
    # Se torcida for NULL, é um plano geral da SAT
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True, related_name='planos_socio')

    def get_beneficios_lista(self):
        return self.beneficios.split('\n')

    def __str__(self):
        return f"{self.nome} - {self.torcida.nome if self.torcida else 'SAT'}"

# SAT/accounts/models.py

class Assinatura(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(PlanoSocio, on_delete=models.RESTRICT)
    data_inicio = models.DateField(auto_now_add=True)
    ativa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.perfil.user.username} - {self.plano.nome}"

class Fatura(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]
    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name='faturas')
    valor = models.DecimalField(max_digits=7, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    metodo_pagamento = models.CharField(max_length=50, blank=True, help_text="Ex: PIX, Cartão")

    def __str__(self):
        return f"Fatura {self.id} - {self.status}"