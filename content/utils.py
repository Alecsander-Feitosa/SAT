import requests
from content.api import api_noticias
def buscar_noticias_futebol():
    # Substitua pela sua chave do newsapi.org
    api_key = api_noticias
    # Buscamos termos de futebol em português, ordenados pelas mais recentes
    url = f"https://newsapi.org/v2/everything?q=futebol+brasileiro&language=pt&sortBy=publishedAt&pageSize=3&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('status') == 'ok':
            return data.get('articles', [])
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")
    return []