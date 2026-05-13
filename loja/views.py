# loja/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from .models import Produto, ItemCarrinho, Pedido, ItemPedido, Variacao
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from organizadas.models import Evento
import json



@login_required
def loja_view(request):
    perfil = getattr(request.user, 'perfil', None)
    torcida_usuario = perfil.torcida if perfil else None
    total_itens = 0
    
    # 1. Verifica se o usuário tem torcida
    if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        torcida_usuario = request.user.perfil.torcida
        
    # 2. Pega a aba selecionada (padrão é torcida, se ele tiver uma. Senão, vai para global)
    aba_padrao = 'torcida' if torcida_usuario else 'global'
    aba = request.GET.get('aba', aba_padrao)
    
    # Se ele não tem torcida, forçamos a aba para global por segurança
    if not torcida_usuario:
        aba = 'global'
    
    # 3. Filtra os produtos com base na aba selecionada
    if aba == 'torcida' and torcida_usuario:
        base_produtos = Produto.objects.filter(torcida=torcida_usuario)
    else:
        # Global = MOSTRA TODOS OS PRODUTOS (Da SAT e de todas as Torcidas)
        base_produtos = Produto.objects.all()
    
    produtos = base_produtos

    # 4. Aplicar o filtro de categoria
    categoria_atual = request.GET.get('categoria')
    if categoria_atual:
        # CORREÇÃO AQUI: Como agora é um ForeignKey, filtramos pelo nome da categoria relacionada
        if categoria_atual.isdigit():
            produtos = produtos.filter(categoria_id=categoria_atual)
        else:
            produtos = produtos.filter(categoria__nome=categoria_atual)
        
    # 5. Calcular os itens do carrinho para o ícone flutuante
    total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    # 6. Puxar categorias da 'base_produtos' para os botões
    # CORREÇÃO AQUI: Removido o .exclude(categoria__exact='') e adicionado 'categoria__nome'
    categorias = base_produtos.exclude(categoria__isnull=True).values_list('categoria__nome', flat=True).distinct()

    context = {
        'produtos': produtos,
        'total_itens_carrinho': total_itens,
        'torcida': torcida_usuario,
        'categorias': categorias,
        'categoria_atual': categoria_atual,
        'aba_atual': aba, # Apenas para marcação de abas 
    }
    return render(request, 'store.html', context)

@login_required
@login_required
def adicionar_ao_carrinho(request, produto_id):
    # Permite adicionar ao carrinho produtos de qualquer torcida ou SAT
    produto = get_object_or_404(Produto, id=produto_id)

    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    variacao_id = request.POST.get('variacao_id')
    variacao = None
    
    if variacao_id:
        variacao = get_object_or_404(Variacao, id=variacao_id)
    
    if produto.estoque > 0:
        item, created = ItemCarrinho.objects.get_or_create(
            usuario=request.user, 
            produto=produto,
            variacao=variacao
        )
        
        if not created:
            item.quantidade += 1
            item.save()
            
        # Retorno AJAX silencioso para o botão não recarregar a tela
        if is_ajax:
            total_itens = ItemCarrinho.objects.filter(usuario=request.user).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            return JsonResponse({
                'sucesso': True, 
                'total_itens': total_itens, 
                'mensagem': f'{produto.nome} adicionado ao carrinho!'
            })
            
    if is_ajax:
        return JsonResponse({'sucesso': False, 'erro': 'Produto sem estoque.'}, status=400)
        
    return redirect(request.META.get('HTTP_REFERER', 'loja'))

@login_required
def detalhe_produto(request, produto_id):
    # Permite visualizar os detalhes de qualquer produto
    produto = get_object_or_404(Produto, id=produto_id)
        
    return render(request, 'loja/detalhe_produto.html', {'produto': produto})

@login_required
def ver_carrinho(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco * item.quantidade for item in itens)
    return render(request, 'loja/carrinho.html', {'itens': itens, 'total_geral': total_geral})

@login_required
def remover_do_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    item.delete()
    return redirect('ver_carrinho')

@login_required
def calcular_frete(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cep = data.get('cep', '').replace('-', '')
            
            if len(cep) != 8:
                return JsonResponse({'sucesso': False, 'erro': 'CEP inválido.'})
            
            itens = ItemCarrinho.objects.filter(usuario=request.user)
            peso_total = sum((item.produto.peso or 0.500) * item.quantidade for item in itens)
            
            valor_pac = 15.00 + float(peso_total * 2)
            valor_sedex = 30.00 + float(peso_total * 4)
            
            if int(cep[0]) > 5:
                valor_pac += 20.00
                valor_sedex += 40.00
                
            opcoes = [
                {'tipo': 'PAC', 'valor': round(valor_pac, 2), 'prazo': '7 a 10 dias úteis'},
                {'tipo': 'SEDEX', 'valor': round(valor_sedex, 2), 'prazo': '2 a 4 dias úteis'}
            ]
            
            return JsonResponse({'sucesso': True, 'opcoes': opcoes})
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})

