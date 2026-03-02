# accounts/admin.py
from django.contrib import admin
from .models import Perfil

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    # Adicionei 'aprovado' no display para você ver o status na lista geral
    list_display = ('user', 'torcida', 'aprovado', 'cpf', 'whatsapp', 'cidade') 
    
    list_filter = ('aprovado', 'torcida', 'cidade', 'uf') 
    
    fieldsets = (
        ('Identificação', {
            # O campo 'aprovado' deve ser incluído aqui:
            'fields': ('user', 'torcida', 'aprovado', 'cpf', 'rg_cnh', 'orgao_expedidor', 'data_nascimento')
        }),
        ('Endereço', {
            'fields': ('cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'uf')
        }),
        ('Documentação e Social', {
            'fields': ('foto_documento_frente', 'foto_documento_verso', 'verificacao_facial', 'vulgo', 'pelotao', 'rede_social')
        }),
    )