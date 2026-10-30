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
from django import forms
from gamification.models import PerfilGamificacao
from organizadas.models import Evento, Torcida, Noticia # Removido o Post daqui para evitar confusão
from social.models import Post as SocialPost
from django.contrib.auth.models import User
from organizadas.models import Parceiro
from organizadas.models import Publicidade
from django.db.models import Q, Count
from django.urls import reverse
from datetime import date, timedelta
from organizadas.models import Comentario
from accounts.models import Perfil
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .decorators import torcida_required
from .models import Perfil, Presenca, Conquista, Evento, CheckIn, PlanoSocio, Assinatura, Fatura, BeneficioTorcida, NIVEIS_PLANO, ORDEM_NIVEL
from .planos import planos_oficiais, beneficios_por_nivel, nivel_libera, ativar_assinatura, confirmar_pagamento_fatura
from django.conf import settings
from .times import TIMES_BRASIL, escudo_do_time
from . import noticias as noticias_svc
from .forms import CadastroForm, PerfilCompletoForm
from loja.models import Produto
from .models import Presenca, PresencaCaravana
import csv
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Importação do Utilitário PIX
try:
    from .efi_utils import gerar_cobranca_pix
except ImportError:
    # Caso falte alguma lib, não quebra tudo
    pass

# 1. Ecrã para escolher a torcida ANTES de logar
def escolher_torcida_publico(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    torcidas = Torcida.objects.all()
    return render(request, 'escolher_torcida_publico.html', {'torcidas': torcidas})

# 2. O Ecrã do PDF (Login/Registo personalizado da Torcida)
def entrada_torcida(request, torcida_id):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    torcida = get_object_or_404(Torcida, id=torcida_id)
    
    # Guardamos a torcida na sessão para sabermos qual ele escolheu 
    # quando ele for redirecionado para o registo ou login real
    request.session['torcida_pre_selecionada'] = torcida.id
    
    return render(request, 'pre_login_torcida.html', {'torcida': torcida})




@login_required
def viagens_view(request):
    perfil = request.user.perfil
    if not perfil.torcida or not perfil.aprovado:
        return redirect('dashboard')
        
    # FILTRO MÁGICO: Puxa SÓ as viagens da torcida dele
    caravanas = Caravana.objects.filter(torcida=perfil.torcida).order_by('saida_horario')
    return render(request, 'viagens.html', {'caravanas': caravanas})


# accounts/views.py

# SAT/accounts/views.py

# accounts/views.py

def cadastro(request):
    # 1. Verifica se existe uma torcida pré-selecionada na sessão (vinda do pre_login_torcida)
    torcida_id_sessao = request.session.get('torcida_pre_selecionada')
    torcida_pre = Torcida.objects.filter(id=torcida_id_sessao).first() if torcida_id_sessao else None

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            # Validação de senhas conforme o teu formulário personalizado
            if request.POST.get('senha') != request.POST.get('confirmar_senha'):
                messages.error(request, "As senhas não coincidem.")
                return render(request, 'cadastro.html', {'form': form, 'torcida': torcida_pre})

            # Cria o utilizador e o perfil base através do form.save()
            user = form.save()
            perfil = user.perfil
            
            # Se ele já veio de um link de torcida, vincula logo
            if torcida_pre:
                perfil.torcida = torcida_pre
                perfil.aprovado = torcida_pre.aprovacao_automatica
                perfil.save()
            
            # GUARDA O ID NA SESSÃO: Fundamental para a Etapa 2 saber quem é o utilizador
            request.session['novo_usuario_id'] = user.id
            request.session.modified = True 
            
            # Redireciona para a Etapa 2 SEM fazer login ainda
            return redirect('cadastro_etapa2') 
        else:
            # Exibe os erros reais do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    # Se for um erro num campo específico, exibe o nome do campo
                    nome_campo = form.fields[field].label if field in form.fields and form.fields[field].label else field.capitalize()
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f"{nome_campo}: {error}")
    else:
        form = CadastroForm()
        
    return render(request, 'cadastro.html', {'form': form, 'torcida': torcida_pre})


