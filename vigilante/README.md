# App del vigilante (web)

Web instalable (PWA) para el móvil del vigilante de la puerta: escanea el QR del parte y dice en grande si el alumno **puede salir**, si **todavía no** es su hora, si el parte es **de otro día** o si **no vale** (falso, alterado o de un equipo que no está dado de alta). Solo verifica: no firma, no guarda datos del alumnado y, una vez abierta, no necesita red.

**Dirección:** <https://cferrerobonet.github.io/partes_salida/>. Funciona en Android y en iPhone, sin tiendas ni cuentas de desarrollador.

Sustituye a la app Android (hasta la versión 1.3.1). El porqué está en [ADR-018](../docs/DECISIONES.md).

## Instalar en el móvil

1. Abrir la dirección en el navegador del móvil: **Chrome** en Android o **Safari** en iPhone.
2. Instalarla en la pantalla de inicio: en Android, menú ⋮ → «Instalar aplicación» o «Añadir a pantalla de inicio»; en iPhone, botón Compartir → «Añadir a pantalla de inicio».
3. Abrirla desde el icono **Vigilante**, pulsar «Equipos de confianza» → «Dar de alta» y escanear el QR de Ajustes → QR y verificación de cada equipo de jefatura. La primera vez pide permiso para la cámara.

Con eso ya funciona sin cobertura. Las versiones nuevas se instalan solas la siguiente vez que se abre con conexión.

## Piezas

| Archivo | Qué hace |
| --- | --- |
| [ESPECIFICACION_QR.md](ESPECIFICACION_QR.md) + [vectores_qr.json](vectores_qr.json) | Contrato del QR con la app de escritorio, que firma (`src/partes_salida/firma.py`). Los dos lados pasan los mismos vectores (`tests/test_seguridad.py` y `tests/test_vigilante.py`) |
| `verificador.js` | Verificación: formato, equipo, firma Ed25519 (la del navegador o, si no la tiene, `vendor/noble-ed25519.js`) y veredicto con la hora de Madrid |
| `app.js` · `index.html` · `estilos.css` | Pantalla: tarjeta del resultado, «Escanear parte», «Equipos de confianza». Colores y letras de la app de escritorio (`DESIGN.md`) |
| `vendor/jsQR.js` | Lector de QR para los navegadores sin `BarcodeDetector` (Safari en iPhone) |
| `sw.js` · `manifest.webmanifest` | Funcionamiento sin conexión e instalación |

Las librerías de `vendor/` son de terceros, con su licencia al lado: noble-ed25519 (MIT) y jsQR (Apache 2.0).

## Publicar y probar

- Se publica sola en GitHub Pages (`.github/workflows/vigilante.yml`) con cada push a `main` que la toque, después de pasar sus pruebas en Chromium: vectores del QR con los dos motores de firma, pantalla, cámara simulada con un QR de verdad, lector sin `BarcodeDetector` con el QR del parte pequeño (como en el iPhone) y modo sin conexión. `scripts/web_vigilante.py` monta lo que se publica (añade las fuentes de la app de escritorio, los iconos de `imagenes/vigilante-*.png` y la versión).
- En local: `make vigilante` y abrir <http://localhost:8000> (la cámara del navegador funciona en `localhost`).
