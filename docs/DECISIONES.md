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

## ADR-005 · QR firmado con Ed25519, una clave por instalación — 2026-10-08 · **La app Android, sustituida por la web (ADR-018)**

- **Contexto**: la futura app del vigilante debe distinguir partes auténticos. Un QR con solo NIA y hora se falsifica en un minuto.
- **Decisión**: el QR lleva NIA (o ID), salida, expedición, id de clave y firma Ed25519. Cada instalación tiene su clave; la pública se da de alta en la app Android escaneando un QR.
- **Consecuencias**: equipos aislados sin compartir secretos; el contrato vive en `android/` con vectores de prueba compartidos.

## ADR-006 · Una instalación independiente por etapa — 2026-10-08

- **Contexto**: cada Jefatura de Estudios usa la app por separado, con su sello y su firma (CarlosFB).
- **Decisión**: todos los ajustes son locales; las etapas visibles se eligen en cada equipo; se puede exportar/importar la configuración.
- **Consecuencias**: no hay sincronización ni conflicto entre equipos.

## ADR-007 · Compilar solo en GitHub — 2026-10-08

- **Contexto**: compilar en local da problemas y exige muchas dependencias (CarlosFB).
- **Decisión**: `compilar.yml` compila macOS y Windows al subir una etiqueta `vX.Y.Z` y adjunta DMG, instalador y portable al release. No se compila en local.
- **Consecuencias**: publicar = commit, push, etiqueta y seguimiento de la CI (`docs/OPERACIONES.md`).

## ADR-008 · Correo desde el buzón de Guardias de patio — 2026-10-08 · **Sustituida por ADR-020**

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
- **Consecuencias**: en una impresora sin márgenes, el parte sale como antes (148 × 105 mm); en las demás, algo más pequeño pero entero. Junto a esto, el ajuste «Color / Blanco y negro» fija el modo de la impresora y dibuja en grises sin depender del controlador. Ampliado por ADR-017.

## ADR-017 · Tamaño del parte en papel ajustable (zoom) — 2026-10-19

- **Contexto**: con ADR-016 el parte nunca se amplía, y en algunas impresoras los márgenes que declara el controlador son mayores que los reales: el parte sale entero pero no aprovecha el A6. CarlosFB pidió un control para ajustar el tamaño, como un zoom, junto al ajuste fino.
- **Alternativas**: un zoom sobre el papel (100 % = 148 × 105 reales, perdiendo la reducción automática de ADR-016); calcular solo el tamaño que llena el papel con un botón; o un zoom sobre lo que cabe, acotado.
- **Decisión**: `Ajustes.escala_pct` (50–200, 100 de serie) multiplica la escala que calcula `colocacion` tras la reducción automática. Por debajo del 100 % se centra y el ajuste fino lo mueve sin sacarlo del área; por encima puede sobresalir del área declarada, centrado, porque es quien calibra la impresora quien decide hasta dónde llega el papel. Solo afecta al papel: la vista previa y el parte del correo no cambian. Control en Ajustes → Impresión → «Tamaño» (número en %, −5 %, +5 % y 100 %), encima del ajuste fino y con el parte de prueba al lado.
- **Consecuencias**: los equipos ya instalados siguen al 100 % (igual que hasta ahora). La copia de ajustes lo lleva, como el resto de campos.

## ADR-018 · La app del vigilante pasa a ser una web instalable (PWA) — 2026-10-22

- **Contexto**: la app del vigilante era nativa de Android (Kotlin, APK firmado en la CI con una clave guardada en secretos). Solo servía en Android, exigía instalar un APK de origen desconocido y guardar la clave de firma. CarlosFB quiere que valga también en iPhone sin cuenta de desarrollador de Apple ni tiendas.
- **Alternativas**: Flutter para Android e iOS (en iPhone, sin la cuenta de pago de Apple, la app caduca a los 7 días y solo se instala desde el Mac); mantener Android y añadir iOS nativo (dos códigos y la misma cuenta de pago); o una web instalable.
- **Decisión**: web estática instalable en `vigilante/`, publicada en GitHub Pages por `vigilante.yml` tras pasar sus pruebas. Mismo contrato del QR (`ESPECIFICACION_QR.md` y `vectores_qr.json`), misma pantalla que la app Android. Firma con el Ed25519 del navegador y, si no lo tiene, noble-ed25519; lector con `BarcodeDetector` y, si no lo hay (iPhone), jsQR. Sin conexión gracias al service worker; los equipos de confianza, en el almacenamiento del navegador. Se retira `android/`, el trabajo del APK de `compilar.yml` y su clave de firma.
- **Consecuencias**: un solo código para Android y iPhone, sin instalar APK ni firmar nada; se actualiza sola. La primera vez pide permiso para la cámara y los equipos hay que darlos de alta otra vez en cada móvil (la app Android guardaba los suyos aparte). Si se borran los datos del navegador, se pierden los equipos dados de alta y hay que volver a escanearlos. La hora del veredicto es la de Madrid, no la del móvil.