def cadastro_etapa2(request):
    # 1. Recupera o ID do utilizador que acabou de se registar na Etapa 1
    novo_usuario_id = request.session.get('novo_usuario_id')
    
    # Segurança: se não houver ID na sessão, volta para o início
    if not novo_usuario_id:
        return redirect('cadastro')
        
    from django.contrib.auth.models import User
    user_alvo = get_object_or_404(User, id=novo_usuario_id)
    perfil = user_alvo.perfil

    if request.method == 'POST':
        # Captura os dados enviados pelo teu HTML (cadastro_etapa2.html)
        time_escolhido = request.POST.get('time_coracao')
        torcida_escolhida_id = request.POST.get('torcida_id')

        # 1. Grava o Time do Coração
        if time_escolhido:
            perfil.time_coracao = time_escolhido

        # 2. Grava a Torcida e define como pendente para aprovação
        if torcida_escolhida_id:
            if torcida_escolhida_id == 'neutro':
                perfil.torcida = None
                perfil.aprovado = False
            else:
                from organizadas.models import Torcida
                nova_torcida = Torcida.objects.filter(id=torcida_escolhida_id).first()
                if nova_torcida:
                    perfil.torcida = nova_torcida
                    perfil.aprovado = nova_torcida.aprovacao_automatica 
        
        # SALVA TUDO NO BANCO DE DADOS ANTES DO LOGIN
        perfil.save()

        # 3. REALIZA O LOGIN FINAL (Agora com os dados guardados)
        from django.contrib.auth import login
        user_alvo.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user_alvo)
        
        # Limpa as variáveis temporárias da sessão
        if 'novo_usuario_id' in request.session:
            del request.session['novo_usuario_id']
        if 'torcida_pre_selecionada' in request.session:
            del request.session['torcida_pre_selecionada']

        messages.success(request, f"Bem-vindo, {user_alvo.first_name}! Perfil configurado com sucesso.")
        return redirect('dashboard')

    # Dados para carregar os escudos e a lista de torcidas no template
    from organizadas.models import Torcida
    torcidas_lista = Torcida.objects.all()
    
    times_brasil = [
        # ==========================================
        # SÉRIE A (2026)
        # ==========================================
        {"nome": "Athletico-PR", "escudo": "https://s.sde.globo.com/media/organizations/2019/09/09/Athletico-PR.svg"},
        {"nome": "Atlético-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/10/atletico-mg.svg"},
        {"nome": "Bahia", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/bahia.svg"},
        {"nome": "Botafogo", "escudo": "https://s.sde.globo.com/media/organizations/2019/02/04/botafogo-svg.svg"},
        {"nome": "Chapecoense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/chapecoense.svg"},
        {"nome": "Corinthians", "escudo": "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png"},
        {"nome": "Coritiba", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/coritiba.svg"},
        {"nome": "Cruzeiro", "escudo": "https://s.sde.globo.com/media/organizations/2021/02/13/cruzeiro_2021.svg"},
        {"nome": "Flamengo", "escudo": "https://s.sde.globo.com/media/organizations/2018/04/10/Flamengo-2018.svg"},
        {"nome": "Fluminense", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/fluminense.svg"},
        {"nome": "Grêmio", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/gremio.svg"},
        {"nome": "Internacional", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/internacional.svg"},
        {"nome": "Mirassol", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/ac/Mirassol_escudo_antigo.png"},
        {"nome": "Palmeiras", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/palmeiras.svg"},
        {"nome": "Red Bull Bragantino", "escudo": "https://s.sde.globo.com/media/organizations/2021/06/28/bragantino.svg"},
        {"nome": "Remo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Clube_do_Remo.svg/960px-Clube_do_Remo.svg.png"},
        {"nome": "Santos", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/12/santos.svg"},
        {"nome": "São Paulo", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sao-paulo.svg"},
        {"nome": "Vasco", "escudo": "https://s.sde.globo.com/media/organizations/2021/09/04/vasco_SVG.svg"},
        {"nome": "Vitória", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/vitoria.svg"},

        # ==========================================
        # SÉRIE B (2026)
        # ==========================================
        {"nome": "América-MG", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/america-mg.svg"},
        {"nome": "Athletic Club", "escudo": "https://s.sde.globo.com/media/organizations/2021/02/22/athletic-mg.svg"},
        {"nome": "Atlético-GO", "escudo": "https://s.sde.globo.com/media/organizations/2020/07/02/atletico-go-2020.svg"},
        {"nome": "Avaí", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/avai.svg"},
        {"nome": "Botafogo-SP", "escudo": "https://s.sde.globo.com/media/organizations/2019/02/28/botafogo-sp-svg.svg"},
        {"nome": "Ceará", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ceara.svg"},
        {"nome": "CRB", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/crb.svg"},
        {"nome": "Criciúma", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/criciuma.svg"},
        {"nome": "Cuiabá", "escudo": "https://s.sde.globo.com/media/organizations/2018/12/26/Cuiaba_EC.svg"},
        {"nome": "Fortaleza", "escudo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAJ6UlEQVR42u1aeXSU1RV/7X/9Q0+rtrY9FFqqeDyWtp5SFARrEWSpLCK0KPRUq7IoQpHdigeKQCIgSw4EErKHJECABMgCgbCE7AGykY3MZLJN9o2Qdea923vvZJIwDltmIMtwz7lnvu+bt93f+937ViF6UZKdX/s96hDhqILGb0dd58gAVKDmOJLBU1G3oK6hnkeFDl2JuhbVCXWCI9Ae7qAbHIUJL1oYLpOdx/zGkVzhCcvej9sywqGC39oOw6ejzu14XuRIAJxGfabb+yDUUIcw/tr20eKxPJbH0j+krOrmW+tdL8LqXdEt/U3X7I5uoba3GeUrPQZAV1o7SbzlC7FXdXApWYuq6fg1P2ssnu+m2jvk1VpJZ+3dMv9dykvRwoUkDYiJvtBqkKN6DEChvm6iGOMN/VXE697IAPWqbQCMNQFgNEqobWhSdQ3Nqra+SbW1GxV9b2ltV6Xl9fTM723tBmVOh8+Svt1qbuP3upsmpfz0vbmlXdXgMwpnpzLp3SglvxsMxtvqbG3rKLtbOaa8AA2NLZSuw3QFVIZdASgpr1NisDuIyX5KvOQhszUV8lpWiRRPuoGYE6jENH/VhIYmpxcp8TsPwDRKPO0GJ89nyT2BiUYh9isxyRfEnz1BiN1s4UffRErxC3eIjr/BQKXllCoh9kBVbSNblV9YpcTQA6Y6R3jK6MR8LGevEoPclXjDB8vZDwQKgS6ewnb8xI1A5bLsB0CHC+gr6pV44QAg8p0Ue37hUXUgOIUrFHODVGBYqszI1RNA3A2HItLkrxYES1OfgFEM94CUzGIjv6NQ2bO+OiW/3nuB01y/UcZ5q+tuMQAFxdVKDDuARrZ3Zzb/t/9IshwyP5ifU7NL1dAFwYrakJJRpB4eAKO9IPTcdXkxWSOx/VKM9lbnOnrvw40RyvVQksrMK6PegsqaRrlh30X1+dYo/h97ShIz4q/pzMZKMd6X0kvxsif7gBmAmu4AYJ0Rl3K4TqI5fS/U10ohXEFXWsNluQQkyL1BiWqrd6za4Rf3EAEY5wNrXc6rddhjbNDYLgD+9b8I2GcGYJo/iLf9lRjlBegmRmsAIHPUJvcYNlwMcYfSinqZoyn/PgPe9AFiCNVZVtXA35/66IhCg2VnsJsdoNKQBdT75Ir2BWDs7S6APdsVZbGyyJgcrvCfG8KVe3CyZACQtiTex69I8X6QsgbACwuD1bMfH4G/rwuTNFxRrLihq2QA6jHAURpdSQ2X1dTS1lknpROzAjqDbl1DkxR/8YYJK0Ll+OWhkjoJASSG2pcBpQTAs278a27MWpdo9fGmSFVRfVOKV7wg9koB94T4qRv/H34xR4opfl0AYBBNSNXJxlutioJfQmqhLC6rA2LCuOUhSluEPY7lHD2TIaPi8mRKRrEUIz3hcopWpufqKa2Rgij6vzErv5zAlsfPZhrFdH9VUl4PxRSoR3qp6AQTK+3KADRSjVxynH47ewPRV7O/OqXEB4dgo9slrjQT/ZjSkVBvj/kPP/OQOGrpccAgKTHay0mrTnT2Io0m474IUZhXzvk6DN5DnbzqBE1mjHPXhwPWAZNWhkJQeJoBmQbz8Ns7X56EGajoesrz2JXOTtnpH6/2H05WdgfgtjCM9DKPv5bfLYJ1t+/qvsvpiViWZfcg6JAzQV4LzA6gxRAs3RoFS/qJUltX7ToHGCxtWwvUN7aME3/zgwqM/EQuaSe6dtHW5BjW1FbBIAnivUB6HG7TktjtSHL6WFMgo+FJHovKlDQxMStF+ts1m1R11zBLvZCtsBxlpOlgUxO0njiu2iLCbNbWo4cVtLcp6igx1R8ORaSH27wngHY/OWPtSQg5e51BQIopHNqYXjbpHz0A1z5KVlfBTazGHtpyYD+PRDiswuJvz4DdNkbScvSLaUqKKzEwGCXPtmjoEx8e7rlO8IV2SQBUc+MbX/pRz3Uo5h81zDSdJurjTFRf2fC2XXeH9h1OyvzrFyHMAlzxSTHJr88AQPmNJUVSmWanSP20CLtvj2HZP566+gScjM5iEFbuPCcpyNgCgEEqaSsATH1vD6b+Fo8Y+MzZjtS3FFx2LqEFDgZDaDcYFS54oMeuYALANgb8FvP9aRBTP0tjon5phZ2pbymuQUnZNC0loXm9mOzXawAw9YsKTdSf7k9T5ciHvlNMq9EpOE/H4Y1BWLb9LK74Ah85AEx9DzemvpPn5YdLfUu5mlWyjFyhobGF9wBpxffArmBLDHgO0w9/gqmfrangMR+pP/WRnhnsCUzMnbrmBLMg7mqB5LnBIwKAqa8rMC15Zxx8NNS34grPTFwRCpExuQzC51vPPJgrEAAKHhgApr6bKxv/rVcsfOr0CKlvKSmZxSvIFRpvtfLuLAfE+3UFBuABGUDUHyaY+jnaStp2g5KK+mm9enzmEpBw493/nmIW0M4NLZ4eFgBMfW2+ifozmfqne/38ENvyszeXh0BUbB6DsMjptBLvB9kdAErT7OrCxm/ziaV6QPQVScooWk1rhVvNrXxSxAcg93KFB4kBz+P/g03Uzy1A6iPLSsp7mfqWsvtggpb280guJmnu7QoIgPE+AWDq5+eZqP/uQQgMTzvT547SsW0/f2NZCB1zMQifbIqkkxqbAWDqu+xg47/zjYOFfYn6lpKYVvileM2b9/FRFR2tiw9sAICo/7SJ+nm6KqZ+cXn99D59qWKnf7yOtq5JzifkS14w9RAApn5ejon6swIgMKwPUt+KK/ySzgIuJOWD+czQqivcAwCm/s5tbPwOv3hYuKUPU99S4lN162g7HUcEvhsgxltxhbsBMIy3uJj6NwqR+lOI+nUz+tX9IgxYRf/eGMEsOBuXJ2nBcr8A0LshO0t2HHwS9aP63QUrbPugV5ccg5gULYMwb3347a5wBwCY+tud2Phd/vGwAKlPOPRLib1asJ6O1nCdAHwgOt6nyxWsAdCN+vlF1XQzBIrL+hn1LWWbT1zJ/M3ci3Dmcq7kuwN3AICpfz3TRP1/BEJAWOrZfn/XEG0ZPGLxMUA2MAg4W1RiXpAJAOgCgKnv/I35xgcs2NyPqW8pMVe0G+kSQ1u7gW9z0SUGcgcLAOigTGmKa5j6RWV174iBJFu9YvW0b0dCR2p0+8sMQANRPyPdRP05SP1TA4D6Vlzh13/49CjtJDMIwxYGK94SqyiHppVL2fg9gYkwf3MkPf5ADES5lKzdTPf72g1GoAtPLW0GKasqFbQ2K20JUh+X0UX6upliIIuz5+XypduivneLhE6ZkPrnxEAXtHXoi4uCISm9sNP4vUGJ8MlApr6lXEjSONNIQPd4dKU1fKu7UF87UziSOHlcrqT7/C9/dhQOnkqNFo4mSPfnXsdlM11kQPmhcETBqfF3abn62b3Zhv8DlywbSls3TmwAAAAASUVORK5CYII="},
        {"nome": "Goiás", "escudo": "https://upload.wikimedia.org/wikipedia/commons/7/75/Goi%C3%A1s_Esporte_Clube_logo.svg"},
        {"nome": "Juventude", "escudo": "https://s.sde.globo.com/media/organizations/2021/04/29/Juventude-2021-01.svg"},
        {"nome": "Londrina", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/londrina.svg"},
        {"nome": "Náutico", "escudo": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Clube_N%C3%A1utico_Capibaribe_logo.svg"},
        {"nome": "Novorizontino", "escudo": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Gr%C3%AAmio_Novorizontino_logo.svg"},
        {"nome": "Operário-PR", "escudo": "data:image/png;base64,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"},
        {"nome": "Ponte Preta", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/ponte-preta.svg"},
        {"nome": "São Bernardo", "escudo": "https://upload.wikimedia.org/wikipedia/commons/9/96/S%C3%A3o_Bernardo_Futebol_Clube_logo.svg"},
        {"nome": "Sport", "escudo": "https://s.sde.globo.com/media/organizations/2018/03/11/sport.svg"},
        {"nome": "Vila Nova", "escudo": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Vila_Nova_Futebol_Clube_logo.svg"}
    ]

    context = {
        'perfil': perfil,
        'torcida': perfil.torcida, 
        'torcidas': torcidas_lista,
        'times_brasil': times_brasil,
    }
    return render(request, 'cadastro_etapa2.html', context)

from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class CadastroForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput())
    confirmar_senha = forms.CharField(widget=forms.PasswordInput())
    cpf = forms.CharField(max_length=14)
    telefone = forms.CharField(max_length=20) 
    nome = forms.CharField(max_length=150) 
    
    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        import re
        cpf_limpo = re.sub(r'[^0-9]', '', cpf)
        
        if len(cpf_limpo) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
            
        if cpf_limpo == cpf_limpo[0] * 11:
            raise forms.ValidationError("CPF inválido.")
            
        # Cálculo 1º dígito
        soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
        resto = (soma * 10) % 11
        if resto >= 10: resto = 0
        if resto != int(cpf_limpo[9]):
            raise forms.ValidationError("CPF inválido.")
            
        # Cálculo 2º dígito
        soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
        resto = (soma * 10) % 11
        if resto >= 10: resto = 0
        if resto != int(cpf_limpo[10]):
            raise forms.ValidationError("CPF inválido.")
            
        # Verificar se já existe (ignorando a máscara, buscando pelo cpf limpo)
        if Perfil.objects.filter(cpf=cpf_limpo).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")
            
        return cpf_limpo

    def save(self, commit=True):
        email_limpo = self.cleaned_data["email"]
        nome_completo = self.cleaned_data.get("nome", "")
        
        user = super().save(commit=False)
        user.email = email_limpo
        
        # 1. Separar o Nome Completo em Nome e Sobrenome
        partes_nome = nome_completo.split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''
        
        # 2. Gerar um username único a partir do nome
        import unicodedata
        import re
        import random
        # Tira acentos e caracteres especiais
        base = unicodedata.normalize('NFKD', nome_completo).encode('ASCII', 'ignore').decode('utf-8')
        base = re.sub(r'[^a-zA-Z0-9]', '', base).lower()
        if not base:
            base = "usuario"
            
        username = base
        # Garante que seja único
        while User.objects.filter(username=username).exists():
            username = f"{base}{random.randint(100, 9999)}"
            
        user.username = username
        
        user.set_password(self.cleaned_data["senha"])
        
        if commit:
            user.save()
            
            # 2. Guardar CPF e Telefone corretamente no Perfil
            Perfil.objects.update_or_create(
                user=user,
                defaults={
                    'cpf': self.cleaned_data.get('cpf'),
                    'telefone': self.cleaned_data.get('telefone'),
                    'whatsapp': self.cleaned_data.get('telefone'), # Preenche o whatsapp com o mesmo número
                }
            )
        return user


class PerfilCompletoForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = [
            'foto',
            'data_nascimento', 'rg_cnh', 
            'orgao_expedidor', 

            'cep', 
            'rua', 
            'numero', 
            'complemento', 
            'bairro',
            'cidade', 
            'uf',
            'doc_frente', 
            'doc_verso', 
            'doc_selfie',
            'vulgo', 
            'pelotao',
            'rede_social'
        ]
        widgets = {
            field: forms.TextInput(attrs={'class': 'form-control sat-input'}) 
            for field in fields if field not in ['data_nascimento', 'foto', 'foto_documento_frente', 'foto_documento_verso', 'verificacao_facial']
        }

@login_required
def dashboard(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    agora = timezone.now() 
    
    # 1 e 2. NOTÍCIAS (feeds do ge, em cache por 15 min; abrem no leitor interno do app)
    noticias_gerais_api = noticias_svc.noticias_gerais()[:10]
    noticias_time_api = noticias_svc.noticias_do_time(perfil.time_coracao)[:10]

    # 3. COMUNICADOS SAT (Base de Dados Local)
    noticias_sat = Noticia.objects.all().order_by('-data_publicacao')[:3]

    torcida_selecionada = perfil.torcida

    if torcida_selecionada:
        eventos = Evento.objects.filter(torcida=torcida_selecionada, data__gte=agora).order_by('data')[:3]
        # Trending topic: mostra os posts mais curtidos no geral
        posts_sociais = SocialPost.objects.select_related('autor_s', 'autor_s__perfil').annotate(num_curtidas=Count('curtidas')).order_by('-num_curtidas', '-data_criacao')[:10]
        parceiros = Parceiro.objects.filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
        publicidades = Publicidade.objects.filter(ativo=True, data_inicio__lte=agora, data_fim__gte=agora).filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))
        produtos_destaque = Produto.objects.filter(destaque=True).filter(Q(torcida=torcida_selecionada) | Q(torcida__isnull=True))[:4]
    else:
        eventos = Evento.objects.filter(data__gte=agora).order_by('data')[:3]
        posts_sociais = SocialPost.objects.select_related('autor_s', 'autor_s__perfil').annotate(num_curtidas=Count('curtidas')).order_by('-num_curtidas', '-data_criacao')[:10]
        parceiros = Parceiro.objects.filter(torcida__isnull=True)
        publicidades = Publicidade.objects.filter(ativo=True, data_inicio__lte=agora, data_fim__gte=agora, torcida__isnull=True)
        produtos_destaque = Produto.objects.filter(destaque=True)[:4]

    context = {
        'produtos_destaque': produtos_destaque,
        'proximos_eventos': eventos,
        'perfil': perfil,
        'perfil_game': perfil_game,
        'xp_atual': perfil_game.xp_total or 0,
        'torcida': torcida_selecionada, 
        
        # --- AS TRÊS VARIÁVEIS EXATAS PARA O HTML ---
        'noticias_time_api': noticias_time_api, 
        'escudo_time': escudo_do_time(perfil.time_coracao),
        'noticias_gerais_api': noticias_gerais_api,
        'noticias_sat': noticias_sat,
        
        'posts_sociais': posts_sociais,
        'parceiros': parceiros,
        'publicidades': publicidades,
    }
    # Cartão de sócio com frente e verso (toque vira para o verso)
    context.update(contexto_carteirinha(perfil, request))

    return render(request, 'dashboard.html', context)



# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py
import requests
from django.shortcuts import render

# accounts/views.py

# accounts/views.py

@login_required
def noticias(request):
    perfil = request.user.perfil
    do_time = noticias_svc.noticias_do_time(perfil.time_coracao)
    ids = {n['id'] for n in do_time}
    gerais = [n for n in noticias_svc.noticias_gerais() if n['id'] not in ids]
    return render(request, 'noticias.html', {
        'noticias': do_time + gerais,
        'time': perfil.time_coracao if do_time else None,
        'escudo_time': escudo_do_time(perfil.time_coracao),
    })


@login_required
def noticia_ler(request, noticia_id):
    """Leitor interno: o usuário lê o resumo sem sair do app."""
    noticia = noticias_svc.obter(noticia_id)
    if not noticia:
        messages.info(request, 'Essa notícia não está mais disponível. Veja as mais recentes.')
        return redirect('noticias')

    perfil = request.user.perfil
    if noticia['time']:
        relacionadas = noticias_svc.noticias_do_time(noticia['time'])
    else:
        relacionadas = noticias_svc.noticias_do_time(perfil.time_coracao) or noticias_svc.noticias_gerais()
    return render(request, 'noticia_ler.html', {
        'noticia': noticia,
        'relacionadas': [n for n in relacionadas if n['id'] != noticia_id][:6],
    })


def ads_txt(request):
    """/ads.txt exigido pelas redes de anúncio (MGID) para aprovar o site."""
    linhas = [l.strip() for l in settings.ADS_TXT.split('|') if l.strip()]
    return HttpResponse('\n'.join(linhas) + '\n', content_type='text/plain')

# accounts/views.py

@login_required
def seja_socio(request):
    # Força a atualização do objeto perfil para evitar cache de estado antigo
    perfil = get_object_or_404(Perfil, user=request.user)
    
    if request.method == 'POST':
        time_coracao = request.POST.get('time_coracao')
        torcida_id = request.POST.get('torcida_id')
        
        # 1. Atualiza o Time do Coração
        if time_coracao:
            perfil.time_coracao = time_coracao
            
        # 2. Atualiza ou Vincula Torcida
        if torcida_id:
            if torcida_id == "neutro":
                perfil.torcida = None
                perfil.aprovado = False
            else:
                try:
                    nova_torcida = Torcida.objects.get(id=torcida_id)
                    # Se ele trocar de torcida ou entrar numa nova, volta para pendente
                    if perfil.torcida != nova_torcida:
                        perfil.torcida = nova_torcida
                        perfil.aprovado = nova_torcida.aprovacao_automatica
                except (Torcida.DoesNotExist, ValueError):
                    pass
                    
        perfil.save()
        messages.success(request, 'Perfil e preferências atualizados com sucesso!')
        return redirect('seja_socio')

    # Planos oficiais SAT (Grátis, Bronze, Prata, Ouro) + benefícios extras da torcida
    planos = planos_oficiais()
    niveis = beneficios_por_nivel(perfil.torcida)
    torcidas = Torcida.objects.all()

    times_brasil = TIMES_BRASIL

    context = {
        'perfil': perfil,
        'torcidas': torcidas,
        'times_brasil': times_brasil,
        'planos': planos,
        'niveis': niveis,
        'nivel_atual': perfil.nivel_plano,
        'assinatura_vigente': perfil.assinatura_vigente,
    }
    return render(request, 'seja_socio.html', context)


@login_required
def torcidas(request):
    perfil = request.user.perfil
    
    # 1. Correção do nome da URL (de 'hub_organizadas' para 'hub')
    if perfil.torcida and perfil.aprovado:
        return redirect('hub')
    
    # Carrega a lista de torcidas SEMPRE, para não travar a tela
    lista_de_torcidas = Torcida.objects.all()
    
    # 2. Se está pendente, enviamos a lista junto para permitir que ele mude de ideia
    if perfil.torcida and not perfil.aprovado:
        return render(request, 'torcidas.html', {
            'status': 'pendente', 
            'torcida': perfil.torcida,
            'torcidas': lista_de_torcidas # Faltava isso aqui!
        })
    
    # 3. Se não tem torcida nenhuma
    return render(request, 'torcidas.html', {
        'torcidas': lista_de_torcidas,
        'neutro': True 
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
def area_hub(request):
    perfil = request.user.perfil
    
    # BLOQUEIO ABSOLUTO: Se não tiver torcida ou NÃO estiver aprovado, volta para a página de torcidas!
    if not perfil.torcida or not perfil.aprovado:
        messages.warning(request, "Acesso restrito. Escolha uma torcida ou aguarde a aprovação da diretoria.")
        return redirect('torcidas')
        
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    context = {
        'perfil': perfil,
        'perfil_game': perfil_game,
        'torcida': perfil.torcida,
    }
    context.update(contexto_carteirinha(perfil, request))  # cartão de sócio com frente e verso
    return render(request, 'hub.html', context)


def socio_view(request):
    # Explica os planos e benefícios de ser sócio
    return render(request, 'seja_socio.html')

def contexto_carteirinha(perfil, request=None):
    """Dados do cartão de sócio (templates/includes/cartao_socio.html), usados na Carteirinha e no Início."""
    from gamification.models import BadgeUsuario

    # QR Code abre a página de validação da matrícula (funciona com a câmera do celular)
    url_validacao = request.build_absolute_uri(reverse('validar_matricula', args=[perfil.matricula])) if request else f"SAT:{perfil.matricula}"
    img = qrcode.make(url_validacao)
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return {
        'perfil': perfil,
        'qr_code': base64.b64encode(buffer.getvalue()).decode(),
        'badges_conquistadas': BadgeUsuario.objects.filter(user=perfil.user).select_related('badge').order_by('-data_ganha'),
        'passagens': perfil.passagens_torcida.select_related('torcida'),
        'nivel_plano': perfil.nivel_plano,
        'assinatura_vigente': perfil.assinatura_vigente,
    }


@torcida_required
@login_required
def carteirinha(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    from gamification.models import PerfilGamificacao
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)

    context = contexto_carteirinha(perfil, request)
    context.update({
        'perfil_game': perfil_game,
        'torcida': perfil.torcida,
        # Planos acima do atual, para mostrar como a carteirinha fica em cada um
        'niveis_preview': [(n, nome) for n, nome in NIVEIS_PLANO if ORDEM_NIVEL[n] > ORDEM_NIVEL[perfil.nivel_plano]],
    })
    return render(request, 'carteirinha.html', context)

@login_required
def confirmar_presenca(request, evento_id):
    # IMPORTAÇÃO LOCAL: Força o sistema a guardar a vaga no Evento correto
    from organizadas.models import Evento as OrgEvento
    from accounts.models import CheckIn
    
    if request.method == "POST":
        evento = get_object_or_404(OrgEvento, id=evento_id)
        
        # Bloqueia duplicações (caso o utilizador clique duas vezes rápido)
        if not CheckIn.objects.filter(user=request.user, evento=evento).exists():
            
            # Captura dados opcionais
            lat = request.POST.get('latitude', 0.0)
            lon = request.POST.get('longitude', 0.0)
            foto = request.FILES.get('foto')

            # Salva a presença ligada 100% ao evento real
            CheckIn.objects.create(
                user=request.user,
                evento=evento,
                latitude=float(lat) if lat else 0.0,
                longitude=float(lon) if lon else 0.0,
                foto=foto,
                validado=True
            )
            from gamification.xp import xp_participacao_evento
            ganho = xp_participacao_evento(request.user, evento)
            messages.success(request, f"Presença confirmada no {evento.titulo}!" + (f" +{ganho} EXP" if ganho else ""))
        
        # ATUALIZADO: Em vez de mandar para o Dashboard, devolve para o evento
        # para que o utilizador veja logo a tela verde de sucesso e a barra atualizada!
        return redirect('detalhe_evento', evento_id=evento.id)
    
    return redirect('detalhe_evento', evento_id=evento_id)

@login_required
def detalhe_evento(request, evento_id):
    # IMPORTAÇÃO LOCAL: Força o sistema a puxar o Evento correto da Torcida
    from organizadas.models import Evento as OrgEvento
    from accounts.models import CheckIn
    
    evento = get_object_or_404(OrgEvento, id=evento_id)
    
    # ATUALIZADO: Agora procura corretamente na tabela de CheckIn
    confirmado = CheckIn.objects.filter(user=request.user, evento=evento).exists()
    
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    
    cor_tema = "#ff6b00"
    if perfil_game.nivel:
        cor_tema = perfil_game.nivel.cor_tema

    context = {
        'evento': evento,
        'confirmado': confirmado,
    }
    return render(request, 'detalhe_evento.html', context)

@login_required
def beneficios_view(request):
    perfil = request.user.perfil
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    nivel_atual = perfil.nivel_plano
    niveis = beneficios_por_nivel(perfil.torcida)
    for n in niveis:
        n['liberado'] = nivel_libera(nivel_atual, n['nivel'])

    context = {
        'niveis': niveis,
        'nivel_atual': nivel_atual,
        'assinatura_vigente': perfil.assinatura_vigente,
        'clube_ben_url': getattr(settings, 'CLUBE_BEN_PORTAL_URL', ''),
        'xp_atual': perfil_game.xp_total,
    }
    return render(request, 'beneficios.html', context)


@login_required
def perfil_view(request):
    """Meu Perfil = a mesma tela do Perfil Público, com carteirinha e configurações da conta."""
    from social.views import render_perfil
    return render_perfil(request, request.user)

@login_required
def ranking_torcida(request):
    from gamification.models import PerfilGamificacao
    # Busca os top 10 torcedores com mais XP, trazendo o usuário e o nível junto

# ==========================================
# VIEWS DO EFÍ BANK (PIX)
# ==========================================

@login_required
def pagar_fatura_pix(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id, assinatura__perfil=request.user.perfil)
    
    # Se a fatura não tem um txid (nunca foi gerado PIX ou expirou), gera agora
    if not fatura.txid:
        resultado = gerar_cobranca_pix(fatura)
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('financeiro')
            
    return render(request, 'checkout_pix.html', {'fatura': fatura})

@csrf_exempt
def webhook_efi(request):
    """
    Endpoint que a Efí chama quando um PIX é pago.
    Precisa retornar 200 OK rapidamente.
    """
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            # O payload da Efí envia uma lista de "pix" recebidos
            if 'pix' in body:
                for pix in body['pix']:
                    txid = pix.get('txid')
                    
                    if txid:
                        # Busca a fatura com esse txid
                        fatura = Fatura.objects.filter(txid=txid, status='pendente').first()
                        if fatura:
                            # Marca como pago e ativa a assinatura se necessário
                            fatura.status = 'pago'
                            fatura.metodo_pagamento = 'PIX'
                            fatura.data_pagamento = timezone.now()
                            fatura.save()
                            
                            if not fatura.assinatura.ativa:
                                fatura.assinatura.ativa = True
                                fatura.assinatura.save()
                                
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            print("Erro no webhook Efí:", e)
            return JsonResponse({'status': 'erro'}, status=400)
            
    return JsonResponse({'status': 'método não permitido'}, status=405)

@login_required
def financeiro(request):
    perfil = request.user.perfil
    
    # Pega todas as faturas do usuário
    faturas = Fatura.objects.filter(assinatura__perfil=perfil).order_by('-data_vencimento')
    faturas_pendentes = faturas.filter(status='pendente')
    faturas_pagas = faturas.filter(status='pago')
    
    # Verifica a fatura atrasada mais urgente
    hoje = timezone.now().date()
    fatura_atrasada = faturas_pendentes.filter(data_vencimento__lt=hoje).first()
    
    # Se não tem atrasada, pega a próxima a vencer
    proxima_fatura = fatura_atrasada if fatura_atrasada else faturas_pendentes.first()
    
    # Assinatura ativa (se tiver)
    assinatura_ativa = Assinatura.objects.filter(perfil=perfil, ativa=True).first()
    
    context = {
        'faturas': faturas,
        'proxima_fatura': proxima_fatura,
        'assinatura_ativa': assinatura_ativa,
    }
    return render(request, 'financeiro.html', context)
    lideres = PerfilGamificacao.objects.select_related('user', 'nivel').order_by('-xp_total')[:10]
    
    context = {
        'lideres': lideres,
        'cor_tema': "#D37129" # Laranja oficial da SAT
    }
    return render(request, 'ranking.html', context)


@login_required
def games_hub(request):
    perfil_game, _ = PerfilGamificacao.objects.get_or_create(user=request.user)
    return render(request, 'games_menu.html', {
        'perfil_game': perfil_game,
        'progresso': perfil_game.progresso_nivel()
    })


# accounts/views.py

@login_required
def moderacao_torcida(request):
    perfil_moderador = request.user.perfil
    
    # Segurança: Apenas staff com torcida vinculada pode moderar
    if not request.user.is_staff or not perfil_moderador.torcida:
        messages.error(request, "Não tem permissão para aceder à área de moderação.")
        return redirect('dashboard')
        
    torcida_mod = perfil_moderador.torcida

    # --- PROCESSAMENTO DE AÇÕES (POST) ---
    if request.method == 'POST':
        acao = request.POST.get('acao')
        perfil_id = request.POST.get('perfil_id')
        
        # Para ações que envolvem um sócio específico
        if perfil_id:
            perfil_alvo = get_object_or_404(Perfil, id=perfil_id, torcida=torcida_mod)
            user_alvo = perfil_alvo.user

            if acao == 'aprovar_socio':
                perfil_alvo.aprovado = True
                perfil_alvo.save()
                messages.success(request, f"O torcedor {user_alvo.first_name or user_alvo.username} foi aprovado!")

            elif acao == 'rejeitar_socio':
                # Em vez de apagar a conta inteira, apenas remove o pedido da torcida
                perfil_alvo.torcida = None
                perfil_alvo.aprovado = False
                perfil_alvo.save()
                messages.warning(request, "Solicitação rejeitada. O utilizador voltou a ser membro neutro da SAT.")

            elif acao == 'editar_socio':
                # 1. Atualiza Dados do User (Django Nativo)
                user_alvo.first_name = request.POST.get('first_name', user_alvo.first_name)
                user_alvo.email = request.POST.get('email', user_alvo.email)
                user_alvo.save()

                # 2. Atualiza Dados Pessoais do Perfil
                perfil_alvo.cpf = request.POST.get('cpf') or None
                perfil_alvo.rg_cnh = request.POST.get('rg_cnh', perfil_alvo.rg_cnh)
                perfil_alvo.orgao_expedidor = request.POST.get('orgao_expedidor', perfil_alvo.orgao_expedidor)
                perfil_alvo.whatsapp = request.POST.get('whatsapp', perfil_alvo.whatsapp)
                
                data_nasc = request.POST.get('data_nascimento')
                if data_nasc:
                    perfil_alvo.data_nascimento = data_nasc

                # 3. Atualiza Endereço
                perfil_alvo.cep = request.POST.get('cep', perfil_alvo.cep)
                perfil_alvo.rua = request.POST.get('rua', perfil_alvo.rua)
                perfil_alvo.numero = request.POST.get('numero', perfil_alvo.numero)
                perfil_alvo.complemento = request.POST.get('complemento', perfil_alvo.complemento)
                perfil_alvo.bairro = request.POST.get('bairro', perfil_alvo.bairro)
                perfil_alvo.cidade = request.POST.get('cidade', perfil_alvo.cidade)
                perfil_alvo.uf = request.POST.get('uf', perfil_alvo.uf)

                # 4. Atualiza Identidade na Torcida
                perfil_alvo.vulgo = request.POST.get('vulgo', perfil_alvo.vulgo)
                perfil_alvo.pelotao = request.POST.get('pelotao', perfil_alvo.pelotao)
                perfil_alvo.rede_social = request.POST.get('rede_social', perfil_alvo.rede_social)
                
                perfil_alvo.save()
                messages.success(request, f"Perfil de {user_alvo.first_name} atualizado com sucesso!")
                
            elif acao == 'remover_socio':
                # Nova Lógica de Banimento: Remove da torcida, mas mantém o Perfil SAT
                perfil_alvo.torcida = None
                perfil_alvo.aprovado = False
                
                # Opcional: Você também pode limpar dados específicos da torcida aqui, se quiser
                perfil_alvo.vulgo = ""
                perfil_alvo.pelotao = ""
                
                perfil_alvo.save()
                messages.error(request, f"O sócio {user_alvo.first_name} foi banido da torcida e agora é apenas membro SAT.")

        return redirect('moderacao_torcida')

    membros_pendentes = Perfil.objects.filter(torcida=torcida_mod, aprovado=False).exclude(user=request.user)
    membros_ativos = Perfil.objects.filter(torcida=torcida_mod, aprovado=True)
    
    # IMPORTAÇÃO LOCAL CORRIGIDA (Forçamos o OrgEvento e adicionamos as Caravanas)
    from organizadas.models import Parceiro, Publicidade, Regra, CategoriaDiretoria, FotoGaleria, ConquistaTorcida, Evento as OrgEvento, Caravana as OrgCaravana
    from accounts.models import Cancao, CampoPersonalizado
    from loja.models import Produto, CategoriaProduto
    context = {
        'torcida': torcida_mod,
        'membros_pendentes': membros_pendentes,
        'membros_ativos': membros_ativos,
        
        # CORREÇÃO PRINCIPAL: Usar o OrgEvento para puxar os check-ins verdadeiros
        'eventos': OrgEvento.objects.filter(torcida=torcida_mod).order_by('-data'), 
        'caravanas': OrgCaravana.objects.filter(torcida=torcida_mod).order_by('-saida_horario'),
        
        # Restantes dados...
        'parceiros': Parceiro.objects.filter(torcida=torcida_mod),
        'publicidades': Publicidade.objects.filter(torcida=torcida_mod),
        'campos_kyc': CampoPersonalizado.objects.filter(torcida=torcida_mod),
        'cancoes': Cancao.objects.filter(torcida=torcida_mod),
        'galeria': FotoGaleria.objects.filter(torcida=torcida_mod),
        'regras': Regra.objects.filter(torcida=torcida_mod),
        'conquistas': ConquistaTorcida.objects.filter(torcida=torcida_mod),
        'categorias_diretoria': CategoriaDiretoria.objects.filter(torcida=torcida_mod),
        
        'produtos': Produto.objects.filter(torcida=torcida_mod),
        'categorias_loja': CategoriaProduto.objects.filter(torcida=torcida_mod),
    }
    
    return render(request, 'moderacao.html', context)

@login_required
def aprovar_membro(request, perfil_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    perfil_moderador = request.user.perfil
    perfil_alvo = get_object_or_404(Perfil, id=perfil_id)
    
    # Validação de segurança: claque do alvo deve ser igual à do moderador
    if perfil_alvo.torcida == perfil_moderador.torcida:
        perfil_alvo.aprovado = True
        perfil_alvo.save()
        messages.success(request, f"O torcedor {perfil_alvo.user.username} foi aprovado!")
    else:
        messages.error(request, "Ação não permitida: Este utilizador pertence a outra claque.")
        
    return redirect('moderacao_torcida')


@login_required
@torcida_required
def cartao_socio_view(request):
    # Esta view renderiza especificamente o cartão estilo banco
    return render(request, 'torcida/cartao_socio.html')

@login_required
def area_torcida(request):
    perfil = request.user.perfil
    lista_de_torcidas = Torcida.objects.all()

    if perfil.torcida and not perfil.aprovado:
        return render(request, 'torcidas.html', {
            'status': 'pendente',
            'torcidas': lista_de_torcidas # Garantindo que a lista apareça aqui também
        })
        
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

class CustomLoginView(LoginView):
    template_name = 'login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Apanha o ID da torcida que foi guardado na sessão
        torcida_id = self.request.session.get('torcida_pre_selecionada')
        if torcida_id:
            context['torcida'] = Torcida.objects.filter(id=torcida_id).first()
        return context

@login_required
def curtir_post(request, post_id):
    # Procura o post (certifique-se que o nome do modelo está correto, ex: Post ou PostTorcida)
    post = get_object_or_404(PostTorcida, id=post_id)
    curtida, created = Curtida.objects.get_or_create(post=post, usuario=request.user)
    
    if created:
        # Lógica de XP: O autor do post ganha 1 XP
        perfil_autor, _ = PerfilGamificacao.objects.get_or_create(user=post.autor)
        perfil_autor.xp_total += 1
        perfil_autor.save()
        liked = True # Avisa que foi curtido
    else:
        # Se clicar de novo, remove a curtida
        curtida.delete()
        perfil_autor = PerfilGamificacao.objects.get(user=post.autor)
        if perfil_autor.xp_total > 0:
            perfil_autor.xp_total -= 1
            perfil_autor.save()
        liked = False # Avisa que foi descurtido

    # SE FOR UM PEDIDO DO NOSSO JAVASCRIPT (AJAX), DEVOLVE APENAS OS DADOS EM JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
        return JsonResponse({'liked': liked, 'likes_count': post.curtidas.count()})
            
    # Fallback de segurança (caso o utilizador acesse o link diretamente pelo navegador)
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)


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

        # 5. Publicação automática no Feed [cite: 77, 95, 97]
        PostTorcida.objects.create(
            autor=request.user,
            torcida=request.user.perfil.torcida,
            texto=f"Presença confirmada no evento: {evento.titulo}! 🏟️🔥"
        )

        messages.success(request, "Check-in realizado! EXP de participação creditado.")
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


def pre_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Se ele voltar ao menu principal, "esquece" a torcida pre-selecionada
    if 'torcida_pre_selecionada' in request.session:
        del request.session['torcida_pre_selecionada']
        
    return render(request, 'pre_login.html')

@login_required
def hub_socio(request):
    perfil = request.user.perfil
    
    # Sócio = qualquer plano pago vigente (Bronze, Prata ou Ouro)
    if perfil.nivel_plano != 'gratis':
        return redirect('beneficios') # Vai para a página de benefícios
    else:
        return redirect('seja_socio')
    

@login_required
def adicionar_comentario(request, post_id):
    if request.method == "POST":
        texto = request.POST.get('comentario')
        
        if texto:
            from organizadas.models import Post # Importação local para evitar erros
            post = get_object_or_404(Post, id=post_id)
            
            # Cria e guarda o comentário
            Comentario.objects.create(
                post=post,
                autor=request.user,
                texto=texto
            )
            
    # Redireciona de volta para a exata página onde o utilizador estava (o Mural)
    url_anterior = request.META.get('HTTP_REFERER', '/')
    return redirect(url_anterior)

@login_required
def editar_perfil(request):
    usuario = request.user
    perfil = usuario.perfil 

    if request.method == 'POST':
        try:
            # 1. ATUALIZANDO DADOS DO USER (Nativo do Django)
            nome_completo = request.POST.get('nome_completo', '')
            if nome_completo:
                partes_nome = nome_completo.split(' ', 1)
                usuario.first_name = partes_nome[0]
                usuario.last_name = partes_nome[1] if len(partes_nome) > 1 else ''
            
            usuario.email = request.POST.get('email', usuario.email)
            usuario.save()

            # 2. ATUALIZANDO DADOS TEXTUAIS DO PERFIL
            perfil.cpf = request.POST.get('cpf') or None
            
            data_nascimento = request.POST.get('data_nascimento')
            if data_nascimento:
                perfil.data_nascimento = data_nascimento

            perfil.rg_cnh = request.POST.get('rg_cnh', perfil.rg_cnh)
            
            perfil.orgao_expedidor = request.POST.get('orgao_expedidor', perfil.orgao_expedidor) 
            
            perfil.whatsapp = request.POST.get('whatsapp', perfil.whatsapp)
            perfil.nome_mae = request.POST.get('nome_mae', perfil.nome_mae)
            perfil.nome_pai = request.POST.get('nome_pai', perfil.nome_pai)

            perfil.cep = request.POST.get('cep', perfil.cep)
            perfil.rua = request.POST.get('rua', perfil.rua)
            perfil.numero = request.POST.get('numero', perfil.numero)
            perfil.complemento = request.POST.get('complemento', perfil.complemento)
            perfil.bairro = request.POST.get('bairro', perfil.bairro)
            perfil.cidade = request.POST.get('cidade', perfil.cidade)
            perfil.uf = request.POST.get('uf', perfil.uf)

            # Dados da Torcida 
            perfil.vulgo = request.POST.get('vulgo', perfil.vulgo)
            perfil.pelotao = request.POST.get('pelotao', perfil.pelotao)

            # 3. TRATANDO OS UPLOADS DE IMAGEM (request.FILES)
            if 'foto' in request.FILES:
                perfil.foto = request.FILES['foto']

            docs_novos = False
            for campo in ('doc_frente', 'doc_verso', 'doc_selfie'):
                if campo in request.FILES:
                    setattr(perfil, campo, request.FILES[campo])
                    docs_novos = True

            # Verificação: documento novo (ou trocado) com os 3 completos -> volta para análise da moderação
            if docs_novos and perfil.docs_completos:
                perfil.docs_status = 'em_analise'
                perfil.docs_motivo = ''

            # 4. SALVANDO TUDO
            perfil.save()

            if docs_novos and perfil.docs_status == 'em_analise':
                from social.notificacoes import notificar_muitos
                moderadores = User.objects.filter(is_superuser=True)
                if perfil.torcida_id:
                    moderadores = User.objects.filter(
                        Q(is_superuser=True) | Q(is_staff=True, perfil__torcida=perfil.torcida) |
                        Q(perfil__cargo_especial='presidente', perfil__torcida=perfil.torcida)
                    ).distinct()
                notificar_muitos(moderadores, 'moderacao',
                                 f'Documentos de {usuario.get_full_name() or usuario.username} aguardando verificação.',
                                 ator=usuario, link=reverse('moderacao_torcida') + '#documentos')
                messages.success(request, 'Perfil atualizado! Seus documentos foram enviados para verificação.')
            elif docs_novos:
                messages.success(request, 'Perfil atualizado! Envie os 3 documentos (frente, verso e selfie) para a verificação.')
            else:
                messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil')

        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao atualizar o perfil: {str(e)}')
            return redirect('editar_perfil')

    return render(request, 'editar_perfil.html')

@login_required
def meus_pedidos(request):
    try:
        from loja.models import Pedido
        # CORREÇÃO 1: Mudar de 'cliente' para 'usuario'
        # CORREÇÃO 2: Adicionar .prefetch_related('itens') para carregar a quantidade de itens rápido
        pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('itens').order_by('-data_pedido')
    except Exception as e:
        print(f"Erro ao carregar pedidos: {e}")
        pedidos = [] 
        
    # CORREÇÃO 3: O template está na raiz da pasta templates, então tiramos o 'loja/'
    return render(request, 'meus_pedidos.html', {'pedidos': pedidos})


@login_required
def detalhe_pedido(request, pedido_id):
    from loja.models import Pedido
    pedido = get_object_or_404(Pedido.objects.prefetch_related('itens__produto'), id=pedido_id, usuario=request.user)
    return render(request, 'pedido_detalhe.html', {'pedido': pedido})

@login_required
def seguranca(request):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from .dispositivos import dispositivos_ativos, encerrar

    if request.method == 'POST':
        acao = request.POST.get('acao', 'senha')

        if acao == 'senha':
            senha_atual = request.POST.get('senha_atual')
            nova_senha = request.POST.get('nova_senha', '')
            confirmar_senha = request.POST.get('confirmar_senha')
            if not request.user.check_password(senha_atual):
                messages.error(request, 'A senha atual está incorreta.')
            elif nova_senha != confirmar_senha:
                messages.error(request, 'As novas senhas não coincidem.')
            else:
                try:
                    validate_password(nova_senha, request.user)
                except ValidationError as e:
                    messages.error(request, ' '.join(e.messages))
                else:
                    request.user.set_password(nova_senha)
                    request.user.save()
                    update_session_auth_hash(request, request.user)  # não desloga este aparelho
                    messages.success(request, 'Senha atualizada com sucesso!')
                    return redirect('seguranca')

        elif acao == 'encerrar_dispositivo':
            chave = request.POST.get('session_key', '')
            if chave and chave != request.session.session_key:
                encerrar(request.user, [chave])
                messages.success(request, 'Aparelho desconectado.')

        elif acao == 'encerrar_outros':
            outros = [d.session_key for d in dispositivos_ativos(request.user) if d.session_key != request.session.session_key]
            encerrar(request.user, outros)
            messages.success(request, f'{len(outros)} aparelho(s) desconectado(s).')
        return redirect('seguranca')

    return render(request, 'seguranca.html', {
        'dispositivos': dispositivos_ativos(request.user),
        'sessao_atual': request.session.session_key,
    })


def politica_privacidade(request):
    return render(request, 'politica_privacidade.html')


@login_required
def deletar_conta(request):
    """
    Exclui a conta (exige a senha). Os dados pessoais e as publicações são apagados;
    pedidos e faturas ficam guardados SEM identificação, porque a lei obriga a manter registros fiscais.
    """
    if request.method == 'POST':
        if request.POST.get('confirmacao', '').strip().upper() != 'EXCLUIR':
            messages.error(request, 'Digite EXCLUIR para confirmar.')
        elif not request.user.check_password(request.POST.get('senha', '')):
            messages.error(request, 'Senha incorreta.')
        else:
            from social.models import Post
            user = request.user
            perfil = user.perfil
            Post.objects.filter(autor_s=user).delete()
            for campo in ('foto', 'doc_frente', 'doc_verso', 'doc_selfie'):
                arquivo = getattr(perfil, campo)
                if arquivo:
                    arquivo.delete(save=False)
            Perfil.objects.filter(id=perfil.id).update(
                cpf=None, whatsapp='', telefone='', data_nascimento=None, nome_mae='', nome_pai='', rg_cnh='',
                orgao_expedidor='', cep='', rua='', numero='', complemento='', bairro='', cidade='', uf='',
                vulgo='', pelotao='', rede_social='', torcida=None, aprovado=False, docs_status='pendente',
                foto=None, doc_frente=None, doc_verso=None, doc_selfie=None,
            )
            perfil.seguidores.clear()
            user.username = f'excluido_{user.id}'
            user.first_name, user.last_name, user.email = 'Conta', 'excluída', ''
            user.is_active = False
            user.set_unusable_password()
            user.save()
            from .dispositivos import dispositivos_ativos, encerrar
            encerrar(user, [d.session_key for d in dispositivos_ativos(user)])
            logout(request)
            messages.success(request, 'Sua conta foi excluída.')
            return redirect('pre_login')
    return render(request, 'deletar_conta.html')

@login_required
def admin_editar_utilizador(request, perfil_id):
    # Trava de segurança: Apenas superusuários (Admin Master) podem acessar
    if not request.user.is_superuser:
        messages.error(request, "Acesso negado. Área restrita à administração geral.")
        return redirect('dashboard')
        
    # Busca o perfil alvo
    perfil = get_object_or_404(Perfil, id=perfil_id)
    
    if request.method == 'POST':
        user_alvo = perfil.user
        user_alvo.first_name = request.POST.get('first_name', user_alvo.first_name)
        user_alvo.email = request.POST.get('email', user_alvo.email)
        user_alvo.save()
        
        # O "or None" evita o erro de UNIQUE constraint caso o campo venha vazio
        perfil.cpf = request.POST.get('cpf') or None
        perfil.telefone = request.POST.get('telefone', perfil.telefone) 
        perfil.whatsapp = request.POST.get('whatsapp', perfil.whatsapp)
        perfil.rg_cnh = request.POST.get('rg_cnh', perfil.rg_cnh)
        perfil.orgao_expedidor = request.POST.get('orgao_expedidor', perfil.orgao_expedidor)
        
        data_nasc = request.POST.get('data_nascimento')
        if data_nasc:
            perfil.data_nascimento = data_nasc

        # Endereço
        perfil.cep = request.POST.get('cep', perfil.cep)
        perfil.rua = request.POST.get('rua', perfil.rua)
        perfil.numero = request.POST.get('numero', perfil.numero)
        perfil.complemento = request.POST.get('complemento', perfil.complemento)
        perfil.bairro = request.POST.get('bairro', perfil.bairro)
        perfil.cidade = request.POST.get('cidade', perfil.cidade)
        perfil.uf = request.POST.get('uf', perfil.uf)

        # Identidade na Torcida
        perfil.vulgo = request.POST.get('vulgo', perfil.vulgo)
        perfil.pelotao = request.POST.get('pelotao', perfil.pelotao)
        perfil.rede_social = request.POST.get('rede_social', perfil.rede_social)
        
        perfil.save()
        
        messages.success(request, f"O utilizador {user_alvo.first_name} foi editado com sucesso pelo painel Admin!")
        return redirect('admin_utilizadores') 

    context = {
        'perfil_edit': perfil,
    }
    return render(request, 'admin_utilizadores.html', context)

# --- LÓGICA PARA EVENTOS ---
@login_required
def toggle_presenca_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    presenca = Presenca.objects.filter(user=request.user, evento=evento).first()
    
    if presenca:
        presenca.delete() # Desconfirma
        messages.warning(request, "Presença cancelada.")
    else:
        Presenca.objects.create(user=request.user, evento=evento) # Confirma
        messages.success(request, "Presença confirmada!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def toggle_salvar_evento(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    perfil = request.user.perfil
    
    if evento in perfil.eventos_salvos.all():
        perfil.eventos_salvos.remove(evento)
    else:
        perfil.eventos_salvos.add(evento)
        messages.success(request, "Evento salvo!")
        
    # Devolve o utilizador à página onde ele estava
    return redirect(request.META.get('HTTP_REFERER', '/'))

# --- LÓGICA PARA CARAVANAS ---
@login_required
def toggle_presenca_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    presenca = PresencaCaravana.objects.filter(user=request.user, caravana=caravana).first()
    
    if presenca:
        presenca.delete()
        messages.warning(request, "Nome retirado da caravana.")
    else:
        PresencaCaravana.objects.create(user=request.user, caravana=caravana)
        from gamification.xp import xp_participacao_caravana
        xp_participacao_caravana(request.user, caravana)
        messages.success(request, "Nome adicionado à caravana!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def toggle_salvar_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    perfil = request.user.perfil
    
    if caravana in perfil.caravanas_salvas.all():
        perfil.caravanas_salvas.remove(caravana)
    else:
        perfil.caravanas_salvas.add(caravana)
        messages.success(request, "Caravana salva com sucesso!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def exportar_csv_moderacao(request, tipo, item_id=0):
    perfil = request.user.perfil
    
    # Bloqueio de segurança
    if not request.user.is_staff or not perfil.torcida:
        return redirect('dashboard')
        
    torcida = perfil.torcida
    
    # Configura a resposta para baixar um arquivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    # Adiciona o BOM do UTF-8 para o Excel ler os acentos brasileiros perfeitamente
    response.write('\ufeff'.encode('utf8')) 
    writer = csv.writer(response, delimiter=';') # Ponto e vírgula divide melhor no Excel PT-BR
    
    if tipo == 'socios':
        response['Content-Disposition'] = f'attachment; filename="socios_{torcida.sigla or torcida.nome}.csv"'
        writer.writerow(['NOME', 'EMAIL', 'CPF', 'WHATSAPP', 'VULGO', 'PELOTAO', 'STATUS'])
        
        membros = Perfil.objects.filter(torcida=torcida)
        for m in membros:
            status = "Aprovado" if m.aprovado else "Pendente"
            writer.writerow([
                m.user.first_name or m.user.username, 
                m.user.email, 
                m.cpf or "", 
                m.whatsapp or "", 
                m.vulgo or "", 
                m.pelotao or "", 
                status
            ])
            
    elif tipo == 'evento':
        from organizadas.models import Evento as OrgEvento
        evento = get_object_or_404(OrgEvento, id=item_id, torcida=torcida)
        response['Content-Disposition'] = f'attachment; filename="evento_{evento.id}_lista.csv"'
        writer.writerow(['NOME', 'EMAIL', 'WHATSAPP', 'VULGO', 'TIPO_CONFIRMACAO'])
        
        # Presenças Simples
        for presenca in evento.presencas.all():
            u = presenca.user
            writer.writerow([u.first_name or u.username, u.email, u.perfil.whatsapp or "", u.perfil.vulgo or "", "Confirmou Presenca"])
            
        # Check-ins Validados (via Gamificação)
        for checkin in evento.checkins_accounts.all():
            u = checkin.user
            writer.writerow([u.first_name or u.username, u.email, u.perfil.whatsapp or "", u.perfil.vulgo or "", "Check-in Gamificado"])
            
    elif tipo == 'caravana':
        from organizadas.models import Caravana as OrgCaravana
        from accounts.models import PresencaCaravana
        caravana = get_object_or_404(OrgCaravana, id=item_id, torcida=torcida)
        response['Content-Disposition'] = f'attachment; filename="caravana_{caravana.id}_lista.csv"'
        writer.writerow(['NOME', 'EMAIL', 'WHATSAPP', 'VULGO', 'PELOTAO', 'RG/CNH'])
        
        presencas = PresencaCaravana.objects.filter(caravana=caravana)
        for p in presencas:
            u = p.user
            writer.writerow([
                u.first_name or u.username, 
                u.email, 
                u.perfil.whatsapp or "", 
                u.perfil.vulgo or "", 
                u.perfil.pelotao or "", 
                u.perfil.rg_cnh or ""
            ])

    return response

# ==========================================
# INTEGRAÇÃO EFÍ BANK (PIX)
# ==========================================

@login_required
def pagar_fatura_pix(request, fatura_id):
    from accounts.models import Fatura
    from accounts.efi_utils import gerar_cobranca_pix
    
    fatura = get_object_or_404(Fatura, id=fatura_id, assinatura__perfil__user=request.user)
    
    if fatura.status == 'pago':
        messages.info(request, "Esta fatura já está paga.")
        return redirect('dashboard')
        
    # Se ainda não tem txid ou qr code, gera
    if not fatura.txid:
        resultado = gerar_cobranca_pix(fatura, tipo='fatura')
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('dashboard')
            
    return render(request, 'pagar_pix.html', {'fatura': fatura})

@csrf_exempt
def webhook_efi(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # A Efí envia um array de 'pix' quando o pagamento é confirmado
            if 'pix' in data:
                for pagamento in data['pix']:
                    txid = pagamento.get('txid')
                    
                    if txid:
                        from accounts.models import Fatura
                        from loja.models import Pedido
                        
                        # Tenta encontrar e atualizar na Loja
                        pedido = Pedido.objects.filter(txid=txid).first()
                        if pedido:
                            pedido.status = 'pago'
                            pedido.save()
                            from gamification.xp import conceder_xp
                            conceder_xp(pedido.usuario, 'compra', referencia=pedido.id)
                            continue
                            
                        # Tenta encontrar e atualizar nos Planos (ativa/renova e sincroniza com o club_ben)
                        fatura = Fatura.objects.filter(txid=txid).first()
                        if fatura:
                            confirmar_pagamento_fatura(fatura)
                            
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return HttpResponse(status=405)


# ==========================================
# ASSINATURA DE PLANO PELO USUÁRIO
# ==========================================

@login_required
def assinar_plano(request, plano_id):
    """
    Grátis: ativa na hora.
    Pago: cria (ou reaproveita, na renovação) a assinatura + fatura PIX. O plano atual
    só é trocado quando o pagamento for confirmado (webhook da Efí).
    """
    if request.method != 'POST':
        return redirect('seja_socio')

    perfil = request.user.perfil
    plano = get_object_or_404(PlanoSocio, id=plano_id, ativo=True, torcida__isnull=True, nivel__isnull=False)
    vigente = perfil.assinatura_vigente

    if plano.gratuito:
        if vigente and not vigente.plano.gratuito:
            messages.info(request, f'Seu plano {vigente.plano.nome} continua valendo até {vigente.valida_ate:%d/%m/%Y}.')
            return redirect('seja_socio')
        assinatura, _ = Assinatura.objects.get_or_create(perfil=perfil, plano=plano, defaults={'ativa': False})
        ativar_assinatura(assinatura)
        messages.success(request, 'Plano Grátis ativado!')
        return redirect('beneficios')

    # Reaproveita a assinatura deste plano (renovação soma os dias que ainda restam)
    assinatura = Assinatura.objects.filter(perfil=perfil, plano=plano).order_by('-id').first()
    if assinatura:
        fatura_pendente = assinatura.faturas.filter(status='pendente').order_by('-id').first()
        if fatura_pendente:
            return redirect('pagar_fatura_pix', fatura_id=fatura_pendente.id)
    else:
        assinatura = Assinatura.objects.create(perfil=perfil, plano=plano, ativa=False)

    fatura = Fatura.objects.create(
        assinatura=assinatura,
        valor=plano.preco,
        data_vencimento=timezone.now().date() + timedelta(days=3),
        status='pendente'
    )

    try:
        resultado = gerar_cobranca_pix(fatura, tipo='fatura')
        if not resultado.get('sucesso'):
            messages.error(request, f"Erro ao gerar PIX: {resultado.get('erro')}")
            return redirect('financeiro')
    except Exception as e:
        messages.error(request, f"Erro ao gerar PIX: {str(e)}")
        return redirect('financeiro')

    return redirect('pagar_fatura_pix', fatura_id=fatura.id)


# ==========================================
# PAINEL DO MODERADOR: BENEFÍCIOS EXTRAS DA TORCIDA POR PLANO
# (Os 4 planos e preços são oficiais da SAT; cada torcida só acrescenta benefícios)
# ==========================================

def _torcida_moderada(request):
    if request.user.is_staff and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        return request.user.perfil.torcida
    return None


@login_required
def painel_planos(request):
    torcida = _torcida_moderada(request)
    if not torcida:
        messages.error(request, "Acesso negado. Apenas moderadores autorizados.")
        return redirect('dashboard')

    context = {
        'niveis': beneficios_por_nivel(torcida),
        'torcida': torcida,
        'inativos': BeneficioTorcida.objects.filter(torcida=torcida, ativo=False),
    }
    return render(request, 'painel_planos.html', context)


@login_required
def form_beneficio(request, beneficio_id=None):
    torcida = _torcida_moderada(request)
    if not torcida:
        return redirect('dashboard')

    beneficio = get_object_or_404(BeneficioTorcida, id=beneficio_id, torcida=torcida) if beneficio_id else None

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        nivel = request.POST.get('nivel_minimo')
        if not titulo or nivel not in dict(NIVEIS_PLANO):
            messages.error(request, 'Preencha o benefício e escolha o plano.')
        else:
            beneficio = beneficio or BeneficioTorcida(torcida=torcida)
            beneficio.titulo = titulo
            beneficio.descricao = request.POST.get('descricao', '').strip()
            beneficio.nivel_minimo = nivel
            beneficio.ativo = request.POST.get('ativo') == 'on'
            beneficio.save()
            messages.success(request, 'Benefício salvo!')
            return redirect('painel_planos')

    return render(request, 'form_beneficio.html', {
        'beneficio': beneficio,
        'torcida': torcida,
        'niveis': NIVEIS_PLANO,
        'nivel_inicial': request.GET.get('nivel', 'bronze'),
    })


@login_required
def excluir_beneficio(request, beneficio_id):
    torcida = _torcida_moderada(request)
    if torcida and request.method == 'POST':
        get_object_or_404(BeneficioTorcida, id=beneficio_id, torcida=torcida).delete()
        messages.success(request, 'Benefício removido.')
    return redirect('painel_planos')

@login_required
def cancelar_vinculo(request):
    perfil = request.user.perfil
    perfil.torcida = None
    perfil.aprovado = False
    perfil.save()
    messages.success(request, "Vínculo cancelado. Você agora é um membro neutro.")
    return redirect('torcidas')


@login_required
def validar_matricula(request, matricula=''):
    """
    Identificação do sócio pela matrícula (é o destino do QR da carteirinha).
    Moderadores, BEPE e admins veem os dados completos; os demais, só o essencial.
    """
    from bepe.permissions import is_bepe
    codigo = matricula or request.GET.get('m', '').strip()
    perfil = Perfil.por_matricula(codigo) if codigo else None
    autoridade = request.user.is_superuser or request.user.is_staff or is_bepe(request.user)
    return render(request, 'validar_matricula.html', {
        'codigo': codigo,
        'socio': perfil,
        'autoridade': autoridade,
        'assinatura': perfil.assinatura_vigente if perfil else None,
    })