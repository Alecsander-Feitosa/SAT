from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Torcida, Evento, Caravana
from django.utils import timezone


def lista_torcidas(request):
    torcidas = Torcida.objects.all()
    return render(request, 'organizadas/lista.html', {'torcidas': torcidas})

def perfil_torcida(request, slug):
    torcida = get_object_or_404(Torcida, slug=slug)
    eventos = torcida.eventos.order_by('data_hora')
    caravanas = torcida.caravanas.order_by('saida_horario')
    
    return render(request, 'organizadas/perfil.html', {
        'torcida': torcida,
        'eventos': eventos,
        'caravanas': caravanas
    })

@login_required
def confirmar_presenca(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)
    if request.user in evento.confirmados.all():
        evento.confirmados.remove(request.user)
        messages.warning(request, "Presença cancelada.")
    else:
        evento.confirmados.add(request.user)
        messages.success(request, "Presença confirmada!")
    return redirect('perfil_torcida', slug=evento.torcida.slug)

@login_required
def reservar_caravana(request, caravana_id):
    caravana = get_object_or_404(Caravana, id=caravana_id)
    
    if caravana.vagas_restantes() <= 0:
        messages.error(request, "Caravana lotada!")
    elif request.user in caravana.passageiros.all():
        messages.info(request, "Você já está nessa caravana.")
    else:
        caravana.passageiros.add(request.user)
        messages.success(request, "Lugar reservado na caravana!")
        
    return redirect('perfil_torcida', slug=caravana.torcida.slug)

def lista_eventos(request):
    # Procura todos os eventos a partir de hoje, ordenados pelo mais próximo
    eventos = Evento.objects.filter(data_evento__gte=timezone.now()).order_by('data_evento')
    
    return render(request, 'eventos.html', {
        'eventos': eventos
    })