---
name: Partes de salida
description: Herramienta de escritorio de Jefatura de Estudios para imprimir el pase de salida DIN-A6; tres zonas, tokens verde EPLA y dorado, claro y oscuro.
colors:
  accent: "#2c7a3a"
  accent_soft: "#e2f0e3"
  gold: "#b97a12"
  gold_soft: "#fbf0d9"
  bg: "#f3f5f1"
  surface: "#ffffff"
  surface2: "#eef2ec"
  line: "#d9e0d5"
  fg: "#1d2a20"
  muted: "#5d6b60"
  warn: "#9a5b00"
  danger: "#a32d2d"
  tinta_parte: "#1b1f1c"
typography:
  display: { fontFamily: "Barlow Condensed", weights: [600, 700, 800] }
  body: { fontFamily: "Barlow", weights: [400, 500, 600, 700] }
  mono: { fontFamily: "JetBrains Mono", use: "NIA y teléfonos" }
---

# Design System: Partes de salida

Fuente de verdad del código: `src/partes_salida/ui/estilo.py` (tokens `CLARO` y `OSCURO`, hoja de estilos) y `src/partes_salida/parte.py` (parte impreso). Maqueta aprobada por CarlosFB el 2026-10-08; capturas vigentes en `docs/capturas/` (`make capturas`).

## Overview

**Creative North Star: «La ventanilla de jefatura».** Una herramienta de mostrador: se usa decenas de veces al día, con un alumno delante y prisa. Todo lo necesario está a la vista y en el orden en que se hace: buscar → comprobar → imprimir.

### Named Rules

- **The Three Zones Rule.** Ventana principal en tres columnas fijas: buscar (300 px) · alumno y familia (flexible) · hora, vista previa e imprimir (340 px). El botón de imprimir está siempre en el mismo sitio, abajo a la derecha.
- **The Just Enough Fields Rule.** Solo los campos que pide el flujo. Un campo nuevo necesita un motivo de uso real (se quitó «motivo» de la maqueta por esta regla).
- **The Token Rule.** Todo color de la interfaz sale de `T[...]`; nada de hexadecimales sueltos en widgets.
- **The Paper Rule.** El parte impreso y el correo no siguen el tema: tinta oscura sobre blanco siempre.
- **The What-You-See Rule.** La vista previa es el mismo dibujo que va a la impresora (`parte.dibujar_parte`).

## Colors

| Token | Claro | Oscuro | Uso |
| --- | --- | --- | --- |
| `accent` | `#2c7a3a` | `#5fbf6e` | Verde EPLA: acción principal, selección, cifrado activo |
| `accent_soft` | `#e2f0e3` | `#1f3524` | Fila elegida, fondo de iconos |
| `gold` / `gold_soft` | `#b97a12` / `#fbf0d9` | `#e3a94a` / `#3a2e17` | Etiqueta de etapa |
| `bg` · `surface` · `surface2` | `#f3f5f1` · `#ffffff` · `#eef2ec` | `#121713` · `#1a211c` · `#222b24` | Campos · lienzo · barra y menú lateral |
| `line` | `#d9e0d5` | `#323d35` | Bordes y separadores |
| `fg` · `muted` | `#1d2a20` · `#5d6b60` | `#e4ebe5` · `#9aa89d` | Texto · secundario |
| `warn` / `warn_soft` | `#9a5b00` / `#fff3dc` | `#f0b45a` / `#3a2c14` | Avisos (mayor de edad, pendiente) |
| `danger` | `#a32d2d` | `#f08a8a` | Acciones destructivas |

Los neutros tiran ligeramente al verde para casar con el acento. El tema se elige según el sistema.

## Typography

| Rol | Familia | Tamaño | Dónde |
| --- | --- | --- | --- |
| Nombre del alumno | Barlow Condensed Bold | 30 px | Ficha |
| Títulos | Barlow Condensed Bold | 19–26 px | «Contactos», apartados de Ajustes, estado vacío |
| Hora de salida | Barlow Condensed Bold | 40 px | Campo de hora |
| Cuerpo | Barlow | 14 px (13 secundario, 12 pequeño) | Todo lo demás |
| Etiquetas | Barlow Bold, mayúsculas, espaciado 0,9 px | 12 px | «HORA DE SALIDA», «VISTA PREVIA» |
| Datos | JetBrains Mono | 14 px | NIA y teléfonos |

