const CACHE = 'site-v1';

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const res = await fetch('/level/2/v1/');
    if (!res.ok) throw new Error('failed to fetch /level/2/v1/: ' + res.status);
    const cache = await caches.open(CACHE);
    await cache.put('/level/2', res);
  })().catch((err) => {
    console.error('[sw] precaching failed:', err);
    throw err;
  }));
});
