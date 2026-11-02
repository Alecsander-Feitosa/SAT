# accounts/futebol.py
"""
Jogos do time do coração e tabelas de classificação, pela API pública da ESPN (sem chave).
A ESPN não é uma API oficial/documentada: se mudar, só este arquivo precisa ser ajustado.
Se ela estiver fora do ar, as telas mostram listas vazias em vez de dar erro.
"""
import logging
import unicodedata
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

URL_JOGOS = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard'
URL_TABELA = 'https://site.api.espn.com/apis/v2/sports/soccer/{liga}/standings'
PARAMS = {'lang': 'pt', 'region': 'br'}
TEMPO_JOGOS = 10 * 60
TEMPO_TABELA = 30 * 60
ESPERA_MAXIMA = 10  # segundos: se a ESPN travar, a página abre com o que chegou até aqui

SELECAO = 'Seleção Brasileira'

CLUBES = [
    ('bra.1', 'Brasileirão Série A'),
    ('bra.2', 'Brasileirão Série B'),
    ('conmebol.libertadores', 'Libertadores'),
    ('bra.copa_do_brazil', 'Copa do Brasil'),
    ('conmebol.sudamericana', 'Sul-Americana'),
    ('bra.camp.carioca', 'Carioca'),
    ('bra.camp.paulista', 'Paulista'),
    ('bra.camp.mineiro', 'Mineiro'),
    ('bra.camp.gaucho', 'Gaúcho'),
]
SELECOES = [
    ('fifa.world', 'Copa do Mundo'),
    ('fifa.worldq.conmebol', 'Eliminatórias'),
    ('conmebol.america', 'Copa América'),
    ('fifa.friendly', 'Amistosos'),
]
NOMES = dict(CLUBES + SELECOES)
# Mata-mata puro: no lugar da tabela, a tela mostra os confrontos
SEM_TABELA = {'bra.copa_do_brazil', 'fifa.friendly', 'conmebol.america'}

# Nome em accounts/times.py -> nome na ESPN, quando é diferente
NOMES_ESPN = {
    SELECAO: 'Brasil',
    'Athletico-PR': 'Athletico Paranaense',
    'Vasco': 'Vasco da Gama',
    'América-MG': 'América Mineiro',
    'Athletic Club': 'Athletic',
    'Atlético-GO': 'Atlético Goianiense',
    'Operário-PR': 'Operário PR',
}


def _sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', (texto or '').lower()) if unicodedata.category(c) != 'Mn')


def nome_normalizado(time):
    return _sem_acento(NOMES_ESPN.get(time, time))


def campeonatos_do_time(time):
    """Campeonatos oferecidos na tela: os da Seleção para quem torce por ela, os de clubes para os demais."""
    return SELECOES if time == SELECAO else CLUBES


def _meses():
    """Mês passado (resultados recentes), o atual e os dois próximos, no formato AAAAMM."""
    hoje = timezone.localdate()
    indice = hoje.year * 12 + hoje.month - 1
    return [f'{i // 12}{i % 12 + 1:02d}' for i in range(indice - 1, indice + 3)]


def _buscar_mes(liga, ano_mes):
    chave = f'futebol_jogos_{liga}_{ano_mes}'
    eventos = cache.get(chave)
    if eventos is None:
        try:
            resposta = requests.get(URL_JOGOS.format(liga=liga), params={**PARAMS, 'dates': ano_mes}, timeout=8)
            resposta.raise_for_status()
            eventos = resposta.json().get('events', [])
        except Exception:
            logger.warning("ESPN indisponível para %s %s", liga, ano_mes, exc_info=True)
            return []  # não guarda falha no cache: tenta de novo na próxima
        cache.set(chave, eventos, TEMPO_JOGOS)
    return [(liga, e) for e in eventos]


def _converter(liga, evento):
    comp = evento['competitions'][0]
    times = {c.get('homeAway'): c for c in comp.get('competitors', [])}
    tipo = (comp.get('status') or evento.get('status') or {}).get('type', {})
    comecou = tipo.get('state') in ('in', 'post')

    def lado(casa_fora):
        c = times.get(casa_fora) or {}
        t = c.get('team') or {}
        return {'nome': t.get('displayName', '?'), 'logo': t.get('logo', ''), 'placar': c.get('score') if comecou else None}

    venue = comp.get('venue') or {}
    return {
        'id': evento.get('id'),
        'liga': liga,
        'campeonato': NOMES.get(liga, liga),
        'data': timezone.localtime(datetime.fromisoformat(evento['date'].replace('Z', '+00:00'))),
        'mandante': lado('home'),
        'visitante': lado('away'),
        'estadio': venue.get('fullName', ''),
        'cidade': (venue.get('address') or {}).get('city', ''),
        'ao_vivo': tipo.get('state') == 'in',
        'encerrado': tipo.get('state') == 'post',
        'status': tipo.get('shortDetail', ''),
    }


