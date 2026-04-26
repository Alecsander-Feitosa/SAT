from organizadas.models import Torcida


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



def torcida_branding(request):
    torcida = None
    
    # 1. Se o usuário estiver logado e tiver uma torcida vinculada
    if request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.torcida:
        torcida = request.user.perfil.torcida
    
    # 2. Se não estiver logado, mas escolheu uma torcida na sessão (Pré-login)
    else:
        torcida_id = request.session.get('torcida_pre_selecionada')
        if torcida_id:
            torcida = Torcida.objects.filter(id=torcida_id).first()

    if torcida:
        return {
            'branding': {
                'nome': torcida.nome,
                'logo': torcida.logo.url if torcida.logo else None,
                'cor_primaria': torcida.cor_primaria or "#D37129",
                'cor_secundaria': torcida.cor_secundaria or "#FFFFFF",
                'cor_fundo': torcida.cor_fundo or "#121212",
                'cor_terciaria': torcida.cor_terciaria or "#FFFFFF",
            }
        }
    
    # Cores padrão da SAT caso nenhuma torcida seja detectada
    return {
        'branding': {
            'nome': 'SAT',
            'logo': None,
            'cor_primaria': "#D37129",
            'cor_secundaria': "#FFFFFF",
            'cor_fundo': "#121212",
            'cor_terciaria': "#FFFFFF",
        }
    }