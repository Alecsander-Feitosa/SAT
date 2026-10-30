# loja/views.py
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum, Value
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import (
    AvaliacaoProduto, CategoriaProduto, ConfigLoja, ImagemProduto, ItemCarrinho, ItemPedido,
    Pedido, Produto, Variacao,
)
from . import frete
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from organizadas.models import Evento, Caravana, InscricaoPagamento
import json

# Pedidos que contam como compra feita (liberam a avaliação do produto)
STATUS_COMPRA_CONFIRMADA = ('pago', 'enviado', 'aguardando_retirada', 'concluido')


def _pode_gerir_loja(user):
    return user.is_staff and hasattr(user, 'perfil') and user.perfil.torcida_id


def _decimal(valor, padrao=None):
    try:
        return Decimal(str(valor).replace(',', '.')) if str(valor or '').strip() else padrao
    except InvalidOperation:
        return padrao


def _inteiro(valor, padrao=0):
    try:
        return max(int(valor), 0)
    except (TypeError, ValueError):
        return padrao


def _estoque_disponivel(produto, variacao):
    return variacao.estoque if variacao else produto.estoque


@login_required
def loja_view(request):
    perfil = getattr(request.user, 'perfil', None)
    torcida_usuario = perfil.torcida if perfil else None

    # 1. Pega a aba selecionada (padrão é torcida, se ele tiver uma. Senão, vai para global)
    aba_padrao = 'torcida' if torcida_usuario else 'global'
    aba = request.GET.get('aba', aba_padrao)

    # Se ele não tem torcida, forçamos a aba para global por segurança
    if not torcida_usuario:
        aba = 'global'

    # 2. Filtra os produtos com base na aba selecionada
    if aba == 'torcida' and torcida_usuario:
        base_produtos = Produto.objects.filter(torcida=torcida_usuario)
    else:
        # Global = MOSTRA TODOS OS PRODUTOS (Da SAT e de todas as Torcidas)
        base_produtos = Produto.objects.all()

    produtos = base_produtos.select_related('torcida', 'categoria').annotate(
        nota_media=Avg('avaliacoes__nota'), num_avaliacoes=Count('avaliacoes', distinct=True),
        num_variacoes=Count('variacoes', distinct=True),
    )

    # 3. Aplicar o filtro de categoria
    categoria_atual = request.GET.get('categoria')
    if categoria_atual:
        if categoria_atual.isdigit():
            produtos = produtos.filter(categoria_id=categoria_atual)
        else:
            produtos = produtos.filter(categoria__nome=categoria_atual)

    # 4. Categorias da 'base_produtos' para os botões
    categorias = base_produtos.exclude(categoria__isnull=True).values_list('categoria__nome', flat=True).distinct()

    # 5. Banner: o da torcida na aba dela, o da SAT na aba global
    if aba == 'torcida':
        banner = ConfigLoja.objects.filter(torcida=torcida_usuario).first()
    else:
        banner = ConfigLoja.objects.filter(torcida__isnull=True).first()

    context = {
        'produtos': produtos,
        'torcida': torcida_usuario,
        'categorias': categorias,
        'categoria_atual': categoria_atual,
        'aba_atual': aba, # Apenas para marcação de abas
        'banner': banner,
    }
    return render(request, 'store.html', context)

