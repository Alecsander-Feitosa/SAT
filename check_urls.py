import urllib.request
import re

urls = [
    "https://upload.wikimedia.org/wikipedia/commons/b/b3/Club_Athletico_Paranaense_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/5/5f/Atletico_mineiro_galo.png",
    "https://upload.wikimedia.org/wikipedia/commons/e/e1/Esporte_Clube_Bahia_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/c/cb/Escudo_Botafogo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/b/b3/Associa%C3%A7%C3%A3o_Chapecoense_de_Futebol.svg",
    "https://upload.wikimedia.org/wikipedia/pt/b/b4/Corinthians_simbolo.png",
    "https://upload.wikimedia.org/wikipedia/commons/8/83/Coritiba_FBC_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/9/90/Cruzeiro_Esporte_Clube_%28logo%29.svg",
    "https://upload.wikimedia.org/wikipedia/commons/2/2e/Flamengo_braz_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/a/a3/Escudo_Fluminense_FC_2024.svg",
    "https://upload.wikimedia.org/wikipedia/commons/b/b4/Gr%C3%AAmio_Logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/f/f1/Escudo_do_Sport_Club_Internacional.svg",
    "https://upload.wikimedia.org/wikipedia/commons/3/30/Mirassol_Futebol_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/1/10/Palmeiras_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/9/9e/Red_Bull_Bragantino_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/4/4c/Clube_do_Remo_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/1/15/Santos_Logo.png",
    "https://upload.wikimedia.org/wikipedia/commons/2/2b/S%C3%A3o_Paulo_Futebol_Clube.svg",
    "https://upload.wikimedia.org/wikipedia/pt/a/ac/CRVascodaGama.png",
    "https://upload.wikimedia.org/wikipedia/commons/3/36/Esporte_Clube_Vit%C3%B3ria_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/a/aa/Am%C3%A9rica_Futebol_Clube_MG_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/1/16/Athletic_Club_de_S%C3%A3o_Jo%C3%A3o_del-Rei_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/4/44/Atl%C3%A9tico_Club_Goianiense_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/f/fe/Ava%C3%AD_Futebol_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/b/b3/Botafogo_Futebol_Clube_SP_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/5/58/Cear%C3%A1_Sporting_Club_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/9/9c/Clube_de_Regatas_Brasil_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/5/59/Crici%C3%BAma_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/2/20/Cuiab%C3%A1_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/e/e9/Fortaleza_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/7/75/Goi%C3%A1s_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/4/4f/Esporte_Clube_Juventude_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/d/df/Londrina_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/c/cc/Clube_N%C3%A1utico_Capibaribe_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/a/a1/Gr%C3%AAmio_Novorizontino_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/7/73/Oper%C3%A1rio_Ferrovi%C3%A1rio_Esporte_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/8/8c/Associa%C3%A7%C3%A3o_Atl%C3%A9tica_Ponte_Preta_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/9/96/S%C3%A3o_Bernardo_Futebol_Clube_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/a/a9/Sport_Club_do_Recife_logo.svg",
    "https://upload.wikimedia.org/wikipedia/commons/1/1b/Vila_Nova_Futebol_Clube_logo.svg"
]

broken = []
for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
    except Exception as e:
        broken.append(url)
        print(f"Broken: {url}")

print(f"Total broken: {len(broken)}")