## ADR-019 · Patria potestad exclusiva: el otro familiar no recibe avisos — 2026-11-06

- **Contexto**: CarlosFB pidió marcar en la ficha qué progenitor tiene en exclusiva el derecho a recibir los avisos, para no escribir al que no lo tiene. En Derecho español la guarda y custodia (con quién vive el menor) no quita la patria potestad (arts. 154 y 156 del Código Civil): separados o divorciados, los dos conservan el derecho a la información escolar. Solo lo pierde quien está privado de la patria potestad (art. 170) o tiene prohibido comunicarse con el menor por resolución judicial.
- **Alternativas**: «Guarda y custodia» (término incorrecto: bloquearía a quien sí tiene derecho); usar solo «Recibe información» de Educamos (vale para todos los equipos, pero depende de secretaría y se pisa en cada importación si no está al día); o una marca local en la ficha.
- **Decisión**: casilla «Patria potestad exclusiva» junto a cada familiar cuando hay dos. Marcar uno pide confirmación (recuerda que hace falta resolución judicial), pone al otro en gris con «Sin patria potestad: no recibe avisos» y bloquea su correo en `Tutor.puede_recibir_correo`, que usan la ficha y los recurrentes. Se guarda cifrada en `seguimiento.bin` por alumno con el nombre normalizado del titular, así sobrevive a las importaciones; si el Excel nuevo ya no trae ese nombre, no se avisa a nadie hasta revisarla. Se borra con la baja del alumno y con «Vaciar todos los datos».
- **Consecuencias**: la marca es de cada equipo (no hay servidor): en los demás hay que ponerla también, o que secretaría deje «Recibe información = No» en Educamos, que vale en todos. El teléfono del familiar bloqueado se sigue viendo.

## ADR-020 · Buzón propio y lo que vuelve: respuestas a jefatura, rebotes al historial — 2026-11-06

- **Contexto**: las familias responden al aviso aunque diga que no hace falta, y lo hacen al buzón de envío, que nadie lee y que compartía Guardias de patio. En ESO sobre todo, muchos correos rebotan porque la dirección ya no existe o está mal escrita, y jefatura no lo sabe: la app marcaba «Enviado» cuando el servidor aceptaba el correo, no cuando llegaba. Cada etapa tiene su jefatura y el buzón de envío es uno.
- **Alternativas**: un buzón de envío por etapa con reenvío en el servidor (más buzones; los rebotes llegan en bruto y la app sigue sin saberlo); la dirección de jefatura como remitente real (el servidor la rechaza o acaba en spam); solo «Responder a» (no cubre los rebotes ni a quien escribe la dirección a mano).
- **Decisión**: Partes deja el buzón de Guardias y usa uno propio (CarlosFB, 2026-11-06). Cada aviso lleva «Responder a» la jefatura del alumno: ESO, la suya; Bachillerato, Grado Superior y 2º de Carrocería (`correo.GRUPOS_MANANA`), la de mañana; Grado Básico y el resto de Grado Medio, la de tarde. Infantil y Primaria no tienen una sola: sin «Responder a». Cada correo lleva un Message-ID propio que se guarda en el historial. Con «Servidor IMAP» escrito en Ajustes → Correo, la app revisa el buzón cada 5 minutos mientras está abierta (`vuelta.py`): un rebote de un correo suyo deja el parte «Rebotado» con la dirección y avisa para llamar; un mensaje de una familia o de un alumno (que responde a un aviso suyo o escribe desde un correo del padrón) se reenvía a su jefatura con «Responder a» quien lo escribió y el original adjunto (CarlosFB prefiere el reenvío a verlo en la app). Lo tratado se marca en el servidor con una palabra clave (o como leído si no las admite) para que otro equipo no lo repita; no se borra nada.
- **Consecuencias**: las respuestas automáticas y los correos de direcciones que no están en el padrón no se reenvían (evita el spam); para estos, una respuesta automática del buzón en el servidor con las direcciones de jefatura. Un rebote solo se recoge en el equipo que hizo el parte y con la app abierta. Que no haya rebote no prueba que se haya leído. Un mensaje se reserva (marca) antes de reenviarlo para que dos equipos no lo dupliquen; si el reenvío falla 3 veces, se deja marcado y se avisa de que sigue en el buzón. De lo que pasa de 10 MB solo se leen las cabeceras y se reenvía sin el original. Los avisos llevan `Auto-Submitted: auto-generated` para que las respuestas de vacaciones no lleguen a jefatura.

