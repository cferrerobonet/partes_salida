# Especificación funcional

Estado: implementado en 0.1.0 salvo lo marcado como *pendiente* (ver [PENDIENTE.md](PENDIENTE.md)). Si este documento contradice al código, manda el código y se corrige aquí.

## 1. Propósito

Cuando un alumno sale del centro antes de su hora con autorización, Jefatura de Estudios le entrega un **pase impreso** que enseña al vigilante de la puerta. La app lo emite en segundos, con foto para que el vigilante lo identifique, y puede avisar a la familia por correo.

## 2. Usuarios y contexto

| Quién | Qué hace | Contexto |
| --- | --- | --- |
| Jefatura de Estudios de cada etapa (usuario principal) | Busca al alumno, comprueba la familia, fija la hora, imprime y avisa | La app está abierta todo el día en segundo plano; se usa muchas veces y con prisa |
| Vigilante de la puerta | Lee el pase; en el futuro escanea el QR con la app Android | Mira foto, nombre y hora en un segundo |
| Familia | Recibe el aviso por correo | Correo corporativo, sin responder |

Cada jefatura instala la app en su equipo y la configura a su manera (logos, sello, firma, textos, etapas visibles); las instalaciones no se comunican entre sí.

## 3. Casos de uso

### CU-1 Emitir un parte (camino principal)

1. Escribir parte del nombre o apellidos (sin tildes, en cualquier orden, con erratas) o filtrar por etapa y curso.
2. La lista se reduce; el primero queda elegido y su ficha aparece en el centro.
3. Comprobar foto, etapa y curso; ver teléfonos y correos de la familia.
4. Fijar la hora de salida (por defecto, la actual redondeada a 5 min; botón «Ahora»).
5. Marcar o desmarcar «Avisar por correo» en cada familiar.
6. Elegir la **entrega del parte**: «En papel» (de serie) o «Por correo al alumno» (solo si Educamos tiene su correo).
7. «Imprimir parte» o «Enviar parte» (⌘P / Ctrl+P, el botón dice cuál): sale el DIN-A6 o el correo al alumno y, si hay casillas marcadas, el aviso a la familia. El parte queda en el historial del alumno.

**Criterios de aceptación**

- De abrir la ventana a tener el parte en la mano, con teclado: escribir, Intro, ⌘P.
- El parte impreso coincide con la vista previa (mismo dibujo, en milímetros).
- El parte cabe entero en el área que la impresora puede imprimir: si no llega al filo del papel, se reduce en proporción (nunca se amplía ni se deforma) y se centra; también en los recurrentes, uno por hoja. El ajuste fino lo desplaza sin sacarlo de esa área.
- En blanco y negro, la impresora se pone en escala de grises y el parte (foto, logos, sello, firma y tintas) se dibuja ya en grises, así no depende del controlador; la vista previa lo sigue. El parte del correo sale siempre en color.
- Si la impresión se cancela o falla, no se envía ningún correo ni se apunta en el historial.
- Si el correo falla, el parte ya impreso vale; se avisa con los teléfonos de la familia para llamar. Si fallaba el del alumno, se avisa para imprimirlo.
- Por correo al alumno no se imprime nada; al elegir otro alumno, la entrega vuelve a «En papel».
- Sin la contraseña del correo, un parte por correo se ofrece imprimir en papel.

### CU-2 Importar o actualizar el alumnado

- Excel de Educamos (`.xls` o `.xlsx`): sustituye el padrón entero. Columnas por cabecera; se leen solo las de `importar_excel.COLUMNAS`. Alumnos sin NIA se identifican por su ID de persona.
- Fotos: uno o varios ZIP, con carpetas y subcarpetas; archivos `APELLIDOS, NOMBRE.png|jpg`. Se casan sin tildes ni mayúsculas; las casi iguales (≥ 88 % de parecido) se confirman en una ventana; las que no son de nadie se ignoran. Si un alumno sale dos veces, gana la foto más reciente del ZIP.
- **Volver a importar**: un Excel nuevo sustituye a todo el alumnado (es el colegio entero) y borra las fotos, el historial y el parte recurrente de quien ya no está; los de quien sigue se conservan. Unas fotos nuevas sustituyen a las que ya tenía cada alumno y se añaden las que faltaban.
- **Después de importar**, la app ofrece enviar el Excel o los ZIP a la papelera (RGPD): los datos ya están cifrados en la app.
- **Ayuda «?»** junto a cada importación: dónde se descarga el Excel en Educamos (Datos → Import/Export → Exportación de datos de los alumnos → Exportar) y cómo preparar el ZIP de fotos. Textos y capturas de Educamos en `ui/ayuda.py` y `recursos/ayuda_educamos_*.png`.
- **Fin de curso**: «Vaciar todos los datos del alumnado» borra padrón, fotos, historial y partes recurrentes; ajustes, sello y firma se conservan.
- También por arrastrar y soltar sobre la zona de cada importación.

### CU-3 Configurar el equipo (Ajustes)

| Apartado | Contenido |
| --- | --- |
| Logos e identidad | Logo izquierdo y derecho (por defecto escudo de EPLA y Colegios Amigó), nombre del centro, localidad |
| Sello y firma | Sello de la etapa y firma del Jefe de Estudios (se les quita el fondo blanco), texto bajo la firma |
| Textos del parte | Título y texto de dos líneas en femenino y masculino, con variables `{hora}`, `{nombre}`, `{curso}`, `{etapa}`, `{fecha}` |
| Datos del alumnado | Importaciones, cifras, fotos por confirmar, etapas detectadas (se pueden ocultar), cifrado, vaciar el historial de todos, borrar datos |
| Correo | SMTP, remitente, contraseña (llavero), contactos de jefatura de mañana y tarde, **correo de prueba** a una dirección cualquiera |
| Impresión | Impresora, orientación del parte (horizontal 148 × 105 o vertical 105 × 148), color o blanco y negro, imprimir sin diálogo, ajuste fino en mm, parte de prueba |
| QR y verificación | Nombre del equipo, QR con la clave pública para la app del vigilante |
| General | Arrancar con la sesión, siempre encima, exportar o importar ajustes, versión y actualizaciones |

