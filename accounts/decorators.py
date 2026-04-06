# accounts/decorators.py
from django.shortcuts import redirect
from functools import wraps
from django.urls import resolve

def torcida_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = request.user.perfil
        
        # 1. Se não tem torcida, manda escolher
        if not perfil.torcida:
            return redirect('torcida')
        
        # 2. Se tem torcida mas não está aprovado
        if not perfil.aprovado:
            # Pegamos o nome da URL atual de forma segura
            current_url = resolve(request.path).url_name
            
            # Bloqueia apenas páginas de interação da organizada
            if current_url in ['mural_social', 'ranking', 'checkin']:
                return redirect('dashboard')
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def torcida_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = request.user.perfil
        
        # 1. Se não tem torcida, manda escolher
        if not perfil.torcida:
            return redirect('torcidas')
        
        # 2. Se tem torcida mas não está aprovado, bloqueia o acesso
        if not perfil.aprovado:
            messages.warning(request, "Acesso restrito. A diretoria ainda está a analisar a sua entrada.")
            return redirect('dashboard')
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view

