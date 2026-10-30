import json
from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Perfil, CheckIn as CheckInAccounts
from gamification.models import CheckIn as CheckInGame
from organizadas.models import Torcida, Evento
from .forms import RegistroProntuarioForm, NovaConversaForm, MensagemForm, DenunciaForm, DenunciaGestaoForm, ReuniaoForm
from .models import RegistroProntuario, Conversa, Mensagem, Denuncia, LocalizacaoTorcedor, PlanoRota, Reuniao
from .permissions import bepe_required, diretoria_required


# ==========================================
# PAINEL PRINCIPAL
# ==========================================
@bepe_required
def painel(request):
    contexto = {
        'aba': 'painel',
        'total_cadastrados': Perfil.objects.count(),
        'total_registros': RegistroProntuario.objects.count(),
        'denuncias_novas': Denuncia.objects.filter(status='nova').count(),
        'mensagens_nao_lidas': Mensagem.objects.filter(do_bepe=False, lida=False).count(),
        'ultimas_denuncias': Denuncia.objects.select_related('torcida')[:5],
        'ultimos_registros': RegistroProntuario.objects.select_related('perfil__user', 'autor')[:5],
    }
    return render(request, 'bepe/painel.html', contexto)


# ==========================================
# CADASTRADOS + PRONTUÁRIOS
# ==========================================
@bepe_required
def cadastrados(request):
    q = request.GET.get('q', '').strip()
    cpf = ''.join(c for c in request.GET.get('cpf', '') if c.isdigit())
    time = request.GET.get('time', '').strip()
    torcida_id = request.GET.get('torcida', '')

    perfis = Perfil.objects.select_related('user', 'torcida').annotate(
        num_registros=Count('prontuario_bepe')
    ).order_by('user__first_name', 'user__username')

    socio_matricula = Perfil.por_matricula(q) if q else None
    if socio_matricula:
        perfis = perfis.filter(id=socio_matricula.id)
    elif q:
        perfis = perfis.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) | Q(user__email__icontains=q) |
            Q(rg_cnh__icontains=q) | Q(vulgo__icontains=q) |
            Q(nome_mae__icontains=q) | Q(whatsapp__icontains=q)
        )
    if cpf:
        # Aceita com ou sem pontuação ("123.456.789-00" ou "12345678900")
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        perfis = perfis.filter(Q(cpf__icontains=cpf) | Q(cpf__icontains=cpf_formatado))
    if time:
        perfis = perfis.filter(time_coracao__iexact=time)
    if torcida_id:
        perfis = perfis.filter(torcida_id=torcida_id)
    if request.GET.get('com_registro'):
        perfis = perfis.filter(num_registros__gt=0)

    pagina = Paginator(perfis, 30).get_page(request.GET.get('page'))
    filtros = request.GET.copy()
    filtros.pop('page', None)
    return render(request, 'bepe/cadastrados.html', {
        'aba': 'cadastrados',
        'pagina': pagina,
        'q': q,
        'cpf': request.GET.get('cpf', ''),
        'time': time,
        'torcida_id': torcida_id,
        'filtros_url': filtros.urlencode(),
        'torcidas': Torcida.objects.order_by('nome'),
        'times': Perfil.objects.exclude(time_coracao__isnull=True).exclude(time_coracao='')
                   .values_list('time_coracao', flat=True).distinct().order_by('time_coracao'),
    })


@bepe_required
def cadastrado_detalhe(request, perfil_id):
    perfil = get_object_or_404(Perfil.objects.select_related('user', 'torcida'), id=perfil_id)

    if request.method == 'POST':
        form = RegistroProntuarioForm(request.POST, request.FILES)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.perfil = perfil
            registro.autor = request.user
            registro.save()
            messages.success(request, "Registro adicionado ao prontuário.")
            return redirect('bepe:cadastrado_detalhe', perfil_id=perfil.id)
    else:
        form = RegistroProntuarioForm(initial={'data_fato': timezone.localtime().strftime('%Y-%m-%dT%H:%M')})

    checkins = sorted(
        list(CheckInAccounts.objects.filter(user=perfil.user).select_related('evento')) +
        list(CheckInGame.objects.filter(user=perfil.user).select_related('evento')),
        key=lambda c: getattr(c, 'data_criacao', None) or getattr(c, 'data'),
        reverse=True,
    )[:20]

    return render(request, 'bepe/cadastrado_detalhe.html', {
        'aba': 'cadastrados',
        'perfil': perfil,
        'registros': perfil.prontuario_bepe.select_related('autor'),
        'checkins': checkins,
        'form': form,
    })


