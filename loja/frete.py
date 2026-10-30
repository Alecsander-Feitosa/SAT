# loja/frete.py
"""Cotação de frete por CEP.

Com MELHOR_ENVIO_TOKEN configurado, cota de verdade nos Correios/transportadoras pela API
do Melhor Envio (https://melhorenvio.com.br). Sem token, usa uma estimativa por peso e região.
O CEP de origem vem da ConfigLoja da torcida dona do produto (ou da loja SAT Global),
e por último de settings.LOJA_CEP_ORIGEM.
"""
import logging
from collections import defaultdict
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Caixa padrão (cm) para itens sem medidas cadastradas: cabe camisa/boné dobrados
CAIXA_PADRAO = {'width': 20, 'height': 6, 'length': 28}


def so_digitos(cep):
    return ''.join(c for c in (cep or '') if c.isdigit())


def cep_origem(torcida_id):
    from .models import ConfigLoja
    config = ConfigLoja.objects.filter(torcida_id=torcida_id).first()
    if config and so_digitos(config.cep_origem):
        return so_digitos(config.cep_origem)
    if torcida_id:
        config = ConfigLoja.objects.filter(torcida__isnull=True).first()
        if config and so_digitos(config.cep_origem):
            return so_digitos(config.cep_origem)
    return so_digitos(getattr(settings, 'LOJA_CEP_ORIGEM', ''))


def _estimativa(peso_total, cep_destino):
    """Tabela simples usada quando não há integração configurada."""
    peso = float(peso_total)
    valor_pac = 15.00 + peso * 2
    valor_sedex = 30.00 + peso * 4
    if int(cep_destino[0]) > 5:
        valor_pac += 20.00
        valor_sedex += 40.00
    return [
        {'tipo': 'PAC', 'valor': round(valor_pac, 2), 'prazo': '7 a 10 dias úteis'},
        {'tipo': 'SEDEX', 'valor': round(valor_sedex, 2), 'prazo': '2 a 4 dias úteis'},
    ]


def _melhor_envio(origem, destino, itens):
    base = 'https://sandbox.melhorenvio.com.br' if getattr(settings, 'MELHOR_ENVIO_SANDBOX', False) else 'https://melhorenvio.com.br'
    produtos = [{
        'id': str(produto.id),
        **CAIXA_PADRAO,
        'weight': float(produto.peso or Decimal('0.5')),
        'insurance_value': float(produto.preco_atual()),
        'quantity': qtd,
    } for produto, qtd in itens]
    resp = requests.post(
        f'{base}/api/v2/me/shipment/calculate',
        json={'from': {'postal_code': origem}, 'to': {'postal_code': destino}, 'products': produtos},
        headers={
            'Authorization': f'Bearer {settings.MELHOR_ENVIO_TOKEN}',
            'Accept': 'application/json',
            'User-Agent': f"SAT ({getattr(settings, 'MELHOR_ENVIO_EMAIL', '') or 'contato@sat.app'})",
        },
        timeout=10,
    )
    resp.raise_for_status()
    opcoes = []
    for s in resp.json():
        if s.get('error') or not s.get('price'):
            continue
        dias = s.get('custom_delivery_time') or s.get('delivery_time')
        opcoes.append({
            'tipo': f"{s.get('company', {}).get('name', '')} {s['name']}".strip(),
            'valor': round(float(s.get('custom_price') or s['price']), 2),
            'prazo': f'até {dias} dias úteis' if dias else '',
        })
    return opcoes


def cotar(cep_destino, itens):
    """itens: lista de (Produto, quantidade). Retorna lista de {'tipo', 'valor', 'prazo'}, mais barata primeiro.

    Itens de torcidas diferentes saem de lugares diferentes: cota cada origem e soma
    as modalidades que existem em todas elas.
    """
    destino = so_digitos(cep_destino)
    if len(destino) != 8:
        raise ValueError('CEP inválido.')

    grupos = defaultdict(list)
    for produto, qtd in itens:
        grupos[produto.torcida_id].append((produto, qtd))

    cotacoes = []
    for torcida_id, itens_grupo in grupos.items():
        origem = cep_origem(torcida_id)
        opcoes = None
        if getattr(settings, 'MELHOR_ENVIO_TOKEN', '') and len(origem) == 8:
            try:
                opcoes = _melhor_envio(origem, destino, itens_grupo)
            except Exception:
                logger.exception('Falha na cotação do Melhor Envio')
        if not opcoes:
            peso = sum((p.peso or Decimal('0.5')) * q for p, q in itens_grupo)
            opcoes = _estimativa(peso, destino)
        cotacoes.append({o['tipo']: o for o in opcoes})

    comuns = set(cotacoes[0]).intersection(*cotacoes[1:]) if cotacoes else set()
    resultado = []
    for tipo in comuns:
        partes = [c[tipo] for c in cotacoes]
        resultado.append({
            'tipo': tipo,
            'valor': round(sum(p['valor'] for p in partes), 2),
            'prazo': max((p['prazo'] for p in partes), key=len),
        })
    if not resultado:
        return _estimativa(sum((p.peso or Decimal('0.5')) * q for p, q in itens), destino)
    return sorted(resultado, key=lambda o: o['valor'])
