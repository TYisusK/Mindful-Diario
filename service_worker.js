// Simple, tolerant service worker for Mindful+
// - precaches a small set of urls (best-effort)
// - network-first for navigations (HTML)
// - cache-first for static assets
// - supports skipWaiting via postMessage {type: 'SKIP_WAITING'}

// Allow CACHE_NAME to be updated at install time if a generated manifest exists.
let CACHE_VERSION = 'v1';
let CACHE_NAME = `mindful-${CACHE_VERSION}`;

// List of candidate URLs to precache. We try to cache them but ignore failures.
const PRECACHE_URLS = [
	'/',
	'/assets/logo.png',
	'/offline.html',
	'/web/icons/log1024.png',
	'/web/icons/log192.png',
	'/web/icons/log512.png',
	'/web/index.html',
	'/web/manifest.json',
	'/web/offline.html',
	'/web/service_worker.js',
];


self.addEventListener('install', (event) => {
	self.skipWaiting();
	event.waitUntil(
		(async () => {
			// Try to load an externally generated precache manifest first.
			let precacheList = PRECACHE_URLS;
			try {
				const tryFetch = async (path) => {
					const resp = await fetch(path, {cache: 'no-cache'});
					if (!resp || !resp.ok) return null;
					return await resp.json();
				};
				let manifest = await tryFetch('/precache-manifest.json');
				if (!manifest) manifest = await tryFetch('/web/precache-manifest.json');
				if (manifest && Array.isArray(manifest.precache) && manifest.precache.length) {
					precacheList = manifest.precache;
				}
				if (manifest && manifest.generated_at) {
					CACHE_VERSION = String(manifest.generated_at);
					CACHE_NAME = `mindful-${CACHE_VERSION}`;
				}
			} catch (e) {
				// ignore manifest load errors and fall back to embedded PRECACHE_URLS
			}

			const cache = await caches.open(CACHE_NAME);
			// Best-effort caching: fetch each and add if ok.
			await Promise.all(precacheList.map(async (url) => {
				try {
					const r = await fetch(url, {cache: 'no-cache'});
					if (r && r.ok) await cache.put(url, r.clone());
				} catch (e) {
					// ignore missing resources
				}
			}));
		})()
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil((async () => {
		// cleanup old caches
		const keys = await caches.keys();
		await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
		self.clients.claim();
	})());
});

function isNavigationRequest(req) {
	return req.mode === 'navigate' || (req.headers && req.headers.get('accept') && req.headers.get('accept').includes('text/html'));
}

self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;

	// Navigation requests: try network first, fallback to cache -> offline page
	if (isNavigationRequest(req)) {
		event.respondWith((async () => {
			try {
				const networkResponse = await fetch(req);
				// update cache with latest HTML
				const cache = await caches.open(CACHE_NAME);
				try { await cache.put(req, networkResponse.clone()); } catch (e) {}
				return networkResponse;
			} catch (err) {
				const cacheResp = await caches.match(req);
				if (cacheResp) return cacheResp;
				// try common offline pages
				const offlineMatch = await caches.match('/offline.html') || await caches.match('/web/offline.html');
				return offlineMatch || new Response('Offline', {status: 503, statusText: 'Offline'});
			}
		})());
		return;
	}

	// For other requests (assets): cache-first then network, and cache successful network responses.
	event.respondWith((async () => {
		const cache = await caches.open(CACHE_NAME);
		const cached = await cache.match(req);
		if (cached) return cached;
		try {
			const resp = await fetch(req);
			if (resp && resp.ok) {
				try { await cache.put(req, resp.clone()); } catch (e) {}
			}
			return resp;
		} catch (err) {
			// image fallback could be implemented here
			return new Response(null, {status: 504, statusText: 'Gateway Timeout'});
		}
	})());
});

// allow page to trigger skipWaiting
self.addEventListener('message', (event) => {
	if (!event.data) return;
	if (event.data.type === 'SKIP_WAITING') {
		self.skipWaiting();
	}
});

// end service worker
