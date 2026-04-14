# accounts/context_processors.py

def tema_torcida(request):
    # Cor padrão do SAT Elite
    context = {'cor_tema': '#CD7F32', 'logo_tema': None, 'nome_tema': 'SAT ELITE'}
    
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
            # Só de ter a torcida escolhida, o app já se pinta com as cores dela!
            if perfil.torcida:
                context['cor_tema'] = perfil.torcida.cor_primaria
                context['nome_tema'] = perfil.torcida.nome
                if perfil.torcida.logo:
                    context['logo_tema'] = perfil.torcida.logo.url
        except:
            pass
            
    return context