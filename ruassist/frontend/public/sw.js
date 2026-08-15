/**
 * Offline cache for the dictionary.
 *
 * Cache-first rather than network-first, deliberately: the bundle is immutable
 * for a given build, the app must work on a plane or in a classroom with no
 * signal, and a lookup that waits on a dead network is worse than no app at
 * all. Freshness comes from bumping CACHE, not from revalidating on each read.
 *
 * Vite emits content-hashed asset names, so runtime caching covers the whole
 * shell without a build-time file manifest.
 */

const CACHE = "ruassist-v1";
const PRECACHE = ["./", "./index.html", "./dictionary.json", "./manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // Individual failures must not abort the install: the shell is still
      // usable, and anything missed is picked up by runtime caching below.
      .then((cache) => Promise.allSettled(PRECACHE.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    caches.match(request).then((hit) => {
      if (hit) return hit;
      return fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(async () => {
          // A navigation that misses the cache still gets the app shell, which
          // then reads the dictionary from cache.
          if (request.mode === "navigate") {
            return (await caches.match("./index.html")) ?? Response.error();
          }
          return Response.error();
        });
    }),
  );
});
