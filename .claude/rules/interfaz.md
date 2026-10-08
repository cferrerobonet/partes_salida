---
paths:
  - "src/partes_salida/ui/**"
  - "src/partes_salida/parte.py"
  - "DESIGN.md"
  - "docs/capturas/**"
---

# Interfaz y parte impreso

Contrato visual: `DESIGN.md` (maqueta aprobada por CarlosFB el 2026-10-08). Leerlo antes de tocar una pantalla.

- **Colores solo de los tokens** de `ui/estilo.py` (`T[...]`, claro y oscuro). Ningún hexadecimal suelto en widgets; el parte impreso usa sus propias tintas (`parte.TINTA`), que no cambian con el tema.
- **Tres zonas fijas** en la ventana principal: buscar (300 px) · alumno y familia (flexible) · hora, vista previa e imprimir (340 px). No añadir campos sin motivo: el número justo es un requisito.
- **El parte se dibuja en milímetros** (`parte.dibujar_parte`, 148 × 105 mm) y el mismo código sirve para la vista previa y la impresora. Un cambio de maquetación del parte se comprueba con `make capturas` y con un parte de prueba impreso (Ajustes → Impresión).
- Textos que no caben: `_Lienzo.texto` reduce el cuerpo hasta que caben; no recortar.
- Teclado: el buscador recibe el foco al mostrarse; ↓ e Intro eligen; ⌘P / Ctrl+P imprime; Esc limpia.
- Tras un cambio visible: `make capturas` y revisar `docs/capturas/`.
