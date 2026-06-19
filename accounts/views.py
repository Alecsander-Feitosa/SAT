from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import qrcode
from io import BytesIO
import base64
import requests
from django.db import models
from .models import Perfil, Presenca               # Modelos do App Accounts
from .forms import CadastroForm, PerfilCompletoForm                  
from content.api import api_noticias
from gamification.models import PerfilGamificacao, Nivel # Modelos do App Gamification
from organizadas.models import Torcida, Evento
from django.core.cache import cache
from organizadas.models import Noticia
from organizadas.models import Evento
from django.utils import timezone
from .models import Conquista
from django.contrib.auth.views import LoginView
from .decorators import torcida_required
from content.models import Post as PostGeral
from organizadas.models import Post as PostTorcida
from organizadas.models import Torcida, Evento, Post as PostTorcida, Curtida
from .models import Evento
from organizadas.models import Post, Caravana # Certifique-se de importar os modelos
from django import forms
from gamification.models import PerfilGamificacao
from organizadas.models import Evento, Torcida, Noticia # Removido o Post daqui para evitar confusão
from social.models import Post as SocialPost
from django.contrib.auth.models import User
from organizadas.models import Parceiro
from organizadas.models import Publicidade
from django.db.models import Q, Count
from datetime import date
from organizadas.models import Comentario
from accounts.models import Perfil
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .decorators import torcida_required
from .models import Perfil, Presenca, Conquista, Evento, CheckIn, PlanoSocio, Assinatura, Fatura
from .forms import CadastroForm, PerfilCompletoForm
from loja.models import Produto
from .models import Presenca, PresencaCaravana
import csv
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Importação do Utilitário PIX
try:
    from .efi_utils import gerar_cobranca_pix
except ImportError:
    # Caso falte alguma lib, não quebra tudo
    pass

# 1. Ecrã para escolher a torcida ANTES de logar
def escolher_torcida_publico(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    torcidas = Torcida.objects.all()
    return render(request, 'escolher_torcida_publico.html', {'torcidas': torcidas})

# 2. O Ecrã do PDF (Login/Registo personalizado da Torcida)
def entrada_torcida(request, torcida_id):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    torcida = get_object_or_404(Torcida, id=torcida_id)
    
    # Guardamos a torcida na sessão para sabermos qual ele escolheu 
    # quando ele for redirecionado para o registo ou login real
    request.session['torcida_pre_selecionada'] = torcida.id
    
    return render(request, 'pre_login_torcida.html', {'torcida': torcida})




@login_required
def viagens_view(request):
    perfil = request.user.perfil
    if not perfil.torcida or not perfil.aprovado:
        return redirect('dashboard')
        
    # FILTRO MÁGICO: Puxa SÓ as viagens da torcida dele
    caravanas = Caravana.objects.filter(torcida=perfil.torcida).order_by('saida_horario')
    return render(request, 'viagens.html', {'caravanas': caravanas})


# accounts/views.py

# SAT/accounts/views.py

# accounts/views.py

def cadastro(request):
    # 1. Verifica se existe uma torcida pré-selecionada na sessão (vinda do pre_login_torcida)
    torcida_id_sessao = request.session.get('torcida_pre_selecionada')
    torcida_pre = Torcida.objects.filter(id=torcida_id_sessao).first() if torcida_id_sessao else None

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            # Validação de senhas conforme o teu formulário personalizado
            if request.POST.get('senha') != request.POST.get('confirmar_senha'):
                messages.error(request, "As senhas não coincidem.")
                return render(request, 'cadastro.html', {'form': form, 'torcida': torcida_pre})

            # Cria o utilizador e o perfil base através do form.save()
            user = form.save()
            perfil = user.perfil
            
            # Se ele já veio de um link de torcida, vincula logo como pendente
            if torcida_pre:
                perfil.torcida = torcida_pre
                perfil.aprovado = False 
                perfil.save()
            
            # GUARDA O ID NA SESSÃO: Fundamental para a Etapa 2 saber quem é o utilizador
            request.session['novo_usuario_id'] = user.id
            request.session.modified = True 
            
            # Redireciona para a Etapa 2 SEM fazer login ainda
            return redirect('cadastro_etapa2') 
        else:
            # Exibe os erros reais do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    # Se for um erro num campo específico, exibe o nome do campo
                    nome_campo = form.fields[field].label if field in form.fields and form.fields[field].label else field.capitalize()
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f"{nome_campo}: {error}")
    else:
        form = CadastroForm()
        
    return render(request, 'cadastro.html', {'form': form, 'torcida': torcida_pre})


