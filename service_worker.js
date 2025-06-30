/**
 * AI Companion - Service Worker
 * Final Version: June 29, 2025
 * Handles caching for offline functionality and fast load times.
 */

const CACHE_NAME = 'ai-companion-v1.1'; // Updated version name
const urlsToCache = [
    '/',
    '/main',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/manifest.json',
    '/static/icons/android-icon-192.png',
    '/static/icons/android-icon-512.png',
    '/static/icons/apple-icon-180.png',
    // This service worker file itself.
    '/static/service-worker.js',
    // External resources to cache for true offline capability
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/dompurify@3.0.11/dist/purify.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js'
];

// Install event: Caches all critical application shell assets.
self.addEventListener('install', event => {
    self.skipWaiting(); // Force the new service worker to activate immediately
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[Service Worker] Caching application shell');
                return cache.addAll(urlsToCache);
            })
            .catch(error => {
                console.error('[Service Worker] Failed to cache during install:', error);
            })
    );
});

// Activate event: Cleans up old, unused caches to save space.
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(cacheName => {
                    // Delete all caches that are not the current one
                    return cacheName !== CACHE_NAME;
                }).map(cacheName => {
                    console.log('[Service Worker] Deleting old cache:', cacheName);
                    return caches.delete(cacheName);
                })
            );
        }).then(() => self.clients.claim()) // Take control of all open clients immediately
    );
});

// Fetch event: Handles requests with a network-first or cache-first strategy.
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // --- STRATEGY: Network Only for API and Socket.IO ---
    // These requests must always go to the network and should never be cached.
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/') || url.pathname.startsWith('/socket.io/')) {
        // Do not use respondWith here, let the browser handle it.
        // This ensures the request completely bypasses the service worker's cache logic.
        return;
    }

    // --- STRATEGY: Cache First, Falling Back to Network (for all other GET requests) ---
    // Ideal for static assets that make up the app shell.
    if (request.method === 'GET') {
        event.respondWith(
            caches.match(request)
                .then(cachedResponse => {
                    // If a cached response is found, return it immediately.
                    if (cachedResponse) {
                        return cachedResponse;
                    }

                    // If not in cache, fetch from the network.
                    return fetch(request).then(networkResponse => {
                        // Check if we received a valid response to cache.
                        if (!networkResponse || networkResponse.status !== 200) {
                            return networkResponse;
                        }

                        // Clone the response because it's a stream that can only be consumed once.
                        const responseToCache = networkResponse.clone();

                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(request, responseToCache);
                            });

                        return networkResponse;
                    });
                })
        );
    }
});
