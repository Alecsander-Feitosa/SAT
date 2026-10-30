# bepe/jogos.py
"""
Jogos que acontecem no estado do RJ, a partir da API pública da ESPN (sem chave).
A ESPN não é uma API oficial/documentada: se mudar, só este arquivo precisa ser ajustado.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard'

CAMPEONATOS = {
    'bra.1': 'Brasileirão Série A',
    'bra.2': 'Brasileirão Série B',
    'bra.camp.carioca': 'Campeonato Carioca',
    'bra.copa_do_brazil': 'Copa do Brasil',
    'conmebol.libertadores': 'Libertadores',
    'conmebol.sudamericana': 'Sul-Americana',
}

# Cidades do estado do RJ que recebem jogos profissionais
CIDADES_RJ = {
    'Rio de Janeiro', 'Volta Redonda', 'Nova Iguaçu', 'Nova Iguacu', 'Saquarema', 'Macaé', 'Macae',
    'Campos dos Goytacazes', 'Mesquita', 'Niterói', 'Niteroi', 'Duque de Caxias', 'São Gonçalo',
    'Sao Goncalo', 'Bacaxá', 'Cabo Frio', 'Resende', 'Petrópolis', 'Petropolis', 'Itaboraí',
}

# Coordenadas dos estádios (a ESPN informa só nome e cidade). Chave = trecho do nome em minúsculas.
ESTADIOS = {
    'maracan': ('Maracanã', -22.91216, -43.23019),
    'havelange': ('Nilton Santos (Engenhão)', -22.89325, -43.29214),
    'nilton santos': ('Nilton Santos (Engenhão)', -22.89325, -43.29214),
    'engenh': ('Nilton Santos (Engenhão)', -22.89325, -43.29214),
    'januário': ('São Januário', -22.89107, -43.22821),
    'januario': ('São Januário', -22.89107, -43.22821),
    'raulino': ('Raulino de Oliveira', -22.50878, -44.09440),
    'moça bonita': ('Moça Bonita (Proletário)', -22.87393, -43.46793),
    'moca bonita': ('Moça Bonita (Proletário)', -22.87393, -43.46793),
    'proletário': ('Moça Bonita (Proletário)', -22.87393, -43.46793),
    'luso': ('Luso-Brasileiro', -22.80598, -43.18810),
    'giulite': ('Giulite Coutinho', -22.78927, -43.40963),
    'laranjão': ('Laranjão', -22.77044, -43.43008),
}


def localizar_estadio(nome):
    nome_min = (nome or '').lower()
    for trecho, dados in ESTADIOS.items():
        if trecho in nome_min:
            return dados
    return None


def _buscar_mes(liga, ano_mes):
    chave = f'bepe_jogos_{liga}_{ano_mes}'
    eventos = cache.get(chave)
    if eventos is None:
        try:
            resposta = requests.get(URL.format(liga=liga), params={'dates': ano_mes}, timeout=12)
            resposta.raise_for_status()
            eventos = resposta.json().get('events', [])
        except Exception:
            logger.warning("ESPN indisponível para %s %s", liga, ano_mes, exc_info=True)
            return []  # não guarda falha no cache: tenta de novo na próxima
        cache.set(chave, eventos, 30 * 60)
    return [(liga, e) for e in eventos]


def _converter(liga, evento):
    comp = evento['competitions'][0]
    venue = comp.get('venue') or {}
    cidade = (venue.get('address') or {}).get('city', '')
    if cidade not in CIDADES_RJ:
        return None

    times = {c.get('homeAway'): c for c in comp.get('competitors', [])}
    def time(lado):
        c = times.get(lado) or {}
        t = c.get('team') or {}
        return {'nome': t.get('displayName', '?'), 'sigla': t.get('abbreviation', ''),
                'logo': t.get('logo', ''), 'placar': c.get('score')}

    estadio = localizar_estadio(venue.get('fullName'))
    status = (comp.get('status') or evento.get('status') or {}).get('type', {})
    data = datetime.fromisoformat(evento['date'].replace('Z', '+00:00'))
    return {
        'id': evento.get('id'),
        'campeonato': CAMPEONATOS.get(liga, liga),
        'data': timezone.localtime(data),
        'mandante': time('home'),
        'visitante': time('away'),
        'estadio': estadio[0] if estadio else venue.get('fullName', 'Estádio não informado'),
        'cidade': cidade,
        'lat': estadio[1] if estadio else None,
        'lng': estadio[2] if estadio else None,
        'status': status.get('shortDetail') or status.get('description', ''),
        'encerrado': status.get('completed', False),
    }


def jogos_no_rj(meses=2, incluir_encerrados=False):
    """Jogos no RJ do mês atual e dos próximos (meses-1), ordenados por data."""
    hoje = timezone.localdate()
    ano_meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(meses):
        ano_meses.append(f'{ano}{mes:02d}')
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1

    tarefas = [(liga, am) for liga in CAMPEONATOS for am in ano_meses]
    with ThreadPoolExecutor(max_workers=6) as pool:
        resultados = pool.map(lambda t: _buscar_mes(*t), tarefas)

    jogos, vistos = [], set()
    for lista in resultados:
        for liga, evento in lista:
            jogo = _converter(liga, evento)
            if not jogo or jogo['id'] in vistos:
                continue
            if not incluir_encerrados and jogo['encerrado'] and jogo['data'].date() < hoje:
                continue
            vistos.add(jogo['id'])
            jogos.append(jogo)
    return sorted(jogos, key=lambda j: j['data'])
