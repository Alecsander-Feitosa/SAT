from django.contrib import admin

from .models import Post, Comentario, DenunciaPost, Notificacao, Penalidade, CPFBloqueado, Popup, AvisoCabecalho


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'autor_s', 'visibilidade', 'tipo', 'torcida', 'em_revisao', 'data_criacao')
    list_filter = ('visibilidade', 'tipo', 'em_revisao')
    search_fields = ('texto', 'autor_s__username')


@admin.register(DenunciaPost)
class DenunciaPostAdmin(admin.ModelAdmin):
    list_display = ('post', 'autor', 'motivo', 'criada_em')
    list_filter = ('motivo',)


@admin.register(Penalidade)
class PenalidadeAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo', 'motivo', 'inicio', 'fim', 'revogada')
    list_filter = ('tipo', 'revogada')
    search_fields = ('user__username',)


@admin.register(CPFBloqueado)
class CPFBloqueadoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'motivo', 'ate', 'criado_em')


admin.site.register(Notificacao)
admin.site.register(Comentario)


@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'torcida', 'modo', 'exibir_em', 'exibir_ate', 'ativo')
    list_filter = ('ativo', 'modo', 'torcida')
    search_fields = ('titulo', 'mensagem')


@admin.register(AvisoCabecalho)
class AvisoCabecalhoAdmin(admin.ModelAdmin):
    list_display = ('texto', 'cor', 'ativo', 'atualizado_em')
    list_editable = ('ativo',)
