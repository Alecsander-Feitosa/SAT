from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from organizadas.models import Torcida
from django.db import models
from django.contrib.auth.models import User


# INICIO DA ATUALIZAÇÃO: Classe Perfil (Arquivo: accounts/models.py)
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to='perfil_fotos/', null=True, blank=True)
    
    # Mantemos o time do coração em destaque e opcional. 
    # Ele será o grande motor do Nível 1 (Público Geral).
    time_coracao = models.CharField("Time do Coração", max_length=100, null=True, blank=True)
    
    # ATUALIZAÇÃO AQUI: Adicionado blank=True
    # Agora a torcida é 100% opcional tanto no banco quanto nos formulários do sistema.
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True)
    
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    aprovado = models.BooleanField(default=False)
    
    # --- DADOS PESSOAIS ADICIONADOS ---
    data_nascimento = models.DateField(null=True, blank=True)
    rg_cnh = models.CharField("RG ou CNH", max_length=20, blank=True)
    orgao_expedidor = models.CharField(max_length=20, blank=True)
    
    # --- ENDEREÇO ---
    cep = models.CharField(max_length=9, blank=True)
    rua = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=10, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    
    # --- DOCUMENTOS E VERIFICAÇÃO ---
    foto_documento_frente = models.ImageField(upload_to='docs/', blank=True)
    foto_documento_verso = models.ImageField(upload_to='docs/', blank=True)
    verificacao_facial = models.ImageField(upload_to='selfies/', blank=True)
    
    # --- INFORMAÇÕES DA TORCIDA ---
    vulgo = models.CharField(max_length=50, blank=True)
    pelotao = models.CharField(max_length=50, blank=True)
    rede_social = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"
# FIM DA ATUALIZAÇÃO: Classe Perfil


class Aliada(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='aliadas')
    nome_organizada = models.CharField(max_length=100)
    clube = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='torcidas/aliadas/', blank=True, null=True)

    def __str__(self):
        return f"{self.nome_organizada} ({self.clube})"

class Cancao(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='cancoes')
    titulo = models.CharField(max_length=100)
    letra = models.TextField()

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