Cada cambio se guarda al momento.

### CU-4 Restaurar un equipo

Instalar, importar el Excel y los ZIP y, opcionalmente, la copia de ajustes exportada. La contraseña del correo se vuelve a escribir. Sin nube ni copias de datos.

### CU-5 Verificar un parte (app Android, *pendiente*)

El vigilante escanea el QR: «auténtico» con NIA y hora de salida, o «falso / alterado / de un equipo desconocido». Contrato en [../android/ESPECIFICACION_QR.md](../android/ESPECIFICACION_QR.md).

### CU-6 Consultar, imprimir o vaciar el historial de un alumno

En la ficha, «Historial» resume cuántas salidas tiene y la última; «Ver historial» abre la lista: fecha y hora de salida, expedición, entrega (impreso, por correo al alumno, recurrente), avisados y estado del correo. Con buscador, 10 filas por página (5/10/15/20/50), «Limpiar filtros», cabeceras ordenables y pie «Mostrando 1–10 de N» con primera, anterior, cinco números, siguiente y última; la salida más reciente sale resaltada. «Imprimir…» saca el historial en A4 por la impresora o a PDF; «Vaciar historial…» lo borra tras confirmar. Para todo el alumnado: Ajustes → Datos del alumnado.

### CU-7 Partes recurrentes

1. En la ficha, «Parte recurrente → Configurar…»: rejilla de lunes a viernes; se marcan los días y la hora de cada uno («Misma hora para todos los días marcados» la copia). Motivo opcional, entrega (papel o correo al alumno) y si se avisa a la familia cada día.
2. Cada día, el botón **«Partes recurrentes · N hoy»** de la barra (verde mientras quede alguno) lista los de hoy de las etapas visibles en el equipo, por hora. Los pendientes salen marcados; los ya emitidos hoy, desmarcados.
3. «Imprimir N (uno por hoja) y enviar M por correo»: todos los de papel en un solo trabajo de impresión, un parte por hoja; los de correo, al alumno; los avisos, a la familia si está marcado. Cada uno queda en el historial como recurrente.
4. La pestaña «Todos» lista los recurrentes para editarlos o quitarlos.

**Criterios de aceptación**: un recurrente de una etapa oculta no sale ni se imprime; si la impresión se cancela no se apunta ni se envía nada; el fin de semana no hay partes.

## 4. Reglas de negocio

| ID | Regla |
| --- | --- |
| RN-1 | Etapa y curso salen de la columna CLASE: `INF` Infantil, `PRI` Primaria, `ESO`, `BAC`/`BAH` Bachillerato (Ciencias/Humanidades), `CFB` FP Grado Básico, `CFM` Grado Medio, `CFS` Grado Superior. Las etapas del buscador son las presentes en el Excel |
| RN-2 | Género del parte y del correo según la columna SEXO (`F` femenino; si falta, masculino y aviso al importar) |
| RN-3 | Un familiar con «Recibe información = FALSE» o sin correo no se puede marcar |
| RN-4 | Alumnado mayor de edad: el aviso sale desmarcado y con advertencia (puede marcarse) |
| RN-5 | Teléfonos en la ficha, nunca en el parte impreso |
| RN-6 | El parte lleva el NIA (pequeño), la fecha y hora de expedición y un QR firmado; vale solo para esa fecha y hora |
| RN-7 | La hora de salida puede ser anterior a la actual (se avisa «Esa hora ya ha pasado») |
| RN-8 | Remitente: el buzón compartido de las apps, escrito en Ajustes → Correo (no viene de serie); el correo incluye los contactos de jefatura de mañana y tarde que estén rellenos |
| RN-9 | El correo del alumno sale de EMAIL ALUMNO o, si está vacía, de EMAILGOOGLE ALUMNO. Sin correo, solo papel |
| RN-10 | Entrega en papel por defecto; por correo es una elección de jefatura en cada parte (o en la ficha del recurrente) |
| RN-11 | El historial y el recurrente de un alumno existen mientras esté en el Excel importado |

## 5. Requisitos no funcionales

- **Siempre a mano**: cerrar la ventana la oculta; la app sigue en la barra de menús o la bandeja. Una sola instancia: abrirla otra vez trae la ventana al frente.
- **Ventana compacta** (1100 × 700, mínimo 980 × 620), modo claro y oscuro según el sistema.
- **Privacidad**: ver [SEGURIDAD_Y_DATOS.md](SEGURIDAD_Y_DATOS.md).
- **Presentación**: al abrir, una tarjeta corporativa (escudo, título, versión, autoría) muestra el progreso real de la carga; dura al menos 1,4 s y se cierra con un fundido. No sale al arrancar oculta con la sesión.
- **Actualización**: al arrancar (y cada 4 horas) consulta GitHub. El instalador descargado solo se abre si su suma sha256 coincide con la que publica GitHub; si no coincide o no se puede comprobar, se avisa y se ofrece la página de descargas. Si hay versión nueva: diálogo por encima de la app con las novedades del CHANGELOG y «Actualizar ahora» destacado; si se pospone, botón dorado «Actualizar a X.Y.Z» fijo en la barra superior. También en Ajustes → General → «Buscar actualizaciones».
- **Plataformas**: macOS (Apple Silicon e Intel según el runner de GitHub) y Windows 10/11 x64; instalación sin permisos de administrador.
