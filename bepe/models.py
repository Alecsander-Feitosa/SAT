import secrets

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# --- PRONTUÁRIOS INTERNOS (vinculados aos cadastrados da plataforma) ---
class RegistroProntuario(models.Model):
    TIPO_CHOICES = [
        ('observacao', 'Observação'),
        ('ocorrencia', 'Ocorrência'),
        ('abordagem', 'Abordagem'),
        ('advertencia', 'Advertência'),
        ('impedimento', 'Impedimento / Restrição'),
    ]
    perfil = models.ForeignKey('accounts.Perfil', on_delete=models.CASCADE, related_name='prontuario_bepe')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='observacao')
    titulo = models.CharField("Título", max_length=150)
    descricao = models.TextField("Descrição")
    data_fato = models.DateTimeField("Data do Fato", default=timezone.now)
    local = models.CharField("Local", max_length=200, blank=True)
    anexo = models.FileField(upload_to='bepe/prontuarios/', blank=True, null=True)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='registros_bepe')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_fato']
        verbose_name = 'Registro de Prontuário'
        verbose_name_plural = 'Prontuários'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.perfil.user.username}: {self.titulo}"


# --- GEOLOCALIZAÇÃO (compartilhada pelo torcedor, com consentimento) ---
class LocalizacaoTorcedor(models.Model):
    """
    Última localização conhecida do torcedor. Só é preenchida se ele ativar o compartilhamento;
    ao desativar, as coordenadas são apagadas.
    """
    STATUS_CHOICES = [
        ('ativo', 'Compartilhando'),
        ('recusado', 'Não compartilha'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='localizacao_bepe')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='recusado')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    precisao = models.FloatField("Precisão (m)", null=True, blank=True)
    atualizada_em = models.DateTimeField(null=True, blank=True)
    consentido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Localização de Torcedor'
        verbose_name_plural = 'Localizações de Torcedores'

    @property
    def ativo(self):
        return self.status == 'ativo'

    def __str__(self):
        return f"{self.user.username} ({self.get_status_display()})"


# --- CANAL DIRETO BEPE <-> DIRETORIAS ---
class Conversa(models.Model):
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, related_name='conversas_bepe')
    assunto = models.CharField(max_length=150)
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='conversas_bepe_criadas')
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    encerrada = models.BooleanField(default=False)

    class Meta:
        ordering = ['-atualizada_em']

    def __str__(self):
        return f"{self.torcida.nome} - {self.assunto}"


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    do_bepe = models.BooleanField(default=False, help_text="True = enviada pelo BEPE; False = enviada pela diretoria")
    texto = models.TextField()
    anexo = models.FileField(upload_to='bepe/mensagens/', blank=True, null=True)
    enviada_em = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        ordering = ['enviada_em']


# --- FALE COM O BEPE (denúncias anônimas) ---
def gerar_protocolo():
    # Ex: BP-7K3QX9M2 — sem caracteres ambíguos (0/O, 1/I)
    alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return 'BP-' + ''.join(secrets.choice(alfabeto) for _ in range(8))


class Denuncia(models.Model):
    """
    Denúncia anônima. Propositalmente NÃO guarda usuário, IP, nem nada que identifique quem enviou.
    O denunciante acompanha apenas pelo número de protocolo.
    """
    CATEGORIA_CHOICES = [
        ('violencia', 'Violência / Briga'),
        ('ameaca', 'Ameaça'),
        ('arma', 'Porte de arma / Artefato'),
        ('drogas', 'Drogas'),
        ('cambismo', 'Cambismo / Fraude de ingresso'),
        ('extorsao', 'Extorsão / Cobrança indevida'),
        ('discriminacao', 'Racismo / Discriminação'),
        ('outro', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('nova', 'Recebida'),
        ('em_analise', 'Em análise'),
        ('encaminhada', 'Encaminhada'),
        ('concluida', 'Concluída'),
        ('arquivada', 'Arquivada'),
    ]
    protocolo = models.CharField(max_length=12, unique=True, default=gerar_protocolo, editable=False)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True, related_name='denuncias_bepe')
    descricao = models.TextField("O que aconteceu?")
    local = models.CharField("Onde?", max_length=200, blank=True)
    data_fato = models.DateTimeField("Quando?", null=True, blank=True)
    anexo = models.FileField(upload_to='bepe/denuncias/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nova')
    resposta_publica = models.TextField(blank=True, help_text="Visível para quem consultar o protocolo")
    nota_interna = models.TextField(blank=True, help_text="Visível apenas para o BEPE")
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='denuncias_bepe')
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Denúncia'

    def __str__(self):
        return f"{self.protocolo} - {self.get_categoria_display()}"


# --- ROTAS DAS TORCIDAS (planejamento de deslocamento A x B até o estádio) ---
class PlanoRota(models.Model):
    titulo = models.CharField(max_length=150, help_text="Ex: Vasco x Flamengo - Engenhão")
    data_jogo = models.DateTimeField(null=True, blank=True)
    destino_nome = models.CharField("Destino", max_length=200)
    destino_lat = models.FloatField()
    destino_lng = models.FloatField()

    torcida_a = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True, related_name='rotas_bepe_a')
    origem_a_nome = models.CharField(max_length=200, blank=True)
    origem_a_lat = models.FloatField()
    origem_a_lng = models.FloatField()

    torcida_b = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True, related_name='rotas_bepe_b')
    origem_b_nome = models.CharField(max_length=200, blank=True)
    origem_b_lat = models.FloatField()
    origem_b_lng = models.FloatField()

    # Geometrias calculadas (GeoJSON LineString) e resumo
    rota_a = models.JSONField(null=True, blank=True)
    rota_b = models.JSONField(null=True, blank=True)
    pontos_risco = models.JSONField(default=list, blank=True, help_text="Trechos em que as rotas se aproximam")
    observacoes = models.TextField(blank=True)

    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Plano de Rota'
        verbose_name_plural = 'Planos de Rota'

    def __str__(self):
        return self.titulo


# --- SALA DE REUNIÃO (substitui reuniões presenciais com as diretorias) ---
def gerar_sala():
    return 'SAT-BEPE-' + secrets.token_urlsafe(9).replace('-', '').replace('_', '')


class Reuniao(models.Model):
    titulo = models.CharField(max_length=150)
    pauta = models.TextField(blank=True)
    data_hora = models.DateTimeField()
    duracao_min = models.PositiveIntegerField("Duração (min)", default=60)
    torcidas = models.ManyToManyField('organizadas.Torcida', related_name='reunioes_bepe', blank=True)
    sala = models.CharField(max_length=60, default=gerar_sala, editable=False)
    link_externo = models.URLField("Link Zoom/Meet (opcional)", blank=True,
                                   help_text="Deixe vazio para usar a sala de vídeo automática (Jitsi)")
    cancelada = models.BooleanField(default=False)
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_hora']
        verbose_name = 'Reunião'
        verbose_name_plural = 'Reuniões'

    @property
    def link(self):
        return self.link_externo or f"https://meet.jit.si/{self.sala}"

    @property
    def termino(self):
        return self.data_hora + timezone.timedelta(minutes=self.duracao_min)

    @property
    def acontecendo(self):
        agora = timezone.now()
        return not self.cancelada and self.data_hora - timezone.timedelta(minutes=15) <= agora <= self.termino

    def __str__(self):
        return f"{self.titulo} ({self.data_hora:%d/%m %H:%M})"
