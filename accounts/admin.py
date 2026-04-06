from django.contrib import admin
from .models import Perfil, Evento, CheckIn, Conquista, Cancao, Aliada, Presenca, PlanoSocio

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'vulgo', 'torcida', 'aprovado')
    list_filter = ('aprovado',) # Tiramos o filtro de torcida, pois o moderador só vê a dele
    search_fields = ('user__username', 'cpf', 'vulgo')
    list_editable = ('aprovado',) # Permite aprovar com 1 clique na lista!

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Se for o dono do sistema (Superuser), vê toda a gente
        if request.user.is_superuser:
            return qs
        
        # Se for o Moderador, filtra APENAS pelos membros da torcida dele
        if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            return qs.filter(torcida=request.user.perfil.torcida)
        
        return qs.none()
    
def get_readonly_fields(self, request, obj=None):
        # O Moderador não deve conseguir alterar o CPF ou o User de outra pessoa, apenas aprovar e gerir o perfil.
        if not request.user.is_superuser:
            return ('user', 'cpf', 'data_nascimento', 'rg_cnh', 'torcida')
        return super().get_readonly_fields(request, obj)



@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'local', 'torcida', 'ativo')
    list_filter = ('ativo', 'torcida')
    search_fields = ('nome', 'local')
    list_editable = ('ativo',)

@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'evento', 'data_criacao', 'validado')
    list_filter = ('validado', 'evento')
    search_fields = ('user__username', 'evento__nome')
    
@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'xp_necessario')
    search_fields = ('titulo',)

@admin.register(Cancao)
class CancaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'torcida')

@admin.register(Aliada)
class AliadaAdmin(admin.ModelAdmin):
    list_display = ('nome_organizada', 'clube', 'torcida')

@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
    list_display = ('user', 'evento', 'data_confirmacao')

@admin.register(PlanoSocio)
class PlanoSocioAdmin(admin.ModelAdmin):
    # Quais colunas vão aparecer na lista do painel
    list_display = ('nome', 'preco', 'torcida', 'destaque')
    
    # Adiciona um filtro lateral para achar planos por torcida
    list_filter = ('torcida', 'destaque')
    
    # Adiciona uma barra de pesquisa
    search_fields = ('nome', 'descricao', 'beneficios')