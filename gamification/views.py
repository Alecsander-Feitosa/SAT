import math
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
# Importações de outros apps
from accounts.models import Perfil 
from organizadas.models import Evento
from django.contrib import messages
# Importações deste app (gamification)
from .models import PerfilGamificacao, CheckIn, BadgeUsuario, Nivel, Partida
from django.shortcuts import render, redirect, get_object_or_404



@login_required
def dashboard(request):
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # Se você usa o app 'content' para notícias:
    from content.models import Noticia # Verifique se este é o nome do seu model
    noticias_lista = Noticia.objects.all().order_by('-data_publicacao')[:5]
    
    proximos_eventos = Evento.objects.filter(
        data_evento__gte=timezone.now()
    ).order_by('data_evento')[:3]


    context = {
        'perfil_game': perfil_game,
        'noticias': noticias_lista,
        'eventos': proximos_eventos,
        'xp_faltante': 100, 
        'xp_progresso': perfil_game.progresso_nivel(),
    }
    return render(request, 'dashboard.html', context)

@login_required
def confirmar_presenca(request, evento_id):
    from organizadas.models import Evento
    from gamification.models import CheckIn
    from django.contrib import messages
    
    evento = get_object_or_404(Evento, id=evento_id)
    
    if request.method == "POST":
        foto_enviada = request.FILES.get('foto')
        
        # Verifica se já não tem checkin para evitar que ganhem XP duplicado
        if CheckIn.objects.filter(user=request.user, evento=evento).exists():
            messages.info(request, "Você já confirmou presença neste evento!")
        else:
            if foto_enviada:
                # MÁGICA 2: Salva a foto e dá como validado!
                CheckIn.objects.create(
                    user=request.user, 
                    evento=evento, 
                    foto=foto_enviada,
                    validado=True 
                )
                messages.success(request, "Presença confirmada! +50 XP conquistados!")
            else:
                messages.error(request, "Você precisa enviar uma foto para confirmar presença.")
                
    # MÁGICA 3: Em vez de mostrar código na tela, redireciona de volta para o evento
    return redirect('detalhe_evento', evento_id=evento.id)

@login_required
def noticias(request):
    # Aqui você listará as notícias da SAT
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

    


@login_required
def ranking_torcida(request):
    from gamification.models import PerfilGamificacao
    # Busca os top 10 torcedores ordenados pelo XP total
    lideres = PerfilGamificacao.objects.select_related('user', 'nivel').order_by('-xp_total')[:10]
    
    context = {
        'lideres': lideres,
        'cor_tema': "#D37129" # Laranja oficial SAT
    }
    return render(request, 'ranking.html', context)

@login_required
def mural_presenca(request):
    # Mudamos 'data_checkin' para 'data' conforme a mensagem de erro sugeriu
    postagens = CheckIn.objects.exclude(foto='').order_by('-data')[:20]
    return render(request, 'mural.html', {'postagens': postagens})


@login_required
def mural_torcida(request):
    from gamification.models import CheckIn
    # Busca os check-ins que têm foto, do mais novo para o mais antigo
    postagens = CheckIn.objects.filter(foto__isnull=False).exclude(foto='').select_related('user', 'evento').order_by('-data_checkin')[:20]
    
    context = {
        'postagens': postagens,
        'cor_tema': "#D37129"
    }
    return render(request, 'mural.html', context)

@login_required
def games_hub(request):
    from django.utils import timezone
    from organizadas.models import Evento
    from .models import PerfilGamificacao, Nivel

    # 1. Busca o perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)

    # 2. BUSCA MANUAL DO NÍVEL (Ignora o que está salvo e calcula pelo XP atual)
    # Pega o nível que o usuário REALMENTE pertence agora (700 XP = Bronze 500)
    nivel_real = Nivel.objects.filter(xp_minimo__lte=perfil_game.xp_total).order_by('-xp_minimo').first()
    
    # 3. BUSCA DO PRÓXIMO NÍVEL
    proximo = Nivel.objects.filter(xp_minimo__gt=perfil_game.xp_total).order_by('xp_minimo').first()

    # 4. CÁLCULO DA BARRA NA VIEW (Garante que o HTML receba o valor certo)
    progresso = 0
    if proximo:
        inicio_xp = nivel_real.xp_minimo if nivel_real else 0
        total_necessario = proximo.xp_minimo - inicio_xp
        atual_no_nivel = perfil_game.xp_total - inicio_xp
        progresso = (atual_no_nivel / total_necessario) * 100
    else:
        progresso = 100

    context = {
        'perfil_game': perfil_game,
        'nivel_nome': nivel_real.nome if nivel_real else "Recruta",
        'progresso_barra': min(max(progresso, 5), 100),
        'evento': Evento.objects.filter(data_evento__gte=timezone.now()).first()
    }
    return render(request, 'games_menu.html', context)

def lista_eventos(request):
    from organizadas.models import Evento
    from django.utils import timezone
    eventos = Evento.objects.filter(data_evento__gte=timezone.now()).order_by('data_evento')
    eventos_encontrados = Evento.objects.filter(data_evento__gte=timezone.now()).order_by('data_evento')
    return render(request, 'eventos.html', {'eventos': eventos_encontrados})

@login_required
def detalhe_evento(request, evento_id):
    from organizadas.models import Evento
    from gamification.models import CheckIn
    
    # Busca o evento pelo ID ou retorna erro 404 se não existir
    evento = get_object_or_404(Evento, id=evento_id)
    
    # MÁGICA 1: Verifica se este usuário já fez check-in / mandou a foto
    confirmado = False
    if request.user.is_authenticated:
        confirmado = CheckIn.objects.filter(user=request.user, evento=evento).exists()
    
    context = {
        'evento': evento,
        'confirmado': confirmado, # Agora o HTML sabe se deve esconder o botão!
    }
    return render(request, 'detalhe_evento.html', context)

# Em accounts/views.py ou no app correspondente
def bet_view(request):
    context = {
        'cor_tema': '#D37129', # Laranja padrão do SAT
    }
    return render(request, 'bet_manutencao.html', context)