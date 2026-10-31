# organizadas/templatetags/painel_sat.py
"""Cores das telas do moderador: estrutura da SAT com as cores da torcida."""
from django import template

register = template.Library()

COR_SAT = '#D37129'


def luminancia(cor_hex):
    """Brilho percebido de uma cor #RRGGBB, de 0 (preto) a 1 (branco); None se inválida."""
    try:
        h = (cor_hex or '').strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def cores_destaque(torcida):
    """(cor de destaque, cor do texto sobre ela).
    Usa a cor primária da torcida; se ela some no fundo (ex: preto no preto), tenta a secundária e a terciária."""
    if not torcida:
        return COR_SAT, '#FFFFFF'
    fundo = luminancia(torcida.cor_fundo)
    destaque = torcida.cor_primaria or COR_SAT
    if fundo is not None:
        for cor in (torcida.cor_primaria, torcida.cor_secundaria, torcida.cor_terciaria):
            lum = luminancia(cor)
            if lum is not None and abs(lum - fundo) >= 0.25:
                destaque = cor
                break
    lum = luminancia(destaque)
    texto = '#16191A' if lum is not None and lum > 0.65 else '#FFFFFF'
    return destaque, texto


@register.simple_tag
def cores_painel(torcida):
    return cores_destaque(torcida)
