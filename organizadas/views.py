from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Torcida, Evento, Caravana,Post, Curtida, Parceiro, Publicidade
from django.utils import timezone
from .forms import TorcidaForm
from django.utils.text import slugify
from social.models import Post
from accounts.models import Perfil

# --- FUNÇÕES AUXILIARES DE SEGURANÇA ---
def is_admin_geral(user):
    return user.is_authenticated and user.is_superuser

# --- VIEWS GERAIS ---
def lista_torcidas(request):
    torcidas = Torcida.objects.all()
    return render(request, 'organizadas/lista.html', {'torcidas': torcidas})

@login_required
def curtir_post(request, post_id):
    # Procura o post pelo ID
    post = get_object_or_404(Post, id=post_id)
    
    # Verifica se o utilizador já curtiu este post
    curtida_existente = Curtida.objects.filter(post=post, usuario=request.user).first()
    
    if curtida_existente:
        # Se já curtiu, remove a curtida (Deslike)
        curtida_existente.delete()
    else:
        # Se ainda não curtiu, cria a curtida (Like)
        Curtida.objects.create(post=post, usuario=request.user)
        
    # Redireciona o utilizador de volta para a exata página onde ele estava
    # (Seja no Dashboard ou no Mural Social)
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)


def perfil_torcida(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    # Ajustei para os nomes dos campos no modelo (pode precisar de revisão consoante o teu model Evento)
    eventos = torcida.torcida_eventos.all() # Usando o related_name do seu model Evento
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
    
    # BLOQUEIO ABSOLUTO
    if not perfil or not getattr(perfil, 'torcida', None) or not getattr(perfil, 'aprovado', False):
        messages.warning(request, "Acesso restrito. Escolha uma torcida ou aguarde a aprovação da diretoria.")
        return redirect('seja_socio') 
        
    torcida = perfil.torcida
    
    # Puxa os eventos e caravanas específicos desta torcida (usando os related_names do teu models)
    try:
        eventos = torcida.torcida_eventos.all()[:3] # Pega os 3 mais recentes
        caravanas = torcida.caravanas.order_by('saida_horario')[:3]
    except AttributeError:
        # Prevenção de erro caso os models Evento/Caravana ainda não estejam linkados perfeitamente
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
    # Nota: Precisaremos ajustar a lógica de presença consoante o teu model final
    evento = get_object_or_404(Evento, id=evento_id)
    # A lógica original foi comentada porque o campo 'confirmados' não estava no teu model Evento enviado.
    # Se precisarmos, criamos depois no model.
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
    # Ajustei o nome do campo para 'data' conforme está no teu models.py
    eventos = Evento.objects.filter(data__gte=timezone.now()).order_by('data')
    
    return render(request, 'eventos.html', {
        'eventos': eventos
    })

@user_passes_test(is_admin_geral, login_url='/login/')
def nova_torcida(request):
    if request.method == 'POST':
        # request.FILES é super importante aqui porque estamos a enviar imagens (logo e fundo)
        form = TorcidaForm(request.POST, request.FILES)
        if form.is_valid():
            torcida = form.save(commit=False)
            # Gera o link amigável automaticamente a partir do nome
            torcida.slug = slugify(torcida.nome) 
            torcida.save()
            messages.success(request, f'Torcida {torcida.nome} registada com sucesso!')
            return redirect('admin_dashboard')
    else:
        form = TorcidaForm()

    return render(request, 'admin_nova_torcida.html', {'form': form})

@user_passes_test(is_admin_geral, login_url='/login/')
def gerir_utilizadores(request):
    # Procura se existe algum filtro de torcida no link (ex: ?torcida=2)
    torcida_id = request.GET.get('torcida')
    
    # Traz todos os perfis por padrão
    perfis = Perfil.objects.select_related('user', 'torcida').all().order_by('-user__date_joined')
    
    # Se viemos do botão "Membros" de uma torcida, filtramos a lista!
    if torcida_id:
        perfis = perfis.filter(torcida_id=torcida_id)
        
    return render(request, 'admin_utilizadores.html', {
        'perfis': perfis
    })

@user_passes_test(is_admin_geral, login_url='/login/')
def gerenciar_torcidas(request):
    # Vai buscar todas as torcidas e ordena por nome
    torcidas = Torcida.objects.all().order_by('nome')
    
    return render(request, 'admin_torcidas.html', {
        'torcidas': torcidas
    })

@user_passes_test(is_admin_geral, login_url='/login/')
def editar_torcida(request, id):
    # Vai procurar a torcida pelo ID
    torcida = get_object_or_404(Torcida, id=id)
    
    if request.method == 'POST':
        # O 'instance=torcida' diz ao Django que estamos a atualizar algo que já existe
        form = TorcidaForm(request.POST, request.FILES, instance=torcida)
        if form.is_valid():
            form.save()
            messages.success(request, 'Torcida atualizada com sucesso!')
            return redirect('gerenciar_torcidas')
    else:
        # Preenche o formulário com os dados atuais
        form = TorcidaForm(instance=torcida)

    # Reutilizamos o mesmo HTML, passando uma variável extra 'edit_mode'
    return render(request, 'admin_nova_torcida.html', {'form': form, 'edit_mode': True, 'torcida': torcida})

@user_passes_test(is_admin_geral, login_url='/login/')
def alternar_status_utilizador(request, perfil_id):
    # Vai buscar o perfil
    perfil = get_object_or_404(Perfil, id=perfil_id)
    
    # Inverte o status: se estava aprovado fica falso, se estava falso fica aprovado
    perfil.aprovado = not perfil.aprovado
    perfil.save()
    
    # Mensagem de feedback
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

    # PESQUISA DIRETA NO BANCO DE DADOS (Mais robusta e à prova de falhas)
    membros_ativos = Perfil.objects.filter(torcida=minha_torcida, aprovado=True).count()
    membros_pendentes = Perfil.objects.filter(torcida=minha_torcida, aprovado=False).count()

    # ISTO VAI APARECER NO SEU TERMINAL PARA DESCOBRIRMOS O MISTÉRIO
    print("\n" + "="*40)
    print(f"🔎 DEBUG DO MODERADOR")
    print(f"Líder: {request.user.username}")
    print(f"Torcida que ele lidera: {minha_torcida.nome} (ID da Torcida no Banco: {minha_torcida.id})")
    print(f"Membros encontrados: {membros_ativos} ativos, {membros_pendentes} pendentes")
    print("="*40 + "\n")

    context = {
        'torcida': minha_torcida,
        'parceiros': Parceiro.objects.filter(torcida=minha_torcida),
        'publicidades': Publicidade.objects.filter(torcida=minha_torcida),
        'eventos': Evento.objects.filter(torcida=minha_torcida).order_by('-data')[:5],
        'membros_ativos': membros_ativos,
        'membros_pendentes': membros_pendentes,
    }

    return render(request, 'moderacao.html', context)