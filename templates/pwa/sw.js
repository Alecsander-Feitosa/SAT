// Service worker do SAT (gerado por sat_core/pwa.py)
const CACHE = '{{ versao }}';
const PRECACHE = [{% for url in precache %}'{{ url }}'{% if not forloop.last %}, {% endif %}{% endfor %}];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)));
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((nomes) =>
            Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;

    // Páginas: sempre da rede (dados do usuário nunca vão pro cache).
    // Sem internet, mostra a página offline.
    if (req.mode === 'navigate') {
        event.respondWith(fetch(req).catch(() => caches.match('/offline/')));
        return;
    }

    // Arquivos estáticos: cache primeiro, atualiza em segundo plano.
    if (url.pathname.startsWith('{{ static_url }}')) {
        event.respondWith(
            caches.open(CACHE).then((cache) =>
                cache.match(req).then((cacheado) => {
                    const daRede = fetch(req).then((resp) => {
                        if (resp.ok) cache.put(req, resp.clone());
                        return resp;
                    }).catch(() => cacheado);
                    return cacheado || daRede;
                })
            )
        );
    }
});
