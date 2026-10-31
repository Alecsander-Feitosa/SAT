# INICIO DA ATUALIZAÇÃO: Imports e Classe Post (Arquivo: social/models.py)
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from organizadas.models import Torcida, Evento, Caravana, ConquistaTorcida, FotoGaleria
User = get_user_model()

VISIBILIDADES = [
    ('global', 'Global (todos)'),
    ('torcida', 'Só a minha torcida'),
    ('amigos', 'Só amigos'),
]
TIPOS_POST = [
    ('normal', 'Normal'),
    ('convocacao', 'Convocação (Presidente)'),
    ('anuncio', 'Anúncio oficial (Desenvolvedor)'),
]


class Post(models.Model):
    autor_s = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts_redesocial'
    )
    titulo = models.CharField(max_length=200)
    texto = models.TextField() 
    imagem = models.ImageField(upload_to='posts/', null=True, blank=True)
    
    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, related_name='posts_noticias', null=True, blank=True)
    time_relacionado = models.CharField("Time Relacionado", max_length=100, null=True, blank=True)
    
    # --- NOVOS CAMPOS DE COMPARTILHAMENTO ---
    # Permitem anexar um item oficial da torcida à publicação do mural
    evento_relacionado = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    caravana_relacionada = models.ForeignKey(Caravana, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    conquista_relacionada = models.ForeignKey(ConquistaTorcida, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    foto_relacionada = models.ForeignKey(FotoGaleria, on_delete=models.SET_NULL, null=True, blank=True, related_name='compartilhamentos')
    # ----------------------------------------

    data_criacao = models.DateTimeField(auto_now_add=True)
    curtidas = models.ManyToManyField(User, related_name='post_curtidas', blank=True)

    # Quem vê: global (todos), torcida (só membros da torcida do post) ou amigos (aparece no global só para amigos)
    visibilidade = models.CharField(max_length=10, choices=VISIBILIDADES, default='global')
    tipo = models.CharField(max_length=12, choices=TIPOS_POST, default='normal')
    em_revisao = models.BooleanField(default=False, help_text="Muito denunciado: oculto até a revisão dos administradores")

    def total_curtidas(self):
        return self.curtidas.count()

class PostMedia(models.Model):
    post = models.ForeignKey(Post, related_name='midias', on_delete=models.CASCADE)
    arquivo = models.FileField(upload_to='posts/media/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'webm'])])
    is_video = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)

class Comentario(models.Model):
    
    post = models.ForeignKey(Post, related_name='comentarios', on_delete=models.CASCADE)
    autor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comentarios_sociais' # <--- ADICIONE ISSO
    )
    texto = models.TextField()
    data = models.DateTimeField(auto_now_add=True)
    oculto = models.BooleanField(default=False, help_text="Ocultado por um moderador")

# =====================================================================
# Visibilidade, moderação e notificações da SAT Social
# =====================================================================


class DenunciaPost(models.Model):
    MOTIVOS = [
        ('ofensa', 'Ofensa / discurso de ódio'),
        ('violencia', 'Incitação à violência'),
        ('spam', 'Spam / golpe'),
        ('nudez', 'Nudez ou conteúdo sexual'),
        ('falso', 'Informação falsa'),
        ('outro', 'Outro'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='denuncias')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='denuncias_feitas')
    motivo = models.CharField(max_length=12, choices=MOTIVOS)
    detalhe = models.CharField(max_length=300, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        constraints = [models.UniqueConstraint(fields=['post', 'autor'], name='uma_denuncia_por_usuario')]
        verbose_name = 'Denúncia de post'
        verbose_name_plural = 'Denúncias de posts'


class Notificacao(models.Model):
    TIPOS = [
        ('curtida', 'Curtida'),
        ('comentario', 'Comentário'),
        ('seguidor', 'Novo seguidor'),
        ('amigo', 'Novo amigo'),
        ('convocacao', 'Convocação'),
        ('anuncio', 'Anúncio oficial'),
        ('evento_epico', 'Evento épico'),
        ('xp', 'Bônus de EXP'),
        ('nivel', 'Subiu de nível'),
        ('moderacao', 'Moderação'),
        ('pedido', 'Pedido da loja'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes_sociais')
    ator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    tipo = models.CharField(max_length=15, choices=TIPOS)
    texto = models.CharField(max_length=255)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    link = models.CharField(max_length=255, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'


class Penalidade(models.Model):
    TIPOS = [
        ('suspensao', 'Suspensão de postagem'),
        ('ban', 'Banimento da rede social'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penalidades_sociais')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    motivo = models.CharField(max_length=255)
    inicio = models.DateTimeField(default=timezone.now)
    fim = models.DateTimeField(null=True, blank=True, help_text="Vazio = permanente")
    aplicada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    revogada = models.BooleanField(default=False)

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'Penalidade'

    @property
    def ativa(self):
        agora = timezone.now()
        return not self.revogada and self.inicio <= agora and (self.fim is None or self.fim > agora)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.user.username}"


class CPFBloqueado(models.Model):
    """Lista negra: o CPF banido não volta para a rede social nem criando outra conta."""
    cpf = models.CharField(max_length=11, unique=True, help_text="Somente números")
    motivo = models.CharField(max_length=255)
    ate = models.DateTimeField(null=True, blank=True, help_text="Vazio = permanente")
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        verbose_name = 'CPF bloqueado'
        verbose_name_plural = 'CPFs bloqueados (lista negra)'

    @property
    def ativo(self):
        return self.ate is None or self.ate > timezone.now()

    def __str__(self):
        return f"{self.cpf[:3]}.***.***-{self.cpf[-2:]}"


class Popup(models.Model):
    """Pop-up de aviso. Sem torcida = aviso da SAT para todos; com torcida = só para os membros dela."""
    MODOS = [
        ('tempo', 'Fecha sozinho (1 a 10s)'),
        ('manual', 'O usuário fecha'),
    ]
    LIMITE_DIARIO_TORCIDA = 3

    torcida = models.ForeignKey(Torcida, on_delete=models.CASCADE, null=True, blank=True, related_name='popups',
                                help_text="Vazio = aviso da SAT para todos os usuários")
    titulo = models.CharField(max_length=80)
    mensagem = models.TextField(max_length=500, blank=True)
    imagem = models.ImageField(upload_to='popups/', null=True, blank=True)
    link = models.CharField(max_length=255, blank=True)
    texto_botao = models.CharField(max_length=30, blank=True, help_text="Ex: Ver evento (só aparece se tiver link)")
    modo = models.CharField(max_length=10, choices=MODOS, default='manual')
    duracao = models.PositiveSmallIntegerField("Duração (s)", default=5, help_text="Só no modo 'fecha sozinho': 1 a 10 segundos")
    exibir_em = models.DateTimeField("Aparece a partir de", default=timezone.now)
    exibir_ate = models.DateTimeField("Aparece até", null=True, blank=True, help_text="Vazio = até todos verem")
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-exibir_em']
        verbose_name = 'Pop-up'
        verbose_name_plural = 'Pop-ups'

    def __str__(self):
        return f"{self.titulo} ({self.torcida or 'SAT'})"


class PopupVisto(models.Model):
    popup = models.ForeignKey(Popup, on_delete=models.CASCADE, related_name='vistos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    visto_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['popup', 'usuario'], name='popup_visto_uma_vez')]


class AvisoCabecalho(models.Model):
    """Faixa fixa no topo do app para todos. Os admins ligam e desligam quando quiserem."""
    CORES = [
        ('info', 'Azul (informação)'),
        ('alerta', 'Amarelo (atenção)'),
        ('urgente', 'Vermelho (urgente)'),
        ('tema', 'Cor da SAT'),
    ]
    texto = models.CharField(max_length=160)
    link = models.CharField(max_length=255, blank=True)
    cor = models.CharField(max_length=10, choices=CORES, default='info')
    ativo = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizado_em']
        verbose_name = 'Aviso de cabeçalho'
        verbose_name_plural = 'Avisos de cabeçalho'

    def __str__(self):
        return self.texto
