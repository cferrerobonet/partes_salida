# Registro de decisiones (ADR)

Formato: contexto → decisión → consecuencias. Una decisión no se reescribe: si cambia, se añade otra que la sustituye y se marca la anterior. Fecha en `AAAA-MM-DD`.

## ADR-001 · App de escritorio Python + PyQt6, misma base que Guardias de patio — 2026-10-08

- **Contexto**: uso intensivo en el equipo de jefatura, impresión directa en bandeja A6, sin servidor. Ya existe Guardias de patio con PyQt6, PyInstaller y publicación en GitHub probadas en macOS y Windows.
- **Decisión**: Python 3.11, PyQt6 6.7 (mismas versiones que Guardias), PyInstaller `onedir`, Inno Setup en Windows.
- **Consecuencias**: se reutilizan el comprobador de actualizaciones, la CI y las lecciones de empaquetado (nombres ASCII, sin UPX, `certifi`, `keyring.backends`).

## ADR-002 · Sin base de datos ni servidor: archivos cifrados locales — 2026-10-08

- **Contexto**: un padrón de ~2.200 alumnos que se sustituye entero al importar; nada se edita a mano; datos sensibles.
- **Decisión**: un JSON cifrado para el padrón y un archivo cifrado por foto. Sin SQLite ni nube.
- **Consecuencias**: carga en memoria (~1 MB) y búsqueda instantánea; restaurar = reimportar Excel y ZIP.

## ADR-003 · Cifrado AES-256-GCM con la clave en el llavero del sistema — 2026-10-08

- **Contexto**: CarlosFB quiere los datos cifrados en local pero sin login ni contraseñas que recordar.
- **Decisión**: clave aleatoria generada por la app y guardada con `keyring` (Llavero de macOS / Administrador de credenciales de Windows). Datos asociados por archivo y nombres de foto por HMAC.
- **Consecuencias**: protege copias y discos; no protege una sesión abierta. Si el llavero se pierde, se reimporta.

## ADR-004 · Sin login — 2026-10-08

- **Contexto**: cada jefatura usa su propio equipo con su sesión; un login añadiría fricción a una tarea de segundos.
- **Decisión**: sin usuarios ni contraseña en la app; se confía en la sesión del sistema.
- **Consecuencias**: ver §3 de [SEGURIDAD_Y_DATOS.md](SEGURIDAD_Y_DATOS.md). Revisable si la app se usa en equipos compartidos.

## ADR-005 · QR firmado con Ed25519, una clave por instalación — 2026-10-08

- **Contexto**: la futura app del vigilante debe distinguir partes auténticos. Un QR con solo NIA y hora se falsifica en un minuto.
- **Decisión**: el QR lleva NIA (o ID), salida, expedición, id de clave y firma Ed25519. Cada instalación tiene su clave; la pública se da de alta en la app Android escaneando un QR.
- **Consecuencias**: equipos aislados sin compartir secretos; el contrato vive en `android/` con vectores de prueba compartidos.

## ADR-006 · Una instalación independiente por etapa — 2026-10-08

- **Contexto**: cada Jefatura de Estudios usa la app por separado, con su sello y su firma (CarlosFB).
- **Decisión**: todos los ajustes son locales; las etapas visibles se eligen en cada equipo; se puede exportar/importar la configuración.
- **Consecuencias**: no hay sincronización ni conflicto entre equipos.

## ADR-007 · Compilar solo en GitHub — 2026-10-08

- **Contexto**: compilar en local da problemas y exige muchas dependencias (CarlosFB).
- **Decisión**: `compilar.yml` compila macOS y Windows al subir una etiqueta `vX.Y.Z` y adjunta DMG, instalador y portable al release. El gancho del asistente bloquea compilar en local.
- **Consecuencias**: publicar = skill `publicar` (commit, push, etiqueta, seguimiento de la CI).

## ADR-008 · Correo desde el buzón de Guardias de patio — 2026-10-08

- **Decisión**: `no_contestar@aplicaciones.epla.es` en `smtp.ionos.es:587`; contraseña en el llavero, nunca en el repositorio; contactos de jefatura de mañana y tarde en el pie.

## ADR-009 · Sin historial de partes — 2026-10-08

- **Contexto**: la maqueta incluía un historial con reimpresión.
- **Decisión**: se quita: la salida se registra en Educamos (CarlosFB). Tampoco hay número de parte.
- **Consecuencias**: menos datos guardados; para reimprimir se emite de nuevo.

## ADR-010 · Etapas automáticas desde la columna CLASE — 2026-10-08

- **Decisión**: las etapas del buscador son las que aparecen en el Excel (`INF`, `PRI`, `ESO`, `BAC`/`BAH`, `CFB`, `CFM`, `CFS`); cada equipo puede ocultar las que no use.

## ADR-011 · Pruebas: pytest-qt para la interfaz, Playwright para el correo — 2026-10-08

- **Contexto**: CarlosFB pide tests unitarios y Playwright como en sus webs.
- **Decisión**: Playwright no maneja ventanas Qt; se usa para abrir el correo HTML en Chromium (móvil y escritorio). La interfaz se prueba con pytest-qt sin pantalla.
