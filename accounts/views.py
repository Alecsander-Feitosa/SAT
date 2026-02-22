from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import qrcode
from io import BytesIO
import base64
import requests

# Importações de outros Apps (Cada uma no seu lugar correto)
from .models import Perfil, Presenca               # Modelos do App Accounts
from .forms import CadastroForm, PerfilCompletoForm 
from content.models import Post                    # Modelos do App Content
from content.api import api_noticias
from gamification.models import PerfilGamificacao, Nivel # Modelos do App Gamification
from organizadas.models import Torcida, Evento
from django.core.cache import cache




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
    
    # --- LÓGICA DE NOTÍCIAS COM ATUALIZAÇÃO AUTOMÁTICA ---
    # Tentamos buscar as notícias guardadas no cache primeiro
    noticias_reais = cache.get('noticias_futebol')

    if not noticias_reais:
        # Se não estiver no cache (ou o tempo expirou), busca na API
        api_key = api_noticias
        url = f"https://newsapi.org/v2/everything?q=futebol&language=pt&sortBy=publishedAt&pageSize=5&apiKey={api_key}"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                noticias_reais = response.json().get('articles', [])
                # Guarda no cache por 2 horas (7200 segundos)
                cache.set('noticias_futebol', noticias_reais, 7200)
        except Exception as e:
            print(f"Erro na API de notícias: {e}")
            noticias_reais = []

    # --- LÓGICA DE XP E CORES DINÂMICAS ---
    xp_atual = perfil_game.xp_total or 0
    
    # CORREÇÃO: Verificamos se o atributo 'nivel' existe e se não é nulo
    cor_tema = "#ff6b00" # Cor padrão (laranja)
    if hasattr(perfil_game, 'nivel') and perfil_game.nivel:
        cor_tema = perfil_game.nivel.cor_tema
    
    # Busca o PRÓXIMO nível para a barra
    proximo_nivel_obj = Nivel.objects.filter(xp_minimo__gt=xp_atual).order_by('xp_minimo').first()
    
    meta_xp = proximo_nivel_obj.xp_minimo if proximo_nivel_obj else (xp_atual if xp_atual > 0 else 1000)

    xp_progresso = min((xp_atual / meta_xp) * 100, 100)
    xp_faltante = max(meta_xp - xp_atual, 0)


    eventos_torcida = []
    if perfil.torcida:
        # Buscamos os eventos vinculados à torcida do perfil
        eventos_torcida = Evento.objects.filter(torcida=perfil.torcida).order_by('data_evento')[:3]

    # --- NOVA LÓGICA: Busca IDs dos eventos que o usuário já confirmou ---
    user_presencas = Presenca.objects.filter(user=request.user).values_list('evento_id', flat=True)

    context = {
        'perfil': perfil,
        'torcida': perfil.torcida,
        'perfil_game': perfil_game,
        'noticias': noticias_reais,
        'xp_progresso': xp_progresso,
        'xp_faltante': xp_faltante,
        'cor_tema': cor_tema,
        'eventos': eventos_torcida,
        'user_presencas': user_presencas,
    }
    return render(request, 'dashboard.html', context)

@login_required
def editar_perfil(request):
    perfil, _ = Perfil.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PerfilCompletoForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado!")
            return redirect('dashboard')
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

@login_required
def noticias(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    noticias = Post.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')
    return render(request, 'noticias.html', {'noticias': noticias, 'torcida': perfil.torcida})

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
        return render(request, 'mural_torcida.html', {'torcida': perfil.torcida})
    
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
    return render(request, 'mural_torcida.html', context)

def regras_view(request):
    # Renderiza o template com o regulamento da organizada
    return render(request, 'regras.html')

def socio_view(request):
    # Explica os planos e benefícios de ser sócio
    return render(request, 'seja_socio.html')

def carteirinha_view(request):

    perfil = request.user.perfil
    # Renderiza a carteirinha digital do torcedor
    return render(request, 'carteirinha.html', {'perfil': perfil})

@login_required
def confirmar_presenca(request, evento_id):
    if request.method == "POST":
        evento = get_object_or_404(Evento, id=evento_id)
        # Verifica se já confirmou para não duplicar
        presenca, created = Presenca.objects.get_or_create(user=request.user, evento=evento)
        
        if created:
            # Lógica opcional: dar XP por confirmar presença
            perfil_game = request.user.perfil_game
            perfil_game.xp_total += 50
            perfil_game.save()
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Presença confirmada! +50 XP'})
        
        return JsonResponse({'status': 'erro', 'mensagem': 'Você já confirmou presença.'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

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

@login_required
def bet_view(request):
    # Recupera a cor do tema para manter a identidade visual
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    cor_tema = perfil_game.nivel.cor_tema if perfil_game.nivel else "#ff6b00"
    
    return render(request, 'bet_manutencao.html', {'cor_tema': cor_tema})

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