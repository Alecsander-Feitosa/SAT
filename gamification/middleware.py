from django.utils import timezone


class CheckinDiarioMiddleware:
    """Dá o EXP do check-in diário no primeiro acesso do dia (+20 EXP com o multiplicador do plano)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            hoje = timezone.localdate().isoformat()
            if request.session.get('checkin_diario') != hoje:
                from .xp import checkin_diario
                checkin_diario(user)
                request.session['checkin_diario'] = hoje
        return self.get_response(request)
