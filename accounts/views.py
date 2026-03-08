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

@login_required
def mural_social(request):
    perfil = request.user.perfil
    
    # 1. Bloqueio de segurança: Se não tem torcida ou não tá aprovado, vaza!
    if not perfil.torcida or not perfil.aprovado:
        return redirect('dashboard')
        
    if request.method == "POST":
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        if texto or imagem:
            Post.objects.create(autor=request.user, torcida=perfil.torcida, texto=texto, imagem=imagem)
            return redirect('mural') 

    # 2. O FILTRO MÁGICO: Puxa SÓ os posts da torcida dele
    posts = Post.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')
    return render(request, 'mural.html', {'posts': posts})

@login_required
def viagens_view(request):
    perfil = request.user.perfil
    if not perfil.torcida or not perfil.aprovado:
        return redirect('dashboard')
        
    # FILTRO MÁGICO: Puxa SÓ as viagens da torcida dele
    caravanas = Caravana.objects.filter(torcida=perfil.torcida).order_by('saida_horario')
    return render(request, 'viagens.html', {'caravanas': caravanas})


def cadastro(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Loga automaticamente após cadastrar
            # MUDAMOS AQUI: Agora ele vai para a Etapa 2!
            return redirect('cadastro_etapa2') 
    else:
        form = CadastroForm()
    return render(request, 'cadastro.html', {'form': form})
# accounts/views.py

@login_required
def cadastro_etapa2(request):
    if request.method == 'POST':
        # Quando o utilizador clica em "Concluir", apanhamos as opções dele:
        time_escolhido = request.POST.get('time')
        torcida_id = request.POST.get('torcida')
        data_nasc = request.POST.get('data_nascimento')

        perfil = request.user.perfil
        
        # Se ele escolheu uma torcida, associamos ao perfil dele
        if torcida_id:
            from organizadas.models import Torcida
            torcida = Torcida.objects.filter(id=torcida_id).first()
            if torcida:
                perfil.torcida = torcida
                perfil.aprovado = False # Fica pendente da aprovação da diretoria
        
        # Aqui pode guardar o "time_escolhido" e a "data_nasc" se tiver esses campos no models.py depois
        perfil.save()
        
        # Depois de salvar a etapa 2, finalmente enviamos para o Dashboard!
        return redirect('dashboard')

    # Se ele apenas abriu a página, mostramos o HTML que criámos
    return render(request, 'cadastro_etapa2.html')



@login_required
def dashboard(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    # 1. Busca Notícias da API focadas em Futebol (Você já tinha isso!)
    noticias_api = cache.get('news_api_futebol')
    if not noticias_api:
        try:
            from content.api import api_noticias # Garante o import
            url = f'https://newsapi.org/v2/everything?q=futebol+brasileiro+brasileirao&language=pt&sortBy=publishedAt&pageSize=5&apiKey={api_noticias}'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                noticias_api = response.json().get('articles', [])
                cache.set('news_api_futebol', noticias_api, 900)
        except Exception:
            noticias_api = []

    # 2. Lógica de Eventos Dinâmica
    if perfil.torcida and perfil.aprovado:
        eventos = Evento.objects.filter(torcida=perfil.torcida, data__gte=timezone.now()).order_by('data')[:3]
        cor_tema = perfil.torcida.cor_primaria
        
        # BUSCA REAL NO BANCO: Posts da Torcida e Notícias do Time
        posts_sociais = PostTorcida.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')[:5]
        noticias_time = Noticia.objects.all().order_by('-data_publicacao')[:2] # Notícias internas
    else:
        eventos = Evento.objects.filter(data__gte=timezone.now()).order_by('data')[:3]
        cor_tema = "#CD7F32"
        posts_sociais = PostTorcida.objects.all().order_by('-data_criacao')[:5]
        noticias_time = Noticia.objects.all().order_by('-data_publicacao')[:2]

    context = {
        'proximos_eventos': eventos,
        'perfil': perfil,
        'perfil_game': perfil_game,
        'xp_atual': perfil_game.xp_total or 0,
        'torcida': perfil.torcida,
        'cor_tema': cor_tema,
        # AS VARIÁVEIS NOVAS QUE VÃO PARA O HTML REAL:
        'noticias_api': noticias_api,
        'posts_sociais': posts_sociais,
        'noticias_time': noticias_time,
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
    
    # Se ele já escolheu, mostramos o Mural da torcida dele
    if perfil.torcida:
        return render(request, 'mural.html', {'torcida': perfil.torcida})
    
    # Caso contrário, listamos as opções
    lista_de_torcidas = Torcida.objects.all()
    return render(request, 'torcidas.html', {
        'torcidas': lista_de_torcidas,
        'neutro': True # Flag para mostrar que ele pode continuar sem torcida
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
@torcida_required
def mural_social(request):
    perfil = request.user.perfil
    
    if request.method == "POST":
        texto = request.POST.get('texto')
        imagem = request.FILES.get('imagem')
        
        if texto or imagem:
            # USANDO O MODELO DA TORCIDA (PostTorcida)
            PostTorcida.objects.create(
                autor=request.user,
                torcida=perfil.torcida,
                texto=texto,
                imagem=imagem
            )
            return redirect('mural') 

    # Busca os posts usando o modelo correto
    posts = PostTorcida.objects.filter(torcida=perfil.torcida).order_by('-data_criacao')
    return render(request, 'mural.html', {'posts': posts})



@login_required
def area_hub(request):
    perfil = request.user.perfil
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
def moderacao_torcida(request):
    perfil_moderador = request.user.perfil
    
    # Segurança: Apenas quem tem torcida e é da equipe (is_staff) pode moderar
    if not request.user.is_staff or not perfil_moderador.torcida:
        messages.error(request, "Você não tem permissão para moderar.")
        return redirect('dashboard')
        
    # Filtra apenas pendentes que pertencem à MESMA torcida do moderador
    pendentes = Perfil.objects.filter(
        torcida=perfil_moderador.torcida, 
        aprovado=False
    ).exclude(user=request.user) # Não auto-aprovar
    
    return render(request, 'moderacao.html', {
        'pendentes': pendentes,
        'torcida': perfil_moderador.torcida
    })

@login_required
def aprovar_membro(request, perfil_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    perfil_moderador = request.user.perfil
    perfil_alvo = get_object_or_404(Perfil, id=perfil_id)
    
    # Validação de segurança em nível de banco de dados
    if request.user.is_staff and perfil_alvo.torcida == perfil_moderador.torcida:
        perfil_alvo.aprovado = True
        perfil_alvo.save()
        messages.success(request, f"O torcedor {perfil_alvo.user.username} foi aprovado!")
    else:
        messages.error(request, "Ação não permitida.")
        
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

class MyCustomLoginView(LoginView):
    template_name = 'registration/login.html'


@login_required
def curtir_post(request, post_id):
    post = get_object_or_404(PostTorcida, id=post_id)
    curtida, created = Curtida.objects.get_or_create(post=post, usuario=request.user)
    
    if created:
        # Lógica de XP: O autor do post ganha 1 XP
        perfil_autor, _ = PerfilGamificacao.objects.get_or_create(user=post.autor)
        perfil_autor.xp_total += 1
        perfil_autor.save()
    else:
        # Se clicar de novo, remove a curtida
        curtida.delete()
        # Opcional: remover o 1 XP se a curtida for desfeita
        perfil_autor = PerfilGamificacao.objects.get(user=post.autor)
        if perfil_autor.xp_total > 0:
            perfil_autor.xp_total -= 1
            perfil_autor.save()
            
    return redirect('mural') 

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
def noticias_view(request):
    return render(request, 'noticias.html')

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