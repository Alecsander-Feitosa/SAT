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
from organizadas.models import Evento, Torcida, Post, Noticia # Verifique se é Post ou PostTorcida
from django.contrib.auth.models import User
from organizadas.models import Parceiro
from organizadas.models import Publicidade
from django.db.models import Q
from datetime import date
from organizadas.models import Comentario
from accounts.models import Perfil
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .decorators import torcida_required
from .models import Perfil, Presenca, Conquista, Evento, CheckIn, PlanoSocio
from .forms import CadastroForm, PerfilCompletoForm
from loja.models import Produto


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
# accounts/views.py

def cadastro(request):
    # Identifica se o utilizador veio de uma torcida específica (Sessão)
    torcida_id = request.session.get('torcida_pre_selecionada')
    torcida = Torcida.objects.filter(id=torcida_id).first() if torcida_id else None

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            # Verifica se as senhas batem manualmente para garantir
            if request.POST.get('senha') != request.POST.get('confirmar_senha'):
                messages.error(request, "As senhas não coincidem.")
                return render(request, 'cadastro.html', {'form': form, 'torcida': torcida})

            # 1. Cria o utilizador e o perfil base
            user = form.save()
            perfil = user.perfil
            
            # 2. SOLICITAÇÃO AUTOMÁTICA DA TORCIDA AQUI
            if torcida:
                perfil.torcida = torcida
                perfil.aprovado = False 
                perfil.save()
                
                # Limpa a sessão pois já não precisamos
                if 'torcida_pre_selecionada' in request.session:
                    del request.session['torcida_pre_selecionada']
                    
                messages.success(request, f"Conta criada! Solicitação enviada para a aprovação da {torcida.nome}.")
            
            # 3. Faz o login automático
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # 4. Vai direto para o Dashboard (Eliminamos a Etapa 2 para quem já vem da torcida!)
            return redirect('dashboard') 
        else:
            # Se cair aqui, o e-mail já existe ou falta algo
            print("ERROS DO FORMULÁRIO:", form.errors)
            messages.error(request, "Erro: Este e-mail já está registado ou os dados são inválidos.")
    else:
        form = CadastroForm()
        
    return render(request, 'cadastro.html', {'form': form, 'torcida': torcida})