@login_required
@require_POST
def adicionar_ao_carrinho(request, produto_id):
    # Permite adicionar ao carrinho produtos de qualquer torcida ou SAT
    produto = get_object_or_404(Produto, id=produto_id)
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    def falha(erro):
        if is_ajax:
            return JsonResponse({'sucesso': False, 'erro': erro, 'url': reverse('detalhe_produto', args=[produto.id])}, status=400)
        messages.error(request, erro)
        return redirect('detalhe_produto', produto_id=produto.id)

    variacao = None
    variacao_id = request.POST.get('variacao_id')
    if variacao_id:
        variacao = get_object_or_404(Variacao, id=variacao_id, produto=produto)
    elif produto.variacoes.exists():
        return falha('Escolha as opções do produto antes de adicionar.')

    quantidade = max(_inteiro(request.POST.get('quantidade'), 1), 1)
    item = ItemCarrinho.objects.filter(usuario=request.user, produto=produto, variacao=variacao).first()
    no_carrinho = item.quantidade if item else 0
    if no_carrinho + quantidade > _estoque_disponivel(produto, variacao):
        return falha('Produto sem estoque suficiente.' if no_carrinho == 0 else 'Você já tem todo o estoque disponível no carrinho.')

    if item:
        item.quantidade += quantidade
        item.save(update_fields=['quantidade'])
    else:
        ItemCarrinho.objects.create(usuario=request.user, produto=produto, variacao=variacao, quantidade=quantidade)

    # Retorno AJAX silencioso para o botão não recarregar a tela
    if is_ajax:
        total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        return JsonResponse({
            'sucesso': True,
            'total_itens': total_itens,
            'mensagem': f'{produto.nome} adicionado ao carrinho!'
        })
    messages.success(request, f'{produto.nome} adicionado ao carrinho!')
    return redirect(request.META.get('HTTP_REFERER') or 'loja')

@login_required
def detalhe_produto(request, produto_id):
    # Permite visualizar os detalhes de qualquer produto
    produto = get_object_or_404(Produto.objects.select_related('torcida', 'categoria'), id=produto_id)
    variacoes = list(produto.variacoes.all())
    avaliacoes = produto.avaliacoes.select_related('usuario', 'usuario__perfil')
    resumo = avaliacoes.aggregate(media=Avg('nota'), total=Count('id'))

    comprou = ItemPedido.objects.filter(
        pedido__usuario=request.user, pedido__status__in=STATUS_COMPRA_CONFIRMADA, produto=produto,
    ).exists()

    return render(request, 'loja/detalhe_produto.html', {
        'produto': produto,
        'imagens': ([produto.imagem] if produto.imagem else []) + [i.imagem for i in produto.imagens_extra.all()],
        'variacoes_json': [
            {'id': v.id, 'op1': v.nome, 'op2': v.opcao2, 'estoque': v.estoque} for v in variacoes
        ],
        'tem_variacoes': bool(variacoes),
        'linhas_medidas': [
            [c.strip() for c in linha.split('|')] for linha in produto.tabela_medidas_texto.splitlines() if linha.strip()
        ],
        'avaliacoes': avaliacoes,
        'nota_media': resumo['media'],
        'total_avaliacoes': resumo['total'],
        'minha_avaliacao': avaliacoes.filter(usuario=request.user).first(),
        'pode_avaliar': comprou,
    })


@login_required
@require_POST
def avaliar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    comprou = ItemPedido.objects.filter(
        pedido__usuario=request.user, pedido__status__in=STATUS_COMPRA_CONFIRMADA, produto=produto,
    ).exists()
    if not comprou:
        messages.error(request, 'Só quem comprou o produto pode avaliá-lo.')
        return redirect('detalhe_produto', produto_id=produto.id)

    nota = min(_inteiro(request.POST.get('nota'), 0), 5)
    avaliacao, _ = AvaliacaoProduto.objects.get_or_create(produto=produto, usuario=request.user, defaults={'nota': nota})
    avaliacao.nota = nota
    avaliacao.comentario = request.POST.get('comentario', '').strip()[:300]
    if request.FILES.get('foto'):
        avaliacao.foto = request.FILES['foto']
    elif request.POST.get('remover_foto'):
        avaliacao.foto = None
    avaliacao.save()
    messages.success(request, 'Obrigado pela avaliação!')
    return redirect(reverse('detalhe_produto', args=[produto.id]) + '#avaliacoes')


@login_required
def ver_carrinho(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user).select_related('produto', 'produto__torcida', 'variacao')
    total_geral = sum(item.subtotal for item in itens)
    return render(request, 'loja/carrinho.html', {'itens': itens, 'total_geral': total_geral})

