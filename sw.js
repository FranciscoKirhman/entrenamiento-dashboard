// Cachea el tablero para que funcione sin señal en el gimnasio.
// Estrategia: red primero (para ver siempre el plan actualizado), cache como respaldo.
const CACHE = 'entreno-v2';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-180.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;      // lo externo pasa sin tocar

  // GitHub Pages sirve index.html con cache-control: max-age=600. Un fetch normal se
  // resuelve desde la cache HTTP del navegador, asi que "red primero" devolvia el tablero
  // de hasta 10 minutos atras y ademas lo guardaba como si fuera lo ultimo.
  // cache:'reload' obliga a ir a la red de verdad; si no hay señal, cae al respaldo.
  const aLaRed = new Request(url.href, { cache: 'reload', credentials: 'same-origin' });

  e.respondWith(
    fetch(aLaRed)
      .then(res => {
        if (res && res.ok) {
          const copia = res.clone();
          caches.open(CACHE).then(c => c.put(url.href, copia)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(url.href).then(r => r || caches.match('./index.html')))
  );
});
