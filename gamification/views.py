import math
from django.http import JsonResponse
from .models import CheckIn, PerfilGamificacao
from organizadas.models import Evento
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Perfil
from gamification.models import PerfilGamificacao, CheckIn, BadgeUsuario
from store.models import Produto

@login_required
def dashboard(request):
    """
    Página principal que exibe os pontos, nível e o resumo do torcedor.
    """
    # Garante que o perfil de gamificação existe para evitar erro 500 no dashboard
    perfil_game, created = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # Busca os últimos 5 check-ins e conquistas do usuário
    ultimos_checkins = CheckIn.objects.filter(user=request.user).order_by('-data')
    conquistas = BadgeUsuario.objects.filter(user=request.user).select_related('badge')
    
    context = {
        'perfil': perfil_game,
        'checkins': ultimos_checkins,
        'conquistas': conquistas,
    }
    return render(request, 'dashboard.html', context)

@login_required
def noticias(request):
    """Exibe as novidades da torcida e do clube."""
    return render(request, 'noticias.html')

@login_required
def loja(request):
    """Exibe os produtos (bonés e buckets) da fábrica."""
    produtos = Produto.objects.all()
    return render(request, 'loja.html', {'produtos': produtos})

@login_required
def perfil(request):
    """Permite ao usuário editar seus dados (CPF, WhatsApp, etc)."""
    # Busca o perfil de dados pessoais (Módulo 7)
    perfil_usuario, created = Perfil.objects.get_or_create(user=request.user)
    return render(request, 'perfil.html', {'perfil': perfil_usuario})

@login_required
def socio(request):
    """Área do sócio-torcedor."""
    return render(request, 'socio.html')

@login_required
def torcida_detalhes(request):
    """Informações sobre as organizadas."""
    return render(request, 'torcida.html')

def calcular_distancia(lat1, lon1, lat2, lon2):
    # Fórmula de Haversine para calcular distância entre dois pontos no globo
    raio_terra = 6371  # Raio em quilômetros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return raio_terra * c * 1000  # Retorna em metros

@login_required
def validar_checkin_estadio(request):
    if request.method == 'POST':
        lat_user = float(request.POST.get('latitude'))
        lon_user = float(request.POST.get('longitude'))
        evento_id = request.POST.get('evento_id')
        
        evento = Evento.objects.get(id=evento_id)
        
        # Distância máxima permitida: 500 metros do centro do estádio 
        distancia = calcular_distancia(lat_user, lon_user, evento.latitude, evento.longitude)
        
        if distancia <= 500:
            # Cria o registro de presença e dispara o ganho de XP 
            CheckIn.objects.create(
                user=request.user,
                evento=evento,
                latitude=lat_user,
                longitude=lon_user,
                validado=True
            )
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Check-in realizado! +50 XP'})
        else:
            return JsonResponse({'status': 'erro', 'mensagem': 'Você não está no estádio!'}, status=400)