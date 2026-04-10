from django.contrib import admin
from .models import FotoGaleria, ConquistaTorcida, MembroDiretoria, Regra, Caravana, Evento, Noticia, Post, Curtida, Parceiro, Publicidade, Torcida



class ModeradorBaseAdmin(admin.ModelAdmin):
    """
    Garante que o Admin Global veja TUDO,
    e o Moderador da Torcida veja APENAS os dados da sua própria Torcida.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            minha_torcida = request.user.perfil.torcida
            
            if self.model == Torcida:
                return qs.filter(id=minha_torcida.id)
            elif hasattr(self.model, 'torcida'):
                return qs.filter(torcida=minha_torcida)
                
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(obj, 'torcida'):
            if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
                obj.torcida = request.user.perfil.torcida
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and hasattr(self.model, 'torcida'):
            return self.readonly_fields + ('torcida',)
        return self.readonly_fields


from django.contrib import admin
from .models import Torcida, Evento, Noticia, Post, Parceiro, Publicidade

@admin.register(Torcida)
class TorcidaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla', 'fundacao')
    
    # 1. Filtra a lista: o moderador só vê a sua própria claque
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'perfil') and request.user.perfil.torcida:
            return qs.filter(id=request.user.perfil.torcida.id)
        return qs.none() # Se não tiver claque associada, não vê nada

    # 2. Impede que o moderador crie novas claques (só o dono do sistema pode)
    def has_add_permission(self, request):
        return request.user.is_superuser

    # 3. Impede que o moderador apague a própria claque por engano
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Caravana)
class CaravanaAdmin(ModeradorBaseAdmin):
    list_display = ('titulo', 'torcida', 'saida_local', 'saida_horario', 'vagas_totais')
    list_filter = ('torcida',)
    search_fields = ('titulo', 'saida_local')


@admin.register(Evento)
class EventoAdmin(ModeradorBaseAdmin):
    list_display = ('titulo', 'torcida', 'data', 'local', 'ativo')
    list_filter = ('ativo', 'torcida')
    search_fields = ('titulo', 'local')
    list_editable = ('ativo',)


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_publicacao', 'autor')
    search_fields = ('titulo', 'autor')
    
    def has_module_permission(self, request):
        # Apenas superusuários (Admin global) conseguem ver e gerir Notícias
        return request.user.is_superuser


@admin.register(Post)
class PostAdmin(ModeradorBaseAdmin):
    list_display = ('autor', 'torcida', 'data_criacao')
    list_filter = ('torcida',)
    search_fields = ('autor__username', 'texto')


@admin.register(Curtida)
class CurtidaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'post', 'data_curtida')


@admin.register(Parceiro)
class ParceiroAdmin(ModeradorBaseAdmin):
    list_display = ('nome', 'torcida', 'link')
    list_filter = ('torcida',)
    search_fields = ('nome',)


@admin.register(Publicidade)
class PublicidadeAdmin(ModeradorBaseAdmin):
    list_display = ('titulo', 'data_inicio', 'data_fim', 'tempo_exibicao', 'ativo', 'torcida')
    list_filter = ('ativo', 'torcida', 'data_inicio', 'data_fim')
    search_fields = ('titulo',)

from .models import Regra, MembroDiretoria, ConquistaTorcida, FotoGaleria

# Registre os modelos no Admin
admin.site.register(Regra)
admin.site.register(MembroDiretoria)
admin.site.register(ConquistaTorcida)
admin.site.register(FotoGaleria)