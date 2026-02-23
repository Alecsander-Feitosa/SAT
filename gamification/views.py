import math
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
# Importações de outros apps
from accounts.models import Perfil 
from organizadas.models import Evento

# Importações deste app (gamification)
from .models import PerfilGamificacao, CheckIn, BadgeUsuario, Nivel, Partida

@login_required
def dashboard(request):
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # Se você usa o app 'content' para notícias:
    from content.models import Noticia # Verifique se este é o nome do seu model
    noticias_lista = Noticia.objects.all().order_by('-data_publicacao')[:5]
    
    context = {
        'perfil_game': perfil_game,
        'noticias': noticias_lista,
        'xp_faltante': 100, # Adicione sua lógica de cálculo aqui
        'xp_progresso': perfil_game.progresso_nivel(),
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
    """
    View atualizada com os campos corretos do modelo Evento.
    """
    if request.method == 'POST':
        try:
            lat_user = float(request.POST.get('latitude'))
            lon_user = float(request.POST.get('longitude'))
            evento_id = request.POST.get('evento_id')
            foto_arquivo = request.FILES.get('foto')

            from organizadas.models import Evento 
            evento = Evento.objects.get(id=evento_id)
            
            # Nota: Certifique-se que o modelo Evento tenha campos 'latitude' e 'longitude'
            # Caso contrário, precisaremos ajustar a função calcular_distancia
            distancia = calcular_distancia(lat_user, lon_user, evento.latitude, evento.longitude)
            
            if distancia <= 500:
                CheckIn.objects.create(
                    user=request.user,
                    evento=evento,
                    latitude=lat_user,
                    longitude=lon_user,
                    foto=foto_arquivo,
                    validado=True
                )
                return JsonResponse({'status': 'sucesso', 'mensagem': 'Check-in realizado! +50 XP'})
            else:
                return JsonResponse({'status': 'erro', 'mensagem': 'Você está longe demais do local.'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    # --- CORREÇÃO DO MÉTODO GET ---
    from organizadas.models import Evento
    from django.utils import timezone

    # Ajustado de 'data_hora' para 'data_evento' conforme o erro reportado
    proximo_evento = Evento.objects.filter(
        data_evento__gte=timezone.now()
    ).order_by('data_evento').first()
    
    return render(request, 'checkin.html', {'evento': proximo_evento})
    # --- LÓGICA PARA O MÉTODO GET (Evita o erro anterior) ---
    from organizadas.models import Evento
    
    # Busca o evento mais próximo que ainda não aconteceu
    proximo_evento = Evento.objects.filter(
        data_hora__gte=timezone.now()
    ).order_by('data_hora').first()
    
    context = {
        'evento': proximo_evento,
    }
    
    return render(request, 'checkin.html', context)


@login_required
def ranking_torcida(request):
    # Top 10 geral
    top_torcedores = PerfilGamificacao.objects.select_related('user', 'nivel').order_by('-xp_total')[:10]
    
    # Posição do usuário logado
    todos = PerfilGamificacao.objects.order_by('-xp_total')
    posicao_usuario = None
    count = 1
    for p in todos:
        if p.user == request.user:
            posicao_usuario = {'perfil': p, 'rank': count}
            break
        count += 1

    return render(request, 'ranking.html', {
        'ranking': top_torcedores,
        'meu_rank': posicao_usuario
    })

@login_required
def mural_presenca(request):
    # Pegamos os últimos 20 check-ins validados
    checkins = CheckIn.objects.filter(validado=True).select_related('user', 'user__perfil_game', 'evento').order_by('-data')[:20]
    
    return render(request, 'mural_presenca.html', {'checkins': checkins})
