from django.contrib import admin
from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    # Removidos 'xp_total' e 'nivel_atual' que causavam erro
    list_display = ('user', 'torcida', 'cpf', 'whatsapp', 'cidade') 
    
    #Filtros laterais para facilitar a gestão 
    list_filter = ('torcida', 'cidade', 'uf') 
    
    # Organização por seções no formulário de edição do Admin
    fieldsets = (
        ('Identificação', {
            'fields': ('user', 'torcida', 'cpf', 'rg_cnh', 'orgao_expedidor', 'data_nascimento')
        }),
        ('Endereço', {
            'fields': ('cep', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'uf')
        }),
        ('Documentação e Social', {
            'fields': ('foto_documento_frente', 'foto_documento_verso', 'verificacao_facial', 'vulgo', 'pelotao', 'rede_social')
        }),
    )

