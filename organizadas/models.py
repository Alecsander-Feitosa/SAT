from django.db import models
from django.conf import settings
from gamification.models import Partida
from django.contrib.auth.models import User
from django.utils import timezone


class Torcida(models.Model):
    nome = models.CharField("Nome da Torcida", max_length=150, unique=True)
    sigla = models.CharField("Sigla (Ex: TJF, MV)", max_length=10, blank=True, null=True)
    slug = models.SlugField(unique=True)
    fundacao = models.DateField("Data de Fundação")
    mascote = models.CharField("Mascote", max_length=100, blank=True)
    lema = models.CharField("Lema da Torcida", max_length=200, blank=True)
    historia = models.TextField("Histórico", blank=True)
    
    # --- IDENTIDADE VISUAL ---
    logo = models.ImageField("Logótipo / Escudo", upload_to='logos_torcida/', blank=True)
    imagem_fundo = models.ImageField("Imagem de Fundo (Login/App)", upload_to='fundos_torcida/', blank=True, null=True)
    
    # --- PERSONALIZAÇÃO DE CORES (Baseado nas tuas Telas ADM) ---
    cor_primaria = models.CharField("Cor Primária", max_length=7, default="#D37129")
    cor_secundaria = models.CharField("Cor Secundária", max_length=7, default="#FFFFFF")
    cor_terciaria = models.CharField("Cor Terciária", max_length=7, default="#000000")
    cor_fundo = models.CharField("Cor de Fundo do App", max_length=7, default="#121212")
    
    def __str__(self):
        return f"{self.nome} ({self.sigla})" if self.sigla else self.nome


class Caravana(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='caravanas')
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, verbose_name="Jogo Alvo")
    titulo = models.CharField(max_length=200, help_text="Ex: Invasão do Maracanã")
    
    saida_local = models.CharField("Local de Saída", max_length=200)
    saida_horario = models.DateTimeField("Horário de Saída")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vagas_totais = models.IntegerField()
    
    passageiros = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='caravanas_inscritas', blank=True)

    def vagas_restantes(self):
        return self.vagas_totais - self.passageiros.count()

    def __str__(self):
        return f"Caravana: {self.titulo}"
     
class Evento(models.Model):
    # Use o nome do modelo sem aspas se ele estiver no mesmo arquivo acima
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='torcida_eventos', null=True, blank=True)
    titulo = models.CharField(max_length=100)
    data = models.DateTimeField() # Padronizando para 'data' como a view espera
    local = models.CharField(max_length=255)
    imagem_capa = models.ImageField(upload_to='eventos/', null=True, blank=True)
    informativo = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

# Em organizadas/models.py

class Noticia(models.Model):
    # 1. Campos do Modelo
    titulo = models.CharField("Título", max_length=200)
    subtitulo = models.CharField("Subtítulo", max_length=255, blank=True)
    conteudo = models.TextField("Conteúdo")
    imagem = models.ImageField("Imagem de Capa", upload_to='noticias/')
    data_publicacao = models.DateTimeField(auto_now_add=True)
    autor = models.CharField("Autor", max_length=100, default="Imprensa SAT")

    # 2. A class Meta entra AQUI (dentro da classe Noticia)
    class Meta:
        verbose_name = "Notícia"
        verbose_name_plural = "Notícias"

    # 3. Métodos (opcional)
    def __str__(self):
        return self.titulo


