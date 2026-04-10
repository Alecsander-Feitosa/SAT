from django.contrib import admin
from .models import Perfil, Evento, CheckIn, Conquista, Cancao, Aliada, Presenca, PlanoSocio



@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'torcida', 'aprovado', 'time_coracao')
    list_filter = ('aprovado',)
    search_fields = ('user__username', 'user__first_name', 'cpf')

    # 1. Oculta todos os perfis de outras claques da tabela
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            # Mostra apenas membros que pertençam à mesma claque do moderador
            return qs.filter(torcida=request.user.perfil.torcida)
        return qs.none()

    # 2. Bloqueia os menus de seleção (Dropdowns) de chaves estrangeiras (Foreign Keys)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            # Se o campo for "torcida", ele só pode escolher a própria claque
            if db_field.name == "torcida":
                if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                    kwargs["queryset"] = db_field.related_model.objects.filter(
                        id=request.user.perfil.torcida.id
                    )
                else:
                    kwargs["queryset"] = db_field.related_model.objects.none()
                    
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 3. Opcional: Impedir que o moderador edite os seus próprios privilégios
    def has_change_permission(self, request, obj=None):
        # Se for o próprio perfil do moderador, podes bloquear ou permitir. 
        # Normalmente permitimos.
        return super().has_change_permission(request, obj)



@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    # O moderador só vê os eventos da sua claque
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            return qs.filter(torcida=request.user.perfil.torcida)
        return qs.none()

    # Obriga o evento a ficar preso à claque do moderador
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "torcida":
            if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    id=request.user.perfil.torcida.id
                )
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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