@login_required
def finalizar_checkout(request):
    if request.method != 'POST':
        return redirect('loja')
        
    itens_carrinho = ItemCarrinho.objects.filter(usuario=request.user)
    if not itens_carrinho.exists():
        return redirect('loja')
    
    total_produtos = sum(item.produto.preco_atual() * item.quantidade for item in itens_carrinho)
    
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
        
        modalidade_frete = request.POST.get('modalidade_frete')
        valor_frete_str = request.POST.get('valor_frete', '0')
        try:
            valor_frete = float(valor_frete_str.replace(',', '.'))
        except ValueError:
            valor_frete = 0.0
        
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
                ItemPedido.objects.create(pedido=pedido, produto=item.produto, quantidade=item.quantidade, preco_unitario=item.produto.preco_atual())
                item.produto.estoque -= item.quantidade
                item.produto.save()
            
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
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total_geral = sum(item.produto.preco_atual() * item.quantidade for item in itens)
    
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
    if not request.user.is_staff or not hasattr(request.user, 'perfil') or not request.user.perfil.torcida:
        messages.error(request, "Acesso negado. Apenas moderadores autorizados.")
        return redirect('loja')

    produtos = Produto.objects.filter(torcida=request.user.perfil.torcida).order_by('-id')
    return render(request, 'loja/painel.html', {'produtos': produtos})

@login_required
def form_produto(request, produto_id=None):
    if not (request.user.is_staff and hasattr(request.user, 'perfil') and request.user.perfil.torcida):
        return redirect('loja')
        
    produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida) if produto_id else None
    
    if request.method == 'POST':
        nome = request.POST.get('nome')
        preco = request.POST.get('preco').replace(',', '.') 
        categoria_input = request.POST.get('categoria') # O formulário envia 'Camisetas'
        estoque = request.POST.get('estoque')
        descricao = request.POST.get('descricao')
        destaque = request.POST.get('destaque') == 'on'
        imagem = request.FILES.get('imagem')
        
        # --- CORREÇÃO DA CATEGORIA ---
        # Importamos o modelo e convertemos o input no Objeto CategoriaProduto
        from .models import CategoriaProduto
        categoria_obj = None
        
        if categoria_input:
            if str(categoria_input).isdigit():
                # Se o formulário enviar um número (ID)
                categoria_obj = CategoriaProduto.objects.filter(id=categoria_input).first()
            else:
                # Se o formulário enviar texto (ex: 'Camisetas')
                # Procura essa categoria. Se não existir, cria-a automaticamente!
                categoria_obj, _ = CategoriaProduto.objects.get_or_create(
                    nome=categoria_input,
                    torcida=request.user.perfil.torcida
                )
        # -----------------------------
        
        if produto:
            produto.nome = nome
            produto.preco = preco
            produto.categoria = categoria_obj # Atribuímos o OBJETO, e não o texto
            produto.estoque = estoque
            produto.descricao = descricao
            produto.destaque = destaque
            if imagem:
                produto.imagem = imagem
            produto.save()
            messages.success(request, 'Produto atualizado!')
        else:
            Produto.objects.create(
                nome=nome, 
                preco=preco, 
                categoria=categoria_obj, # Atribuímos o OBJETO, e não o texto
                estoque=estoque, 
                descricao=descricao, 
                destaque=destaque,
                imagem=imagem, 
                torcida=request.user.perfil.torcida
            )
            messages.success(request, 'Produto criado com sucesso!')
            
        # Corrigido também o redirecionamento (o nome da rota correto no urls.py é 'painel_loja')
        return redirect('painel_loja') 
        
    return render(request, 'loja/form_produto.html', {'produto': produto})

@login_required
def excluir_produto(request, produto_id):
    if request.user.is_staff:
        produto = get_object_or_404(Produto, id=produto_id, torcida=request.user.perfil.torcida)
        produto.delete()
        messages.success(request, 'Produto removido com sucesso.')
    return redirect('loja/painel_loja')

def checkout_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    
    # Por enquanto, apenas retorna uma mensagem simples na tela.
    # Depois poderás criar o HTML real de pagamento aqui!
    return HttpResponse(f"<h1>Área de Pagamento</h1><p>A comprar ingresso para: <b>{evento.titulo}</b> por R$ {evento.valor}</p>")
# Force reload server
