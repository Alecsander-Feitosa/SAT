# accounts/noticias.py
"""
Notícias de futebol a partir dos feeds RSS públicos do ge.globo (gratuitos, sem chave e sem limite diário).
Times sem feed no ge usam a busca do Google Notícias (RSS) como reserva.

Cada notícia ganha um `id` e fica guardada no cache, para abrir no leitor interno
(/noticias/ler/<id>/) sem tirar o usuário do app.
"""
import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests
from django.core.cache import cache

from .times import escudo_do_time

logger = logging.getLogger(__name__)

TEMPO_LISTA = 15 * 60          # listas atualizam a cada 15 min
TEMPO_NOTICIA = 24 * 60 * 60   # cada notícia fica disponível no leitor por 24h
CABECALHOS = {'User-Agent': 'Mozilla/5.0 (compatible; SAT-App/1.0)'}

GE = 'https://ge.globo.com/rss/ge/{}/'
FEED_GERAL = 'futebol'

# Caminho do feed de cada time no ge (nome igual ao de accounts/times.py)
FEEDS_TIMES = {
    'Athletico-PR': 'pr/futebol/times/athletico-pr', 'Atlético-MG': 'futebol/times/atletico-mg',
    'Bahia': 'ba/futebol/times/bahia', 'Botafogo': 'futebol/times/botafogo',
    'Chapecoense': 'sc/futebol/times/chapecoense', 'Corinthians': 'futebol/times/corinthians',
    'Coritiba': 'pr/futebol/times/coritiba', 'Cruzeiro': 'futebol/times/cruzeiro',
    'Flamengo': 'futebol/times/flamengo', 'Fluminense': 'futebol/times/fluminense',
    'Grêmio': 'rs/futebol/times/gremio', 'Internacional': 'rs/futebol/times/internacional',
    'Palmeiras': 'futebol/times/palmeiras', 'Red Bull Bragantino': 'sp/vale-do-paraiba-regiao/futebol/times/bragantino',
    'Remo': 'pa/futebol/times/remo', 'Santos': 'sp/santos-e-regiao/futebol/times/santos',
    'São Paulo': 'futebol/times/sao-paulo', 'Vasco': 'futebol/times/vasco', 'Vitória': 'ba/futebol/times/vitoria',
    'América-MG': 'futebol/times/america-mg', 'Atlético-GO': 'go/futebol/times/atletico-go',
    'Avaí': 'sc/futebol/times/avai', 'Ceará': 'ce/futebol/times/ceara', 'CRB': 'al/futebol/times/crb',
    'Criciúma': 'sc/futebol/times/criciuma', 'Cuiabá': 'mt/futebol/times/cuiaba',
    'Fortaleza': 'ce/futebol/times/fortaleza', 'Goiás': 'go/futebol/times/goias',
    'Juventude': 'rs/futebol/times/juventude', 'Londrina': 'pr/futebol/times/londrina',
    'Náutico': 'pe/futebol/times/nautico', 'Operário-PR': 'pr/futebol/times/operario-pr',
    'Ponte Preta': 'sp/campinas-e-regiao/futebol/times/ponte-preta', 'São Bernardo': 'sp/futebol/times/sao-bernardo',
    'Sport': 'pe/futebol/times/sport', 'Vila Nova': 'go/futebol/times/vila-nova',
}
MAX_TEXTO = 1500


def _id(link):
    return hashlib.sha1((link or '').encode('utf-8')).hexdigest()[:16]


def _feed_do_time(time):
    alvo = (time or '').strip().lower()
    for nome, caminho in FEEDS_TIMES.items():
        if nome.lower() == alvo:
            return caminho
    for nome, caminho in FEEDS_TIMES.items():
        if nome.lower() in alvo or alvo in nome.lower():
            return caminho
    return None


def _texto(html_bruto):
    """Tira as tags do HTML do RSS e devolve (texto limpo, primeira imagem)."""
    imagem = re.search(r'<img[^>]+src="([^"]+)"', html_bruto or '')
    texto = re.sub(r'<br\s*/?>', '\n', html_bruto or '')
    texto = html.unescape(re.sub(r'<[^>]+>', '', texto))
    texto = '\n\n'.join(l.strip() for l in texto.splitlines() if l.strip())  # cada linha vira um parágrafo
    if len(texto) > MAX_TEXTO:
        texto = texto[:MAX_TEXTO].rsplit(' ', 1)[0] + '…'
    return texto, (imagem.group(1) if imagem else '')


def _data(item):
    try:
        return parsedate_to_datetime(item.findtext('pubDate'))
    except (TypeError, ValueError):
        return None


def _ler_rss(url):
    resposta = requests.get(url, headers=CABECALHOS, timeout=8)
    resposta.raise_for_status()
    return ET.fromstring(resposta.content).findall('.//item')


def _do_ge(caminho, time):
    noticias = []
    for item in _ler_rss(GE.format(caminho)):
        link = item.findtext('link') or ''
        texto, imagem = _texto(item.findtext('description'))
        media = item.find('{http://search.yahoo.com/mrss/}content')
        noticias.append({
            'id': _id(link),
            'titulo': (item.findtext('title') or '').strip(),
            'subtitulo': (item.findtext('{http://www.w3.org/2005/Atom}subtitle') or '').strip(),
            'descricao': texto,
            'imagem': imagem or (media.get('url') if media is not None else ''),
            'fonte': 'ge',
            'link': link,
            'data': _data(item),
            'time': time,
            'escudo': escudo_do_time(time) if time else None,
        })
    return noticias


def _do_google(time):
    """Reserva para times sem feed no ge (sem foto: o leitor usa o escudo)."""
    url = f'https://news.google.com/rss/search?q={quote_plus(time + " futebol")}&hl=pt-BR&gl=BR&ceid=BR:pt-419'
    noticias = []
    for item in _ler_rss(url):
        link = item.findtext('link') or ''
        fonte = item.findtext('source') or 'Google Notícias'
        titulo = (item.findtext('title') or '').strip()
        if titulo.endswith(' - ' + fonte):
            titulo = titulo[: -len(' - ' + fonte)]
        noticias.append({
            'id': _id(link), 'titulo': titulo, 'subtitulo': '', 'descricao': '', 'imagem': '',
            'fonte': fonte, 'link': link, 'data': _data(item),
            'time': time, 'escudo': escudo_do_time(time),
        })
    return noticias


def _carregar(chave, buscar):
    noticias = cache.get(chave)
    if noticias is not None:
        return noticias
    try:
        vistos, noticias = set(), []
        for n in buscar():
            if n['link'] and n['titulo'] and n['id'] not in vistos:
                vistos.add(n['id'])
                noticias.append(n)
        noticias = noticias[:30]
    except Exception:
        logger.warning("Falha ao buscar notícias (%s)", chave, exc_info=True)
        return []  # não guarda a falha: tenta de novo na próxima visita
    cache.set(chave, noticias, TEMPO_LISTA)
    cache.set_many({f'noticia_{n["id"]}': n for n in noticias}, TEMPO_NOTICIA)
    return noticias


def noticias_gerais(**_):
    return _carregar('noticias_gerais_v3', lambda: _do_ge(FEED_GERAL, None))


def noticias_do_time(time, **_):
    if not time or time == 'Outro':
        return []
    caminho = _feed_do_time(time)
    chave = f'noticias_time_{_id(time.lower())}_v3'
    if caminho:
        return _carregar(chave, lambda: _do_ge(caminho, time))
    return _carregar(chave, lambda: _do_google(time))


def obter(noticia_id):
    return cache.get(f'noticia_{noticia_id}')