# ==========================================
# GEOLOCALIZAÇÃO (a partir dos check-ins)
# ==========================================
# Janelas de tempo do mapa (em minutos)
PERIODOS_MAPA = [
    (15, 'Últimos 15 min'),
    (60, 'Última hora'),
    (60 * 24, 'Últimas 24h'),
    (60 * 24 * 7, 'Últimos 7 dias'),
    (60 * 24 * 30, 'Últimos 30 dias'),
]


def _ponto(user, lat, lng, data, origem, detalhe):
    perfil = getattr(user, 'perfil', None)
    torcida = perfil.torcida if perfil else None
    return {
        'id': f"{origem}-{user.id}",
        'lat': lat,
        'lng': lng,
        'nome': user.get_full_name() or user.username,
        'vulgo': perfil.vulgo if perfil else '',
        'torcida': torcida.nome if torcida else '—',
        'torcida_id': torcida.id if torcida else None,
        'cor': torcida.cor_primaria if torcida else '#D37129',
        'origem': origem,
        'detalhe': detalhe,
        'data': timezone.localtime(data).strftime('%d/%m/%Y %H:%M:%S'),
        'ts': data.timestamp(),
        'perfil_id': perfil.id if perfil else None,
    }


def pontos_ao_vivo(desde, torcida_ids=None):
    qs = LocalizacaoTorcedor.objects.filter(
        status='ativo', latitude__isnull=False, atualizada_em__gte=desde
    ).select_related('user__perfil__torcida')
    if torcida_ids:
        qs = qs.filter(user__perfil__torcida_id__in=torcida_ids)
    pontos = []
    for loc in qs[:3000]:
        precisao = f"precisão ~{loc.precisao:.0f} m" if loc.precisao else "localização compartilhada"
        pontos.append(_ponto(loc.user, loc.latitude, loc.longitude, loc.atualizada_em, 'ao_vivo', precisao))
    return pontos


def _dados_mapa(request):
    torcida_id = request.GET.get('torcida', '')
    evento_id = request.GET.get('evento', '')
    try:
        periodo = int(request.GET.get('periodo', 60 * 24))
    except ValueError:
        periodo = 60 * 24
    desde = timezone.now() - timedelta(minutes=periodo)

    # 1) Localização ao vivo (torcedores que ativaram o compartilhamento)
    ao_vivo = [] if evento_id else pontos_ao_vivo(desde, [torcida_id] if torcida_id else None)

    # 2) Check-ins em eventos
    filtros = Q(latitude__isnull=False) & ~Q(latitude=0, longitude=0) & Q(user__isnull=False)
    if torcida_id:
        filtros &= Q(user__perfil__torcida_id=torcida_id)
    if evento_id:
        filtros &= Q(evento_id=evento_id)
    checkins = []
    consultas = [
        (CheckInAccounts.objects.filter(filtros, data_criacao__gte=desde), 'data_criacao'),
        (CheckInGame.objects.filter(filtros, data__gte=desde), 'data'),
    ]
    for qs, campo_data in consultas:
        for c in qs.select_related('user__perfil__torcida', 'evento')[:2000]:
            checkins.append(_ponto(c.user, c.latitude, c.longitude, getattr(c, campo_data), 'checkin', f"Check-in: {c.evento}"))
    for i, c in enumerate(checkins):
        c['id'] = f"checkin-{i}"

    return {
        'pontos': ao_vivo + checkins,
        'total_ao_vivo': len(ao_vivo),
        'total_checkins': len(checkins),
        'total_compartilhando': LocalizacaoTorcedor.objects.filter(status='ativo').count(),
        'torcida_id': torcida_id,
        'evento_id': evento_id,
        'periodo': periodo,
        'gerado_em': timezone.localtime().strftime('%H:%M:%S'),
    }


