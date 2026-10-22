// Guarda la app entera en el móvil para que funcione sin conexión en la puerta.
// Cada publicación cambia VERSION (scripts/web_vigilante.py): el navegador instala la nueva,
// borra la caché anterior y la app se recarga sola cuando no está escaneando.

const VERSION = "__VERSION__";
const CACHE = `vigilante-${VERSION}`;

// Todo lo que publica scripts/web_vigilante.py (lo vigila tests/test_vigilante.py).
const ARCHIVOS = [
  "./",
  "index.html",
  "estilos.css",
  "app.js",
  "verificador.js",
  "vendor/noble-ed25519.js",
  "vendor/jsQR.js",
  "manifest.webmanifest",
  "icono.svg",
  "iconos/icono-192.png",
  "iconos/icono-512.png",
  "iconos/icono-maskable-512.png",
  "iconos/apple-touch-icon.png",
  "fuentes/Barlow-Regular.ttf",
  "fuentes/Barlow-SemiBold.ttf",
  "fuentes/Barlow-Bold.ttf",
  "fuentes/BarlowCondensed-Bold.ttf",
  "fuentes/JetBrainsMono.ttf",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ARCHIVOS.map((a) => new Request(a, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((c) => c.startsWith("vigilante-") && c !== CACHE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  );
});

// Primero la copia guardada (la puerta no siempre tiene cobertura); lo que no esté, de la red.
self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET" || new URL(peticion.url).origin !== self.location.origin) return;
  evento.respondWith(
    caches.match(peticion, { ignoreSearch: true })
      .then((guardada) => guardada || (peticion.mode === "navigate" ? caches.match("./") : null))
      .then((guardada) => guardada || fetch(peticion)),
  );
});
