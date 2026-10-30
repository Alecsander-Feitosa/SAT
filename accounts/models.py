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
    
    # Verificação dos documentos (frente, verso e selfie) pela moderação
    STATUS_DOCUMENTOS = [
        ('pendente', 'Documentos pendentes'),
        ('em_analise', 'Em análise'),
        ('verificado', 'Verificado'),
        ('recusado', 'Recusado'),
    ]
    docs_status = models.CharField("Verificação de documentos", max_length=12, choices=STATUS_DOCUMENTOS, default='pendente')
    docs_motivo = models.CharField("Motivo da recusa", max_length=255, blank=True)
    docs_analisado_em = models.DateTimeField(null=True, blank=True)
    docs_analisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_analisados')

    # Cargo especial na rede social (atribuído manualmente no /admin)
    CARGOS_ESPECIAIS = [
        ('', 'Nenhum'),
        ('presidente', 'Presidente (líder oficial da torcida)'),
        ('desenvolvedor', 'Desenvolvedor (equipe SAT)'),
    ]
    cargo_especial = models.CharField("Cargo especial", max_length=20, choices=CARGOS_ESPECIAIS, blank=True, default='')

    # NOVOS CAMPOS PARA FAVORITAR (SALVAR)
    eventos_salvos = models.ManyToManyField('organizadas.Evento', related_name='salvo_por', blank=True)
    caravanas_salvas = models.ManyToManyField('organizadas.Caravana', related_name='salvo_por', blank=True)

    @property
    def is_completo(self):
        # Todos os campos da aba de edição precisam estar preenchidos
        campos_obrigatorios = [
            self.cpf, self.whatsapp, self.data_nascimento,
            self.rg_cnh, self.orgao_expedidor, self.cep, 
            self.rua, self.numero, self.bairro, self.cidade, self.uf,
            self.doc_frente, self.doc_verso, self.doc_selfie, self.foto
        ]
        return all(bool(campo) for campo in campos_obrigatorios)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._torcida_original = self.torcida_id

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Registra no histórico sempre que o torcedor entra/sai/troca de torcida
        if self.torcida_id != self._torcida_original:
            agora = timezone.now()
            PassagemTorcida.objects.filter(perfil=self, saida__isnull=True).update(saida=agora)
            if self.torcida_id:
                PassagemTorcida.objects.create(
                    perfil=self, torcida_id=self.torcida_id,
                    torcida_nome=self.torcida.nome, entrada=agora,
                )
            self._torcida_original = self.torcida_id

    @property
    def docs_completos(self):
        return bool(self.doc_frente and self.doc_verso and self.doc_selfie)

    @classmethod
    def por_matricula(cls, codigo):
        """Encontra o sócio pela matrícula (ex: 2026.000046-9), conferindo o dígito verificador."""
        import re
        m = re.fullmatch(r'\s*(\d{4})\.?(\d{6})-?(\d)\s*', codigo or '')
        if not m:
            return None
        perfil = cls.objects.select_related('user', 'torcida').filter(user_id=int(m.group(2))).first()
        if perfil and perfil.matricula.replace('.', '').replace('-', '') == ''.join(m.groups()):
            return perfil
        return None

    @property
    def matricula(self):
        """
        Matrícula SAT padronizada e fixa: ANO DE CADASTRO + ID com 6 dígitos + dígito verificador (módulo 11).
        Ex: 2026.000034-7. Não muda se o sócio trocar de torcida ou de plano.
        """
        ano = self.user.date_joined.year if self.user_id else timezone.now().year
        base = f"{ano}{self.user_id or 0:06d}"
        soma = sum(int(d) * peso for d, peso in zip(reversed(base), range(2, 2 + len(base))))
        dv = 11 - (soma % 11)
        dv = 0 if dv >= 10 else dv
        return f"{ano}.{self.user_id or 0:06d}-{dv}"

    @property
    def assinatura_vigente(self):
        """Assinatura ativa e dentro da validade (cacheada por requisição)."""
        if not hasattr(self, '_assinatura_vigente'):
            hoje = timezone.localdate()
            self._assinatura_vigente = (
                self.assinaturas.filter(ativa=True)
                .filter(models.Q(valida_ate__isnull=True) | models.Q(valida_ate__gte=hoje))
                .select_related('plano').order_by('-id').first()
            )
        return self._assinatura_vigente

    @property
    def nivel_plano(self):
        assinatura = self.assinatura_vigente
        return (assinatura.plano.nivel if assinatura and assinatura.plano.nivel else 'gratis')

    @property
    def plano(self):
        """Nome do nível exibido nos cartões de sócio (ex: OURO)."""
        return dict(NIVEIS_PLANO)[self.nivel_plano].upper()

    def __str__(self):
        return f"Perfil de {self.user.username}"

# NOVO MODELO (Coloque no final do arquivo)
class PresencaCaravana(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    caravana = models.ForeignKey('organizadas.Caravana', on_delete=models.CASCADE, related_name='presencas_caravana')
    data_confirmacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'caravana') # Impede que o usuário confirme 2 vezes na mesma caravana




