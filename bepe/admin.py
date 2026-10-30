from django.contrib import admin
from .models import RegistroProntuario, Conversa, Mensagem, Denuncia, LocalizacaoTorcedor, PlanoRota, Reuniao
from .permissions import is_bepe


class SomenteBepeAdmin(admin.ModelAdmin):
    """Esconde os dados do BEPE no /admin de moderadores de torcida (is_staff)."""
    def has_module_permission(self, request):
        return is_bepe(request.user)

    def has_view_permission(self, request, obj=None):
        return is_bepe(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(RegistroProntuario)
class RegistroProntuarioAdmin(SomenteBepeAdmin):
    list_display = ('perfil', 'tipo', 'titulo', 'data_fato', 'autor')
    list_filter = ('tipo',)
    search_fields = ('perfil__user__username', 'perfil__cpf', 'titulo')


class MensagemInline(admin.TabularInline):
    model = Mensagem
    extra = 0


@admin.register(Conversa)
class ConversaAdmin(SomenteBepeAdmin):
    list_display = ('torcida', 'assunto', 'criada_em', 'encerrada')
    inlines = [MensagemInline]


@admin.register(Denuncia)
class DenunciaAdmin(SomenteBepeAdmin):
    list_display = ('protocolo', 'categoria', 'torcida', 'status', 'criada_em')
    list_filter = ('status', 'categoria')
    search_fields = ('protocolo',)


@admin.register(LocalizacaoTorcedor)
class LocalizacaoTorcedorAdmin(SomenteBepeAdmin):
    list_display = ('user', 'status', 'latitude', 'longitude', 'atualizada_em')
    list_filter = ('status',)
    search_fields = ('user__username',)


@admin.register(PlanoRota)
class PlanoRotaAdmin(SomenteBepeAdmin):
    list_display = ('titulo', 'torcida_a', 'torcida_b', 'data_jogo', 'criado_por')


@admin.register(Reuniao)
class ReuniaoAdmin(SomenteBepeAdmin):
    list_display = ('titulo', 'data_hora', 'cancelada', 'criada_por')
    filter_horizontal = ('torcidas',)