@bepe_required
def mapa(request):
    contexto = _dados_mapa(request)
    contexto.update({
        'aba': 'mapa',
        'torcidas': Torcida.objects.order_by('nome'),
        'eventos': Evento.objects.order_by('-data')[:100],
        'periodos': PERIODOS_MAPA,
    })
    return render(request, 'bepe/mapa.html', contexto)


@bepe_required
def mapa_dados(request):
    """Mesmos dados do mapa em JSON, para a atualização ao vivo sem recarregar a página."""
    dados = _dados_mapa(request)
    return JsonResponse({k: dados[k] for k in ('pontos', 'total_ao_vivo', 'total_checkins', 'total_compartilhando', 'gerado_em')})


# --- Lado do torcedor: ativar/desativar e enviar a própria localização ---
@login_required
@require_POST
def localizacao(request):
    loc, _ = LocalizacaoTorcedor.objects.get_or_create(user=request.user)
    acao = request.POST.get('acao', 'enviar')

    if acao == 'ativar':
        loc.status = 'ativo'
        loc.consentido_em = timezone.now()
        loc.save()
    elif acao in ('desativar', 'recusar'):
        # Ao desativar, a última posição é apagada: o BEPE deixa de vê-la imediatamente
        loc.status = 'recusado'
        loc.latitude = loc.longitude = loc.precisao = loc.atualizada_em = None
        loc.save()
    elif acao == 'enviar' and loc.ativo:
        try:
            lat = float(request.POST['latitude'])
            lng = float(request.POST['longitude'])
        except (KeyError, ValueError):
            return JsonResponse({'ok': False}, status=400)
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return JsonResponse({'ok': False}, status=400)
        precisao = request.POST.get('precisao')
        loc.latitude, loc.longitude = lat, lng
        loc.precisao = float(precisao) if precisao else None
        loc.atualizada_em = timezone.now()
        loc.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'status': loc.status})
    proximo = request.POST.get('next', '')
    return redirect(proximo if url_has_allowed_host_and_scheme(proximo, {request.get_host()}) else 'dashboard')


# ==========================================
# CANAL DIRETO COM AS DIRETORIAS
# ==========================================
def _render_conversa(request, conversa, lado_bepe, template_base):
    """Lógica compartilhada pelo lado BEPE e pelo lado da diretoria."""
    if request.method == 'POST':
        if request.POST.get('acao') == 'encerrar' and lado_bepe:
            conversa.encerrada = not conversa.encerrada
            conversa.save()
            return redirect(request.path)

        form = MensagemForm(request.POST, request.FILES)
        if form.is_valid() and not conversa.encerrada:
            msg = form.save(commit=False)
            msg.conversa = conversa
            msg.autor = request.user
            msg.do_bepe = lado_bepe
            msg.save()
            conversa.save()  # atualiza "atualizada_em" para subir na lista
            return redirect(request.path)
    else:
        form = MensagemForm()

    # Marca como lidas as mensagens que vieram do outro lado
    conversa.mensagens.filter(do_bepe=not lado_bepe, lida=False).update(lida=True)

    return render(request, 'bepe/conversa.html', {
        'aba': 'canal',
        'conversa': conversa,
        'mensagens': conversa.mensagens.select_related('autor'),
        'form': form,
        'lado_bepe': lado_bepe,
        'template_base': template_base,
    })


def _criar_conversa(request, form, torcida, lado_bepe):
    conversa = form.save(commit=False)
    conversa.torcida = torcida
    conversa.criada_por = request.user
    conversa.save()
    Mensagem.objects.create(
        conversa=conversa, autor=request.user,
        do_bepe=lado_bepe,
        texto=form.cleaned_data['texto'],
    )
    return conversa


