# bepe/permissions.py
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

GRUPO_BEPE = 'BEPE'


def is_bepe(user):
    """Acesso total à Área BEPE: superusuários (admins SAT) ou membros do grupo BEPE."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=GRUPO_BEPE).exists()


def torcida_da_diretoria(user):
    """Retorna a torcida que o usuário modera (staff vinculado a uma torcida), ou None."""
    if not user.is_authenticated or not user.is_staff:
        return None
    perfil = getattr(user, 'perfil', None)
    return perfil.torcida if perfil else None


def bepe_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_bepe(request.user):
            messages.error(request, "Acesso restrito ao BEPE.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def diretoria_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        torcida = torcida_da_diretoria(request.user)
        if not torcida:
            messages.error(request, "Acesso restrito à diretoria da torcida.")
            return redirect('dashboard')
        request.torcida_diretoria = torcida
        return view_func(request, *args, **kwargs)
    return _wrapped_view