# --- Histórico de torcidas do sócio (selos no verso da carteirinha) ---
class PassagemTorcida(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='passagens_torcida')
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.SET_NULL, null=True, blank=True, related_name='passagens')
    torcida_nome = models.CharField(max_length=200, help_text="Guardado para o histórico não sumir se a torcida for excluída")
    entrada = models.DateTimeField()
    saida = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-entrada']
        verbose_name = 'Passagem por Torcida'
        verbose_name_plural = 'Histórico de Torcidas'

    @property
    def atual(self):
        return self.saida is None

    def __str__(self):
        return f"{self.perfil.user.username} - {self.torcida_nome}"


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

# Níveis oficiais da SAT (valem para todas as torcidas), do menor para o maior
NIVEIS_PLANO = [
    ('gratis', 'Grátis'),
    ('bronze', 'Bronze'),
    ('prata', 'Prata'),
    ('ouro', 'Ouro'),
]
ORDEM_NIVEL = {valor: i for i, (valor, _) in enumerate(NIVEIS_PLANO)}


class PlanoSocio(models.Model):
    ativo = models.BooleanField("Plano Ativo?", default=True)
    nome = models.CharField("Nome do Plano", max_length=100)
    preco = models.DecimalField("Preço Mensal", max_digits=7, decimal_places=2)
    beneficios = models.TextField("Benefícios (um por linha)")
    destaque = models.BooleanField("Plano Destaque?", default=False)
    nivel = models.CharField("Nível", max_length=10, choices=NIVEIS_PLANO, null=True, blank=True,
                             help_text="Nível oficial SAT (Grátis, Bronze, Prata, Ouro). Vazio = plano antigo.")

    # Se torcida for NULL, é um plano geral da SAT
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, null=True, blank=True, related_name='planos_socio')

    @property
    def gratuito(self):
        return self.preco == 0

    def get_beneficios_lista(self):
        return [b.strip() for b in self.beneficios.split('\n') if b.strip()]

    def __str__(self):
        return f"{self.nome} - {self.torcida.nome if self.torcida else 'SAT'}"


class BeneficioTorcida(models.Model):
    """Benefício extra que cada torcida oferece além dos benefícios oficiais do plano."""
    torcida = models.ForeignKey('organizadas.Torcida', on_delete=models.CASCADE, related_name='beneficios_extras')
    nivel_minimo = models.CharField("Liberado a partir do plano", max_length=10, choices=NIVEIS_PLANO, default='bronze')
    titulo = models.CharField("Benefício", max_length=120, help_text="Ex: 10% de desconto na sede")
    descricao = models.CharField("Detalhes", max_length=255, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Benefício da Torcida'
        verbose_name_plural = 'Benefícios das Torcidas'

    def __str__(self):
        return f"{self.titulo} ({self.get_nivel_minimo_display()}+) - {self.torcida.nome}"

# SAT/accounts/models.py

class Assinatura(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(PlanoSocio, on_delete=models.RESTRICT)
    data_inicio = models.DateField(auto_now_add=True)
    ativa = models.BooleanField(default=True)
    valida_ate = models.DateField("Válida até", null=True, blank=True, help_text="Vazio = sem vencimento (plano grátis)")

    @property
    def vigente(self):
        return self.ativa and (self.valida_ate is None or self.valida_ate >= timezone.localdate())

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
    
    # --- Integração Efí Bank (PIX) ---
    txid = models.CharField(max_length=35, blank=True, null=True, help_text="ID da transação na Efí Bank")
    loc_id = models.IntegerField(blank=True, null=True, help_text="ID da location (Payload do PIX)")
    pix_copia_e_cola = models.TextField(blank=True, null=True)
    pix_qrcode = models.TextField(blank=True, null=True, help_text="URL ou base64 da imagem do QR Code")

    def __str__(self):
        return f"Fatura {self.id} - {self.status}"

class DispositivoSessao(models.Model):
    """Aparelhos com sessão aberta (Segurança > Dispositivos conectados)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispositivos')
    session_key = models.CharField(max_length=40, unique=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_acesso = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ultimo_acesso']

    @property
    def descricao(self):
        """Ex: 'Chrome no Android'."""
        ua = self.user_agent.lower()
        sistema = next((n for chave, n in [('android', 'Android'), ('iphone', 'iPhone'), ('ipad', 'iPad'),
                                           ('windows', 'Windows'), ('mac os', 'Mac'), ('linux', 'Linux')] if chave in ua), 'Dispositivo')
        navegador = next((n for chave, n in [('edg', 'Edge'), ('opr', 'Opera'), ('samsungbrowser', 'Samsung Internet'),
                                             ('chrome', 'Chrome'), ('firefox', 'Firefox'), ('safari', 'Safari')] if chave in ua), 'Navegador')
        return f"{navegador} no {sistema}"

    @property
    def movel(self):
        return any(x in self.user_agent.lower() for x in ('android', 'iphone', 'ipad', 'mobile'))