@login_required
def remover_do_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    item.delete()
    return redirect('ver_carrinho')

@login_required
@require_POST
def atualizar_quantidade(request, item_id):
    item = get_object_or_404(ItemCarrinho.objects.select_related('produto', 'variacao'), id=item_id, usuario=request.user)
    quantidade = _inteiro(request.POST.get('quantidade'), item.quantidade)
    if quantidade == 0:
        item.delete()
    else:
        disponivel = _estoque_disponivel(item.produto, item.variacao)
        if quantidade > disponivel:
            messages.error(request, f'Só há {disponivel} unidade(s) de {item.produto.nome} em estoque.')
            quantidade = max(disponivel, 1)
        item.quantidade = quantidade
        item.save(update_fields=['quantidade'])
    return redirect('ver_carrinho')

@login_required
@require_POST
def calcular_frete(request):
    """Cota o frete do carrinho, ou de um produto só (página do produto: produto_id + quantidade)."""
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'sucesso': False, 'erro': 'Requisição inválida.'})

    if data.get('produto_id'):
        produto = get_object_or_404(Produto, id=data['produto_id'])
        itens = [(produto, max(_inteiro(data.get('quantidade'), 1), 1))]
    else:
        itens = [(i.produto, i.quantidade) for i in ItemCarrinho.objects.filter(usuario=request.user).select_related('produto')]
        if not itens:
            return JsonResponse({'sucesso': False, 'erro': 'Seu carrinho está vazio.'})

    try:
        return JsonResponse({'sucesso': True, 'opcoes': frete.cotar(data.get('cep', ''), itens)})
    except ValueError as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@login_required
