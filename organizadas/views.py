from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from accounts.models import Aliada
from .models import Torcida, Evento, MembroDiretoria, Regra, FotoGaleria

from organizadas.models import (
    Torcida, Evento, Caravana, Post, Curtida, Parceiro, 
    Publicidade, FotoGaleria, ConquistaTorcida, MembroDiretoria, CategoriaDiretoria, Regra
)
from accounts.models import Perfil, Cancao, Aliada, HistoricoSocio, CampoPersonalizado
from loja.models import Produto, CategoriaProduto

# --- VIEWS PÚBLICAS E GERAIS ---

def lista_torcidas(request):
    torcidas = Torcida.objects.all()
    return render(request, 'organizadas/lista.html', {'torcidas': torcidas})

def detalhes_torcida(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    return render(request, 'organizadas/detalhes.html', {'torcida': torcida})

@login_required
def hub_view(request, slug):
    # Busca a torcida específica pelo slug
    torcida = get_object_or_404(Torcida, slug=slug)
    
    # Tenta obter o perfil de gamificação para exibir o nível no cartão do sócio
    # Certifique-se de importar o PerfilGamificacao no topo do arquivo
    from gamification.models import PerfilGamificacao
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    context = {
        'torcida': torcida,
        'perfil_game': perfil_game,
        'eventos': Evento.objects.filter(torcida=torcida, ativo=True).order_by('data'),
        'caravanas': Caravana.objects.filter(torcida=torcida),
        'parceiros': Parceiro.objects.filter(torcida=torcida),
        'publicidades': Publicidade.objects.filter(torcida=torcida),
        
        # Dados institucionais
        'diretoria': MembroDiretoria.objects.filter(torcida=torcida).order_by('categoria__ordem', 'ordem'),
        'regras': Regra.objects.filter(torcida=torcida).order_by('categoria', 'ordem'),
        'aliadas': Aliada.objects.filter(torcida=torcida),
        'conquistas': ConquistaTorcida.objects.filter(torcida=torcida),
        
        # Conteúdo multimédia
        'galeria': FotoGaleria.objects.filter(torcida=torcida).order_by('-data_publicacao')[:6],
        'cancoes': Cancao.objects.filter(torcida=torcida),
    }
    
    return render(request, 'torcida/hub.html', context)

# ==========================================
# VIEWS DAS FUNCIONALIDADES DO HUB DA TORCIDA
# ==========================================

@login_required
def diretoria(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    membros = MembroDiretoria.objects.filter(torcida=torcida).order_by('categoria__ordem', 'ordem')
    return render(request, 'torcida/diretoria.html', {'torcida': torcida, 'membros': membros})

@login_required
def mural_conquistas(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    conquistas = ConquistaTorcida.objects.filter(torcida=torcida)
    return render(request, 'torcida/mural_conquistas.html', {'torcida': torcida, 'conquistas': conquistas})

@login_required
def lista_eventos(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    eventos = Evento.objects.filter(torcida=torcida).order_by('-data')
    # O template de eventos estava na raiz da pasta templates segundo a estrutura
    return render(request, 'eventos.html', {'torcida': torcida, 'eventos': eventos})

@login_required
def regras(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    regras = Regra.objects.filter(torcida=torcida).order_by('categoria', 'ordem')
    return render(request, 'torcida/regras.html', {'torcida': torcida, 'regras': regras})

@login_required
def aliadas(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    # A model Aliada é importada de accounts.models (conforme o topo do seu views.py)
    aliadas_lista = Aliada.objects.filter(torcida=torcida)
    return render(request, 'torcida/aliadas.html', {'torcida': torcida, 'aliadas': aliadas_lista})

@login_required
def viagens(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    caravanas = Caravana.objects.filter(torcida=torcida).order_by('-saida_horario')
    return render(request, 'torcida/viagens.html', {'torcida': torcida, 'caravanas': caravanas})





# --- REDE SOCIAL E CONTEÚDO ---

@login_required
def curtir_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    curtida, created = Curtida.objects.get_or_create(post=post, usuario=request.user)
    if not created:
        curtida.delete()
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def galeria_fotos(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    fotos = FotoGaleria.objects.filter(torcida=torcida).order_by('-data_publicacao')
    return render(request, 'torcida/galeria.html', {'torcida': torcida, 'fotos': fotos})

@login_required
def cancoes(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    cancoes_lista = Cancao.objects.filter(torcida=torcida)
    
    if request.method == 'POST' and request.user.is_staff:
        # Atualizado para os novos nomes do banco de dados (titulo e url_youtube)
        Cancao.objects.create(
            titulo=request.POST.get('nome', 'Sem título'),
            letra=request.POST.get('letra'),
            url_youtube=request.POST.get('link_youtube'),
            torcida=torcida
        )
        messages.success(request, 'Canção adicionada!')
        return redirect('cancoes', slug=slug)

    return render(request, 'torcida/cancoes.html', {'cancoes': cancoes_lista, 'torcida': torcida})

@login_required
def excluir_cancao(request, cancao_id):
    cancao = get_object_or_404(Cancao, id=cancao_id)
    if request.user.is_staff and request.user.perfil.torcida == cancao.torcida:
        cancao.delete()
        messages.success(request, 'Canção removida.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))



# --- PAINEL DE MODERAÇÃO CENTRALIZADO SAT ---
@login_required
def painel_moderador(request):
    # Trava de segurança: Apenas Staff entra
    if not request.user.is_staff:
        messages.error(request, "Acesso restrito a moderadores.")
        return redirect('dashboard')

    minha_torcida = request.user.perfil.torcida
    if not minha_torcida:
        messages.error(request, "Não estás vinculado a nenhuma torcida para moderar.")
        return redirect('dashboard')

    # ==========================================
    # PROCESSAMENTO DE FORMULÁRIOS (POST)
    # ==========================================
    if request.method == "POST":
        acao = request.POST.get('acao')

        # 1. SÓCIOS E KYC
        if acao == 'aprovar_socio':
            p = get_object_or_404(Perfil, id=request.POST.get('perfil_id'), torcida=minha_torcida)
            p.aprovado = True
            p.save()
            HistoricoSocio.objects.create(perfil=p, acao="Aprovado", moderador=request.user, observacao="Aprovado via Painel SAT")
            messages.success(request, f"Sócio {p.user.username} aprovado!")
            
        elif acao == 'rejeitar_socio':
            p = get_object_or_404(Perfil, id=request.POST.get('perfil_id'), torcida=minha_torcida)
            HistoricoSocio.objects.create(perfil=p, acao="Rejeitado", moderador=request.user, observacao=request.POST.get('motivo', 'Rejeitado via Painel'))
            p.delete() 
            messages.warning(request, "Solicitação de sócio rejeitada.")
            
        elif acao == 'remover_socio':
            p = get_object_or_404(Perfil, id=request.POST.get('perfil_id'), torcida=minha_torcida)
            p.delete()
            messages.success(request, "Sócio removido permanentemente da base.")

        # --- NOVO: AÇÃO PARA EDITAR SÓCIO ---
        elif acao == 'editar_socio':
            p = get_object_or_404(Perfil, id=request.POST.get('perfil_id'), torcida=minha_torcida)
            
            # Atualiza os campos do Perfil
            p.vulgo = request.POST.get('vulgo', p.vulgo)
            p.pelotao = request.POST.get('pelotao', p.pelotao)
            p.rede_social = request.POST.get('rede_social', p.rede_social)
            p.whatsapp = request.POST.get('whatsapp', p.whatsapp)
            p.save()
            
            # Atualiza os dados base do User (Django)
            u = p.user
            if 'first_name' in request.POST:
                u.first_name = request.POST.get('first_name')
            if 'email' in request.POST:
                u.email = request.POST.get('email')
                u.username = request.POST.get('email') # Mantém o username igual ao email
            u.save()
            
            messages.success(request, f"Dados do sócio {u.first_name} atualizados com sucesso!")

        elif acao == 'novo_campo_custom':
            CampoPersonalizado.objects.create(
                torcida=minha_torcida,
                nome_campo=request.POST.get('nome_campo'),
                obrigatorio=request.POST.get('obrigatorio') == 'on'
            )
            messages.success(request, "Campo personalizado adicionado ao formulário de sócios!")

        # 2. EVENTOS E CARAVANAS
        elif acao == 'novo_evento':
            Evento.objects.create(
                torcida=minha_torcida,
                categoria=request.POST.get('categoria', 'evento_social'),
                titulo=request.POST.get('titulo'),
                data=parse_datetime(request.POST.get('data')),
                data_fim=parse_datetime(request.POST.get('data_fim')) if request.POST.get('data_fim') else None,
                local=request.POST.get('local'),
                max_participantes=request.POST.get('max_participantes') or None,
                informativo=request.POST.get('informativo', ''),
                imagem_capa=request.FILES.get('imagem_capa')
            )
            messages.success(request, "Novo evento publicado!")
            
        elif acao == 'deletar_evento':
            get_object_or_404(Evento, id=request.POST.get('item_id'), torcida=minha_torcida).delete()
            messages.success(request, "Evento apagado.")

        elif acao == 'nova_caravana':
            Caravana.objects.create(
                torcida=minha_torcida,
                titulo=request.POST.get('titulo'),
                saida_local=request.POST.get('saida_local'),
                saida_horario=parse_datetime(request.POST.get('saida_horario')),
                vagas_totais=request.POST.get('vagas_totais'),
                valor=request.POST.get('valor')
            )
            messages.success(request, "Caravana criada com sucesso!")

        elif acao == 'deletar_caravana':
            get_object_or_404(Caravana, id=request.POST.get('item_id'), torcida=minha_torcida).delete()
            messages.success(request, "Caravana removida.")

        # 3. DIRETORIA E REGRAS
        elif acao == 'nova_categoria_diretoria':
            CategoriaDiretoria.objects.create(torcida=minha_torcida, nome=request.POST.get('nome'), ordem=request.POST.get('ordem', 0))
            messages.success(request, "Categoria da diretoria criada.")

        elif acao == 'novo_membro':
            cat_id = request.POST.get('categoria_id')
            categoria = CategoriaDiretoria.objects.get(id=cat_id) if cat_id else None
            MembroDiretoria.objects.create(
                torcida=minha_torcida,
                categoria=categoria,
                nome=request.POST.get('nome'),
                cargo=request.POST.get('cargo'),
                ano_ingresso=request.POST.get('ano_ingresso') or None,
                ordem=request.POST.get('ordem', 0),
                foto=request.FILES.get('foto')
            )
            messages.success(request, "Membro adicionado à diretoria!")
            
        elif acao == 'deletar_membro':
            get_object_or_404(MembroDiretoria, id=request.POST.get('item_id'), torcida=minha_torcida).delete()
            messages.success(request, "Membro removido da diretoria.")

        elif acao == 'nova_regra':
            Regra.objects.create(
                torcida=minha_torcida,
                categoria=request.POST.get('categoria', 'Geral'),
                ordem=request.POST.get('ordem', 1),
                titulo=request.POST.get('titulo'),
                descricao=request.POST.get('descricao')
            )
            messages.success(request, "Nova regra de estatuto criada.")
        
        elif acao == 'deletar_regra':
            get_object_or_404(Regra, id=request.POST.get('item_id'), torcida=minha_torcida).delete()
            messages.success(request, "Regra removida.")

        # 4. MARCA, IDENTIDADE E GALERIA
        elif acao == 'salvar_identidade':
            minha_torcida.nome = request.POST.get('nome', minha_torcida.nome)
            minha_torcida.sigla = request.POST.get('sigla', minha_torcida.sigla)
            minha_torcida.lema = request.POST.get('lema', minha_torcida.lema)
            minha_torcida.historia = request.POST.get('historia', minha_torcida.historia)
            
            # ATUALIZAÇÃO DAS 4 CORES (Obrigatório estarem todas aqui!)
            minha_torcida.cor_primaria = request.POST.get('cor_primaria', minha_torcida.cor_primaria)
            minha_torcida.cor_secundaria = request.POST.get('cor_secundaria', minha_torcida.cor_secundaria)
            minha_torcida.cor_terciaria = request.POST.get('cor_terciaria', minha_torcida.cor_terciaria)
            minha_torcida.cor_fundo = request.POST.get('cor_fundo', minha_torcida.cor_fundo)
            
            nova_fundacao = request.POST.get('fundacao')
            if nova_fundacao:
                minha_torcida.fundacao = nova_fundacao
                
            if 'logo' in request.FILES:
                minha_torcida.logo = request.FILES['logo']
            if 'imagem_fundo' in request.FILES:
                minha_torcida.imagem_fundo = request.FILES['imagem_fundo']
                
            minha_torcida.save() # Grava tudo na base de dados
            messages.success(request, "Identidade do App atualizada com sucesso!")

        elif acao == 'nova_foto_galeria':
            FotoGaleria.objects.create(
                torcida=minha_torcida,
                titulo=request.POST.get('titulo'),
                legenda=request.POST.get('legenda', ''),
                imagem=request.FILES.get('imagem')
            )
            messages.success(request, "Foto adicionada à galeria!")

        # 5. CONQUISTAS E CANÇÕES
        elif acao == 'nova_conquista':
            ConquistaTorcida.objects.create(
                torcida=minha_torcida,
                titulo=request.POST.get('titulo'),
                descricao=request.POST.get('descricao', ''),
                icone=request.POST.get('icone', 'bi-trophy'),
                imagem=request.FILES.get('imagem')
            )
            messages.success(request, "Conquista registada no mural!")

        elif acao == 'nova_cancao':
            Cancao.objects.create(
                torcida=minha_torcida,
                titulo=request.POST.get('titulo'),
                descricao=request.POST.get('descricao', ''),
                letra=request.POST.get('letra', ''),
                url_youtube=request.POST.get('url_youtube', '')
            )
            messages.success(request, "Canção adicionada ao repertório!")

        # 6. ALIADAS
        elif acao == 'nova_aliada':
            Aliada.objects.create(
                torcida=minha_torcida,
                nome_organizada=request.POST.get('nome_organizada'),
                clube=request.POST.get('clube'),
                logo=request.FILES.get('logo'),
                status='aceito'
            )
            messages.success(request, "Torcida Aliada adicionada com sucesso!")

        # 7. LOJA E PRODUTOS
        elif acao == 'nova_categoria_loja':
            CategoriaProduto.objects.create(torcida=minha_torcida, nome=request.POST.get('nome'))
            messages.success(request, "Categoria de loja criada!")

        elif acao == 'novo_produto':
            cat_id = request.POST.get('categoria_id')
            categoria = CategoriaProduto.objects.get(id=cat_id) if cat_id else None
            
            preco_promo = request.POST.get('preco_promocional')
            
            Produto.objects.create(
                torcida=minha_torcida,
                nome=request.POST.get('nome'),
                descricao=request.POST.get('descricao', ''),
                categoria=categoria,
                preco=request.POST.get('preco'),
                preco_promocional=preco_promo if preco_promo else None,
                estoque=request.POST.get('estoque', 0),
                destaque=request.POST.get('destaque') == 'on',
                imagem=request.FILES.get('imagem')
            )
            messages.success(request, "Produto adicionado à loja oficial!")

        elif acao == 'deletar_produto':
            get_object_or_404(Produto, id=request.POST.get('item_id'), torcida=minha_torcida).delete()
            messages.success(request, "Produto removido da loja.")

        # Redireciona sempre para limpar o POST e evitar submissão duplicada ao atualizar a página
        return redirect('painel_moderador')


    # ==========================================
    # RENDERIZAÇÃO DA PÁGINA (GET)
    # ==========================================
    context = {
        'torcida': minha_torcida,
        # Sócios e KYC
        'membros_ativos': Perfil.objects.filter(torcida=minha_torcida, aprovado=True).select_related('user'),
        'membros_pendentes': Perfil.objects.filter(torcida=minha_torcida, aprovado=False).select_related('user'),
        'campos_custom': CampoPersonalizado.objects.filter(torcida=minha_torcida),
        
        # Eventos
        'eventos': Evento.objects.filter(torcida=minha_torcida).order_by('-data'),
        'caravanas': Caravana.objects.filter(torcida=minha_torcida).order_by('-saida_horario'),
        
        # Institucional e Marca
        'regras': Regra.objects.filter(torcida=minha_torcida).order_by('categoria', 'ordem'),
        'parceiros': Parceiro.objects.filter(torcida=minha_torcida),
        'diretoria': MembroDiretoria.objects.filter(torcida=minha_torcida).order_by('categoria__ordem', 'ordem'),
        'categorias_diretoria': CategoriaDiretoria.objects.filter(torcida=minha_torcida).order_by('ordem'),
        
        # Cultura e Identidade
        'galeria': FotoGaleria.objects.filter(torcida=minha_torcida).order_by('-data_publicacao'),
        'conquistas': ConquistaTorcida.objects.filter(torcida=minha_torcida).order_by('-id'),
        'cancoes': Cancao.objects.filter(torcida=minha_torcida),
        'aliadas': Aliada.objects.filter(torcida=minha_torcida),
        
        # Loja
        'produtos': Produto.objects.filter(torcida=minha_torcida).order_by('-id'),
        'categorias_loja': CategoriaProduto.objects.filter(torcida=minha_torcida),
    }
    
    return render(request, 'moderacao.html', context)