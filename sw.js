// Cachea el tablero para que funcione sin señal en el gimnasio.
// Estrategia: red primero con limite de tiempo, cache como respaldo.
const CACHE = 'entreno-v4';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-180.png'];
const LIMITE_MS = 3000;   // en el subterraneo la señal existe pero no llega: no esperar mas que esto

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function delCache(href) {
  return caches.match(href).then(r => r || caches.match('./index.html'));
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;      // lo externo pasa sin tocar
  // version.json nunca se cachea: es justamente el archivo que delata una copia vieja
  if (url.pathname.endsWith('/version.json')) return;

  // GitHub Pages sirve index.html con cache-control: max-age=600. Un fetch normal se
  // resuelve desde la cache HTTP del navegador, asi que "red primero" devolvia el tablero
  // de hasta 10 minutos antes y ademas lo guardaba como si fuera lo ultimo.
  // cache:'reload' obliga a ir a la red de verdad.
  const aLaRed = new Request(url.href, { cache: 'reload', credentials: 'same-origin' });

  e.respondWith(new Promise(resolve => {
    let resuelto = false;
    const listo = r => { if (!resuelto) { resuelto = true; resolve(r); } };

    // si la red no contesta a tiempo, se sirve lo cacheado y no se deja al usuario esperando
    const reloj = setTimeout(() => {
      delCache(url.href).then(r => { if (r) listo(r); });
    }, LIMITE_MS);

    fetch(aLaRed).then(res => {
      clearTimeout(reloj);
      if (res && res.ok) {
        const copia = res.clone();
        caches.open(CACHE).then(c => c.put(url.href, copia)).catch(() => {});
      }
      listo(res);                                   // aunque el reloj ya haya servido cache, la copia queda guardada
    }).catch(() => {
      clearTimeout(reloj);
      delCache(url.href).then(r => listo(r || Response.error()));
    });
  }));
});
