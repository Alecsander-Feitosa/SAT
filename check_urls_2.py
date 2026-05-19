import urllib.request
import re

file_path = 'c:/Users/Micro/Desktop/venv/SAT/accounts/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

urls = re.findall(r'\"escudo\":\s*\"([^\"]+)\"', content)

broken = []
for url in set(urls):
    if 'placehold.co' in url: continue
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        resp = urllib.request.urlopen(req)
        if resp.status != 200:
            broken.append(url)
    except Exception as e:
        broken.append(url)
        print(f'Broken: {url} - {e}')

print(f'Total broken: {len(broken)}')
