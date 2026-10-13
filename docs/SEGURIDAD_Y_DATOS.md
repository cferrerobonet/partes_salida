# Seguridad y datos personales

La app trata datos de menores (nombre, foto, curso, teléfonos y correos del alumno y de la familia, y el historial de salidas). Este documento dice qué se trata, dónde y cómo se protege.

## 1. Qué datos y de dónde

| Origen | Se guarda | Se descarta al importar |
| --- | --- | --- |
| Excel de Educamos (214 columnas) | Nombre y apellidos, sexo, clase, NIA (o ID de persona si no hay), fecha de nacimiento (para avisar de la mayoría de edad), móvil, teléfono de emergencia y correo (EMAIL ALUMNO o, si falta, EMAILGOOGLE ALUMNO) del alumno; de cada familiar (hasta dos): nombre, parentesco, «recibe información», correo y teléfono | DNI, NIA de otros sistemas, tarjeta sanitaria, Seguridad Social, direcciones, nacionalidad, datos bancarios (IBAN, pagadores), centro de procedencia y el resto |
| ZIP de fotos | Una foto por alumno, reducida a 360 × 480 JPEG | Fotos que no son de ningún alumno del Excel, nombres de archivo y carpetas |
| Ajustes | Logos, sello, firma, textos, contactos de jefatura, impresora | — |

La lista exacta de columnas leídas está en `src/partes_salida/importar_excel.py` (`COLUMNAS`); el Excel y los ZIP originales no se copian: se leen en memoria. Al terminar, la app ofrece **enviarlos a la papelera** (y la ayuda recuerda vaciarla): conservarlos en el equipo es innecesario y contrario al RGPD.

## 2. Dónde vive cada cosa

| Qué | Dónde | Protección |
| --- | --- | --- |
| Padrón | `alumnado.bin` en la carpeta de datos del usuario | AES-256-GCM |
| Fotos | `fotos/<HMAC del id>.bin` | AES-256-GCM; el nombre no identifica a nadie |
| Historial de salidas y partes recurrentes | `seguimiento.bin` | AES-256-GCM |
| Clave de datos, clave de firma, contraseña SMTP | Llavero del sistema (Llavero de macOS, Administrador de credenciales de Windows), servicio `PartesSalida` | La del sistema y la sesión del usuario |
| Ajustes e imágenes | `ajustes.json`, `imagenes/` | Sin datos personales |
| Registro | `logs/` | Sin nombres, correos ni teléfonos |

No hay servidor ni nube. El repositorio de GitHub es público y **nunca** contiene datos: `.gitignore`, `.githooks/pre-commit` y `tests/test_seguridad.py` lo impiden (incluidas imágenes fuera de las carpetas propias y nombres «APELLIDOS, NOMBRE»).

## 3. Amenazas consideradas

| Amenaza | Medida | Límite |
| --- | --- | --- |
| Copia de la carpeta de datos, copia de seguridad del equipo, disco extraído | Cifrado con clave fuera de la carpeta (llavero) | — |
| Equipo con la sesión abierta y desatendido | Bloqueo de pantalla del sistema | **Sin login en la app** (decisión de CarlosFB, ADR-004): quien use la sesión ve los datos |
| Parte falsificado (fotocopia retocada, generado aparte) | QR firmado con Ed25519; la app del vigilante solo acepta claves dadas de alta | El papel en sí se puede copiar: el QR dice qué alumno y qué hora, el vigilante compara con la foto |
| Correo suplantado | Remitente corporativo `no_contestar@aplicaciones.epla.es` del dominio del centro | Depende de SPF/DKIM de IONOS |
| Actualización maliciosa | Solo se descarga de `github.com` por HTTPS con certificados de `certifi` | Instaladores sin firma de pago de Apple ni de Microsoft |
| Fuga por el repositorio público | Ver §2 | — |
| Llavero borrado o equipo nuevo | Los datos guardados no se pueden abrir: la app los borra y pide reimportar | Es el comportamiento buscado: no hay recuperación sin la clave |

## 4. Correo

Se envía solo a los familiares marcados en el momento y, si se elige «Por correo al alumno», al propio alumno; nunca de forma automática (tampoco en los recurrentes: se emiten al pulsar). Los dos mensajes llevan el parte (imagen y PDF). Por defecto, desmarcado si el alumno es mayor de edad y bloqueado si Educamos dice que el familiar no recibe información. El pie identifica al centro, indica que el buzón no recibe respuestas y cita el RGPD. Transporte: STARTTLS en el puerto 587 (o SSL en 465) contra `smtp.ionos.es`.

## 5. Firma del QR

Cada instalación genera su par Ed25519 la primera vez; la privada se queda en su llavero. La pública se entrega a la app del vigilante escaneando el QR de Ajustes → QR y verificación. Contenido firmado: identificador del alumno, hora de salida y hora de expedición (ver `android/ESPECIFICACION_QR.md`). No hay datos de nombre ni de familia en el QR.

## 6. Derechos y conservación

Los datos son una copia operativa de Educamos: se sustituyen en cada importación y se borran con «Vaciar todos los datos del alumnado» o desinstalando y borrando la carpeta de datos. El historial de salidas (fecha y hora, entrega, a quién se avisó y si el correo salió; nunca direcciones ni teléfonos) y los partes recurrentes viven mientras el alumno siga en el Excel: al importar uno nuevo se borra lo de las bajas. Se vacían por alumno, para todos o con el resto de datos (ADR-012). El historial impreso lleva el aviso de documento interno con datos personales.