def cadastro_etapa2(request):
    # 1. Recupera o ID do utilizador que acabou de se registar na Etapa 1
    novo_usuario_id = request.session.get('novo_usuario_id')
    
    # Segurança: se não houver ID na sessão, volta para o início
    if not novo_usuario_id:
        return redirect('cadastro')
        
    from django.contrib.auth.models import User
    user_alvo = get_object_or_404(User, id=novo_usuario_id)
    perfil = user_alvo.perfil

    if request.method == 'POST':
        # Captura os dados enviados pelo teu HTML (cadastro_etapa2.html)
        time_escolhido = request.POST.get('time_coracao')
        torcida_escolhida_id = request.POST.get('torcida_id')

        # 1. Grava o Time do Coração
        if time_escolhido:
            perfil.time_coracao = time_escolhido

        # 2. Grava a Torcida e define como pendente para aprovação
        if torcida_escolhida_id:
            if torcida_escolhida_id == 'neutro':
                perfil.torcida = None
                perfil.aprovado = False
            else:
                from organizadas.models import Torcida
                nova_torcida = Torcida.objects.filter(id=torcida_escolhida_id).first()
                if nova_torcida:
                    perfil.torcida = nova_torcida
                    perfil.aprovado = False 
        
        # SALVA TUDO NO BANCO DE DADOS ANTES DO LOGIN
        perfil.save()

        # 3. REALIZA O LOGIN FINAL (Agora com os dados guardados)
        from django.contrib.auth import login
        user_alvo.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user_alvo)
        
        # Limpa as variáveis temporárias da sessão
        if 'novo_usuario_id' in request.session:
            del request.session['novo_usuario_id']
        if 'torcida_pre_selecionada' in request.session:
            del request.session['torcida_pre_selecionada']

        messages.success(request, f"Bem-vindo, {user_alvo.first_name}! Perfil configurado com sucesso.")
        return redirect('dashboard')

    # Dados para carregar os escudos e a lista de torcidas no template
    from organizadas.models import Torcida
    torcidas_lista = Torcida.objects.all()
    
    times_brasil = [
        # ==========================================
        # SÉRIE A (2026)
        # ==========================================
        {"nome": "Athletico-PR", "escudo": "https://s.sde.globo.com/media/organizations/2019/09/09/Athletico-PR.svg"},
        {"nome": "Atlético-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/10/atletico-mg.svg"},
        {"nome": "Bahia", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/bahia.svg"},
        {"nome": "Botafogo", "escudo": "https://s.sde.globo.com/media/organizations/2019/02/04/botafogo-svg.svg"},
        {"nome": "Chapecoense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/chapecoense.svg"},
        {"nome": "Corinthians", "escudo": "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png"},
        {"nome": "Coritiba", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/coritiba.svg"},
        {"nome": "Cruzeiro", "escudo": "https://s.sde.globo.com/media/organizations/2021/02/13/cruzeiro_2021.svg"},
        {"nome": "Flamengo", "escudo": "https://s.sde.globo.com/media/organizations/2018/04/10/Flamengo-2018.svg"},
        {"nome": "Fluminense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/fluminense.svg"},
        {"nome": "Grêmio", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/gremio.svg"},
        {"nome": "Internacional", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/internacional.svg"},
        {"nome": "Mirassol", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/ac/Mirassol_escudo_antigo.png"},
        {"nome": "Palmeiras", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/palmeiras.svg"},
        {"nome": "Red Bull Bragantino", "escudo": "https://s.sde.globo.com/media/organizations/2021/06/28/bragantino.svg"},
        {"nome": "Remo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Clube_do_Remo.svg/960px-Clube_do_Remo.svg.png"},
        {"nome": "Santos", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/santos.svg"},
        {"nome": "São Paulo", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sao-paulo.svg"},
        {"nome": "Vasco", "escudo": "https://s.sde.globo.com/media/organizations/2021/09/04/vasco_SVG.svg"},
        {"nome": "Vitória", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/vitoria.svg"},

        # ==========================================
        # SÉRIE B (2026)
        # ==========================================
        {"nome": "América-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/america-mg.svg"},
        {"nome": "Athletic Club", "escudo": "https://s.sde.globo.com/media/organizations/2021/02/22/athletic-mg.svg"},
        {"nome": "Atlético-GO", "escudo": "https://s.sde.globo.com/media/organizations/2020/07/02/atletico-go-2020.svg"},
        {"nome": "Avaí", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/avai.svg"},
        {"nome": "Botafogo-SP", "escudo": "https://s.sde.globo.com/media/organizations/2019/02/28/botafogo-sp-svg.svg"},
        {"nome": "Ceará", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ceara.svg"},
        {"nome": "CRB", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/crb.svg"},
        {"nome": "Criciúma", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/criciuma.svg"},
        {"nome": "Cuiabá", "escudo": "https://s.sde.globo.com/media/organizations/2018/12/26/Cuiaba_EC.svg"},
        {"nome": "Fortaleza", "escudo": "data:image/png;base64,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"},
        {"nome": "Goiás", "escudo": "https://upload.wikimedia.org/wikipedia/commons/7/75/Goi%C3%A1s_Esporte_Clube_logo.svg"},
        {"nome": "Juventude", "escudo": "https://s.sde.globo.com/media/organizations/2021/04/29/Juventude-2021-01.svg"},
        {"nome": "Londrina", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/londrina.svg"},
        {"nome": "Náutico", "escudo": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Clube_N%C3%A1utico_Capibaribe_logo.svg"},
        {"nome": "Novorizontino", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Gr%C3%AAmio_Novorizontino_logo.svg"},
        {"nome": "Operário-PR", "escudo": "data:image/png;base64,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"},
        {"nome": "Ponte Preta", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ponte-preta.svg"},
        {"nome": "São Bernardo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/9/96/S%C3%A3o_Bernardo_Futebol_Clube_logo.svg"},
        {"nome": "Sport", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sport.svg"},
        {"nome": "Vila Nova", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Vila_Nova_Futebol_Clube_logo.svg"}
    ]

    context = {
        'perfil': perfil,
        'torcida': perfil.torcida, 
        'torcidas': torcidas_lista,
        'times_brasil': times_brasil,
    }
    return render(request, 'cadastro_etapa2.html', context)

from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class CadastroForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput())
    confirmar_senha = forms.CharField(widget=forms.PasswordInput())
    cpf = forms.CharField(max_length=14)
    telefone = forms.CharField(max_length=20) 
    nome = forms.CharField(max_length=150) 
    
    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        import re
        cpf_limpo = re.sub(r'[^0-9]', '', cpf)
        
        if len(cpf_limpo) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
            
        if cpf_limpo == cpf_limpo[0] * 11:
            raise forms.ValidationError("CPF inválido.")
            
        # Cálculo 1º dígito
        soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
        resto = (soma * 10) % 11
        if resto >= 10: resto = 0
        if resto != int(cpf_limpo[9]):
            raise forms.ValidationError("CPF inválido.")
            
        # Cálculo 2º dígito
        soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
        resto = (soma * 10) % 11
        if resto >= 10: resto = 0
        if resto != int(cpf_limpo[10]):
            raise forms.ValidationError("CPF inválido.")
            
        # Verificar se já existe (ignorando a máscara, buscando pelo cpf limpo)
        if Perfil.objects.filter(cpf=cpf_limpo).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")
            
        return cpf_limpo

    def save(self, commit=True):
        email_limpo = self.cleaned_data["email"]
        nome_completo = self.cleaned_data.get("nome", "")
        
        user = super().save(commit=False)
        user.email = email_limpo
        
        # 1. Separar o Nome Completo em Nome e Sobrenome
        partes_nome = nome_completo.split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''
        
        # 2. Gerar um username único a partir do nome
        import unicodedata
        import re
        import random
        # Tira acentos e caracteres especiais
        base = unicodedata.normalize('NFKD', nome_completo).encode('ASCII', 'ignore').decode('utf-8')
        base = re.sub(r'[^a-zA-Z0-9]', '', base).lower()
        if not base:
            base = "usuario"
            
        username = base
        # Garante que seja único
        while User.objects.filter(username=username).exists():
            username = f"{base}{random.randint(100, 9999)}"
            
        user.username = username
        
        user.set_password(self.cleaned_data["senha"])
        
        if commit:
            user.save()
            
            # 2. Guardar CPF e Telefone corretamente no Perfil
            Perfil.objects.update_or_create(
                user=user,
                defaults={
                    'cpf': self.cleaned_data.get('cpf'),
                    'telefone': self.cleaned_data.get('telefone'),
                    'whatsapp': self.cleaned_data.get('telefone'), # Preenche o whatsapp com o mesmo número
                }
            )
        return user


class PerfilCompletoForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            'foto',
            'data_nascimento', 'rg_cnh', 
            'orgao_expedidor', 

            'cep', 
            'rua', 
            'numero', 
            'complemento', 
            'bairro',
            'cidade', 
            'uf',
            'doc_frente', 
            'doc_verso', 
            'doc_selfie',
            'vulgo', 
            'pelotao',
            'rede_social'
        ]
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control sat-input'}) 
            for field in fields if field not in ['data_nascimento', 'foto', 'foto_documento_frente', 'foto_documento_verso', 'verificacao_facial']
        }

@login_required
def dashboard(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    agora = timezone.now() 
    
    time_busca = perfil.time_coracao
    api_key = "pub_629d163494fb4b3c9f19c706166a65e9"
    
    # 1. GIRO DO FUTEBOL (Notícias Gerais)
    noticias_gerais_api = cache.get('news_geral_v1')
    if not noticias_gerais_api:
        try:
            url_geral = 'https://newsdata.io/api/1/news'
            params_gerais = {'apikey': api_key, 'country': 'br', 'category': 'sports', 'language': 'pt', 'q': 'futebol'}
            response_geral = requests.get(url_geral, params=params_gerais, timeout=5)
            if response_geral.status_code == 200:
                noticias_gerais_api = response_geral.json().get('results', [])[:15]
                cache.set('news_geral_v1', noticias_gerais_api, 900)
        except Exception:
            noticias_gerais_api = []

    # 2. NOTÍCIAS DO TIME DO CORAÇÃO
    noticias_time_api = []
    if time_busca and time_busca != "Outro":
        # Mudei a chave de cache para _v3 para forçar a atualização imediata
        cache_key_time = f'news_time_{time_busca.replace(" ", "_")}_v3' 
        noticias_time_api = cache.get(cache_key_time)
        
        if noticias_time_api is None:
            try:
                url_time = 'https://newsdata.io/api/1/news'
                
                params = {
                    'apikey': api_key, 
                    'country': 'br', 
                    'language': 'pt', 
                    'category': 'sports', 
                    # Retiramos as aspas para a API não falhar com acentos
                    'q': time_busca 
                }
                
                response_time = requests.get(url_time, params=params, timeout=5)
                if response_time.status_code == 200:
                    resultados_brutos = response_time.json().get('results', [])
                    
                    # FILTRO RIGOROSO NO PYTHON: Só passa se o time estiver no título ou descrição
                    time_busca_lower = time_busca.lower()
                    noticias_time_api = []
                    
                    for art in resultados_brutos:
                        titulo = (art.get('title') or '').lower()
                        descricao = (art.get('description') or '').lower()
                        
                        if time_busca_lower in titulo or time_busca_lower in descricao:
                            noticias_time_api.append(art)
                            
                        # Limita a 15 notícias rigorosamente validadas
                        if len(noticias_time_api) == 15:
                            break
                            
                    cache.set(cache_key_time, noticias_time_api, 900)
            except Exception:
                noticias_time_api = []

    # 3. COMUNICADOS SAT (Base de Dados Local)
    noticias_sat = Noticia.objects.all().order_by('-data_publicacao')[:3]

    torcida_selecionada = perfil.torcida

    if torcida_selecionada:
        eventos = Evento.objects.filter(torcida=torcida_selecionada, data__gte=agora).order_by('data')[:3]
        # Trending topic: mostra os posts mais curtidos no geral
        posts_sociais = SocialPost.objects.all().annotate(num_curtidas=Count('curtidas')).order_by('-num_curtidas', '-data_criacao')[:10]
        parceiros = Parceiro.objects.filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
        publicidades = Publicidade.objects.filter(ativo=True, data_inicio__lte=agora, data_fim__gte=agora).filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
        produtos_destaque = Produto.objects.filter(destaque=True).filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))[:4]
    else:
        eventos = Evento.objects.filter(data__gte=agora).order_by('data')[:3]
        posts_sociais = SocialPost.objects.all().annotate(num_curtidas=Count('curtidas')).order_by('-num_curtidas', '-data_criacao')[:10]
        parceiros = Parceiro.objects.filter(torcida__isnull=True)
        publicidades = Publicidade.objects.filter(ativo=True, data_inicio__lte=agora, data_fim__gte=agora, torcida__isnull=True)
        produtos_destaque = Produto.objects.filter(destaque=True)[:4]

    context = {
        'produtos_destaque': produtos_destaque,
        'proximos_eventos': eventos,
        'perfil': perfil,
        'perfil_game': perfil_game,
        'xp_atual': perfil_game.xp_total or 0,
        'torcida': torcida_selecionada, 
        
        # --- AS TRÊS VARIÁVEIS EXATAS PARA O HTML ---
        'noticias_time_api': noticias_time_api, 
        'noticias_gerais_api': noticias_gerais_api,
        'noticias_sat': noticias_sat,
        
        'posts_sociais': posts_sociais,
        'parceiros': parceiros,
        'publicidades': publicidades,
    }
    
    return render(request, 'dashboard.html', context)



# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py

# accounts/views.py

@login_required
def noticias(request):
    perfil = request.user.perfil
    time_busca = perfil.time_coracao

    api_key = "pub_629d163494fb4b3c9f19c706166a65e9"
    url_api = 'https://newsdata.io/api/1/news'
    
    lista_final = []
    


    urls_vistas = set()

    # Só pesquisa o time se ele não escolheu a opção "Outro"
    if time_busca and time_busca != "Outro":
        try:
            params_time = {
                'apikey': api_key, 
                'country': 'br', 
                'language': 'pt', 
                'category': 'sports', 
                'q': time_busca # Sem as aspas
            }
            resp_time = requests.get(url_api, params=params_time, timeout=5)
            if resp_time.status_code == 200:
                time_busca_lower = time_busca.lower()
                
                for art in resp_time.json().get('results', []):
                    # FILTRO RIGOROSO AQUI
                    titulo = (art.get('title') or '').lower()
                    descricao = (art.get('description') or '').lower()
                    
                    if time_busca_lower in titulo or time_busca_lower in descricao:
                        link = art.get('link') or '#'
                        if link not in urls_vistas:
                            urls_vistas.add(link)
                            lista_final.append({
                                'url': link,
                                'title': art.get('title') or f'Notícia do {time_busca.title()}',
                                'description': art.get('description') or '',
                                'image': art.get('image_url') or f'https://placehold.co/600x400/D37129/white?text={time_busca.upper()}',
                                'source': art.get('source_id') or time_busca.upper()
                            })
        except Exception as e:
            print(f"Erro ao buscar time: {e}")

    try:
        params_gerais = {'apikey': api_key, 'country': 'br', 'category': 'sports', 'language': 'pt', 'q': 'futebol'}
        resp_geral = requests.get(url_api, params=params_gerais, timeout=5)
        if resp_geral.status_code == 200:
            for art in resp_geral.json().get('results', []):
                link = art.get('link') or '#'
                if link not in urls_vistas:
                    urls_vistas.add(link)
                    lista_final.append({
                        'url': link,
                        'title': art.get('title') or 'Futebol Nacional',
                        'description': art.get('description') or '',
                        'image': art.get('image_url') or 'https://placehold.co/600x400/4A4D4E/white?text=FUTEBOL+SAT',
                        'source': art.get('source_id') or 'FUTEBOL GERAL'
                    })
    except Exception as e:
        print(f"Erro ao buscar futebol geral: {e}")

    return render(request, 'noticias.html', {'noticias': lista_final})

# accounts/views.py

@login_required
def seja_socio(request):
    # Força a atualização do objeto perfil para evitar cache de estado antigo
    perfil = get_object_or_404(Perfil, user=request.user)
    
    if request.method == 'POST':
        time_coracao = request.POST.get('time_coracao')
        torcida_id = request.POST.get('torcida_id')
        
        # 1. Atualiza o Time do Coração
        if time_coracao:
            perfil.time_coracao = time_coracao
            
        # 2. Atualiza ou Vincula Torcida
        if torcida_id:
            if torcida_id == "neutro":
                perfil.torcida = None
                perfil.aprovado = False
            else:
                try:
                    nova_torcida = Torcida.objects.get(id=torcida_id)
                    # Se ele trocar de torcida ou entrar numa nova, volta para pendente
                    if perfil.torcida != nova_torcida:
                        perfil.torcida = nova_torcida
                        perfil.aprovado = False
                except (Torcida.DoesNotExist, ValueError):
                    pass
                    
        perfil.save()
        messages.success(request, 'Perfil e preferências atualizados com sucesso!')
        return redirect('seja_socio')

    # Busca planos e torcidas para o contexto
    if perfil.torcida:
        planos = PlanoSocio.objects.filter(torcida=perfil.torcida).order_by('preco')
    else:
        planos = PlanoSocio.objects.filter(torcida__isnull=True).order_by('preco')
        
    torcidas = Torcida.objects.all()

    # 2. Lista de times com os links dos escudos
    times_brasil = [
        # ==========================================
        # SÉRIE A (2026)
        # ==========================================
        {"nome": "Athletico-PR", "escudo": "https://s.sde.globo.com/media/organizations/2019/09/09/Athletico-PR.svg"},
        {"nome": "Atlético-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/10/atletico-mg.svg"},
        {"nome": "Bahia", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/bahia.svg"},
        {"nome": "Botafogo", "escudo": "https://s.sde.globo.com/media/organizations/2019/02/04/botafogo-svg.svg"},
        {"nome": "Chapecoense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/chapecoense.svg"},
        {"nome": "Corinthians", "escudo": "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png"},
        {"nome": "Coritiba", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/coritiba.svg"},
        {"nome": "Cruzeiro", "escudo": "https://s.sde.globo.com/media/organizations/2021/02/13/cruzeiro_2021.svg"},
        {"nome": "Flamengo", "escudo": "https://s.sde.globo.com/media/organizations/2018/04/10/Flamengo-2018.svg"},
        {"nome": "Fluminense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/fluminense.svg"},
        {"nome": "Grêmio", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/gremio.svg"},
        {"nome": "Internacional", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/internacional.svg"},
        {"nome": "Mirassol", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/ac/Mirassol_escudo_antigo.png"},
        {"nome": "Palmeiras", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/palmeiras.svg"},
        {"nome": "Red Bull Bragantino", "escudo": "https://s.sde.globo.com/media/organizations/2021/06/28/bragantino.svg"},
        {"nome": "Remo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Clube_do_Remo.svg/960px-Clube_do_Remo.svg.png"},
        {"nome": "Santos", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/santos.svg"},
        {"nome": "São Paulo", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sao-paulo.svg"},
        {"nome": "Vasco", "escudo": "https://s.sde.globo.com/media/organizations/2021/09/04/vasco_SVG.svg"},
        {"nome": "Vitória", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/vitoria.svg"},
        # ==========================================
        # SÉRIE B (2026)
        # ==========================================
        {"nome": "América-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/america-mg.svg"},
        {"nome": "Athletic Club", "escudo": "data:image/png;base64,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"},
        {"nome": "Atlético-GO", "escudo": "https://s.sde.globo.com/media/organizations/2020/07/02/atletico-go-2020.svg"},
        {"nome": "Avaí", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/avai.svg"},
        {"nome": "Botafogo-SP", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Botafogo_Ribeirao_Preto_SP.png/960px-Botafogo_Ribeirao_Preto_SP.png"},
        {"nome": "Ceará", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ceara.svg"},
        {"nome": "CRB", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/crb.svg"},
        {"nome": "Criciúma", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/criciuma.svg"},
        {"nome": "Cuiabá", "escudo": "https://s.sde.globo.com/media/organizations/2018/12/26/Cuiaba_EC.svg"},
        {"nome": "Fortaleza", "escudo": "data:image/png;base64,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"},
        {"nome": "Goiás", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Goi%C3%A1s_Esporte_Clube_logo.svg/960px-Goi%C3%A1s_Esporte_Clube_logo.svg.png"},
        {"nome": "Juventude", "escudo": "https://s.sde.globo.com/media/organizations/2021/04/29/Juventude-2021-01.svg"},
        {"nome": "Londrina", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/londrina.svg"},
        {"nome": "Náutico", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/N%C3%A1utico_Logo_%282006-2008%29.png/960px-N%C3%A1utico_Logo_%282006-2008%29.png"},
        {"nome": "Novorizontino", "escudo": "data:image/png;base64,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"},
        {"nome": "Operário-PR", "escudo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAUgklEQVR4AdSXA7AkWRBF17vBZWBsfNu2NbZt27Zt27a+bdt/bOPujYyuHtsZcbqqXuVT6lX/8CUEwO/EhLQko8lispnsJrvIOjKPDCXNiBH5g/zwuflcA/9IjMlYEkzugfLo0SMUFBQgJiYGp0+dwrGjR3H82DEEBwUhOSkJFy9cwJMnT6CSBySSTCMO5JfvwQCVVJvOAaW0tBTbt23DkEGD4OHqBh0NTTja2qFJw0bo1L4DevfoiV7de6Bju/Zo3KAhHGxtoa+tA18vbwwbMgQ7tm9HSXExVHKBzCXa36IBtMgm8vDSxYtYuXw5Anx8YWVmjkEDBmInN5KRkYGHDx/iLSI66Wlp2EHDDeo/ABYmpvDx9MKSRYtQVlYGyhNylFh9CwYoT9aQx6mpqejXpw9MDY0wasRIxETHSDi/aoPF9CpDXnSI3LPtVQaSMaKjojFq+AgY6emDESP6KtlHan1pAyg53oVcZ06jZ/fusDa3wOpVq3Dr1q1nFy+LXb50Kbp27gwHhn/t6jVQo0rVV8J3kiLdOnfBimXLkJKc/KwRZezVK1dKZPXo2k3qCeUuGUJ+/lIG+I8corewYN58mBgYSnjeu3sPimRnZ2PKpMmwsbB85Ua162rAxdEJrAlyb2pkjFrVqr9S19bSClMnT0FuTg4UuXv3LhYvXKSae7EUV8o5UvFzG0Cf5Ofl5cGfOd6+TVuUlpRAkdiYGGmrWbXaa72cEB+PhfMXYOSw4RLSfXv1xuGDh7B08WLMmjFDdAzZ3rZVa2jUqq3uxzGlWMbFxkKREs7drnUbNKpfH8VFRaCUEevPZQAXcvPM6dMwo8fWr10HRQoLCyVslcXSm1LlvT08XzQAcz4a69etg5O9vTxPGDceRw8fwcjhwxUdKX5rVq/GsiVLsWXT5peio3vXrijihhVZt2atpEVYaKiSEvU/tQG8yX0uRiaip9U5vnbNGgllxUtjRo0G9aRYBQUGvWgAOf+16moozwzlhdi+dZv0a9a4ibQdPHAAu3fuwtzZcxAVGamMLd5WootzihNUNUIMa82U27dnLyiPSItPZQBHcm/NqtXitUIpPMD169clJF/M7fCwMPXzhvXr4eft85yOs4Mj6tSo+Wzhk4jy5HeCq5OztM2fOxcatesgNCQE7s4u0taHqbJ3zx5s27IFXu4e6v6dO3TEjRs3QEFBfj7X6CA6KiM0/FgDaJHr27ZshTMHlnNYNZELN6IsYkC/fmgQECD3mzZuRJeOnbiJedi6eQuszC0UPTki27RsRW+PkjqweuUqgfdgG9+1hAl1FH1fLy/5BtDV1JLjcvOmTfByc+fJkvysUcVwimPKSktlrXt27wblPrH7UAP8RbLPnT0n1VzJucyMDPk44cTQrFNX2ZiEKsNSqjY3JEce34lnl7DAsR9yc3Oxf+8+Ce3hQ4ehT89ewgjez5szB/v37UMedTLSM+Rk8XBxlTEsTM1Y6BqgX+8+8tnMq7Qb6uqp08+SOlmZWeqaxDWLLuUiqfYhBthJT8vkiQkJoHBxeTA3MZEJGdqcIFjClc9S9BbMm6f2SusWLRERFi5n+fixY2FvbSMnBz2NDSyC/A+AkOBggf8JpJDxA0rGpS4mjB2H1JQUSalWzVvImEb6BmI83kstioyIkLSgA1SGMkU+10xBfFy8GIUnFigR5Nf3MUBLnvMI8PWTb3kKrl65Aic7qdxSrFYsX84N+eDkiRMSpqzUqFuzlnj+3NmzXFwkmjdpynee2LRhA65cvox3lcuXLkv9YF+0aNoM0VFR4OkDexvb/5u3ByDLsiQMwGtbwbV32109tm3btlo707Yxtm3btm1PM8Y+m1/U5Ivb1fUKremMONG3bl+cmyfx55/neY9AyOKYvlRaLrzgAnHkqxizfJk5Y0YhXJDSP/1UXVUGt1UBv/O9VnPvPfYs5IsvvrCitdXdafsdiggvNoweObJYfed7Bu7nKnL72pECb77ppjKXEs+4uVAwmO3ZBx9wYPGuIyZPFmscQ43eWZsfDGHOZI/ddgt8MSaryw5tUcAxLwTqWiz8fFqsGgFS/vuVv+fwQkEp8750aNWXDfMFfaGzeSSeFc88pnAN1iBweickesVllxdo0DxYCyt0bA5k6pSpZdGGHmKQP29oTQEdvG+nHXYop4fZkueee64oUQGVhq7dpLpUgmBoIiJuBLeL4fiMF/NcwF9Khw4vu/TSwAnnezc3rKXTe+6+u7ZQ/4k0+kJAcnLqySfDEA7J6i0p4HSBJXB6rmAEoC09MOLBOuWxRx8tTPL5UMpBX5ni6aeeVi6+8CL1vhTE3yJ4PRmpUlqaewF0+DiQs8tOOwFSFkQ28WG5GLiFQJUDHeeQVmsVKAxDQQiaegqQKj7fftttixcSPlx9IJR1ztlnl4aIxv5WogIrMAEsLh4obC4Ja7j+2usCyh5Vbrj++jKnIgOsF1kBQXLn7XcUz5IqZacVIiD7f+nUXG668SYI0txnyUa33qJGKsFJnKdOcUiWaE4Bg5579lnAJevyADcbzKKAzTfZJALOscXxaiuvXIAPkfnpp58uE8aOK+8EpXXF5ZfPUsIO7NcfuVHaIyo/Ac5cLjjvPBRaOT/+nTZ1al4iRUa8WUrOTwRZHbX6QaFEWOYSiy4abqGqLCc1VcC34IdhQ4bIszVs7QFQWL/Iz0pPf0Ny0pBgJPpLNfL40089Xcjbb79dTgpeAFSWkylk6ODB5d34uzWRagf27x/VYGerCBCF8s5VezRLlkiVu+2yCzxQqxEE4bPOPBMYS2XUKshxY8aUkcOHO0Ra/LiqgMVi1QAHta4Lgso6yM1AjEmVi8K0+vTsRbMIEL4YFrFpISiwFBDYffD+8ccdVwi258orrij15JNPPmFZXMs78AmKIRgj3GpUWWbJpQCoWVilDz74oJjzxhtsyFXLnrvtrg4o1117bdlwvfWq1oCTrFmWZxEVY1UBQx6OOl3uJh9//HHp3KEDrQZqO1XwgdgAIOfKU0F/yc1qe6LyYwV8tGvHTvli6SrNT3nbbIBjIcuHGwlY2KOrrrxSeVyuvuqqssG66wl2mCCmnrdxD4vifFjsOOixPBEuYW6d/9thtvK5S8yJkola4rF4DzeoKuAOK0fbJFCXGwW0CHJ3yqF83jnoDsYGjErKoREMn434QZis6yA0JjcjUJnrocOqMGv+uVrgfQFMLS+Avffue4VY8TGjRpcUC7Drzjs7VAzBIKwKlR6xYjHzZJGUUXtWv0MPo8SyWEOPfD8XCFxzlENpqta0+HiHiP4ZMYcMGjSLBj1k1IiRxbEPVMBcFauUwseqqM/Kp8YFQBGbFWShImWZlMoRmeqZzldEShV3gnF6s8gw+8Q9UCB/vyAwwJQpU4AjbqMgghQhU3MMC9k5rt+r3BdxSlEkk0R8y8WNbFDDBH+kgG6OPGjmzJmNzrEuH4pyNMw8QYbBtJTECiRuUhHAKQqQh4pewHXXXJsmrmYQMNXswe0NK107dWZpYo3UFKZ+del18CFFVG8qzBu+MB/Fkj6BguzySy8rUCHIi0KHAJk+pZnjsuHnLEP6zEWU0cj0CLQ9uvnkQtangM1AXqxu4v5kbEx+0YYGjC4kFRTX6gWYQIQ0J4KWBodJC4zg6DORIjE3KjarpCSWy33E+LFjyzZbbSXjzBIXRPF3IpuwGnyhgsw1hg/hNlWXogDzVSCtseqqAqkYVbViVpL1gWDPghz2oYC+8eDw7c0Kee3V12rpb3zkdrwc84GkRFMfhZFti1DIKoEq4QcBk/kBSR8HrB3Qr1/B7ak7FCsV3M/lBFVKiqh+XVjLywJtLdXdcF0NXFUVEEo/TiMmsxAX0m1KJUSX6Y1CdKb0GtQ9FDBexN1/330LuSd8zMXKWr6tnmaeigzIjrlKNS2JaG5SlObZPp75sp4qoytjMGNW4h6pjHKQMOr8t8Pdhg8ZWmWHjdnQ5VZbNCpAOw2RsvQSS0aavrEAduB79iK4YogYlGn5Ugo4FZgZEIiN8MnqyxQX8qtjRc9222xTROHmhA9idGlek4TyBDjFi1QKFVYEDY5Ndo+s4lpD2Rs+fxK3Uc97d5sUAOoKkI6hSN8l3gBWzuXCyQ7cTF1AAedBbtIDoXkXSy1SI5/2dz6ADzYpdIAS/oyiigwyGPCRhoIzuLWoIiFGq5Hy4YcfFllCHpdWzzz9dBaCPRJA1RYwR1SWj8oubVYA2uyaxgUMF7omrruhsECFlHNiDxkWVgV4SWAUcP4J0W4aNXyEE4H4LnSx1pNgwq/yxeHT14vIaoAMmBhYVFTNn01A4EroalUmhyKlVnieaJyKLRR3cViV9PtomKo4hOqihJT2KAAqRLVlDbBuZAGumLFD/CHDh86qgDOgPRMkkJmLRWf+eUwEvXwxU/ZASPC2W24Nenq1ImCJvvyb+akBqqIrzAcBlyySpEvupHpT2WGVE70hPMmcKAB3qGL1wU3jhgFhEihSZgq5kwKOZPY9I7gRRKeLpRETfSQIjtTqySeeVJASq660cmDqJWmUafNbLXDMbi3VVOV/ffokEBGIWAI/F/2rBEsdBdzcZgUcuN/+5YTjjgey3KdUly5rFgAhkoP2P6BcdsmlDi+jgH5gZjImyI46fb3Q3ADgxAMAHh+CmcEdCiwCmZWuNU4mhEK4wtQoY62MfA4yC0AoN/d1+Pe8UwCGun/Mo978YRDCUihDHUcB2zFDLFAWQkw2c6kgBQ9AV7C2QCgwyvF4QAQppRG1tuApuAEaG6y7bnk8AhtFgbBWQ59AIE3wI3DOKwUIegKhACodyvfVb0k4DpqzQGUMBSzKbLtWKqZVGwkGJalMID9HYTNWSoTQ4Gv+rFhR65eqUAiXsPIIS4AGjhBPPFPGcS+ZhwrwgeaGC4z0d6aACMnKTu6BTpNbBPLSVTelgB8BYG5I4gC97SYfnXz72RHts7kpECa+BytZkHJ66y22DIUMKddGCpIG4YC+vXvnKhhJmrZVAaymVQVsHQpg1qxTtyq5Qhko+5cyWsYg3xpC/pHl8H0jhw1XXVVToX4fZTAp5Sstm2DQVOeDnC5Fikpd/FnO5efY2GBkJtH07PsD5oMCuKY5Q3iyEvfkujiIrGvwCkSbziLpv9jpkgoYKRdvG6kvKyYfa+WkPtFdlyjpZju39AAhP+KjfDjIy20UVsDPqBEj5osCqrUAX8by+DdT3wYx18mxAFnCg/FZ6bLem4N/AACrhMhy/B+EzQvTZ5sbPky7XNq5JFKoXC2qrpsMbpATRGqcfYfIvFUAjkCpDNw0P1+drO2Tc7T7JEv5HasK+DYoH+ktUNHpVUBUb48Pv9e7l9KyRaVYyuCyIBRA6cpfsSYbIs0Orkk0ZZXkIdLBr6sKMMY3ruJaSTyqquo91MYEQZOrVNjXhwppWQEPzwsFcFOlri5wBLod6s0TS5xNHuAu8/+FzfUF/vVlCJQH1qbGPKTesPqY3/wbcmyvAphkexVw1RVX8mUVJ4ttcY5ot4q1ZAperV5r7EpBDKJLNhdoqPdwAdHODX2D5N8XhAKs6oDD+klpzWL+6nacz+IbiBQN8itFRP96CliCubgRk0tuDHTVkoYbunZVHAXe7wtOl/fee2/uFLBf6wqwkQK46t4l7212JFGr2rSvKOPTxq21xy+RZ/FuqT1sUQsvkj2Yvza1NpVU1+Yg2L0dCpCWldEPhqVlf7LeUGGmFXNrC8oTrH5rCvibkgC1rLgg2lpYWA9uKTNwn7tjWwwLGjRgoJp7rhUA1Div9a6eUFe0FPGTznsvUGqIVl+6leXv0dYtMn2mvDNF/788FCtLsDW5Iak6UFpekhun9o2eAVCihtCRaR4Ita4A7THskrpDn88zcf2useFBKZ0wtzqgT+35xubLg+7XnCmyXHv2CH0HWdC4L2dpO0VyNappr4qpmVi1FYU5to1Wlojou5rzte0sTwWXD3DxyaZpUJtsrfBXFLwGi7LbZkp7AvIanEVS6KBvnjc3ZGjuM2K1Sn3rp+Zp7y6xP8R45/CJk5SViZ7waqkEneJqd6jpaqgwka2sSC2OK8Dcwu6IVsSFYV+fcwonqVXTBKZwb6tWJGPlx6s+ibluGmUx3I+yjNFxTjdKLud5fXv1hvaS58MQ8XlMi13hCpHc01d3+FBdZYFSAxQfoC1mOHbOhF3j2paeZQ+yngGsbw7mwjqJwL3rTjtlR1jS32Rut8puGqnxC/3A3XfZNTkD6Sy3w7c4FEYAiOM2Dh+olG3TtYoy7DH55OOPLRRCN9Ffz3m1WXoHSqBVZebMGTOzaqSUFicoXcnHmSkENn0AzFBufqwGM8xzz4MP9m9rH28LXAY4/3IjET8tdfC83i6/eQSdTyaOn6DjIyuUFOaIE2huktrqeETHNlz1PqQn/2eymGD3ZTveEAAx1Dq8gmddq1Kspej3S31cApzX7ptfP5hYQYAVA5CaKCeRPJsdonVTgHLwgQfiAGvZQSk9bPAQBEtegz1K5halpp0lGM6W5mzTw/V5F/FuvUqslV4ExgvnOb9/MmM32b16eyIwoqRSBJmcTk+zLS1D0DwlKKvto8WW50bEucQYICsLqdzjWfHMM8pHjR+eOV7f3xzy1yKY2YYF9aOp7/ExSFOBIRiixNQEVbHzW2dJQMt835bhWve41zMqogbQhZLjuV5GettCf/Z1/GxOfr0J0wrw8GcrolyVLarCNfUMASYbI7gPhGfPr2Pn/J9rXFsVz2LiYgigdHrsDvs0zrFEBdzC8MPJNe1rVHgASpQgFugi8W8m2k4BfbXaPEOXWHqz+TJjjrp7I4XNwvbT2aURxUIB+Kxwge2Z6yLdu0uhpXfPXuh25m0bvaGdhb+P/+vpGpuz5Pdy4P7724ary5QB7uwYy/vwhf3H0z+1ESPGKRazaJUF9kdgsAi7tPQK/XTOGDl8hHNWHBtV/W3B1Bi2maKrf77w/3i6/vhjjHVj9BKwcA7qJ6ZsqNOxUTFsLOxPeSg6O1jn99z+D4ux68wdubS4AAAAAElFTkSuQmCC"},
        {"nome": "Ponte Preta", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ponte-preta.svg"},
        {"nome": "São Bernardo", "escudo": "data:image/png;base64,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"},
        {"nome": "Sport", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sport.svg"},
        {"nome": "Vila Nova", "escudo": "data:image/png;base64,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"}
    ]

    context = {
        'perfil': perfil,
        'torcidas': torcidas,
        'times_brasil': times_brasil,
        'planos': planos,
    }
    return render(request, 'seja_socio.html', context)


@login_required
def torcidas(request):
    perfil = request.user.perfil
    
    # 1. Correção do nome da URL (de 'hub_organizadas' para 'hub')
    if perfil.torcida and perfil.aprovado:
        return redirect('hub')
    
    # Carrega a lista de torcidas SEMPRE, para não travar a tela
    lista_de_torcidas = Torcida.objects.all()
    
    # 2. Se está pendente, enviamos a lista junto para permitir que ele mude de ideia
    if perfil.torcida and not perfil.aprovado:
        return render(request, 'torcidas.html', {
            'status': 'pendente', 
            'torcida': perfil.torcida,
            'torcidas': lista_de_torcidas # Faltava isso aqui!
        })
    
    # 3. Se não tem torcida nenhuma
    return render(request, 'torcidas.html', {
        'torcidas': lista_de_torcidas,
        'neutro': True 
    })

@login_required
def vincular_torcida(request, torcida_id):
    torcida = get_object_or_404(Torcida, id=torcida_id)
    perfil = request.user.perfil
    
    perfil.torcida = torcida
    perfil.aprovado = False # Para a lógica de aprovação que criamos
    perfil.save()
    
    messages.success(request, f"Solicitação enviada para {torcida.nome}!")
    return redirect('dashboard')

def logout_view(request):
    logout(request)
    return redirect('login')







@login_required
def area_hub(request):
    perfil = request.user.perfil
    
    # BLOQUEIO ABSOLUTO: Se não tiver torcida ou NÃO estiver aprovado, volta para a página de torcidas!
    if not perfil.torcida or not perfil.aprovado:
        messages.warning(request, "Acesso restrito. Escolha uma torcida ou aguarde a aprovação da diretoria.")
        return redirect('torcidas')
        
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    context = {
        'perfil': perfil,
        'perfil_game': perfil_game,
        'torcida': perfil.torcida,
    }
    return render(request, 'hub.html', context)


def socio_view(request):
    # Explica os planos e benefícios de ser sócio
    return render(request, 'seja_socio.html')

@torcida_required
@login_required
def carteirinha(request):
    # 1. Busca o perfil básico do usuário (onde está a torcida)
    perfil = get_object_or_404(Perfil, user=request.user)
    
    # 2. Busca o perfil de gamificação (onde estão o nível e o XP)
    from gamification.models import PerfilGamificacao, BadgeUsuario # Certifique-se dos imports
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # 3. Busca as medalhas para exibir no destaque da carteirinha
    badges = BadgeUsuario.objects.filter(user=request.user).select_related('badge')

    # 4. Lógica de geração do QR Code (sua lógica original preservada)
    img = qrcode.make(f"SAT-{request.user.id}")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # 5. Organiza o contexto com TODOS os dados para o template
    context = {
        'perfil': perfil,
        'perfil_game': perfil_game,
        'qr_code': qr_base64,
        'torcida': perfil.torcida,
        'badges_conquistadas': badges
    }
    
    return render(request, 'carteirinha.html', context)

@login_required
def confirmar_presenca(request, evento_id):
    # IMPORTAÇÃO LOCAL: Força o sistema a guardar a vaga no Evento correto
    from organizadas.models import Evento as OrgEvento
    from accounts.models import CheckIn
    
    if request.method == "POST":
        evento = get_object_or_404(OrgEvento, id=evento_id)
        
        # Bloqueia duplicações (caso o utilizador clique duas vezes rápido)
        if not CheckIn.objects.filter(user=request.user, evento=evento).exists():
            
            # Captura dados opcionais
            lat = request.POST.get('latitude', 0.0)
            lon = request.POST.get('longitude', 0.0)
            foto = request.FILES.get('foto')

            # Salva a presença ligada 100% ao evento real
            CheckIn.objects.create(
                user=request.user,
                evento=evento,
                latitude=float(lat) if lat else 0.0,
                longitude=float(lon) if lon else 0.0,
                foto=foto,
                validado=True
            )
            messages.success(request, f"Presença confirmada no {evento.titulo}! +50 XP")
        
        # ATUALIZADO: Em vez de mandar para o Dashboard, devolve para o evento
        # para que o utilizador veja logo a tela verde de sucesso e a barra atualizada!
        return redirect('detalhe_evento', evento_id=evento.id)
    
    return redirect('detalhe_evento', evento_id=evento_id)

@login_required
def detalhe_evento(request, evento_id):
    # IMPORTAÇÃO LOCAL: Força o sistema a puxar o Evento correto da Torcida
    from organizadas.models import Evento as OrgEvento
    from accounts.models import CheckIn
    
    evento = get_object_or_404(OrgEvento, id=evento_id)
    
    # ATUALIZADO: Agora procura corretamente na tabela de CheckIn
    confirmado = CheckIn.objects.filter(user=request.user, evento=evento).exists()
    
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    cor_tema = "#ff6b00"
    if perfil_game.nivel:
        cor_tema = perfil_game.nivel.cor_tema

    context = {
        'evento': evento,
        'confirmado': confirmado,
    }
    return render(request, 'detalhe_evento.html', context)

@login_required
def bet_manutencao(request):
    perfil = request.user.perfil
    
    # 1. Verifica se a data de nascimento está preenchida
    if not perfil.data_nascimento:
        messages.error(request, "Para acessar as Apostas, preencha sua data de nascimento no seu Perfil.")
        return redirect('perfil')
        
    # 2. Calcula a idade
    hoje = date.today()
    idade = hoje.year - perfil.data_nascimento.year - ((hoje.month, hoje.day) < (perfil.data_nascimento.month, perfil.data_nascimento.day))
    
    # 3. Bloqueia menores de 18
    if idade < 18:
        messages.error(request, "Acesso Negado: A área de BET é permitida apenas para maiores de 18 anos.")
        return redirect('dashboard')
        
    return render(request, 'bet_manutencao.html', {'cor_tema': '#D37129'})

@login_required
def beneficios_view(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    cor_tema = perfil_game.nivel.cor_tema if perfil_game.nivel else "#ff6b00"
    
    # Verifica se o usuário tem algum plano ativo (ajuste conforme seu campo de sócio)
    is_socio = hasattr(perfil, 'socio') and perfil.socio 

    context = {
        'cor_tema': cor_tema,
        'is_socio': is_socio,
        'xp_atual': perfil_game.xp_total
    }
    return render(request, 'beneficios.html', context)


@login_required
def perfil_view(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # O request.FILES é quem captura a foto enviada pelo input type="file"
        form = PerfilCompletoForm(request.POST, request.FILES, instance=perfil)
        
        if form.is_valid():
            # 1. Salva os dados do formulário (Foto, CPF, Telefone, etc)
            form.save()
            
            # 2. Salva o Nome e Sobrenome na tabela base do Django (User), se estiverem no form
            user = request.user
            nome_alterado = False
            if 'first_name' in request.POST:
                user.first_name = request.POST.get('first_name')
                nome_alterado = True
            if 'last_name' in request.POST:
                user.last_name = request.POST.get('last_name')
                nome_alterado = True
                
            if nome_alterado:
                user.save()

            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('perfil')
    else:
        form = PerfilCompletoForm(instance=perfil)
        
    seguindo_count = request.user.seguindo.count() if hasattr(request.user, 'seguindo') else 0

    context = {
        'form': form, 
        'perfil': perfil,
        'perfil_game': perfil_game,
        'seguindo_count': seguindo_count
    }
    
    return render(request, 'perfil.html', context)

@login_required
def ranking_torcida(request):
    from gamification.models import PerfilGamificacao
    # Busca os top 10 torcedores com mais XP, trazendo o usuário e o nível junto

# ==========================================
# VIEWS DO EFÍ BANK (PIX)
# ==========================================

@login_required
def pagar_fatura_pix(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id, assinatura__perfil=request.user.perfil)
    
    # Se a fatura não tem um txid (nunca foi gerado PIX ou expirou), gera agora
    if not fatura.txid:
        resultado = gerar_cobranca_pix(fatura)
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('financeiro')
            
    return render(request, 'checkout_pix.html', {'fatura': fatura})

@csrf_exempt
def webhook_efi(request):
    """
    Endpoint que a Efí chama quando um PIX é pago.
    Precisa retornar 200 OK rapidamente.
    """
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            # O payload da Efí envia uma lista de "pix" recebidos
            if 'pix' in body:
                for pix in body['pix']:
                    txid = pix.get('txid')
                    
                    if txid:
                        # Busca a fatura com esse txid
                        fatura = Fatura.objects.filter(txid=txid, status='pendente').first()
                        if fatura:
                            # Marca como pago e ativa a assinatura se necessário
                            fatura.status = 'pago'
                            fatura.metodo_pagamento = 'PIX'
                            fatura.data_pagamento = timezone.now()
                            fatura.save()
                            
                            if not fatura.assinatura.ativa:
                                fatura.assinatura.ativa = True
                                fatura.assinatura.save()
                                
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            print("Erro no webhook Efí:", e)
            return JsonResponse({'status': 'erro'}, status=400)
            
    return JsonResponse({'status': 'método não permitido'}, status=405)

@login_required
def financeiro(request):
    perfil = request.user.perfil
    
    # Pega todas as faturas do usuário
    faturas = Fatura.objects.filter(assinatura__perfil=perfil).order_by('-data_vencimento')
    faturas_pendentes = faturas.filter(status='pendente')
    faturas_pagas = faturas.filter(status='pago')
    
    # Verifica a fatura atrasada mais urgente
    hoje = timezone.now().date()
    fatura_atrasada = faturas_pendentes.filter(data_vencimento__lt=hoje).first()
    
    # Se não tem atrasada, pega a próxima a vencer
    proxima_fatura = fatura_atrasada if fatura_atrasada else faturas_pendentes.first()
    
    # Assinatura ativa (se tiver)
    assinatura_ativa = Assinatura.objects.filter(perfil=perfil, ativa=True).first()
    
    context = {
        'faturas': faturas,
        'proxima_fatura': proxima_fatura,
        'assinatura_ativa': assinatura_ativa,
    }
    return render(request, 'financeiro.html', context)
    lideres = PerfilGamificacao.objects.select_related('user', 'nivel').order_by('-xp_total')[:10]
    
    context = {
        'lideres': lideres,
        'cor_tema': "#D37129" # Laranja oficial da SAT
    }
    return render(request, 'ranking.html', context)


@login_required
def games_hub(request):
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    return render(request, 'games_menu.html', {
        'perfil_game': perfil_game,
        'progresso': perfil_game.progresso_nivel()
    })


# accounts/views.py

@login_required
def moderacao_torcida(request):
    perfil_moderador = request.user.perfil
    
    # Segurança: Apenas staff com torcida vinculada pode moderar
    if not request.user.is_staff or not perfil_moderador.torcida:
        messages.error(request, "Não tem permissão para aceder à área de moderação.")
        return redirect('dashboard')
        
    torcida_mod = perfil_moderador.torcida

    # --- PROCESSAMENTO DE AÇÕES (POST) ---
    if request.method == 'POST':
        acao = request.POST.get('acao')
        perfil_id = request.POST.get('perfil_id')
        
        # Para ações que envolvem um sócio específico
        if perfil_id:
            perfil_alvo = get_object_or_404(Perfil, id=perfil_id, torcida=torcida_mod)
            user_alvo = perfil_alvo.user

            if acao == 'aprovar_socio':
                perfil_alvo.aprovado = True
                perfil_alvo.save()
                messages.success(request, f"O torcedor {user_alvo.first_name or user_alvo.username} foi aprovado!")

            elif acao == 'rejeitar_socio':
                # Em vez de apagar a conta inteira, apenas remove o pedido da torcida
                perfil_alvo.torcida = None
                perfil_alvo.aprovado = False
                perfil_alvo.save()
                messages.warning(request, "Solicitação rejeitada. O utilizador voltou a ser membro neutro da SAT.")

            elif acao == 'editar_socio':
                # 1. Atualiza Dados do User (Django Nativo)
                user_alvo.first_name = request.POST.get('first_name', user_alvo.first_name)
                user_alvo.email = request.POST.get('email', user_alvo.email)
                user_alvo.save()

                # 2. Atualiza Dados Pessoais do Perfil
                perfil_alvo.cpf = request.POST.get('cpf') or None
                perfil_alvo.rg_cnh = request.POST.get('rg_cnh', perfil_alvo.rg_cnh)
                perfil_alvo.orgao_expedidor = request.POST.get('orgao_expedidor', perfil_alvo.orgao_expedidor)
                perfil_alvo.whatsapp = request.POST.get('whatsapp', perfil_alvo.whatsapp)
                
                data_nasc = request.POST.get('data_nascimento')
                if data_nasc:
                    perfil_alvo.data_nascimento = data_nasc

                # 3. Atualiza Endereço
                perfil_alvo.cep = request.POST.get('cep', perfil_alvo.cep)
                perfil_alvo.rua = request.POST.get('rua', perfil_alvo.rua)
                perfil_alvo.numero = request.POST.get('numero', perfil_alvo.numero)
                perfil_alvo.complemento = request.POST.get('complemento', perfil_alvo.complemento)
                perfil_alvo.bairro = request.POST.get('bairro', perfil_alvo.bairro)
                perfil_alvo.cidade = request.POST.get('cidade', perfil_alvo.cidade)
                perfil_alvo.uf = request.POST.get('uf', perfil_alvo.uf)

                # 4. Atualiza Identidade na Torcida
                perfil_alvo.vulgo = request.POST.get('vulgo', perfil_alvo.vulgo)
                perfil_alvo.pelotao = request.POST.get('pelotao', perfil_alvo.pelotao)
                perfil_alvo.rede_social = request.POST.get('rede_social', perfil_alvo.rede_social)
                
                perfil_alvo.save()
                messages.success(request, f"Perfil de {user_alvo.first_name} atualizado com sucesso!")
                
            elif acao == 'remover_socio':
                # Nova Lógica de Banimento: Remove da torcida, mas mantém o Perfil SAT
                perfil_alvo.torcida = None
                perfil_alvo.aprovado = False
                
                # Opcional: Você também pode limpar dados específicos da torcida aqui, se quiser
                perfil_alvo.vulgo = ""
                perfil_alvo.pelotao = ""
                
                perfil_alvo.save()
                messages.error(request, f"O sócio {user_alvo.first_name} foi banido da torcida e agora é apenas membro SAT.")

        return redirect('moderacao_torcida')

    membros_pendentes = Perfil.objects.filter(torcida=torcida_mod, aprovado=False).exclude(user=request.user)
    membros_ativos = Perfil.objects.filter(torcida=torcida_mod, aprovado=True)
    
    # IMPORTAÇÃO LOCAL CORRIGIDA (Forçamos o OrgEvento e adicionamos as Caravanas)
    from organizadas.models import Parceiro, Publicidade, Regra, CategoriaDiretoria, FotoGaleria, ConquistaTorcida, Evento as OrgEvento, Caravana as OrgCaravana
    from accounts.models import Cancao, CampoPersonalizado
    from loja.models import Produto, CategoriaProduto
    context = {
        'torcida': torcida_mod,
        'membros_pendentes': membros_pendentes,
        'membros_ativos': membros_ativos,
        
        # CORREÇÃO PRINCIPAL: Usar o OrgEvento para puxar os check-ins verdadeiros
        'eventos': OrgEvento.objects.filter(torcida=torcida_mod).order_by('-data'), 
        'caravanas': OrgCaravana.objects.filter(torcida=torcida_mod).order_by('-saida_horario'),
        
        # Restantes dados...
        'parceiros': Parceiro.objects.filter(torcida=torcida_mod),
        'publicidades': Publicidade.objects.filter(torcida=torcida_mod),
        'campos_kyc': CampoPersonalizado.objects.filter(torcida=torcida_mod),
        'cancoes': Cancao.objects.filter(torcida=torcida_mod),
        'galeria': FotoGaleria.objects.filter(torcida=torcida_mod),
        'regras': Regra.objects.filter(torcida=torcida_mod),
        'conquistas': ConquistaTorcida.objects.filter(torcida=torcida_mod),
        'categorias_diretoria': CategoriaDiretoria.objects.filter(torcida=torcida_mod),
        
        'produtos': Produto.objects.filter(torcida=torcida_mod),
        'categorias_loja': CategoriaProduto.objects.filter(torcida=torcida_mod),
    }
    
    return render(request, 'moderacao.html', context)

@login_required
def aprovar_membro(request, perfil_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    perfil_moderador = request.user.perfil
    perfil_alvo = get_object_or_404(Perfil, id=perfil_id)
    
    # Validação de segurança: claque do alvo deve ser igual à do moderador
    if perfil_alvo.torcida == perfil_moderador.torcida:
        perfil_alvo.aprovado = True
        perfil_alvo.save()
        messages.success(request, f"O torcedor {perfil_alvo.user.username} foi aprovado!")
    else:
        messages.error(request, "Ação não permitida: Este utilizador pertence a outra claque.")
        
    return redirect('moderacao_torcida')


@login_required
@torcida_required
def cartao_socio_view(request):
    # Esta view renderiza especificamente o cartão estilo banco
    return render(request, 'torcida/cartao_socio.html')

@login_required
def area_torcida(request):
    perfil = request.user.perfil
    lista_de_torcidas = Torcida.objects.all()

    if perfil.torcida and not perfil.aprovado:
        return render(request, 'torcidas.html', {
            'status': 'pendente',
            'torcidas': lista_de_torcidas # Garantindo que a lista apareça aqui também
        })
        
    return render(request, 'torcidas.html', {'torcidas': lista_de_torcidas})

@login_required
@torcida_required
def galeria_fotos(request):
    return render(request, 'torcida/galeria.html')

@login_required
@torcida_required
def diretoria_view(request):
    return render(request, 'torcida/diretoria.html')

@login_required
@torcida_required
def mural_conquistas(request):
    return render(request, 'torcida/conquistas.html')

@login_required
@torcida_required
def cancoes_torcida(request):
    return render(request, 'torcida/cancoes.html')


@login_required
@torcida_required
def aliadas_view(request):
    return render(request, 'torcida/aliadas.html')

@login_required
@torcida_required
def viagens_view(request):
    return render(request, 'torcida/viagens.html')

@login_required
@torcida_required
def regras_view(request):
    return render(request, 'torcida/regras.html')

@login_required
@torcida_required
def lista_eventos(request):
    """Abre o eventos.html puxando do banco"""
    # Corrigido para 'data_evento' conforme seu modelo
    eventos = Evento.objects.all().order_by('data')
    return render(request, 'eventos.html', {'eventos': eventos})

class CustomLoginView(LoginView):
    template_name = 'login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Apanha o ID da torcida que foi guardado na sessão
        torcida_id = self.request.session.get('torcida_pre_selecionada')
        if torcida_id:
            context['torcida'] = Torcida.objects.filter(id=torcida_id).first()
        return context

@login_required
def curtir_post(request, post_id):
    # Procura o post (certifique-se que o nome do modelo está correto, ex: Post ou PostTorcida)
    post = get_object_or_404(PostTorcida, id=post_id)
    curtida, created = Curtida.objects.get_or_create(post=post, usuario=request.user)
    
    if created:
        # Lógica de XP: O autor do post ganha 1 XP
        perfil_autor, _ = PerfilGamificacao.objects.get_or_create(user=post.autor)
        perfil_autor.xp_total += 1
        perfil_autor.save()
        liked = True # Avisa que foi curtido
    else:
        # Se clicar de novo, remove a curtida
        curtida.delete()
        perfil_autor = PerfilGamificacao.objects.get(user=post.autor)
        if perfil_autor.xp_total > 0:
            perfil_autor.xp_total -= 1
            perfil_autor.save()
        liked = False # Avisa que foi descurtido

    # SE FOR UM PEDIDO DO NOSSO JAVASCRIPT (AJAX), DEVOLVE APENAS OS DADOS EM JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
        return JsonResponse({'liked': liked, 'likes_count': post.curtidas.count()})
            
    # Fallback de segurança (caso o utilizador acesse o link diretamente pelo navegador)
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)


@login_required
def realizar_checkin(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    agora = timezone.now()

    # 1. Valida se é o dia do evento [cite: 55]
    if evento.data_evento.date() != agora.date():
        messages.error(request, "O check-in só fica disponível no dia do evento!")
        return redirect('detalhe_evento', evento_id=evento.id)

    if request.method == "POST":
        # 2. Verifica se já existe check-in para este usuário e evento [cite: 56, 59]
        if CheckIn.objects.filter(user=request.user, evento=evento).exists():
            messages.warning(request, "Você já garantiu sua presença neste jogo!")
            return redirect('dashboard')

        # 3. Salva o Check-in [cite: 67]
        foto = request.FILES.get('foto')
        checkin = CheckIn.objects.create(
            user=request.user,
            evento=evento,
            foto=foto,
            validado=True
        )

        # 4. Motor de Gamificação: +50 XP por presença [cite: 68, 82]
        perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
        perfil_game.xp_total += 50
        perfil_game.save()

        # 5. Publicação automática no Feed [cite: 77, 95, 97]
        PostTorcida.objects.create(
            autor=request.user,
            torcida=request.user.perfil.torcida,
            texto=f"Presença confirmada no evento: {evento.titulo}! 🏟️🔥"
        )

        messages.success(request, f"Check-in realizado! +50 XP na conta.")
        return redirect('mural')

    return redirect('detalhe_evento', evento_id=evento.id)


def planos_socio(request):
    # Por enquanto, apenas renderiza uma página simples ou o próprio dashboard
    return render(request, 'seja_socio.html')

# accounts/views.py
@login_required
def hub_games_view(request):
    # Alterado para carregar o menu de lista de games
    return render(request, 'games_menu.html')

@login_required
def viagens_view(request):
    return render(request, 'viagens.html')


@login_required
def ranking_view(request):
    return render(request, 'ranking.html')


def adicionar_xp(perfil, quantidade):
    if perfil.is_socio:
        quantidade *= 2
    perfil.xp_total += quantidade
    perfil.save()
  

@login_required
def configurar_torcida(request):
    perfil = request.user.perfil
    if not request.user.is_staff or not perfil.torcida:
        return redirect('dashboard')
        
    torcida = perfil.torcida
    if request.method == 'POST':
        torcida.cor_primaria = request.POST.get('cor_primaria')
        if request.FILES.get('logo'):
            torcida.logo = request.FILES.get('logo')
        torcida.save()
        messages.success(request, "Visual da torcida atualizado!")
        
    return render(request, 'configurar_torcida.html', {'torcida': torcida})


def pre_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Se ele voltar ao menu principal, "esquece" a torcida pre-selecionada
    if 'torcida_pre_selecionada' in request.session:
        del request.session['torcida_pre_selecionada']
        
    return render(request, 'pre_login.html')

@login_required
def beneficios_view(request):
    # ... aqui depois faremos a integração com a API do Lecupon ...
    return render(request, 'beneficios.html', context)

@login_required
def hub_socio(request):
    perfil = request.user.perfil
    
    # Verifica de forma segura se o utilizador tem o plano de sócio ativo
    # (Usando a mesma lógica que você já tem na sua beneficios_view)
    is_socio = hasattr(perfil, 'socio') and perfil.socio 
    
    if is_socio:
        return redirect('beneficios') # Vai para a página de benefícios
    else:
        return redirect('seja_socio')
    

@login_required
def adicionar_comentario(request, post_id):
    if request.method == "POST":
        texto = request.POST.get('comentario')
        
        if texto:
            from organizadas.models import Post # Importação local para evitar erros
            post = get_object_or_404(Post, id=post_id)
            
            # Cria e guarda o comentário
            Comentario.objects.create(
                post=post,
                autor=request.user,
                texto=texto
            )
            
    # Redireciona de volta para a exata página onde o utilizador estava (o Mural)
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)

@login_required
def editar_perfil(request):
    usuario = request.user
    perfil = usuario.perfil 

    if request.method == 'POST':
        try:
            # 1. ATUALIZANDO DADOS DO USER (Nativo do Django)
            nome_completo = request.POST.get('nome_completo', '')
            if nome_completo:
                partes_nome = nome_completo.split(' ', 1)
                usuario.first_name = partes_nome[0]
                usuario.last_name = partes_nome[1] if len(partes_nome) > 1 else ''
            
            usuario.email = request.POST.get('email', usuario.email)
            usuario.save()

            # 2. ATUALIZANDO DADOS TEXTUAIS DO PERFIL
            perfil.cpf = request.POST.get('cpf') or None
            
            data_nascimento = request.POST.get('data_nascimento')
            if data_nascimento:
                perfil.data_nascimento = data_nascimento

            perfil.rg_cnh = request.POST.get('rg_cnh', perfil.rg_cnh)
            
            perfil.orgao_expedidor = request.POST.get('orgao_expedidor', perfil.orgao_expedidor) 
            
            perfil.whatsapp = request.POST.get('whatsapp', perfil.whatsapp)
            perfil.nome_mae = request.POST.get('nome_mae', perfil.nome_mae)
            perfil.nome_pai = request.POST.get('nome_pai', perfil.nome_pai)

            perfil.cep = request.POST.get('cep', perfil.cep)
            perfil.rua = request.POST.get('rua', perfil.rua)
            perfil.numero = request.POST.get('numero', perfil.numero)
            perfil.complemento = request.POST.get('complemento', perfil.complemento)
            perfil.bairro = request.POST.get('bairro', perfil.bairro)
            perfil.cidade = request.POST.get('cidade', perfil.cidade)
            perfil.uf = request.POST.get('uf', perfil.uf)

            # Dados da Torcida 
            perfil.vulgo = request.POST.get('vulgo', perfil.vulgo)
            perfil.pelotao = request.POST.get('pelotao', perfil.pelotao)
            perfil.rede_social = request.POST.get('rede_social', perfil.rede_social)

            # 3. TRATANDO OS UPLOADS DE IMAGEM (request.FILES)
            if 'foto' in request.FILES:
                perfil.foto = request.FILES['foto']
            
            if 'doc_frente' in request.FILES:
                perfil.doc_frente = request.FILES['doc_frente']
                
            if 'doc_verso' in request.FILES:
                perfil.doc_verso = request.FILES['doc_verso']
                
            if 'doc_selfie' in request.FILES:
                perfil.doc_selfie = request.FILES['doc_selfie']

            # 4. SALVANDO TUDO
            perfil.save()
            
            messages.success(request, 'Seu perfil e documentos foram atualizados com sucesso!')
            return redirect('perfil') 

        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao atualizar o perfil: {str(e)}')
            return redirect('editar_perfil')

    return render(request, 'editar_perfil.html')

@login_required
def meus_pedidos(request):
    try:
        from loja.models import Pedido
        # CORREÇÃO 1: Mudar de 'cliente' para 'usuario'
        # CORREÇÃO 2: Adicionar .prefetch_related('itens') para carregar a quantidade de itens rápido
        pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('itens').order_by('-data_pedido')
    except Exception as e:
        print(f"Erro ao carregar pedidos: {e}")
        pedidos = [] 
        
    # CORREÇÃO 3: O template está na raiz da pasta templates, então tiramos o 'loja/'
    return render(request, 'meus_pedidos.html', {'pedidos': pedidos})

@login_required
def seguranca(request):
    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        # 1. Verifica se a senha antiga está certa
        if not request.user.check_password(senha_atual):
            messages.error(request, 'A senha atual está incorreta.')
        # 2. Verifica se as senhas novas coincidem
        elif nova_senha != confirmar_senha:
            messages.error(request, 'As novas senhas não coincidem.')
        # 3. Se estiver tudo OK, guarda a nova senha
        else:
            request.user.set_password(nova_senha)
            request.user.save()
            # Esta linha garante que o utilizador não é deslogado ao mudar a senha:
            update_session_auth_hash(request, request.user) 
            messages.success(request, 'Senha atualizada com sucesso e segurança!')
            return redirect('perfil')
            
    return render(request, 'seguranca.html')

@login_required
def admin_editar_utilizador(request, perfil_id):
    # Trava de segurança: Apenas superusuários (Admin Master) podem acessar
    if not request.user.is_superuser:
        messages.error(request, "Acesso negado. Área restrita à administração geral.")
        return redirect('dashboard')
        
    # Busca o perfil alvo
    perfil = get_object_or_404(Perfil, id=perfil_id)
    
    if request.method == 'POST':
        user_alvo = perfil.user
        user_alvo.first_name = request.POST.get('first_name', user_alvo.first_name)
        user_alvo.email = request.POST.get('email', user_alvo.email)
        user_alvo.save()
        
        # O "or None" evita o erro de UNIQUE constraint caso o campo venha vazio
        perfil.cpf = request.POST.get('cpf') or None
        perfil.telefone = request.POST.get('telefone', perfil.telefone) 
        perfil.whatsapp = request.POST.get('whatsapp', perfil.whatsapp)
        perfil.rg_cnh = request.POST.get('rg_cnh', perfil.rg_cnh)
        perfil.orgao_expedidor = request.POST.get('orgao_expedidor', perfil.orgao_expedidor)
        
        data_nasc = request.POST.get('data_nascimento')
        if data_nasc:
            perfil.data_nascimento = data_nasc

        # Endereço
        perfil.cep = request.POST.get('cep', perfil.cep)
        perfil.rua = request.POST.get('rua', perfil.rua)
        perfil.numero = request.POST.get('numero', perfil.numero)
        perfil.complemento = request.POST.get('complemento', perfil.complemento)
        perfil.bairro = request.POST.get('bairro', perfil.bairro)
        perfil.cidade = request.POST.get('cidade', perfil.cidade)
        perfil.uf = request.POST.get('uf', perfil.uf)

        # Identidade na Torcida
        perfil.vulgo = request.POST.get('vulgo', perfil.vulgo)
        perfil.pelotao = request.POST.get('pelotao', perfil.pelotao)
        perfil.rede_social = request.POST.get('rede_social', perfil.rede_social)
        
        perfil.save()
        
        messages.success(request, f"O utilizador {user_alvo.first_name} foi editado com sucesso pelo painel Admin!")
        return redirect('admin_utilizadores') 

    context = {
        'perfil_edit': perfil,
    }
    return render(request, 'admin_utilizadores.html', context)

# --- LÓGICA PARA EVENTOS ---
@login_required
def toggle_presenca_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    presenca = Presenca.objects.filter(user=request.user, evento=evento).first()
    
    if presenca:
        presenca.delete() # Desconfirma
        messages.warning(request, "Presença cancelada.")
    else:
        Presenca.objects.create(user=request.user, evento=evento) # Confirma
        messages.success(request, "Presença confirmada!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def toggle_salvar_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    perfil = request.user.perfil
    
    if evento in perfil.eventos_salvos.all():
        perfil.eventos_salvos.remove(evento)
    else:
        perfil.eventos_salvos.add(evento)
        messages.success(request, "Evento salvo!")
        
    # Devolve o utilizador à página onde ele estava
    return redirect(request.META.get('HTTP_REFERER', '/'))

# --- LÓGICA PARA CARAVANAS ---
@login_required
def toggle_presenca_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    presenca = PresencaCaravana.objects.filter(user=request.user, caravana=caravana).first()
    
    if presenca:
        presenca.delete()
        messages.warning(request, "Nome retirado da caravana.")
    else:
        PresencaCaravana.objects.create(user=request.user, caravana=caravana)
        messages.success(request, "Nome adicionado à caravana!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def toggle_salvar_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    perfil = request.user.perfil
    
    if caravana in perfil.caravanas_salvas.all():
        perfil.caravanas_salvas.remove(caravana)
    else:
        perfil.caravanas_salvas.add(caravana)
        messages.success(request, "Caravana salva com sucesso!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def exportar_csv_moderacao(request, tipo, item_id=0):
    perfil = request.user.perfil
    
    # Bloqueio de segurança
    if not request.user.is_staff or not perfil.torcida:
        return redirect('dashboard')
        
    torcida = perfil.torcida
    
    # Configura a resposta para baixar um arquivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    # Adiciona o BOM do UTF-8 para o Excel ler os acentos brasileiros perfeitamente
    response.write('\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';') # Ponto e vírgula divide melhor no Excel PT-BR
    
    if tipo == 'socios':
        response['Content-Disposition'] = f'attachment; filename="socios_{torcida.sigla or torcida.nome}.csv"'
        writer.writerow(['NOME', 'EMAIL', 'CPF', 'WHATSAPP', 'VULGO', 'PELOTAO', 'STATUS'])
        
        membros = Perfil.objects.filter(torcida=torcida)
        for m in membros:
            status = "Aprovado" if m.aprovado else "Pendente"
            writer.writerow([
                m.user.first_name or m.user.username, 
                m.user.email, 
                m.cpf or "", 
                m.whatsapp or "", 
                m.vulgo or "", 
                m.pelotao or "", 
                status
            ])
            
    elif tipo == 'evento':
        from organizadas.models import Evento as OrgEvento
        evento = get_object_or_404(OrgEvento, id=item_id, torcida=torcida)
        response['Content-Disposition'] = f'attachment; filename="evento_{evento.id}_lista.csv"'
        writer.writerow(['NOME', 'EMAIL', 'WHATSAPP', 'VULGO', 'TIPO_CONFIRMACAO'])
        
        # Presenças Simples
        for presenca in evento.presencas.all():
            u = presenca.user
            writer.writerow([u.first_name or u.username, u.email, u.perfil.whatsapp or "", u.perfil.vulgo or "", "Confirmou Presenca"])
            
        # Check-ins Validados (via Gamificação)
        for checkin in evento.checkins_accounts.all():
            u = checkin.user
            writer.writerow([u.first_name or u.username, u.email, u.perfil.whatsapp or "", u.perfil.vulgo or "", "Check-in Gamificado"])
            
    elif tipo == 'caravana':
        from organizadas.models import Caravana as OrgCaravana
        from accounts.models import PresencaCaravana
        caravana = get_object_or_404(OrgCaravana, id=item_id, torcida=torcida)
        response['Content-Disposition'] = f'attachment; filename="caravana_{caravana.id}_lista.csv"'
        writer.writerow(['NOME', 'EMAIL', 'WHATSAPP', 'VULGO', 'PELOTAO', 'RG/CNH'])
        
        presencas = PresencaCaravana.objects.filter(caravana=caravana)
        for p in presencas:
            u = p.user
            writer.writerow([
                u.first_name or u.username, 
                u.email, 
                u.perfil.whatsapp or "", 
                u.perfil.vulgo or "", 
                u.perfil.pelotao or "", 
                u.perfil.rg_cnh or ""
            ])

    return response

# ==========================================
# INTEGRAÇÃO EFÍ BANK (PIX)
# ==========================================

@login_required
def pagar_fatura_pix(request, fatura_id):
    from accounts.models import Fatura
    from accounts.efi_utils import gerar_cobranca_pix
    
    fatura = get_object_or_404(Fatura, id=fatura_id, assinatura__perfil__user=request.user)
    
    if fatura.status == 'pago':
        messages.info(request, "Esta fatura já está paga.")
        return redirect('dashboard')
        
    # Se ainda não tem txid ou qr code, gera
    if not fatura.txid:
        resultado = gerar_cobranca_pix(fatura, tipo='fatura')
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('dashboard')
            
    return render(request, 'pagar_pix.html', {'fatura': fatura})

@csrf_exempt
def webhook_efi(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # A Efí envia um array de 'pix' quando o pagamento é confirmado
            if 'pix' in data:
                for pagamento in data['pix']:
                    txid = pagamento.get('txid')
                    
                    if txid:
                        from accounts.models import Fatura
                        from loja.models import Pedido
                        
                        # Tenta encontrar e atualizar na Loja
                        pedido = Pedido.objects.filter(txid=txid).first()
                        if pedido:
                            pedido.status = 'pago'
                            pedido.save()
                            continue
                            
                        # Tenta encontrar e atualizar nos Planos
                        fatura = Fatura.objects.filter(txid=txid).first()
                        if fatura:
                            fatura.status = 'pago'
                            fatura.data_pagamento = timezone.now()
                            fatura.save()
                            
                            # Ativa a assinatura vinculada
                            if not fatura.assinatura.ativa:
                                fatura.assinatura.ativa = True
                                fatura.assinatura.save()
                            
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return HttpResponse(status=405)


# ==========================================
# ASSINATURA DE PLANO PELO USUÁRIO
# ==========================================

@login_required
def assinar_plano(request, plano_id):
    """
    Cria a Assinatura + primeira Fatura para o plano escolhido,
    gera a cobrança PIX e redireciona para o checkout.
    """
    if request.method != 'POST':
        return redirect('seja_socio')
    
    perfil = request.user.perfil
    plano = get_object_or_404(PlanoSocio, id=plano_id, ativo=True)
    
    # Verifica se o usuário já tem uma assinatura ativa para esse plano
    assinatura_existente = Assinatura.objects.filter(perfil=perfil, plano=plano, ativa=True).first()
    if assinatura_existente:
        # Se já tem assinatura, verifica se há fatura pendente
        fatura_pendente = Fatura.objects.filter(assinatura=assinatura_existente, status='pendente').first()
        if fatura_pendente:
            return redirect('pagar_fatura_pix', fatura_id=fatura_pendente.id)
        messages.info(request, 'Você já possui este plano ativo!')
        return redirect('financeiro')
    
    # Desativa assinaturas anteriores (troca de plano)
    Assinatura.objects.filter(perfil=perfil, ativa=True).update(ativa=False)
    
    # Cria a nova assinatura
    assinatura = Assinatura.objects.create(
        perfil=perfil,
        plano=plano,
        ativa=False  # Só ativa depois de pagar
    )
    
    # Cria a primeira fatura
    from datetime import timedelta
    fatura = Fatura.objects.create(
        assinatura=assinatura,
        valor=plano.preco,
        data_vencimento=timezone.now().date() + timedelta(days=3),
        status='pendente'
    )
    
    # Gera a cobrança PIX
    try:
        resultado = gerar_cobranca_pix(fatura, tipo='fatura')
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('financeiro')
    except Exception as e:
        messages.error(request, f"Erro ao gerar PIX: {str(e)}")
        return redirect('financeiro')
    
    return redirect('pagar_fatura_pix', fatura_id=fatura.id)


# ==========================================
# PAINEL DO MODERADOR DE PLANOS
# ==========================================

@login_required
def painel_planos(request):
    if not request.user.is_staff or not hasattr(request.user, 'perfil') or not request.user.perfil.torcida:
        messages.error(request, "Acesso negado. Apenas moderadores autorizados.")
        return redirect('dashboard')

    planos = PlanoSocio.objects.filter(torcida=request.user.perfil.torcida).order_by('-id')
    context = {
        'planos': planos,
        'torcida': request.user.perfil.torcida
    }
    return render(request, 'painel_planos.html', context)

@login_required
def form_plano(request, plano_id=None):
    if not (request.user.is_staff and hasattr(request.user, 'perfil') and request.user.perfil.torcida):
        return redirect('dashboard')
        
    plano = get_object_or_404(PlanoSocio, id=plano_id, torcida=request.user.perfil.torcida) if plano_id else None
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        preco = request.POST.get('preco').replace(',', '.')
        beneficios = request.POST.get('beneficios')
        destaque = request.POST.get('destaque') == 'on'
        ativo = request.POST.get('ativo') == 'on'
        
        if plano:
            plano.nome = nome
            plano.preco = preco
            plano.beneficios = beneficios
            plano.destaque = destaque
            plano.ativo = ativo
            plano.save()
            messages.success(request, 'Plano atualizado!')
        else:
            PlanoSocio.objects.create(
                nome=nome,
                preco=preco,
                beneficios=beneficios,
                destaque=destaque,
                ativo=ativo,
                torcida=request.user.perfil.torcida
            )
            messages.success(request, 'Plano criado com sucesso!')
            
        return redirect('painel_planos')
        
    context = {
        'plano': plano,
        'torcida': request.user.perfil.torcida
    }
    return render(request, 'form_plano.html', context)

@login_required
def excluir_plano(request, plano_id):
    if request.user.is_staff and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        plano = get_object_or_404(PlanoSocio, id=plano_id, torcida=request.user.perfil.torcida)
        plano.delete()
        messages.success(request, 'Plano removido com sucesso.')
    return redirect('painel_planos')

@login_required
def cancelar_vinculo(request):
    perfil = request.user.perfil
    perfil.torcida = None
    perfil.aprovado = False
    perfil.save()
    messages.success(request, "Vínculo cancelado. Você agora é um membro neutro.")
    return redirect('torcidas')