def finalizar_checkout(request):
    if request.method != 'POST':
        return redirect('loja')

    itens_carrinho = ItemCarrinho.objects.filter(usuario=request.user).select_related('produto', 'variacao')
    if not itens_carrinho.exists():
        return redirect('loja')

    for item in itens_carrinho:
        if item.quantidade > _estoque_disponivel(item.produto, item.variacao):
            nome = item.produto.nome + (f' ({item.variacao.descricao})' if item.variacao else '')
            messages.error(request, f'{nome} não tem mais estoque suficiente. Ajuste o carrinho.')
            return redirect('ver_carrinho')

    total_produtos = sum(item.subtotal for item in itens_carrinho)

    # --- Tipo de entrega ---
    retirada_sede = request.POST.get('tipo_entrega') == 'sede'
    metodo_pagamento = request.POST.get('metodo_pagamento', 'pix')

    # --- Dados de endereço (só se for envio) ---
    cep = endereco = numero = complemento = bairro = cidade = estado = None
    modalidade_frete = None
    valor_frete = 0.0

    if not retirada_sede:
        cep = request.POST.get('cep')
        endereco = request.POST.get('rua')
        numero = request.POST.get('numero')
        complemento = request.POST.get('complemento')
        bairro = request.POST.get('bairro')
        cidade = request.POST.get('cidade')
        estado = request.POST.get('estado')

        # O valor do frete é recalculado aqui: o que veio do navegador não é confiável
        modalidade_frete = request.POST.get('modalidade_frete')
        try:
            opcoes = frete.cotar(cep, [(i.produto, i.quantidade) for i in itens_carrinho])
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('checkout_exemplo')
        escolhida = next((o for o in opcoes if o['tipo'] == modalidade_frete), None)
        if not escolhida:
            messages.error(request, 'Selecione novamente a forma de envio.')
            return redirect('checkout_exemplo')
        valor_frete = escolhida['valor']

    total_geral = float(total_produtos) + valor_frete

    # --- Dados pessoais (para boleto e cartão) ---
    cpf = request.POST.get('cpf', '')
    nome_completo = request.POST.get('nome_completo', request.user.get_full_name() or request.user.username)
    email = request.POST.get('email', request.user.email)

    try:
        with transaction.atomic():
            pedido = Pedido.objects.create(
                usuario=request.user,
                total=total_geral,
                status='aguardando_retirada' if (retirada_sede and metodo_pagamento == 'sede') else 'pendente',
                retirada_sede=retirada_sede,
                metodo_pagamento=metodo_pagamento,
                cep=cep,
                endereco=endereco,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                estado=estado,
                valor_frete=valor_frete,
                modalidade_frete=modalidade_frete if not retirada_sede else 'Retirada na Sede'
            )
            for item in itens_carrinho:
                ItemPedido.objects.create(
                    pedido=pedido, produto=item.produto, quantidade=item.quantidade,
                    preco_unitario=item.produto.preco_atual(),
                    variacao=item.variacao, variacao_descricao=item.variacao.descricao if item.variacao else '',
                )
                # Baixa no banco: o mesmo produto pode aparecer em vários itens (variações diferentes)
                baixa = Greatest(F('estoque') - item.quantidade, Value(0))
                if item.variacao:
                    Variacao.objects.filter(id=item.variacao_id).update(estoque=baixa)
                Produto.objects.filter(id=item.produto_id).update(estoque=baixa)

            pix_data = None
            boleto_data = None
            cartao_data = None

            # ===== PIX =====
            if metodo_pagamento == 'pix':
                from accounts.efi_utils import gerar_cobranca_pix
                pix_data = gerar_cobranca_pix(pedido, tipo='pedido')

                if not pix_data.get('sucesso'):
                    raise Exception(pix_data.get('erro', 'Erro desconhecido ao gerar PIX'))

            # ===== BOLETO =====
            elif metodo_pagamento == 'boleto':
                from accounts.efi_utils import gerar_cobranca_boleto
                boleto_data = gerar_cobranca_boleto(pedido, cpf, nome_completo, email)

                if not boleto_data.get('sucesso'):
                    raise Exception(boleto_data.get('erro', 'Erro ao gerar boleto'))

            # ===== CARTÃO DE CRÉDITO =====
            elif metodo_pagamento == 'cartao':
                from accounts.efi_utils import gerar_cobranca_cartao
                payment_token = request.POST.get('payment_token', '')
                nascimento = request.POST.get('nascimento', '')
                telefone = request.POST.get('telefone', '')

                endereco_dados = {
                    'rua': endereco or request.POST.get('rua', ''),
                    'numero': numero or request.POST.get('numero', ''),
                    'bairro': bairro or request.POST.get('bairro', ''),
                    'cep': cep or request.POST.get('cep', ''),
                    'cidade': cidade or request.POST.get('cidade', ''),
                    'estado': estado or request.POST.get('estado', ''),
                }

                if not payment_token:
                    raise Exception('Token do cartão não recebido. Tente novamente.')

                cartao_data = gerar_cobranca_cartao(
                    pedido, payment_token, cpf, nome_completo,
                    email, nascimento, telefone, endereco_dados
                )

                if not cartao_data.get('sucesso'):
                    raise Exception(cartao_data.get('erro', 'Erro ao processar cartão'))

            itens_carrinho.delete()

        return render(request, 'loja/sucesso.html', {
            'pedido': pedido,
            'pix_data': pix_data,
            'boleto_data': boleto_data,
            'cartao_data': cartao_data,
            'metodo_pagamento': metodo_pagamento,
            'retirada_sede': retirada_sede
        })

    except Exception as e:
        messages.error(request, f"Erro ao processar pedido: {str(e)}")
        return redirect('checkout_exemplo')

@login_required
def checkout_exemplo_view(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user).select_related('produto', 'variacao')
    total_geral = sum(item.subtotal for item in itens)

    torcida = None
    if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        torcida = request.user.perfil.torcida

    return render(request, 'loja/checkout_exemplo.html', {
        'itens': itens,
        'total_geral': total_geral,
        'torcida': torcida,
        'efi_conta_id': settings.EFI_CONTA_ID,
        'efi_sandbox': settings.EFI_SANDBOX,
    })