@login_required
def cadastro_etapa2(request):
    perfil = request.user.perfil
    
    # Pega o ID da torcida que foi salva lá no início (escolher-torcida)
    torcida_id_sessao = request.session.get('torcida_pre_selecionada')
    
    # BUSCA A TORCIDA NO BANCO PARA MANDAR PRO HTML (Isto corrigirá o texto em branco!)
    torcida_selecionada = None
    if torcida_id_sessao:
        from organizadas.models import Torcida
        torcida_selecionada = Torcida.objects.filter(id=torcida_id_sessao).first()

    # Se já tem tudo, vai pro dashboard
    if perfil.torcida and perfil.time_coracao:
        return redirect('dashboard')

    times_brasil = [
        {"nome": "Flamengo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/2/2e/Flamengo_braz_logo.svg"},
        {"nome": "Corinthians", "escudo": "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png"},
        {"nome": "São Paulo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/2/2b/S%C3%A3o_Paulo_Futebol_Clube.svg"},
        {"nome": "Palmeiras", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/10/Palmeiras_logo.svg"},
        {"nome": "Vasco", "escudo": "https://upload.wikimedia.org/wikipedia/pt/a/ac/CRVascodaGama.png"},
        {"nome": "Grêmio", "escudo": "https://upload.wikimedia.org/wikipedia/commons/b/b4/Gr%C3%AAmio_Logo.svg"},
        {"nome": "Internacional", "escudo": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Escudo_do_Sport_Club_Internacional.svg"},
        {"nome": "Cruzeiro", "escudo": "https://upload.wikimedia.org/wikipedia/commons/9/90/Cruzeiro_Esporte_Clube_%28logo%29.svg"},
        {"nome": "Atlético-MG", "escudo": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Atletico_mineiro_galo.png"},
        {"nome": "Botafogo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Escudo_Botafogo.svg"},
        {"nome": "Fluminense", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/a3/Escudo_Fluminense_FC_2024.svg"},
        {"nome": "Santos", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/15/Santos_Logo.png"},
        {"nome": "Bahia", "escudo": "https://upload.wikimedia.org/wikipedia/pt/9/90/ECBahia.png"},
        {"nome": "Sport", "escudo": "https://upload.wikimedia.org/wikipedia/pt/3/30/Sport_Club_do_Recife.png"},
        {"nome": "Fortaleza", "escudo": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Fortaleza_Esporte_Clube_logo.svg"},
        {"nome": "Ceará", "escudo": "https://upload.wikimedia.org/wikipedia/commons/3/38/Cear%C3%A1_Sporting_Club_logo.svg"},
        {"nome": "Athletico-PR", "escudo": "https://upload.wikimedia.org/wikipedia/commons/b/b3/CA_Paranaense.svg"},
        {"nome": "Coritiba", "escudo": "https://upload.wikimedia.org/wikipedia/commons/b/b0/Coritiba_FBC_%282011%29.svg"},
    ]

    if request.method == 'POST':
        data_nasc = request.POST.get('data_nascimento')
        time_coracao = request.POST.get('time_coracao')
        
        if data_nasc:
            perfil.data_nascimento = data_nasc
        if time_coracao:
            perfil.time_coracao = time_coracao

        # Como a torcida já foi escolhida na tela anterior, apenas salvamos ela aqui
        if torcida_selecionada:
            perfil.torcida = torcida_selecionada
            perfil.aprovado = False 
            perfil.save()
            
            # Limpa a sessão
            if 'torcida_pre_selecionada' in request.session:
                del request.session['torcida_pre_selecionada']
                
            messages.success(request, f"Pedido enviado! Aguarde a aprovação da {torcida_selecionada.nome}.")
            return redirect('dashboard')
        else:
            perfil.save()
            return redirect('dashboard')

    context = {
        'torcida': torcida_selecionada,  # MANDA PARA O HTML PARA PERSONALIZAR
        'times_brasil': times_brasil,
    }
    return render(request, 'cadastro_etapa2.html', context)


# accounts/views.py
class CadastroForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput())
    confirmar_senha = forms.CharField(widget=forms.PasswordInput())
    cpf = forms.CharField(max_length=14)
    telefone = forms.CharField(max_length=20) 
    nome = forms.CharField(max_length=150)   
    
    # O time não pode estar aqui, foi para a Etapa 2

    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def save(self, commit=True):
        email_limpo = self.cleaned_data["email"]
        
        user = super().save(commit=False)
        user.username = email_limpo 
        user.first_name = self.cleaned_data["nome"]
        user.set_password(self.cleaned_data["senha"])
        
        if commit:
            from django.contrib.auth.models import User
            if not User.objects.filter(username=email_limpo).exists():
                user.save()
                
                Perfil.objects.update_or_create(
                    user=user,
                    defaults={
                        'cpf': self.cleaned_data.get('cpf'),
                        'whatsapp': self.cleaned_data.get('telefone'),
                    }
                )
        return user
# FIM DA ATUALIZAÇÃO: Classe CadastroForm

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
                noticias_gerais_api = response_geral.json().get('results', [])[:5]
                cache.set('news_geral_v1', noticias_gerais_api, 900)
        except Exception:
            noticias_gerais_api = []

    # 2. NOTÍCIAS DO TIME DO CORAÇÃO
    noticias_time_api = []
    if time_busca and time_busca != "Outro":
        cache_key_time = f'news_time_{time_busca.replace(" ", "_")}_v2' # Mudei para _v2 para limpar o cache antigo
        noticias_time_api = cache.get(cache_key_time)
        
        if noticias_time_api is None:
            try:
                url_time = 'https://newsdata.io/api/1/news'
                
                # ATUALIZAÇÃO AQUI: Adicionado category='sports' e aspas na busca (q)
                params = {
                    'apikey': api_key, 
                    'country': 'br', 
                    'language': 'pt', 
                    'category': 'sports', 
                    'q': f'"{time_busca}"'
                }
                
                response_time = requests.get(url_time, params=params, timeout=5)
                if response_time.status_code == 200:
                    noticias_time_api = response_time.json().get('results', [])[:5]
                    cache.set(cache_key_time, noticias_time_api, 900)
            except Exception:
                noticias_time_api = []

    # 3. COMUNICADOS SAT (Base de Dados Local)
    noticias_sat = Noticia.objects.all().order_by('-data_publicacao')[:3]

    torcida_selecionada = perfil.torcida

    if torcida_selecionada:
        eventos = Evento.objects.filter(torcida=torcida_selecionada, data__gte=agora).order_by('data')[:3]
        posts_sociais = Post.objects.filter(torcida=torcida_selecionada).order_by('-data_criacao')[:10]
        parceiros = Parceiro.objects.filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
        publicidades = Publicidade.objects.filter(ativo=True, data_inicio__lte=agora, data_fim__gte=agora).filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
    else:
        eventos = Evento.objects.filter(data__gte=agora).order_by('data')[:3]
        posts_sociais = Post.objects.all().order_by('-data_criacao')[:10]
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
    
    lista_final.append({
        'url': '#',
        'title': 'NOVA COLEÇÃO DE BONÉS DA BONELARIA',
        'description': 'Garanta o novo modelo oficial da SAT produzido na nossa fábrica.',
        'image': 'https://placehold.co/600x400/D37129/white?text=BONELARIA+SAT',
        'source': 'DIRETORIA'
    })

    urls_vistas = set()

    # Só pesquisa o time se ele não escolheu a opção "Outro"
    if time_busca and time_busca != "Outro":
        try:
            # ATUALIZAÇÃO AQUI: Forçar categoria de desporto e texto exato
            params_time = {
                'apikey': api_key, 
                'country': 'br', 
                'language': 'pt', 
                'category': 'sports', 
                'q': f'"{time_busca}"'
            }
            resp_time = requests.get(url_api, params=params_time, timeout=5)
            if resp_time.status_code == 200:
                for art in resp_time.json().get('results', []):
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
        {"nome": "Flamengo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/2/2e/Flamengo_braz_logo.svg"},
        {"nome": "Corinthians", "escudo": "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png"},
        {"nome": "São Paulo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/2/2b/S%C3%A3o_Paulo_Futebol_Clube.svg"},
        {"nome": "Palmeiras", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/10/Palmeiras_logo.svg"},
        {"nome": "Vasco", "escudo": "https://upload.wikimedia.org/wikipedia/pt/a/ac/CRVascodaGama.png"},
        {"nome": "Grêmio", "escudo": "https://upload.wikimedia.org/wikipedia/commons/b/b4/Gr%C3%AAmio_Logo.svg"},
        {"nome": "Internacional", "escudo": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Escudo_do_Sport_Club_Internacional.svg"},
        {"nome": "Cruzeiro", "escudo": "https://upload.wikimedia.org/wikipedia/commons/9/90/Cruzeiro_Esporte_Clube_%28logo%29.svg"},
        {"nome": "Atlético-MG", "escudo": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Atletico_mineiro_galo.png"},
        {"nome": "Botafogo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Escudo_Botafogo.svg"},
        {"nome": "Fluminense", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/a3/Escudo_Fluminense_FC_2024.svg"},
        {"nome": "Santos", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/15/Santos_Logo.png"},
        {"nome": "Bahia", "escudo": "https://upload.wikimedia.org/wikipedia/pt/9/90/ECBahia.png"},
        {"nome": "Sport", "escudo": "https://upload.wikimedia.org/wikipedia/pt/3/30/Sport_Club_do_Recife.png"},
        {"nome": "Fortaleza", "escudo": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Fortaleza_Esporte_Clube_logo.svg"},
        {"nome": "Ceará", "escudo": "https://upload.wikimedia.org/wikipedia/commons/3/38/Cear%C3%A1_Sporting_Club_logo.svg"},
        {"nome": "Outro", "escudo": "https://placehold.co/100x100/1a1a1a/FFF?text=OUTRO"},
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
    
    # 1. Se já tem torcida e está APROVADO, vai pro Hub com sucesso.
    if perfil.torcida and perfil.aprovado:
        return redirect('hub_organizadas') # <--- NOME CORRIGIDO AQUI!
    
    # 2. Se tem torcida mas NÃO está aprovado, ele fica na página a ver a mensagem "Pendente"
    if perfil.torcida and not perfil.aprovado:
        return render(request, 'torcidas.html', {'status': 'pendente', 'torcida': perfil.torcida})
    
    # 3. Se não tem torcida nenhuma, mostramos a lista para ele escolher
    lista_de_torcidas = Torcida.objects.all()
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
@torcida_required
def mural_social(request):
    perfil = request.user.perfil
    
    if request.method == "POST":
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        
        # O print abaixo ajudará você a ver no terminal se os dados estão chegando
        print(f"DEBUG: Texto recebido: {texto} | Imagem recebida: {imagem}")

        if texto or imagem:
            # USANDO O NOME CORRIGIDO: PostTorcida
            PostTorcida.objects.create(
                autor=request.user,
                torcida=perfil.torcida,
                texto=texto,
                imagem=imagem
            )
            return redirect('mural.html') 

    # Busca usando PostTorcida e o campo data_criacao (que está correto no seu models.py)
    posts = PostTorcida.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')
    return render(request, 'mural.html', {'posts': posts})




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
    if request.method == "POST":
        evento = get_object_or_404(Evento, id=evento_id)
        
        # 1. Captura os dados do formulário
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        foto = request.FILES.get('foto')

        # 2. Registra o Check-in (O Signal no models.py dará os 50 XP)
        checkin = CheckIn.objects.create(
            user=request.user,
            evento=evento,
            latitude=float(lat) if lat else 0.0,
            longitude=float(lon) if lon else 0.0,
            foto=foto,
            validado=True # Aqui você pode adicionar lógica de conferência depois
        )
        
        messages.success(request, f"Presença confirmada no {evento.titulo}! +50 XP")
        return redirect('dashboard')
    
    return redirect('detalhe_evento', evento_id=evento_id)

@login_required
def detalhe_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    
    # Verifica se o usuário já confirmou presença
    confirmado = Presenca.objects.filter(user=request.user, evento=evento).exists()
    
    # Busca o perfil de gamificação
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # Lógica de segurança para a cor do tema
    # Se o nível não existir, usamos a cor padrão #ff6b00
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
    lideres = PerfilGamificacao.objects.select_related('user', 'nivel').order_by('-xp_total')[:10]
    
    context = {
        'lideres': lideres,
        'cor_tema': "#D37129" # Laranja oficial da SAT
    }
    return render(request, 'ranking.html', context)

class Noticia(models.Model):
    titulo = models.CharField("Título", max_length=200)
    subtitulo = models.CharField("Subtítulo", max_length=255, blank=True)
    conteudo = models.TextField("Conteúdo")
    imagem = models.ImageField("Imagem de Capa", upload_to='noticias/')
    data_publicacao = models.DateTimeField(auto_now_add=True)
    autor = models.CharField("Autor", max_length=100, default="Imprensa SAT")

    class Meta:
        verbose_name = "Notícia"
        verbose_name_plural = "Notícias" 

    def __str__(self):
        return self.titulo

@login_required
def games_hub(request):
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    return render(request, 'games_menu.html', {
        'perfil_game': perfil_game,
        'progresso': perfil_game.progresso_nivel()
    })


@login_required
def moderacao_torcida(request):
    perfil_moderador = request.user.perfil
    
    # Segurança: Apenas quem tem torcida e é da equipa (is_staff) pode moderar
    if not request.user.is_staff or not perfil_moderador.torcida:
        messages.error(request, "Não tem permissão para moderar.")
        return redirect('dashboard')
        
    # FILTRO MÁGICO: Filtra apenas pendentes da MESMA claque do moderador
    pendentes = Perfil.objects.filter(
        torcida=perfil_moderador.torcida, 
        aprovado=False
    ).exclude(user=request.user)
    
    # Dados para os contadores do Cartão de Moderador
    context = {
        'pendentes': pendentes,
        'membros_pendentes': pendentes.count(),
        'torcida': perfil_moderador.torcida,
        'membros_ativos': Perfil.objects.filter(torcida=perfil_moderador.torcida, aprovado=True).count(),
        'eventos': Evento.objects.filter(torcida=perfil_moderador.torcida),
        'parceiros': Parceiro.objects.filter(torcida=perfil_moderador.torcida),
        'publicidades': Publicidade.objects.filter(torcida=perfil_moderador.torcida, ativo=True),
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
    if perfil.torcida and not perfil.aprovado:
        # Se já escolheu e espera aprovação, mostra uma mensagem específica
        return render(request, 'torcidas.html', {'status': 'pendente'})
        
    lista_de_torcidas = Torcida.objects.all()
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
    perfil = request.user.perfil
    if request.method == 'POST':
        # Dados do User
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.save()
        
        # Dados do Perfil
        perfil.vulgo = request.POST.get('vulgo', perfil.vulgo)
        perfil.pelotao = request.POST.get('pelotao', perfil.pelotao)
        perfil.rede_social = request.POST.get('rede_social', perfil.rede_social)
        perfil.time_coracao = request.POST.get('time_coracao', perfil.time_coracao)
        perfil.whatsapp = request.POST.get('whatsapp', perfil.whatsapp)
        
        if 'foto' in request.FILES:
            perfil.foto = request.FILES['foto']
            
        perfil.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('perfil')
        
    return render(request, 'editar_perfil.html', {'perfil': perfil})

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



def cadastro_etapa2_view(request):
    # 1. Recupera o ID da torcida da sessão
    torcida_id = request.session.get('torcida_selecionada_id')
    
    # Se o usuário caiu aqui de paraquedas sem escolher a torcida, manda ele voltar
    if not torcida_id:
        return redirect('escolher_torcida_url_name')
        
    # 2. Busca o objeto da Torcida
    torcida = Torcida.objects.get(id=torcida_id)
    
    if request.method == 'POST':
        form = CadastroEtapa2Form(request.POST)
        if form.is_valid():
            # Salva o perfil, associando também a torcida ao usuário
            perfil = form.save(commit=False)
            perfil.torcida = torcida # Associa a torcida aqui!
            perfil.save()
            
            # Limpa a sessão após o uso (opcional, mas recomendado)
            if 'torcida_selecionada_id' in request.session:
                del request.session['torcida_selecionada_id']
                
            return redirect('dashboard') # Redireciona para o fim do fluxo
    else:
        form = CadastroEtapa2Form()

    # 3. Envia a torcida para o template para personalizar a tela
    context = {
        'form': form,
        'torcida': torcida
    }
    return render(request, 'cadastro_etapa2.html', context)