class Post(models.Model):
    # O campo chama-se 'autor', e o 'related_name' é um parâmetro extra
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizadas_posts')
    torcida = models.ForeignKey('Torcida', on_delete=models.CASCADE)
    texto = models.TextField(max_length=500)
    imagem = models.ImageField(upload_to='posts/', null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_criacao']


class Curtida(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='curtidas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_curtida = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'usuario') # Garante 1 curtida por pessoa

    def __str__(self):
        return f"{self.usuario.username} curtiu o post {self.post.id}"
    

class Parceiro(models.Model):
    nome = models.CharField("Nome do Parceiro", max_length=100)
    logo = models.ImageField("Logo", upload_to='parceiros/', blank=True, null=True)
    link = models.URLField("Link do Parceiro", blank=True, null=True, help_text="Link para o site ou Instagram do parceiro")
    torcida = models.ForeignKey(
        Torcida, 
        on_delete=models.CASCADE, 
        related_name='parceiros', 
        blank=True, 
        null=True, 
        help_text="Deixe em branco se for um parceiro global da SAT"
    )

    class Meta:
        verbose_name = "Parceiro"
        verbose_name_plural = "Parceiros"

    def __str__(self):
        return self.nome
    


class Publicidade(models.Model):
    titulo = models.CharField("Nome da Campanha/Cliente", max_length=150)
    imagem = models.ImageField("Imagem do Banner (Retangular)", upload_to='publicidade/')
    link = models.URLField("Link de Destino", blank=True, null=True, help_text="Link para onde o utilizador vai ao clicar")
    
    data_inicio = models.DateTimeField("Data de Início da Campanha")
    data_fim = models.DateTimeField("Data de Término da Campanha")
    tempo_exibicao = models.PositiveIntegerField("Tempo na tela (Segundos)", default=5, help_text="Quantos segundos este banner aparece antes de trocar para o próximo.")
    
    ativo = models.BooleanField("Ativar Anúncio", default=True)
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, blank=True, null=True, help_text="Deixe em branco para exibir para todas as torcidas.")

    class Meta:
        verbose_name = "Publicidade Paga"
        verbose_name_plural = "Publicidades Pagas"

    def __str__(self):
        return self.titulo
    

class Comentario(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField("Comentário", max_length=300)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_criacao'] # Organiza dos mais antigos para os mais recentes

    def __str__(self):
        return f"Comentário de {self.autor.username} no post {self.post.id}"
    
# Adicione no final de organizadas/models.py

class FotoGaleria(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='fotos_galeria')
    imagem = models.ImageField("Foto", upload_to='galeria_torcida/')
    legenda = models.CharField("Legenda", max_length=200, blank=True)
    data_publicacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foto da Galeria"
        verbose_name_plural = "Fotos da Galeria"

    def __str__(self):
        return f"Foto de {self.torcida.nome} - {self.data_publicacao.strftime('%d/%m/%Y')}"

class ConquistaTorcida(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='conquistas')
    titulo = models.CharField("Título da Conquista", max_length=150, help_text="Ex: Maior Bandeirão, Campeão do Carnaval")
    ano = models.IntegerField("Ano")
    descricao = models.TextField("Descrição", blank=True)
    imagem = models.ImageField("Foto da Conquista", upload_to='conquistas_torcida/', blank=True, null=True)

    class Meta:
        verbose_name = "Conquista"
        verbose_name_plural = "Conquistas"

    def __str__(self):
        return f"{self.titulo} ({self.ano}) - {self.torcida.sigla}"

class MembroDiretoria(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='diretoria')
    nome = models.CharField("Nome", max_length=100)
    cargo = models.CharField("Cargo", max_length=100, help_text="Ex: Presidente, Diretor de Bateria, Puxador")
    foto = models.ImageField("Foto de Perfil", upload_to='diretoria_torcida/', blank=True, null=True)
    ordem = models.IntegerField("Ordem de Exibição", default=0, help_text="0 aparece primeiro (Ex: Presidente)")

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Membro da Diretoria"
        verbose_name_plural = "Membros da Diretoria"

    def __str__(self):
        return f"{self.nome} - {self.cargo}"

class Regra(models.Model):
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='regras')
    titulo = models.CharField("Título da Regra", max_length=150)
    descricao = models.TextField("Descrição da Regra")
    ordem = models.IntegerField("Ordem (Nº da Regra)", default=1)

    class Meta:
        ordering = ['ordem']
        verbose_name = "Regra/Estatuto"
        verbose_name_plural = "Regras/Estatutos"

    def __str__(self):
        return f"Regra {self.ordem}: {self.titulo} ({self.torcida.sigla})"