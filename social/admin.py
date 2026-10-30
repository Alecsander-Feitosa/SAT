from django.contrib import admin

from .models import Post, Comentario, DenunciaPost, Notificacao, Penalidade, CPFBloqueado


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