## ADR-021 · ESO y Grado Básico: sale solo o acompañado, firmado en el QR — 2026-11-11

- **Contexto**: la jefatura de ESO pidió que el parte diga si el alumno sale solo o acompañado. Lo normal es que vengan a buscarlo; algunos se van solos (viven cerca) con la autorización de la familia, y el vigilante tiene que verlo claro al escanear. La app del vigilante no guarda datos del alumnado, así que solo sabe lo que lleva el QR.
- **Alternativas**: solo en el papel (el vigilante no lo vería en el móvil y se podría tachar); un campo sin firmar en el QR (falsificable); una lista de autorizados en el móvil del vigilante (datos del alumnado en el móvil).
- **Decisión** (CarlosFB, 2026-11-11): formato `PS2` con un campo de compañía firmado (`SO`, `SA`, `AO`, `AA` o `-`), en ESO y Grado Básico (`modelo.ETAPAS_COMPANIA`). Se marca una vez en la ficha la autorización de la familia, que vale hasta el 31 de agosto siguiente, y desde entonces sus partes (también los recurrentes) salen con «Solo»; ese día se puede cambiar a «Acompañado» con un clic. «Solo» sin autorización avisa y deja emitir. Texto completo según el sexo: SALE SOLO / SALE SOLA, ACOMPAÑADO / ACOMPAÑADA. En papel solo se imprime «sale solo», en negativo junto al QR. En el vigilante, banda maciza para «solo» y discreta para «acompañado». La autorización se marca a mano (no hay listado de jefatura ni campo en Educamos).
- **Corrección (2.1, CarlosFB, 2026-11-11):** en Grado Básico es al revés: salen solos de serie (`modelo.ETAPAS_SOLO_DE_SERIE`), también los recurrentes, y «Acompañado» es la excepción de un clic. No llevan la fila «Salir solo» ni el aviso de autorización.
- **Consecuencias**: versión mayor de las dos apps. `PS1` se sigue leyendo durante el curso 2026-2027 (sin banda). La autorización es de cada equipo (no hay servidor): la marca quien emite los partes de esa etapa. Se guarda cifrada en `seguimiento.bin` y se borra con la baja del alumno y con «Vaciar todos los datos».

## ADR-022 · Pantalla completa y laterales más anchas, como Programaciones — 2026-11-11

- **Contexto**: CarlosFB pidió que la ventana se abra a pantalla completa y que las columnas laterales sean algo más grandes, como en Programaciones.
- **Decisión**: `mostrar_al_frente` (arranque, icono de la barra, Dock, segunda instancia) usa `showFullScreen`. Sin barra de título, la barra superior lleva «Cerrar» en rojo a la derecha de «Ajustes»: hace lo que la X, oculta la ventana y la app sigue en la barra (no sale, a diferencia del «Salir» de Programaciones, porque Partes revisa el buzón y avisa de los recurrentes). Las columnas laterales siguen la regla de Programaciones: con lo que sobra tras dejar 1040 px a la ficha, crecen a partes iguales hasta 360 y 400 px; en pantallas pequeñas, 300 y 340.
- **Consecuencias**: en una pantalla de 1800 px, 360 · 1040 · 400. «Siempre encima» con pantalla completa tapa todo: tiene poco sentido usar las dos. Prueba: `test_laterales_mas_anchas_sin_quitar_sitio_a_la_ficha` y `test_se_abre_a_pantalla_completa_y_cerrar_la_oculta`.
