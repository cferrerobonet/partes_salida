# Historial de versiones

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [SemVer](https://semver.org/lang/es/). La entrada de cada versión es también la nota de su release en GitHub. Lo más reciente arriba.

## [1.0.0] - 2026-10-08

Primera versión estable.

### Añadido

- Orientación del parte en Ajustes → Impresión: **horizontal** (148 × 105 mm, el diseño de siempre) o **vertical** (105 × 148 mm, con la hora en una franja a todo el ancho). La vista previa, la impresión y el parte de prueba siguen la elegida.

### Corregido

- La «h» de «12:30 h» ya no puede quedarse sola en otra línea del parte.

## [0.4.0] - 2026-10-08

### Cambiado

- La ayuda del Excel enseña las capturas de Educamos bajo cada paso (menú Datos → Import/Export y pestaña Exportación) y nombra la opción exacta: «Exportación de datos de los alumnos», no la de «histórico».

## [0.3.0] - 2026-10-08

### Añadido

- Botón de ayuda «?» junto a la importación del Excel (dónde descargarlo en Educamos: Datos → Import/Export → Exportación de datos de los alumnos → Exportar) y junto a la de las fotos (cómo preparar el ZIP y nombrar cada foto «APELLIDOS, NOMBRE»).
- Tras importar el Excel o los ZIP, la app ofrece enviarlos a la papelera: los datos ya están cifrados y el original tiene datos sensibles (RGPD).

### Cambiado

- «Vaciar todos los datos del alumnado» pasa al apartado «Fin de curso», para empezar de cero en septiembre.
- Ajustes explica qué pasa al volver a importar: un Excel nuevo sustituye a todo el alumnado (y borra las fotos de las bajas); unas fotos nuevas sustituyen a las anteriores y se añaden las que falten.

## [0.2.0] - 2026-10-08

Primera versión con instaladores para macOS y Windows.

### Añadido

- Pantalla de presentación al abrir la app, con el escudo, la versión, la autoría y el progreso real de la carga («Descifrando los datos del alumnado…»). La misma tarjeta, en Ajustes → General → «Acerca de…».
- Aviso de versión nueva bien visible: al abrir la app sale una ventana por encima con las novedades y «Actualizar ahora»; si se deja para más tarde, queda un botón dorado «Actualizar a X.Y.Z» en la barra superior. Con la app abierta todo el día, se vuelve a comprobar cada 4 horas.

### Corregido

- La prueba automática de arranque de macOS no llegaba a abrir la app (su ruta tiene espacios).

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