@bepe_required
def conversas(request):
    lista = Conversa.objects.select_related('torcida').annotate(
        nao_lidas=Count('mensagens', filter=Q(mensagens__do_bepe=False, mensagens__lida=False))
    )
    torcida_id = request.GET.get('torcida', '')
    if torcida_id:
        lista = lista.filter(torcida_id=torcida_id)
    return render(request, 'bepe/conversas.html', {
        'aba': 'canal',
        'conversas': lista,
        'lado_bepe': True,
        'template_base': 'bepe/base_bepe.html',
        'torcidas': Torcida.objects.order_by('nome'),
        'torcida_id': torcida_id,
    })


@bepe_required
def nova_conversa(request):
    form = NovaConversaForm(request.POST or None, initial={'torcida': request.GET.get('torcida')})
    if request.method == 'POST' and form.is_valid():
        conversa = _criar_conversa(request, form, form.cleaned_data['torcida'], lado_bepe=True)
        messages.success(request, f"Conversa aberta com a diretoria da {conversa.torcida.nome}.")
        return redirect('bepe:conversa', conversa_id=conversa.id)
    return render(request, 'bepe/nova_conversa.html', {
        'aba': 'canal', 'form': form, 'lado_bepe': True, 'template_base': 'bepe/base_bepe.html',
    })


@bepe_required
def conversa(request, conversa_id):
    c = get_object_or_404(Conversa.objects.select_related('torcida'), id=conversa_id)
    return _render_conversa(request, c, lado_bepe=True, template_base='bepe/base_bepe.html')


# --- Lado da diretoria (staff vinculado a uma torcida) ---
@diretoria_required
def diretoria_conversas(request):
    lista = Conversa.objects.filter(torcida=request.torcida_diretoria).annotate(
        nao_lidas=Count('mensagens', filter=Q(mensagens__do_bepe=True, mensagens__lida=False))
    )
    return render(request, 'bepe/conversas.html', {
        'conversas': lista, 'lado_bepe': False, 'template_base': 'bepe/base_diretoria.html',
    })


@diretoria_required
def diretoria_nova_conversa(request):
    form = NovaConversaForm(request.POST or None, torcida_fixa=request.torcida_diretoria)
    if request.method == 'POST' and form.is_valid():
        conversa = _criar_conversa(request, form, request.torcida_diretoria, lado_bepe=False)
        messages.success(request, "Mensagem enviada ao BEPE.")
        return redirect('bepe:diretoria_conversa', conversa_id=conversa.id)
    return render(request, 'bepe/nova_conversa.html', {
        'form': form, 'lado_bepe': False, 'template_base': 'bepe/base_diretoria.html',
    })


@diretoria_required
def diretoria_conversa(request, conversa_id):
    c = get_object_or_404(Conversa, id=conversa_id, torcida=request.torcida_diretoria)
    return _render_conversa(request, c, lado_bepe=False, template_base='bepe/base_diretoria.html')


# ==========================================
# DENÚNCIAS (gestão pelo BEPE)
# ==========================================
@bepe_required
def denuncias(request):
    status = request.GET.get('status', '')
    lista = Denuncia.objects.select_related('torcida')
    if status:
        lista = lista.filter(status=status)
    pagina = Paginator(lista, 30).get_page(request.GET.get('page'))
    return render(request, 'bepe/denuncias.html', {
        'aba': 'denuncias',
        'pagina': pagina,
        'status': status,
        'status_choices': Denuncia.STATUS_CHOICES,
    })


@bepe_required
def denuncia_detalhe(request, denuncia_id):
    denuncia = get_object_or_404(Denuncia, id=denuncia_id)
    if denuncia.status == 'nova' and request.method == 'GET':
        denuncia.status = 'em_analise'
        denuncia.responsavel = request.user
        denuncia.save()

    form = DenunciaGestaoForm(request.POST or None, instance=denuncia)
    if request.method == 'POST' and form.is_valid():
        d = form.save(commit=False)
        d.responsavel = request.user
        d.save()
        messages.success(request, "Denúncia atualizada.")
        return redirect('bepe:denuncia_detalhe', denuncia_id=denuncia.id)

    return render(request, 'bepe/denuncia_detalhe.html', {
        'aba': 'denuncias', 'denuncia': denuncia, 'form': form,
    })


