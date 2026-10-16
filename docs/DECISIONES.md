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

- **Decisión**: el buzón compartido de las apps en el servidor de correo del centro; contraseña en el llavero, nunca en el repositorio; contactos de jefatura de mañana y tarde en el pie. Servidor y buzón no se escriben en el repositorio: ver ADR-015.

## ADR-009 · Sin historial de partes — 2026-10-08 · **Sustituida por ADR-012**

- **Contexto**: la maqueta incluía un historial con reimpresión.
- **Decisión**: se quita: la salida se registra en Educamos (CarlosFB). Tampoco hay número de parte.
- **Consecuencias**: menos datos guardados; para reimprimir se emite de nuevo.

## ADR-010 · Etapas automáticas desde la columna CLASE — 2026-10-08

- **Decisión**: las etapas del buscador son las que aparecen en el Excel (`INF`, `PRI`, `ESO`, `BAC`/`BAH`, `CFB`, `CFM`, `CFS`); cada equipo puede ocultar las que no use.

## ADR-011 · Pruebas: pytest-qt para la interfaz, Playwright para el correo — 2026-10-08

- **Contexto**: CarlosFB pide tests unitarios y Playwright como en sus webs.
- **Decisión**: Playwright no maneja ventanas Qt; se usa para abrir el correo HTML en Chromium (móvil y escritorio). La interfaz se prueba con pytest-qt sin pantalla.

## ADR-012 · Historial de salidas por alumno, mientras el alumno exista — 2026-10-13

- **Contexto**: CarlosFB pide un registro permanente de las salidas de cada alumno, consultable e imprimible, fácil de borrar y que no se pierda al actualizar el Excel o las fotos. Sustituye a ADR-009.
- **Decisión**: `seguimiento.bin`, cifrado como el padrón (AES-GCM, datos asociados `seguimiento`), con el historial y los partes recurrentes por identificador de alumno. Al importar un Excel se conserva lo de quien sigue y se borra lo de quien ya no está; importar fotos no lo toca; se vacía por alumno, para todos (Ajustes → Datos del alumnado) o con «Vaciar todos los datos del alumnado». Informe en A4 con `QTextDocument` y el diálogo del sistema (impresora o PDF), nunca por la impresora A6.
- **Alternativas**: SQLite (descartada: ADR-002, un JSON cifrado basta para el volumen de un curso); guardarlo dentro de `alumnado.bin` (descartada: el padrón se sustituye entero en cada importación).
- **Consecuencias**: el historial es de cada equipo, como el resto (ADR-006). Un correo que estaba saliendo al cerrar la app queda «Sin confirmar».

## ADR-013 · Parte por correo al alumno, a elección en cada parte — 2026-10-13

- **Contexto**: para no imprimir, CarlosFB quiere mandar el parte al propio alumno; el envío ha de ser una elección de quien usa la app: correo o papel.
- **Decisión**: se leen `EMAIL ALUMNO` y, si viene vacía, `EMAILGOOGLE ALUMNO` (exportación de Educamos de 2026-10). «Entrega del parte: En papel · Por correo al alumno», en papel por defecto y de nuevo en papel al cambiar de alumno. Por correo no se imprime; el parte va como PNG en el cuerpo (1400 px: el QR se lee desde la pantalla del móvil) y en PDF A6 adjunto. El aviso a la familia sigue con sus casillas y también lleva el parte. Sin contraseña del correo, se ofrece imprimirlo.
- **Alternativas**: casilla «enviar al alumno» además de imprimir (descartada: no ahorra papel); correo escrito a mano en la ficha (descartada: CarlosFB, el envío se usa en las etapas en que Educamos tiene el correo).
- **Consecuencias**: el correo del alumno pasa a `COLUMNAS` y a SEGURIDAD_Y_DATOS.

## ADR-014 · Partes recurrentes con rejilla semanal y emisión de golpe — 2026-10-13

- **Contexto**: alumnado que sale los mismos días a la misma hora todo el curso (deportistas, conservatorio) y necesita su parte cada día.
- **Decisión**: por alumno, los días lunes a viernes con su hora (rejilla de cinco días con hora propia y «misma hora para todos»), motivo opcional, entrega y aviso a la familia. Botón en la barra con los pendientes de hoy; emite solo los de las etapas visibles del equipo; todos los de papel en un solo trabajo de impresión, uno por hoja; los emitidos hoy salen desmarcados para no duplicarlos.
- **Alternativas**: fechas de inicio y fin (descartada por ahora: es para todo el curso y se quita a mano); emisión automática a una hora (descartada: imprimir sin nadie delante gasta papel y puede fallar en silencio).
- **Consecuencias**: el parte de un recurrente es un parte normal (mismo QR y misma maqueta) marcado como recurrente en el historial.

## ADR-015 · Ningún dato del servidor de correo en el repositorio — 2026-10-14

- **Contexto**: el repositorio es público. `ajustes.py` traía de serie el servidor, el puerto y el buzón del correo, y varios documentos y tests los repetían. CarlosFB pide que no haya información del servidor SMTP en los repositorios, ni ahora ni en el futuro.
- **Decisión**: servidor y remitente vacíos por defecto (el puerto 587, estándar, se mantiene). Se escriben en Ajustes → Correo de cada equipo o llegan con la copia de ajustes de otro equipo; la contraseña sigue en el llavero. Sin servidor o remitente, la app no intenta enviar y lo dice («falta configurar el servidor de correo en Ajustes → Correo»). Documentos y tests usan marcadores o direcciones `@ejemplo.es`.
- **Barreras**: `scripts/comprobar_secretos.sh` (común a todas las apps) desde `.githooks/pre-commit` y desde la CI `Secretos`, más el escaneo de secretos y la protección de push de GitHub.
- **Consecuencias**: los equipos ya instalados conservan sus ajustes (el archivo guarda todos los campos). Uno nuevo hay que configurarlo o importar la copia de ajustes. Sustituye en parte a ADR-008.

## ADR-016 · El parte se ajusta al área imprimible de la impresora — 2026-10-16

- **Contexto**: el parte se dibujaba a tamaño real desde la esquina del papel. Las impresoras que no llegan al filo (márgenes físicos) cortaban el borde derecho y el inferior (CarlosFB, en papel).
- **Alternativas**: pedir que cada equipo corrija con el ajuste fino (no recupera lo que cae fuera); encoger siempre un porcentaje fijo (depende de la impresora); o leer el área imprimible real.
- **Decisión**: `impresion.area_imprimible` resta al papel los márgenes físicos de la impresora (`minimumMargins`) o los de la página, los mayores; `colocacion` reduce el parte en proporción para caber, nunca lo amplía, lo centra y aplica el ajuste fino sin sacarlo del área. Igual en la impresión en bloque.
- **Consecuencias**: en una impresora sin márgenes, el parte sale como antes (148 × 105 mm); en las demás, algo más pequeño pero entero. Junto a esto, el ajuste «Color / Blanco y negro» fija el modo de la impresora y dibuja en grises sin depender del controlador.
