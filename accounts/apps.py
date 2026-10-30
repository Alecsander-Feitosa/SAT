from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'  # Certifique-se de que este nome é exatamente 'accounts'

    def ready(self):
        # Registra os aparelhos a cada login (Segurança > Dispositivos conectados)
        from . import dispositivos  # noqa: F401
