import urllib.request
import re

ge_urls = {
    "Athletico-PR": "https://s.sde.globo.com/media/organizations/2019/09/09/Athletico-PR.svg",
    "Atlético-MG": "https://s.sde.globo.com/media/organizations/2018/03/10/atletico-mg.svg",
    "Bahia": "https://s.sde.globo.com/media/organizations/2018/03/11/bahia.svg",
    "Botafogo": "https://s.sde.globo.com/media/organizations/2019/02/04/botafogo-svg.svg",
    "Chapecoense": "https://s.sde.globo.com/media/organizations/2018/03/11/chapecoense.svg",
    "Corinthians": "https://s.sde.globo.com/media/organizations/2019/05/01/Corinthians_2019.svg",
    "Coritiba": "https://s.sde.globo.com/media/organizations/2018/03/11/coritiba.svg",
    "Cruzeiro": "https://s.sde.globo.com/media/organizations/2021/02/13/cruzeiro_2021.svg",
    "Flamengo": "https://s.sde.globo.com/media/organizations/2018/04/10/Flamengo-2018.svg",
    "Fluminense": "https://s.sde.globo.com/media/organizations/2018/03/11/fluminense.svg",
    "Grêmio": "https://s.sde.globo.com/media/organizations/2018/03/12/gremio.svg",
    "Internacional": "https://s.sde.globo.com/media/organizations/2018/03/11/internacional.svg",
    "Mirassol": "https://s.sde.globo.com/media/organizations/2018/03/11/mirassol.svg",
    "Palmeiras": "https://s.sde.globo.com/media/organizations/2018/03/11/palmeiras.svg",
    "Red Bull Bragantino": "https://s.sde.globo.com/media/organizations/2021/06/28/bragantino.svg",
    "Remo": "https://s.sde.globo.com/media/organizations/2018/03/12/remo.svg",
    "Santos": "https://s.sde.globo.com/media/organizations/2018/03/12/santos.svg",
    "São Paulo": "https://s.sde.globo.com/media/organizations/2018/03/11/sao-paulo.svg",
    "Vasco": "https://s.sde.globo.com/media/organizations/2021/09/04/vasco_SVG.svg",
    "Vitória": "https://s.sde.globo.com/media/organizations/2018/03/11/vitoria.svg",
    
    "América-MG": "https://s.sde.globo.com/media/organizations/2018/03/11/america-mg.svg",
    "Athletic Club": "https://s.sde.globo.com/media/organizations/2021/02/22/athletic-mg.svg",
    "Atlético-GO": "https://s.sde.globo.com/media/organizations/2020/07/02/atletico-go-2020.svg",
    "Avaí": "https://s.sde.globo.com/media/organizations/2018/03/11/avai.svg",
    "Botafogo-SP": "https://s.sde.globo.com/media/organizations/2019/02/28/botafogo-sp-svg.svg",
    "Ceará": "https://s.sde.globo.com/media/organizations/2018/03/11/ceara.svg",
    "CRB": "https://s.sde.globo.com/media/organizations/2018/03/11/crb.svg",
    "Criciúma": "https://s.sde.globo.com/media/organizations/2018/03/11/criciuma.svg",
    "Cuiabá": "https://s.sde.globo.com/media/organizations/2018/12/26/Cuiaba_EC.svg",
    "Fortaleza": "https://s.sde.globo.com/media/organizations/2018/06/15/fortaleza.svg",
    "Goiás": "https://s.sde.globo.com/media/organizations/2021/03/01/goias-2021.svg",
    "Juventude": "https://s.sde.globo.com/media/organizations/2021/04/29/Juventude-2021-01.svg",
    "Londrina": "https://s.sde.globo.com/media/organizations/2018/03/11/londrina.svg",
    "Náutico": "https://s.sde.globo.com/media/organizations/2018/03/11/nautico.svg",
    "Novorizontino": "https://s.sde.globo.com/media/organizations/2018/03/11/novorizontino.svg",
    "Operário-PR": "https://s.sde.globo.com/media/organizations/2018/03/12/operario-pr.svg",
    "Ponte Preta": "https://s.sde.globo.com/media/organizations/2018/03/11/ponte-preta.svg",
    "São Bernardo": "https://s.sde.globo.com/media/organizations/2018/03/11/sao-bernardo.svg",
    "Sport": "https://s.sde.globo.com/media/organizations/2018/03/11/sport.svg",
    "Vila Nova": "https://s.sde.globo.com/media/organizations/2021/04/14/vilanova.svg"
}

file_path = "c:/Users/Micro/Desktop/venv/SAT/accounts/views.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def replacer(match):
    name = match.group(1)
    if name in ge_urls:
        return f'{{"nome": "{name}", "escudo": "{ge_urls[name]}"}}'
    return match.group(0)

new_content = re.sub(r'\{\"nome\":\s*\"([^\"]+)\",\s*\"escudo\":\s*\"[^\"]+\"\}', replacer, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Done GE URL replacement!")
