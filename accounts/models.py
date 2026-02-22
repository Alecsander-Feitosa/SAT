from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from organizadas.models import Torcida





#class Torcida(models.Model):
 #   nome = models.CharField(max_length=100)
 #   escudo = models.ImageField(upload_to='torcidas/escudos/', blank=True, null=True)
 #   historia = models.TextField(blank=True)
 #   diretoria = models.TextField(blank=True)
 #   hino = models.TextField(blank=True)
 #   
 #   def __str__(self):
 #       return self.nome



class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to='perfil_fotos/', null=True, blank=True)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True)
    cpf = models.CharField(max_length=14, unique=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    
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