Las tres familias (OFL) van dentro de la app: `src/partes_salida/recursos/fuentes/`.

## Layout

- Ventana 1100 × 700 (mínimo 980 × 620). Barra superior: título, nombre del equipo, «Datos cifrados» y recuento, botón Ajustes.
- Columna izquierda: buscador con lupa · botones de etapa (se parten en filas) · curso + Limpiar · recuento · lista (filas de 58 px con miniatura 36×46).
- Centro: foto 104×132 · nombre en dos líneas · etiquetas etapa y curso · NIA y edad · caja «Contactos» (familiar, teléfono, Copiar y casilla de aviso; móvil del alumno y teléfono de emergencia).
- Derecha: hora + «Ahora» · aviso de hora pasada · vista previa con sombra · hueco flexible · «Imprimir parte ⌘P» (verde, 18 px) · resumen del aviso.
- Ajustes: 980 × 640, menú lateral de 220 px, filas «etiqueta (190 px) | control» con ayuda en gris debajo.

## Elevation & Shapes

Radios: 7–8 px campos y botones, 10 px cajas, 13 px chips, 12 px lienzos. Única sombra: la vista previa del parte (papel sobre la mesa). Bordes de 1 px `line`; zonas de soltar con borde discontinuo.

## Components

- **Botones**: principal verde (`primario`), secundario blanco con borde, pequeño (`pequeno`), peligro en rojo. Chips de etapa redondeados; el elegido, verde.
- **Estados vacíos**: «Empieza importando los datos» (con botón) y «Busca un alumno».
- **Avisos**: banda flotante oscura abajo para confirmaciones (se va sola); diálogo solo para errores que exigen hacer algo (llamar a la familia).
- **Zona de soltar**: icono, título, explicación y botón; acepta arrastrar archivos.
- **Cifras**: tarjetas con número en Barlow Condensed (alumnos, con foto, por confirmar, sobrantes).

## Parte impreso (DIN-A6 horizontal, 148 × 105 mm)

| Elemento | Posición (mm) | Estilo |
| --- | --- | --- |
| Marco | 4 de margen, radio 1,5 | 0,35 mm |
| Logo izquierdo / derecho | (7, 6.5) 19×19 · (111, 7.5) 30×16 | proporción respetada |
| Título | centrado 29–109, y 8.5 | Barlow Condensed ExtraBold 7,4 mm, encoge si no cabe |
| Foto | (7, 29) 25×32 | recorte centrado, borde 0,3 |
| Etapa · curso · alumno/a · NIA | x 36, y 29–60 | etiquetas 2,3 mm; nombre condensado 5,6 mm, dos líneas |
| Hora de salida | caja (105, 29) 36×32 | 13 mm ExtraBold; «hoy, dd/mm/aaaa» |
| Texto | (7, 64.5) 134 de ancho | 3,15 mm, dos líneas, hora en negrita, género según SEXO |
| QR | (7, 77) 20×20 | Ed25519, corrección M |
| Lugar y fecha · expedición | (30, 83.5) | 3,1 mm negrita · 2,7 mm |
| Sello / firma | (117, 70) 25×25 · (110, 78) 27×15 | sin fondo blanco, superpuestos |
| Cargo | alineado a la derecha, y 95.8 | 2,4 mm cursiva |

## Correo a la familia

600 px de ancho, cabecera blanca con los dos logos y filete verde de 4 px, cuerpo en Arial 15 px, tabla curso/hora, caja verde claro con los contactos de jefatura y pie gris con el aviso de buzón sin respuesta y RGPD. Probado en Chromium a 700 y 380 px (`tests/test_correo_navegador.py`).

## Do's and Don'ts

**Do:** leer este documento antes de tocar una pantalla · regenerar `docs/capturas/` tras un cambio visible · imprimir un parte de prueba tras tocar `parte.py` · mantener el flujo con teclado.

**Don't:** añadir campos «por si acaso» · usar colores fuera de los tokens · mostrar teléfonos en el parte · poner diálogos de confirmación en el camino de imprimir.
