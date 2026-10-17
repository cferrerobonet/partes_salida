# Historial de versiones

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [SemVer](https://semver.org/lang/es/). La entrada de cada versión es también la nota de su release en GitHub. Lo más reciente arriba.

## [Sin publicar]

### Corregido

- **macOS: la actualización sustituye la app allí donde está instalada.** Hasta ahora se abría el DMG y, al arrastrar la app al acceso «Applications», la versión nueva quedaba en `/Applications` mientras el Dock seguía abriendo la vieja (por ejemplo, la de `/Applications/EPLA`), que volvía a avisar de la misma actualización. Ahora, tras descargarla y comprobar su sha256, la app se cierra, se cambia sola por la nueva en su misma carpeta y se vuelve a abrir. Si algo falla, se queda la versión anterior y lo avisa; si la carpeta no admite escritura, abre el DMG como antes y dice a qué carpeta arrastrarla. Deja un registro en `~/Library/Application Support/PartesSalida/logs/actualizacion_mac_*.log`.
- **Solo funciona a partir de la versión que lo lleve.** La actualización *a* esa versión todavía va por el camino antiguo: arrastrar la app del DMG a la carpeta donde está instalada (por ejemplo, `/Applications/EPLA`) y sustituir la anterior. En Windows no cambia nada: el instalador ya sustituye en la carpeta de antes (mismo `AppId`).

## [1.1.2] - 2026-10-16

### Corregido

- **El parte ya no sale cortado por la derecha ni por abajo.** Muchas impresoras no llegan al filo del papel; ahora el parte se reduce lo justo para caber en lo que la impresora puede imprimir, centrado y sin deformarse. En una impresora que imprime hasta el borde sale igual que antes. También al imprimir varios partes de golpe (uno por hoja).

### Añadido

- **Impresión en color o en blanco y negro.** En Ajustes → Impresión → «Color» se elige para este equipo. En blanco y negro, la foto, los logos, el sello y la firma salen en grises aunque la impresora esté puesta en color, y la vista previa lo enseña así. El parte que llega por correo sigue en color.

### Seguridad

- **Las actualizaciones se comprueban antes de instalarse.** El instalador descargado solo se abre si es idéntico al publicado (misma suma sha256 que da GitHub). Si no coincide o no se puede comprobar, la app lo avisa y ofrece la página de descargas para hacerlo a mano. La descarga ya no se queda colgada si la red falla.

## [1.1.1] - 2026-10-16

### Seguridad

- El programa ya no trae de serie el servidor ni el buzón de correo.

### Cambiado

- **Barrera común contra secretos y datos personales, versión 2.** La comprobación del repositorio detecta también datos personales (DNI, móviles, correos personales, listados), documentos y bases de datos, y pasa gitleaks; la CI «Secretos» revisa además todo el historial y hay gancho `pre-push`.
- **El servidor y el remitente del correo ya no vienen de serie.** Se escriben una vez en Ajustes → Correo (o llegan al importar la copia de ajustes de otro equipo). Los equipos que ya tenían el correo configurado no notan nada. Si faltan, la app no intenta enviar y avisa de qué falta.

## [1.1.0] - 2026-10-13

### Añadido

- **Entrega del parte en papel o por correo al alumno.** Bajo la vista previa, «Entrega del parte: En papel · Por correo al alumno». Siempre empieza en papel y se elige en cada parte; «Por correo» solo se puede elegir si Educamos tiene el correo del alumno (columna EMAIL ALUMNO o, si falta, EMAILGOOGLE ALUMNO). Por correo no se imprime nada: el alumno recibe su parte en el cuerpo del mensaje, para enseñarlo en la puerta desde el móvil, y en PDF adjunto.
- El aviso a la familia lleva también el parte, dentro del mensaje y en PDF.
- **Historial de salidas de cada alumno.** Cada parte emitido queda apuntado (fecha y hora de salida, expedición, entrega, a quién se avisó y si el correo salió). Se consulta desde la ficha («Ver historial»), con buscador, páginas y orden por columnas, se imprime en A4 (o a PDF) y se vacía desde la misma ventana. Va cifrado. Se conserva al reimportar el Excel o las fotos mientras el alumno siga; se borra con el alumno, al vaciarlo a mano (de uno o de todos, en Ajustes → Datos del alumnado) o con «Vaciar todos los datos del alumnado».
- **Partes recurrentes.** Para el alumnado que sale los mismos días a la misma hora todo el curso (deportistas de élite, conservatorio…): en la ficha, «Parte recurrente» abre una rejilla con los días de la semana y la hora de cada uno, el motivo, la entrega (papel o correo al alumno) y si se avisa a la familia.
- Botón **«Partes recurrentes · N hoy»** en la barra superior, en verde mientras quede alguno por emitir: lista los de hoy de las etapas visibles en el equipo e imprime todos los de papel de una vez, uno por hoja, y envía los de correo. Los ya emitidos hoy salen desmarcados. Otra pestaña lista todos los recurrentes para editarlos o quitarlos.

### Cambiado

- Sustituye la decisión de no guardar historial (ADR-009 → ADR-012).

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