# ==========================================
# FALE COM O BEPE (público e anônimo)
# ==========================================
def _remover_metadados(arquivo):
    """Remove EXIF (GPS, modelo do celular, etc.) de fotos para não identificar o denunciante."""
    if not arquivo or not (arquivo.content_type or '').startswith('image/'):
        return arquivo
    try:
        from PIL import Image
        img = Image.open(arquivo)
        formato = img.format or 'JPEG'
        limpa = Image.new(img.mode, img.size)
        limpa.putdata(list(img.getdata()))
        buffer = BytesIO()
        limpa.save(buffer, format=formato)
        buffer.seek(0)
        return InMemoryUploadedFile(
            buffer, 'anexo', f"anexo.{formato.lower()}", arquivo.content_type, buffer.getbuffer().nbytes, None
        )
    except Exception:
        # Se não conseguir limpar, descarta o anexo em vez de arriscar expor o denunciante
        return None


def fale_com_bepe(request):
    # Sem @login_required de propósito: qualquer pessoa pode denunciar, logada ou não.
    form = DenunciaForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        denuncia = form.save(commit=False)
        denuncia.anexo = _remover_metadados(request.FILES.get('anexo'))
        denuncia.save()  # Nenhum dado do usuário/IP é salvo
        return render(request, 'bepe/fale_protocolo.html', {'denuncia': denuncia})
    return render(request, 'bepe/fale_com_bepe.html', {'form': form})


def acompanhar_denuncia(request):
    protocolo = request.GET.get('protocolo', '').strip().upper()
    denuncia = None
    if protocolo:
        denuncia = Denuncia.objects.filter(protocolo=protocolo).first()
        if not denuncia:
            messages.error(request, "Protocolo não encontrado.")
    return render(request, 'bepe/fale_acompanhar.html', {'denuncia': denuncia, 'protocolo': protocolo})


# ==========================================
# JOGOS NO RJ (API pública da ESPN)
# ==========================================
def torcidas_do_time(nome_time, torcidas):
    """Torcidas cujo 'time relacionado' bate com o nome do time da ESPN (ex: Vasco x Vasco da Gama)."""
    nome = (nome_time or '').lower()
    return [t for t in torcidas if t.time_relacionado and
            (t.time_relacionado.lower() in nome or nome in t.time_relacionado.lower())]


@bepe_required
def jogos(request):
    from .jogos import jogos_no_rj
    lista = jogos_no_rj(meses=2)
    torcidas = list(Torcida.objects.exclude(time_relacionado__isnull=True).exclude(time_relacionado=''))
    for j in lista:
        j['torcidas_mandante'] = torcidas_do_time(j['mandante']['nome'], torcidas)
        j['torcidas_visitante'] = torcidas_do_time(j['visitante']['nome'], torcidas)
    return render(request, 'bepe/jogos.html', {'aba': 'jogos', 'jogos': lista})


