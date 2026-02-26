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
# Importações de outros Apps (Cada uma no seu lugar correto)
from .models import Perfil, Presenca               # Modelos do App Accounts
from .forms import CadastroForm, PerfilCompletoForm 
from content.models import Post                    # Modelos do App Content
from content.api import api_noticias
from gamification.models import PerfilGamificacao, Nivel # Modelos do App Gamification
from organizadas.models import Torcida, Evento
from django.core.cache import cache
from organizadas.models import Noticia
from organizadas.models import Evento
from django.utils import timezone
from .models import Conquista
from django.contrib.auth.views import LoginView


def cadastro(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CadastroForm()
    return render(request, 'cadastro.html', {'form': form})

# accounts/views.py

@login_required
def dashboard(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # 1. Busca Notícias da API focadas em Futebol
    noticias_api = cache.get('news_api_futebol')
    if not noticias_api:
        try:
            # Filtro focado em futebol brasileiro e notícias esportivas
            url = f'https://newsapi.org/v2/everything?q=futebol+brasileiro+brasileirao&language=pt&sortBy=publishedAt&pageSize=5&apiKey={api_noticias}'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                noticias_api = response.json().get('articles', [])
                cache.set('news_api_futebol', noticias_api, 900) # 15 min de cache
        except Exception:
            noticias_api = []

    # 2. Dados de XP e Eventos (mantendo sua lógica atual)
    xp_atual = perfil_game.xp_total or 0
    cor_tema = perfil_game.nivel.cor_tema if perfil_game.nivel else "#D37129"
    eventos_torcida = Evento.objects.filter(torcida=perfil.torcida).order_by('data_evento')[:3] if perfil.torcida else []

    proximos_eventos = Evento.objects.filter(
        data_evento__gte=timezone.now()
    ).order_by('data_evento')[:3]

    conquistas = Conquista.objects.all()

    context = {
        'conquistas': conquistas,
        'eventos': proximos_eventos,
        'perfil': perfil,
        'perfil_game': perfil_game,
        'noticias': noticias_api, # Enviando a lista da API
        'cor_tema': cor_tema,
        'xp_atual': xp_atual,
        'eventos': eventos_torcida,
    }
    return render(request, 'dashboard.html', context)

@login_required
def editar_perfil(request):
    # O use de get_or_create evita que o erro ocorra se o perfil sumir do banco
    perfil, created = Perfil.objects.get_or_create(user=request.user) 
    
    if request.method == 'POST':
        form = PerfilCompletoForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('perfil')
    else:
        form = PerfilCompletoForm(instance=perfil)
    
    return render(request, 'perfil.html', {'form': form, 'perfil': perfil})
@login_required
def carteirinha(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    img = qrcode.make(f"SAT-{request.user.id}")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    return render(request, 'carteirinha.html', {'perfil': perfil, 'qr_code': qr_base64, 'torcida': perfil.torcida})


# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py
def noticias(request):
    api_key = "pub_629d163494fb4b3c9f19c706166a65e9"
    url_api = f"https://newsdata.io/api/1/news?apikey={api_key}&country=br&category=sports&language=pt"
    
    lista_final = []
    
    # 1. Notícia da Fábrica com campos padronizados
    lista_final.append({
        'url': '#',
        'title': 'NOVA COLEÇÃO DE BONÉS DA BONELARIA',
        'description': 'Garanta o novo modelo oficial da SAT produzido na nossa fábrica.',
        'image': 'https://placehold.co/600x400/D37129/white?text=BONELARIA+SAT',
        'source': 'DIRETORIA'
    })

    try:
        response = requests.get(url_api, timeout=5)
        data = response.json()
        results = data.get('results', [])
        
        for art in results:
            # 2. Padronizamos os dados da API para os mesmos nomes
            lista_final.append({
                'url': art.get('link') or '#',
                'title': art.get('title') or 'Notícia SAT',
                'description': art.get('description') or '',
                'image': art.get('image_url') or 'https://placehold.co/600x400/4A4D4E/white?text=SAT+NEWS',
                'source': art.get('source_id') or 'FUTEBOL'
            })
    except Exception as e:
        print(f"Erro: {e}")

    return render(request, 'noticias.html', {'noticias': lista_final})


@login_required
def seja_socio(request):
    # Pega o perfil de gamificação ou cria um se não existir
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # Define cor padrão se o nível for Nulo
    cor_tema = "#ff6b00"
    if perfil_game.nivel:
        cor_tema = perfil_game.nivel.cor_tema
    
    return render(request, 'seja_socio.html', {'cor_tema': cor_tema})

# accounts/views.py

@login_required
def torcidas(request):
    perfil = request.user.perfil
    
    # Se ele já escolheu, mostramos o Mural (image_e9dbf7.png)
    if perfil.torcida:
        return render(request, 'mural.html', {'torcida': perfil.torcida})
    
    # Caso contrário, mostramos a lista de escolha
    lista_de_torcidas = Torcida.objects.all()
    return render(request, 'torcidas.html', {'torcidas': lista_de_torcidas})

@login_required
def vincular_torcida(request, torcida_id):
    # Vincula o torcedor à organizada escolhida
    torcida = get_object_or_404(Torcida, id=torcida_id)
    perfil = get_object_or_404(Perfil, user=request.user)
    torcida = get_object_or_404(Torcida, id=torcida_id)
    perfil = get_object_or_404(Perfil, user=request.user)
    perfil.torcida = torcida
    perfil.save()
    messages.success(request, f"Agora você faz parte da {torcida.nome}!")
    return redirect('dashboard')

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def mural_torcida(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    
    # Se ele não tiver torcida, volta para a seleção
    if not perfil.torcida:
        return redirect('torcida')
        
    context = {
        'torcida': perfil.torcida,
        'perfil': perfil
    }
    return render(request, 'mural.html', context)


def socio_view(request):
    # Explica os planos e benefícios de ser sócio
    return render(request, 'seja_socio.html')

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
        'cor_tema': cor_tema, # Agora garantimos que nunca será None
    }
    return render(request, 'detalhe_evento.html', context)

def bet_manutencao(request):
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

# Na sua views.py (App accounts)
@login_required
def perfil_view(request):
    perfil = request.user.perfil
    if request.method == 'POST':
        # Importante: request.FILES é necessário para fotos
        form = PerfilCompletoForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('perfil')
    else:
        form = PerfilCompletoForm(instance=perfil)
    
    return render(request, 'perfil.html', {'form': form, 'perfil': perfil})

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
def cartao_socio_view(request):
    # Esta view renderiza especificamente o cartão estilo banco
    return render(request, 'torcida/cartao_socio.html')

def area_torcida(request):
    """Abre o mural.html (Hub com ícones)"""
    return render(request, 'mural.html')

def galeria_fotos(request):
    return render(request, 'torcida/galeria.html')

def diretoria_view(request):
    return render(request, 'torcida/diretoria.html')

def mural_conquistas(request):
    return render(request, 'torcida/conquistas.html')

def cancoes_torcida(request):
    return render(request, 'torcida/cancoes.html')

def aliadas_view(request):
    return render(request, 'torcida/aliadas.html')

def viagens_view(request):
    return render(request, 'torcida/viagens.html')

def regras_view(request):
    return render(request, 'torcida/regras.html')

def lista_eventos(request):
    """Abre o eventos.html puxando do banco"""
    # Corrigido para 'data_evento' conforme seu modelo
    eventos = Evento.objects.all().order_by('data_evento')
    return render(request, 'eventos.html', {'eventos': eventos})

class MyCustomLoginView(LoginView):
    template_name = 'registration/login.html'