def _jogos(ligas):
    tarefas = [(liga, mes) for liga in ligas for mes in _meses()]
    pool = ThreadPoolExecutor(max_workers=8)
    futuros = [pool.submit(_buscar_mes, *t) for t in tarefas]
    prontos, _ = wait(futuros, timeout=ESPERA_MAXIMA)
    pool.shutdown(wait=False, cancel_futures=True)
    jogos, vistos = [], set()
    for futuro in prontos:
        for liga, evento in futuro.result():
            if evento.get('id') in vistos:
                continue
            try:
                jogos.append(_converter(liga, evento))
            except (KeyError, IndexError, ValueError):
                logger.warning("Jogo da ESPN em formato inesperado: %s", evento.get('id'))
                continue
            vistos.add(evento.get('id'))
    return jogos


def jogos_do_time(time):
    """{'proximos': [...], 'resultados': [...]} do time, com os próximos em ordem de data e os resultados do mais novo ao mais antigo."""
    alvo = nome_normalizado(time)
    ligas = [liga for liga, _ in campeonatos_do_time(time)]
    do_time = [j for j in _jogos(ligas)
               if alvo in (_sem_acento(j['mandante']['nome']), _sem_acento(j['visitante']['nome']))]
    return {
        'proximos': sorted((j for j in do_time if not j['encerrado']), key=lambda j: j['data']),
        'resultados': sorted((j for j in do_time if j['encerrado']), key=lambda j: j['data'], reverse=True),
    }


def jogos_da_liga(liga):
    """Confrontos de um campeonato sem tabela (ex: Copa do Brasil): próximos primeiro, depois os encerrados."""
    jogos = _jogos([liga])
    abertos = sorted((j for j in jogos if not j['encerrado']), key=lambda j: j['data'])
    encerrados = sorted((j for j in jogos if j['encerrado']), key=lambda j: j['data'], reverse=True)
    return abertos + encerrados


def _estatistica(entrada, nome):
    for item in entrada.get('stats', []):
        if item.get('name') == nome:
            return item.get('displayValue') or ''
    return ''


def _linha(entrada):
    time = entrada.get('team') or {}
    logos = time.get('logos') or [{}]
    return {
        'posicao': _estatistica(entrada, 'rank'),
        'nome': time.get('displayName', '?'),
        'nome_normalizado': _sem_acento(time.get('displayName', '')),
        'logo': logos[0].get('href', ''),
        'pontos': _estatistica(entrada, 'points'),
        'jogos': _estatistica(entrada, 'gamesPlayed'),
        'vitorias': _estatistica(entrada, 'wins'),
        'empates': _estatistica(entrada, 'ties'),
        'derrotas': _estatistica(entrada, 'losses'),
        'saldo': _estatistica(entrada, 'pointDifferential'),
    }


def _posicao(linha):
    return int(linha['posicao']) if linha['posicao'].isdigit() else 999


def classificacao(liga):
    """Lista de grupos [{'nome', 'linhas': [...]}]. Campeonato de pontos corridos vem com um grupo só, sem nome."""
    if liga in SEM_TABELA:
        return []
    chave = f'futebol_tabela_{liga}'
    grupos = cache.get(chave)
    if grupos is not None:
        return grupos
    try:
        resposta = requests.get(URL_TABELA.format(liga=liga), params=PARAMS, timeout=8)
        resposta.raise_for_status()
        filhos = resposta.json().get('children', [])
    except Exception:
        logger.warning("ESPN indisponível para a tabela de %s", liga, exc_info=True)
        return []
    grupos = []
    for filho in filhos:
        linhas = sorted((_linha(e) for e in (filho.get('standings') or {}).get('entries', [])), key=_posicao)
        if linhas:
            grupos.append({'nome': filho.get('name', '') if len(filhos) > 1 else '', 'linhas': linhas})
    cache.set(chave, grupos, TEMPO_TABELA)
    return grupos