# ==========================================
# ROTAS DAS TORCIDAS A x B
# ==========================================
def _float(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


@bepe_required
def rotas(request):
    return render(request, 'bepe/rotas_lista.html', {
        'aba': 'rotas',
        'planos': PlanoRota.objects.select_related('torcida_a', 'torcida_b')[:50],
    })


@bepe_required
def rota_planejar(request, plano_id=None):
    plano = get_object_or_404(PlanoRota, id=plano_id) if plano_id else None

    if request.method == 'POST':
        try:
            dados = json.loads(request.body or '{}')
        except ValueError:
            return JsonResponse({'ok': False, 'erro': 'Dados inválidos.'}, status=400)
        obrigatorios = ['destino_lat', 'destino_lng', 'origem_a_lat', 'origem_a_lng', 'origem_b_lat', 'origem_b_lng']
        if any(_float(dados.get(c)) is None for c in obrigatorios):
            return JsonResponse({'ok': False, 'erro': 'Defina o destino e a origem das duas torcidas.'}, status=400)

        plano = plano or PlanoRota(criado_por=request.user)
        plano.titulo = (dados.get('titulo') or 'Plano de rota').strip()[:150]
        data_jogo = parse_datetime(dados['data_jogo']) if dados.get('data_jogo') else None
        if data_jogo and timezone.is_naive(data_jogo):
            data_jogo = timezone.make_aware(data_jogo)
        plano.data_jogo = data_jogo
        plano.destino_nome = (dados.get('destino_nome') or '')[:200]
        plano.torcida_a = Torcida.objects.filter(id=dados.get('torcida_a') or None).first()
        plano.torcida_b = Torcida.objects.filter(id=dados.get('torcida_b') or None).first()
        plano.origem_a_nome = (dados.get('origem_a_nome') or '')[:200]
        plano.origem_b_nome = (dados.get('origem_b_nome') or '')[:200]
        for campo in obrigatorios:
            setattr(plano, campo, _float(dados[campo]))
        plano.rota_a = dados.get('rota_a')
        plano.rota_b = dados.get('rota_b')
        plano.pontos_risco = dados.get('pontos_risco') or []
        plano.observacoes = dados.get('observacoes', '')
        plano.save()
        return JsonResponse({'ok': True, 'id': plano.id, 'url': reverse('bepe:rota_editar', args=[plano.id])})

    # Pré-preenchimento vindo da tela de Jogos
    inicial = {}
    if not plano:
        campos = ('titulo', 'destino_nome', 'destino_lat', 'destino_lng', 'data_jogo', 'torcida_a', 'torcida_b')
        inicial = {k: request.GET.get(k, '') for k in campos}

    plano_json = None
    if plano:
        plano_json = {
            'id': plano.id, 'titulo': plano.titulo, 'destino_nome': plano.destino_nome,
            'destino_lat': plano.destino_lat, 'destino_lng': plano.destino_lng,
            'data_jogo': timezone.localtime(plano.data_jogo).strftime('%Y-%m-%dT%H:%M') if plano.data_jogo else '',
            'torcida_a': plano.torcida_a_id, 'origem_a_nome': plano.origem_a_nome,
            'origem_a_lat': plano.origem_a_lat, 'origem_a_lng': plano.origem_a_lng,
            'torcida_b': plano.torcida_b_id, 'origem_b_nome': plano.origem_b_nome,
            'origem_b_lat': plano.origem_b_lat, 'origem_b_lng': plano.origem_b_lng,
            'observacoes': plano.observacoes,
        }

    return render(request, 'bepe/rota_planejar.html', {
        'aba': 'rotas',
        'plano': plano,
        'inicial': inicial,
        'plano_json': plano_json,
        'torcidas': Torcida.objects.order_by('nome'),
        'cores_torcidas': {t.id: t.cor_primaria for t in Torcida.objects.all()},
    })


@bepe_required
def rota_torcedores(request):
    """Torcedores compartilhando localização das torcidas do plano (para ver no mapa de rotas)."""
    ids = [i for i in request.GET.getlist('torcida') if i.isdigit()]
    desde = timezone.now() - timedelta(minutes=60)
    return JsonResponse({'pontos': pontos_ao_vivo(desde, ids) if ids else []})


def _link_google_maps(origem_lat, origem_lng, destino_lat, destino_lng):
    return (f"https://www.google.com/maps/dir/?api=1&origin={origem_lat},{origem_lng}"
            f"&destination={destino_lat},{destino_lng}&travelmode=driving")


@bepe_required
@require_POST
def rota_enviar(request, plano_id):
    """Envia a cada diretoria, pelo Canal BEPE, a rota que a torcida dela deve seguir."""
    plano = get_object_or_404(PlanoRota, id=plano_id)
    enviados = []
    trechos = (
        (plano.torcida_a, plano.origem_a_lat, plano.origem_a_lng, plano.origem_a_nome),
        (plano.torcida_b, plano.origem_b_lat, plano.origem_b_lng, plano.origem_b_nome),
    )
    for torcida, lat, lng, origem in trechos:
        if not torcida:
            continue
        quando = f" em {timezone.localtime(plano.data_jogo):%d/%m às %H:%M}" if plano.data_jogo else ''
        linhas = [
            f"Rota definida pelo BEPE para {plano.titulo}{quando}.",
            "",
            f"Saída: {origem or 'ponto combinado'}",
            f"Destino: {plano.destino_nome}",
            "",
            "Siga exatamente este trajeto:",
            _link_google_maps(lat, lng, plano.destino_lat, plano.destino_lng),
        ]
        if plano.observacoes:
            linhas += ["", f"Observações: {plano.observacoes}"]
        conversa = Conversa.objects.create(torcida=torcida, assunto=f"Rota: {plano.titulo}"[:150], criada_por=request.user)
        Mensagem.objects.create(conversa=conversa, autor=request.user, do_bepe=True, texto="\n".join(linhas))
        enviados.append(torcida.nome)
    if enviados:
        messages.success(request, f"Rota enviada para: {', '.join(enviados)}.")
    else:
        messages.error(request, "Selecione as torcidas do plano antes de enviar.")
    return redirect('bepe:rota_editar', plano_id=plano.id)


@bepe_required
@require_POST
def rota_excluir(request, plano_id):
    get_object_or_404(PlanoRota, id=plano_id).delete()
    messages.success(request, "Plano de rota excluído.")
    return redirect('bepe:rotas')


# ==========================================
# SALA DE REUNIÃO (vídeo) COM AS DIRETORIAS
# ==========================================
def _avisar_reuniao(reuniao, autor, texto_inicial):
    quando = timezone.localtime(reuniao.data_hora)
    linhas = [
        texto_inicial,
        "",
        reuniao.titulo,
        f"{quando:%d/%m/%Y às %H:%M} ({reuniao.duracao_min} min)",
    ]
    if reuniao.pauta:
        linhas += ["", f"Pauta: {reuniao.pauta}"]
    linhas += ["", f"Entrar na sala: {reuniao.link}"]
    for torcida in reuniao.torcidas.all():
        conversa = Conversa.objects.create(torcida=torcida, assunto=f"Reunião: {reuniao.titulo}"[:150], criada_por=autor)
        Mensagem.objects.create(conversa=conversa, autor=autor, do_bepe=True, texto="\n".join(linhas))


def _separar_reunioes(lista):
    agora = timezone.now()
    proximas = [r for r in lista if not r.cancelada and r.termino >= agora]
    anteriores = [r for r in lista if r.cancelada or r.termino < agora]
    return proximas, anteriores[::-1][:10]


@bepe_required
def reunioes(request):
    if request.method == 'POST':
        form = ReuniaoForm(request.POST)
        if form.is_valid():
            reuniao = form.save(commit=False)
            reuniao.criada_por = request.user
            reuniao.save()
            form.save_m2m()
            _avisar_reuniao(reuniao, request.user, "O BEPE convocou uma reunião por vídeo.")
            messages.success(request, "Reunião criada e diretorias avisadas pelo Canal BEPE.")
            return redirect('bepe:reunioes')
    else:
        inicio = (timezone.localtime() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:00')
        form = ReuniaoForm(initial={'data_hora': inicio})

    proximas, anteriores = _separar_reunioes(list(Reuniao.objects.prefetch_related('torcidas')))
    return render(request, 'bepe/reunioes.html', {
        'aba': 'reunioes',
        'form': form,
        'proximas': proximas,
        'anteriores': anteriores,
        'lado_bepe': True,
        'template_base': 'bepe/base_bepe.html',
    })


@bepe_required
@require_POST
def reuniao_cancelar(request, reuniao_id):
    reuniao = get_object_or_404(Reuniao, id=reuniao_id)
    reuniao.cancelada = True
    reuniao.save()
    _avisar_reuniao(reuniao, request.user, "REUNIÃO CANCELADA pelo BEPE.")
    messages.success(request, "Reunião cancelada e diretorias avisadas.")
    return redirect('bepe:reunioes')


@diretoria_required
def diretoria_reunioes(request):
    lista = Reuniao.objects.filter(torcidas=request.torcida_diretoria).prefetch_related('torcidas')
    proximas, anteriores = _separar_reunioes(list(lista))
    return render(request, 'bepe/reunioes.html', {
        'aba': 'reunioes',
        'proximas': proximas,
        'anteriores': anteriores,
        'lado_bepe': False,
        'template_base': 'bepe/base_diretoria.html',
    })
