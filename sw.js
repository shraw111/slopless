// Signal Shorts service worker.
// Opening is instant: the page, the clip lists and the icons are answered from the phone's own cache, and
// refreshed in the background. When the refresh brings something newer, the page is told and offers a reload.
const CACHE = "signal-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png",
               "clips.json", "topics.json", "paths.json", "debates.json"];

self.addEventListener("install", (e) => {
  // addAll fails as a whole if one file is missing, so add them one by one
  e.waitUntil(caches.open(CACHE).then((c) => Promise.all(SHELL.map((u) => c.add(u).catch(() => {})))));
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

const version = (res) => res && (res.headers.get("etag") || res.headers.get("last-modified"));
async function tell(path) {
  for (const c of await self.clients.matchAll()) c.postMessage({ type: "updated", path });
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;   // YouTube and thumbnails go straight through
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(e.request, { ignoreSearch: true });
    const fresh = fetch(e.request).then(async (res) => {
      if (res.ok) {
        const before = version(hit), after = version(res);
        await cache.put(e.request, res.clone());
        if (hit && before && after && before !== after) tell(url.pathname);
      }
      return res;
    }).catch(() => null);
    if (hit) { e.waitUntil(fresh); return hit; }   // instant, then refresh behind the scenes
    return (await fresh) || (await cache.match("index.html")) || Response.error();
  })());
});