# ==========================================
# PAINEL DO MODERADOR DA LOJA
# ==========================================

@login_required
def painel_loja(request):
    if not _pode_gerir_loja(request.user):
        messages.error(request, "Acesso negado. Apenas moderadores autorizados.")
        return redirect('loja')

    torcida = request.user.perfil.torcida
    config, _ = ConfigLoja.objects.get_or_create(torcida=torcida)

    # Banner e CEP de envio da loja da torcida
    if request.method == 'POST':
        config.banner_selo = request.POST.get('banner_selo', '').strip()
        config.banner_titulo = request.POST.get('banner_titulo', '').strip()
        config.banner_subtitulo = request.POST.get('banner_subtitulo', '').strip()
        config.banner_link = request.POST.get('banner_link', '').strip()
        config.cep_origem = request.POST.get('cep_origem', '').strip()
        if request.FILES.get('banner_imagem'):
            config.banner_imagem = request.FILES['banner_imagem']
        elif request.POST.get('remover_banner'):
            config.banner_imagem = None
        config.save()
        messages.success(request, 'Banner e dados de envio salvos!')
        return redirect('painel_loja')

    produtos = Produto.objects.filter(torcida=torcida).select_related('categoria').order_by('-id')
    return render(request, 'loja/painel.html', {'produtos': produtos, 'config': config})

def _salvar_variacoes(request, produto):
    """Linhas do editor: var_id[], var_op1[], var_op2[], var_estoque[]. Linha sem 1ª opção é apagada."""
    existentes = {str(v.id): v for v in produto.variacoes.all()}
    mantidas = set()
    linhas = zip(
        request.POST.getlist('var_id'), request.POST.getlist('var_op1'),
        request.POST.getlist('var_op2'), request.POST.getlist('var_estoque'),
    )
    for var_id, op1, op2, estoque in linhas:
        op1, op2 = op1.strip(), op2.strip()
        if not op1:
            continue
        variacao = existentes.get(var_id) or Variacao(produto=produto)
        variacao.nome, variacao.opcao2, variacao.estoque = op1, op2, _inteiro(estoque)
        variacao.save()
        mantidas.add(str(variacao.id))
    for var_id, variacao in existentes.items():
        if var_id not in mantidas:
            variacao.delete()
    # Com variações, o estoque do produto é a soma delas
    if mantidas:
        produto.estoque = sum(v.estoque for v in produto.variacoes.all())
        produto.save(update_fields=['estoque'])

@login_required
def form_produto(request, produto_id=None):
    if not _pode_gerir_loja(request.user):
        return redirect('loja')

    torcida = request.user.perfil.torcida
    produto = get_object_or_404(Produto, id=produto_id, torcida=torcida) if produto_id else None

    if request.method == 'POST':
        produto = produto or Produto(torcida=torcida)
        produto.nome = request.POST.get('nome', '').strip()
        produto.preco = _decimal(request.POST.get('preco'), Decimal('0'))
        produto.preco_promocional = _decimal(request.POST.get('preco_promocional'))
        produto.peso = _decimal(request.POST.get('peso'), produto.peso or Decimal('0.5'))
        produto.estoque = _inteiro(request.POST.get('estoque'))
        produto.descricao = request.POST.get('descricao', '')
        produto.destaque = request.POST.get('destaque') == 'on'
        produto.rotulo_opcao1 = request.POST.get('rotulo_opcao1', '').strip() or 'Tamanho'
        produto.rotulo_opcao2 = request.POST.get('rotulo_opcao2', '').strip()
        produto.tabela_medidas_texto = request.POST.get('tabela_medidas_texto', '').strip()

        # Categoria: texto livre; cria a categoria da torcida se ainda não existir
        categoria_input = request.POST.get('categoria', '').strip()
        produto.categoria = CategoriaProduto.objects.get_or_create(nome=categoria_input, torcida=torcida)[0] if categoria_input else None

        if request.FILES.get('imagem'):
            produto.imagem = request.FILES['imagem']
        if request.FILES.get('tabela_medidas'):
            produto.tabela_medidas = request.FILES['tabela_medidas']
        elif request.POST.get('remover_tabela_medidas'):
            produto.tabela_medidas = None
        criado = produto.pk is None
        produto.save()

        # Galeria: fotos novas e fotos marcadas para remover
        for arquivo in request.FILES.getlist('fotos_extra'):
            ImagemProduto.objects.create(produto=produto, imagem=arquivo)
        produto.imagens_extra.filter(id__in=request.POST.getlist('remover_foto')).delete()

        _salvar_variacoes(request, produto)
        messages.success(request, 'Produto criado com sucesso!' if criado else 'Produto atualizado!')
        return redirect('painel_loja')

    return render(request, 'loja/form_produto.html', {
        'produto': produto,
        'variacoes': produto.variacoes.all() if produto else [],
        'categorias': CategoriaProduto.objects.filter(torcida=torcida).values_list('nome', flat=True),
    })

