# Historial de versiones

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [SemVer](https://semver.org/lang/es/). La entrada de cada versión es también la nota de su release en GitHub. Lo más reciente arriba.

## [0.1.0] - 2026-10-08

Primera versión.

### Añadido

- Ventana principal en tres zonas: búsqueda sin tildes y tolerante a erratas con filtros de etapa y curso; ficha con foto, etapa, curso, NIA, edad y contactos de la familia (copiar teléfono); hora de salida, vista previa del parte e «Imprimir parte» (⌘P / Ctrl+P).
- Parte DIN-A6 horizontal con logos, foto, etapa, curso, nombre, hora de salida destacada, texto en femenino o masculino, fecha y hora de expedición, sello, firma y QR firmado.
- Aviso por correo a madre, padre o ambos, con logos y contactos de jefatura de mañana y tarde; desmarcado para mayores de edad y bloqueado si Educamos dice que el familiar no recibe información.
- Importación del Excel de Educamos (solo las columnas necesarias) y de uno o varios ZIP de fotos con subcarpetas; confirmación de fotos con nombre casi igual.
- Datos del alumnado y fotos cifrados en el equipo (AES-256-GCM, clave en el llavero del sistema).
- Ajustes: logos, sello y firma, textos, etapas visibles, correo (con correo de prueba), impresora y ajuste fino, QR para la app del vigilante, arranque con la sesión, exportar e importar ajustes.
- Icono en la barra de menús o la bandeja, una sola instancia y aviso de versiones nuevas.
- Compilación en GitHub para macOS y Windows (instalador y portable) con prueba de arranque.
