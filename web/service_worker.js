// web/service_worker.js

const CACHE_NAME = "mindful-cache-v5";
const OFFLINE_FALLBACK = "/index.html";

// Archivos base de tu app (ajusta rutas si algo cambia)
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/assets/logo.png",
];

// Helpers
async function cacheFirst(req) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(req);
  if (cached) return cached;

  const res = await fetch(req);
  cache.put(req, res.clone());
  return res;
}

async function networkFirst(req) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const res = await fetch(req);
    cache.put(req, res.clone());
    return res;
  } catch (e) {
    const cached = await cache.match(req);
    if (cached) return cached;
    if (req.mode === "navigate") {
      return cache.match(OFFLINE_FALLBACK);
    }
    throw e;
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // 1) Navegación: SPA offline
  if (req.mode === "navigate") {
    event.respondWith(networkFirst(req));
    return;
  }

  // 2) No cachear llamadas a Gemini / chat (solo online)
  if (url.href.includes("generativelanguage.googleapis.com")) {
    // No usamos cache; si falla, el código Python mostrará mensaje de offline
    return;
  }

  // 3) Archivos estáticos: cache-first
  if (
    url.pathname.startsWith("/assets/") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".webp") ||
    url.pathname.endsWith(".ico")
  ) {
    event.respondWith(cacheFirst(req));
    return;
  }

  // 4) Resto: network-first con fallback
  event.respondWith(networkFirst(req));
});
