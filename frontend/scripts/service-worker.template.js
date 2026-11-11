/* Vite sustituye estos marcadores por la versión y la lista cerrada de recursos. */
const cacheName = 'rutainformada-shell-' + __REVISION__;
const files = __SHELL_FILES__;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(cacheName).then(cache =>
    cache.addAll(files.map(path => new Request(path, {cache: 'reload'})))));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith('rutainformada-shell-') && name !== cacheName) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const {request} = event;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const entry = request.mode === 'navigate' && ['/', '/index.html'].includes(url.pathname);
  const key = entry ? '/index.html' : url.pathname;
  if (!files.includes(key) || (!entry && url.search)) return;
  event.respondWith(caches.open(cacheName).then(async cache =>
    (await cache.match(key)) || fetch(request)));
});