@login_required
def excluir_produto(request, produto_id):
    if _pode_gerir_loja(request.user):
        produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida)
        produto.delete()
        messages.success(request, 'Produto removido com sucesso.')
    return redirect('painel_loja')

@login_required
def checkout_evento_view(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    torcida = evento.torcida

    return render(request, 'checkout_inscricao.html', {
        'item': evento,
        'tipo': 'evento',
        'torcida': torcida,
        'efi_conta_id': settings.EFI_CONTA_ID,
        'efi_sandbox': settings.EFI_SANDBOX,
    })

@login_required
def finalizar_checkout_evento(request, evento_id):
    if request.method != 'POST':
        return redirect('lista_eventos', slug=get_object_or_404(Evento, id=evento_id).torcida.slug)

    evento = get_object_or_404(Evento, id=evento_id)
    metodo_pagamento = request.POST.get('metodo_pagamento', 'pix')

    # Dados pessoais
    cpf = request.POST.get('cpf', '')
    nome_completo = request.POST.get('nome_completo', request.user.get_full_name() or request.user.username)
    email = request.POST.get('email', request.user.email)

    try:
        with transaction.atomic():
            inscricao = InscricaoPagamento.objects.create(
                usuario=request.user,
                tipo='evento',
                evento=evento,
                valor=evento.valor,
                total=evento.valor,
                metodo_pagamento=metodo_pagamento,
                status='pendente'
            )

            pix_data = None
            boleto_data = None
            cartao_data = None

            # ===== PIX =====
            if metodo_pagamento == 'pix':
                from accounts.efi_utils import gerar_cobranca_pix
                pix_data = gerar_cobranca_pix(inscricao, tipo='inscricao')

                if not pix_data.get('sucesso'):
                    raise Exception(pix_data.get('erro', 'Erro ao gerar PIX'))

            # ===== BOLETO =====
            elif metodo_pagamento == 'boleto':
                from accounts.efi_utils import gerar_cobranca_boleto
                boleto_data = gerar_cobranca_boleto(inscricao, cpf, nome_completo, email)

                if not boleto_data.get('sucesso'):
                    raise Exception(boleto_data.get('erro', 'Erro ao gerar boleto'))

            # ===== CARTÃO DE CRÉDITO =====
            elif metodo_pagamento == 'cartao':
                from accounts.efi_utils import gerar_cobranca_cartao
                payment_token = request.POST.get('payment_token', '')
                nascimento = request.POST.get('nascimento', '')
                telefone = request.POST.get('telefone', '')
                endereco_dados = {}

                if not payment_token:
                    raise Exception('Token do cartão não recebido.')

                cartao_data = gerar_cobranca_cartao(
                    inscricao, payment_token, cpf, nome_completo,
                    email, nascimento, telefone, endereco_dados
                )

                if not cartao_data.get('sucesso'):
                    raise Exception(cartao_data.get('erro', 'Erro ao processar cartão'))

        return render(request, 'sucesso_inscricao.html', {
            'inscricao': inscricao,
            'pix_data': pix_data,
            'boleto_data': boleto_data,
            'cartao_data': cartao_data,
            'metodo_pagamento': metodo_pagamento,
            'item_nome': evento.titulo,
            'torcida': evento.torcida
        })

    except Exception as e:
        messages.error(request, f"Erro ao processar pagamento: {str(e)}")
        return redirect('checkout_evento', evento_id=evento.id)


@login_required
def checkout_caravana_view(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    torcida = caravana.torcida

    return render(request, 'checkout_inscricao.html', {
        'item': caravana,
        'tipo': 'caravana',
        'torcida': torcida,
        'efi_conta_id': settings.EFI_CONTA_ID,
        'efi_sandbox': settings.EFI_SANDBOX,
    })

@login_required
def finalizar_checkout_caravana(request, caravana_id):
    if request.method != 'POST':
        return redirect('viagens', slug=get_object_or_404(Caravana, id=caravana_id).torcida.slug)

    caravana = get_object_or_404(Caravana, id=caravana_id)
    metodo_pagamento = request.POST.get('metodo_pagamento', 'pix')

    # Dados pessoais
    cpf = request.POST.get('cpf', '')
    nome_completo = request.POST.get('nome_completo', request.user.get_full_name() or request.user.username)
    email = request.POST.get('email', request.user.email)

    try:
        with transaction.atomic():
            inscricao = InscricaoPagamento.objects.create(
                usuario=request.user,
                tipo='caravana',
                caravana=caravana,
                valor=caravana.valor,
                total=caravana.valor,
                metodo_pagamento=metodo_pagamento,
                status='pendente'
            )

            pix_data = None
            boleto_data = None
            cartao_data = None

            # ===== PIX =====
            if metodo_pagamento == 'pix':
                from accounts.efi_utils import gerar_cobranca_pix
                pix_data = gerar_cobranca_pix(inscricao, tipo='inscricao')

                if not pix_data.get('sucesso'):
                    raise Exception(pix_data.get('erro', 'Erro ao gerar PIX'))

            # ===== BOLETO =====
            elif metodo_pagamento == 'boleto':
                from accounts.efi_utils import gerar_cobranca_boleto
                boleto_data = gerar_cobranca_boleto(inscricao, cpf, nome_completo, email)

                if not boleto_data.get('sucesso'):
                    raise Exception(boleto_data.get('erro', 'Erro ao gerar boleto'))

            # ===== CARTÃO DE CRÉDITO =====
            elif metodo_pagamento == 'cartao':
                from accounts.efi_utils import gerar_cobranca_cartao
                payment_token = request.POST.get('payment_token', '')
                nascimento = request.POST.get('nascimento', '')
                telefone = request.POST.get('telefone', '')
                endereco_dados = {}

                if not payment_token:
                    raise Exception('Token do cartão não recebido.')

                cartao_data = gerar_cobranca_cartao(
                    inscricao, payment_token, cpf, nome_completo,
                    email, nascimento, telefone, endereco_dados
                )

                if not cartao_data.get('sucesso'):
                    raise Exception(cartao_data.get('erro', 'Erro ao processar cartão'))

        return render(request, 'sucesso_inscricao.html', {
            'inscricao': inscricao,
            'pix_data': pix_data,
            'boleto_data': boleto_data,
            'cartao_data': cartao_data,
            'metodo_pagamento': metodo_pagamento,
            'item_nome': caravana.titulo,
            'torcida': caravana.torcida
        })

    except Exception as e:
        messages.error(request, f"Erro ao processar pagamento: {str(e)}")
        return redirect('checkout_caravana', caravana_id=caravana.id)
