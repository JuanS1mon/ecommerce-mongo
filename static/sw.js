// Service Worker básico para PWA
const CACHE_NAME = 'tienda-online-v1';
const urlsToCache = [
  '/',
  '/static/ecomerce/productos/productos_tienda.js',
  '/static/ecomerce/carrito.js',
  '/static/ecomerce/cart_button.js',
  '/static/config.js',
  '/static/css/cart_buttons.css',
  '/static/tailwind.js'
  // Removed external CDN URLs to avoid CORS issues
];

// Instalación del service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Activación del service worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Interceptar peticiones
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Retornar respuesta del cache si existe, sino hacer petición
        return response || fetch(event.request);
      })
  );
});