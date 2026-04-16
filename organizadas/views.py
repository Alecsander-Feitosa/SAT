from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Torcida, Evento, Caravana, Post, Curtida, Parceiro, Publicidade, FotoGaleria, ConquistaTorcida, MembroDiretoria, Regra
from django.utils import timezone
from .forms import TorcidaForm
from django.utils.text import slugify
from social.models import Post
from accounts.models import Perfil
from accounts.models import Cancao, Aliada

# --- FUNÇÕES AUXILIARES DE SEGURANÇA ---
def is_admin_geral(user):
    return user.is_authenticated and user.is_superuser

# --- VIEWS GERAIS ---
def lista_torcidas(request):
    torcidas = Torcida.objects.all()
    return render(request, 'organizadas/lista.html', {'torcidas': torcidas})

@login_required
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    curtida_existente = Curtida.objects.filter(post=post, usuario=request.user).first()
    
    if curtida_existente:
        curtida_existente.delete()
    else:
        Curtida.objects.create(post=post, usuario=request.user)
        
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)


def perfil_torcida(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    eventos = torcida.torcida_eventos.all()
    caravanas = torcida.caravanas.order_by('saida_horario')
    
    return render(request, 'organizadas/perfil.html', {
        'torcida': torcida,
        'eventos': eventos,
        'caravanas': caravanas
    })

# --- VIEWS DE PAINEL (ADMIN E HUB) ---
@user_passes_test(is_admin_geral, login_url='/login/')
def admin_dashboard(request):
    context = {
        'total_torcidas': Torcida.objects.count(),
    }
    return render(request, 'admin_master.html', context)

@login_required
def hub_view(request):
    perfil = getattr(request.user, 'perfil', None)
    
    if not perfil or not getattr(perfil, 'torcida', None) or not getattr(perfil, 'aprovado', False):
        messages.warning(request, "Acesso restrito. Escolha uma torcida ou aguarde a aprovação da diretoria.")
        return redirect('seja_socio') 
        
    torcida = perfil.torcida
    
    try:
        eventos = torcida.torcida_eventos.all()[:3]
        caravanas = torcida.caravanas.order_by('saida_horario')[:3]
    except AttributeError:
        eventos = []
        caravanas = []
    
    context = {
        'perfil': perfil,
        'torcida': torcida,
        'eventos': eventos,
        'caravanas': caravanas,
    }
    return render(request, 'hub.html', context)


# --- VIEWS DE AÇÕES (EVENTOS E CARAVANAS) ---
@login_required
def confirmar_presenca(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    messages.success(request, "Presença registada (funcionalidade em construção).")
    return redirect('perfil_torcida', slug=evento.torcida.slug)

@login_required
def reservar_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    
    if caravana.vagas_restantes() <= 0:
        messages.error(request, "Caravana lotada!")
    elif request.user in caravana.passageiros.all():
        messages.info(request, "Você já está nessa caravana.")
    else:
        caravana.passageiros.add(request.user)
        messages.success(request, "Lugar reservado na caravana!")
        
    return redirect('perfil_torcida', slug=caravana.torcida.slug)

def lista_eventos(request):
    eventos = Evento.objects.filter(data__gte=timezone.now()).order_by('data')
    return render(request, 'eventos.html', {'eventos': eventos})

@user_passes_test(is_admin_geral, login_url='/login/')
def nova_torcida(request):
    if request.method == 'POST':
        form = TorcidaForm(request.POST, request.FILES)
        if form.is_valid():
            torcida = form.save(commit=False)
            torcida.slug = slugify(torcida.nome) 
            torcida.save()
            messages.success(request, f'Torcida {torcida.nome} registada com sucesso!')
            return redirect('admin_dashboard')
    else:
        form = TorcidaForm()

    return render(request, 'admin_nova_torcida.html', {'form': form})

@user_passes_test(is_admin_geral, login_url='/login/')
def gerir_utilizadores(request):
    torcida_id = request.GET.get('torcida')
    perfis = Perfil.objects.select_related('user', 'torcida').all().order_by('-user__date_joined')
    
    if torcida_id:
        perfis = perfis.filter(torcida_id=torcida_id)
        
    return render(request, 'admin_utilizadores.html', {'perfis': perfis})

@user_passes_test(is_admin_geral, login_url='/login/')
def gerenciar_torcidas(request):
    torcidas = Torcida.objects.all().order_by('nome')
    return render(request, 'admin_torcidas.html', {'torcidas': torcidas})

@user_passes_test(is_admin_geral, login_url='/login/')
def editar_torcida(request, id):
    torcida = get_object_or_404(Torcida, id=id)
    
    if request.method == 'POST':
        form = TorcidaForm(request.POST, request.FILES, instance=torcida)
        if form.is_valid():
            form.save()
            messages.success(request, 'Torcida atualizada com sucesso!')
            return redirect('gerenciar_torcidas')
    else:
        form = TorcidaForm(instance=torcida)

    return render(request, 'admin_nova_torcida.html', {'form': form, 'edit_mode': True, 'torcida': torcida})

@user_passes_test(is_admin_geral, login_url='/login/')
def alternar_status_utilizador(request, perfil_id):
    perfil = get_object_or_404(Perfil, id=perfil_id)
    perfil.aprovado = not perfil.aprovado
    perfil.save()
    
    status = "aprovado" if perfil.aprovado else "suspenso"
    messages.success(request, f'O utilizador {perfil.user.username} foi {status} com sucesso!')
    
    return redirect('gerir_utilizadores')

@login_required
def painel_moderador(request):
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Acesso negado. Apenas moderadores podem aceder.")
        return redirect('dashboard')

    try:
        minha_torcida = request.user.perfil.torcida
    except AttributeError:
        minha_torcida = None

    if not minha_torcida:
        messages.error(request, "Não tem nenhuma torcida vinculada.")
        return redirect('dashboard')

    membros_ativos = Perfil.objects.filter(torcida=minha_torcida, aprovado=True).count()
    membros_pendentes = Perfil.objects.filter(torcida=minha_torcida, aprovado=False).count()

    context = {
        'torcida': minha_torcida,
        'parceiros': Parceiro.objects.filter(torcida=minha_torcida),
        'publicidades': Publicidade.objects.filter(torcida=minha_torcida),
        'eventos': Evento.objects.filter(torcida=minha_torcida).order_by('-data')[:5],
        'membros_ativos': membros_ativos,
        'membros_pendentes': membros_pendentes,
    }

    return render(request, 'moderacao.html', context)


# --- VIEWS DAS PÁGINAS DO HUB DA TORCIDA ---

@login_required
def galeria_fotos(request):
    torcida = request.user.perfil.torcida
    fotos = FotoGaleria.objects.filter(torcida=torcida).order_by('-data_publicacao')
    return render(request, 'torcida/galeria.html', {'fotos': fotos, 'torcida': torcida})

@login_required
def diretoria(request):
    torcida = request.user.perfil.torcida
    membros = MembroDiretoria.objects.filter(torcida=torcida) 
    return render(request, 'torcida/diretoria.html', {'membros': membros, 'torcida': torcida})

@login_required
def mural_conquistas(request):
    torcida = request.user.perfil.torcida
    conquistas = ConquistaTorcida.objects.filter(torcida=torcida).order_by('-ano')
    return render(request, 'torcida/mural_conquistas.html', {'conquistas': conquistas, 'torcida': torcida})

@login_required
def regras(request):
    torcida = request.user.perfil.torcida
    regras_lista = Regra.objects.filter(torcida=torcida) 
    return render(request, 'torcida/regras.html', {'regras': regras_lista, 'torcida': torcida})

@login_required
def viagens(request):
    torcida = request.user.perfil.torcida
    caravanas = Caravana.objects.filter(torcida=torcida).order_by('saida_horario')
    return render(request, 'torcida/viagens.html', {'caravanas': caravanas, 'torcida': torcida})

@login_required
def cancoes(request):
    torcida = request.user.perfil.torcida
    cancoes_lista = Cancao.objects.filter(torcida=torcida).order_by('-id')
    
    # Se o moderador enviar o formulário para adicionar uma música
    if request.method == 'POST':
        if not request.user.is_staff:
            messages.error(request, "Apenas moderadores podem adicionar canções.")
            return redirect('cancoes')

        nome = request.POST.get('nome')
        letra = request.POST.get('letra')
        link_yt = request.POST.get('link_youtube')
        video_file = request.FILES.get('arquivo_video')

        Cancao.objects.create(
            nome=nome,
            letra=letra,
            link_youtube=link_yt,
            arquivo_video=video_file,
            torcida=torcida
        )
        messages.success(request, 'Canção adicionada com sucesso!')
        return redirect('cancoes')

    context = {
        'cancoes': cancoes_lista,
        'torcida': torcida,
        'is_moderador': request.user.is_staff # Ajuda a mostrar botões no template
    }
    return render(request, 'torcida/cancoes.html', context)

# Adicione isso no final do seu accounts/views.py
@login_required
def excluir_cancao(request, cancao_id):
    # Verifica se o usuário é moderador
    if request.user.is_staff:
        from .models import Cancao # Importando direto aqui para evitar erro de importação circular
        # Pega a canção que pertence à torcida do moderador
        cancao = get_object_or_404(Cancao, id=cancao_id, torcida=request.user.perfil.torcida)
        cancao.delete()
        messages.success(request, 'Canção removida com sucesso.')
    else:
        messages.error(request, 'Você não tem permissão para apagar canções.')
        
    return redirect('cancoes')

@login_required
def aliadas(request):
    torcida = request.user.perfil.torcida
    aliadas_lista = Aliada.objects.filter(torcida=torcida)
    return render(request, 'torcida/aliadas.html', {'aliadas': aliadas_lista, 'torcida': torcida})