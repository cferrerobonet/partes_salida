---
name: auditar
description: Revisión de calidad de Partes de salida con evidencia fichero:línea — seguridad y datos personales, interfaz frente a DESIGN.md, robustez (importación, impresión, correo), tests y empaquetado — y registro de lo encontrado en docs/PENDIENTE.md. Usar cuando CarlosFB pida «audita», «revisa la app» o antes de una versión mayor.
---

# Auditar

Solo lectura del código hasta que CarlosFB decida qué se arregla.

## 1. Situarse

`git log --oneline -10`, versión en `pyproject.toml`, `docs/PENDIENTE.md` (lo ya conocido no se vuelve a apuntar) y las reglas de `.claude/rules/` de la zona.

## 2. Barreras automáticas

| Barrera | Orden | Debe dar |
| --- | --- | --- |
| Lint | `scripts/qa.sh lint` | OK |
| Suite | `scripts/qa.sh test` | OK |
| Sin datos en el repo | `git ls-files \| grep -Ei '\.(xls\|xlsx\|zip\|bin\|jpe?g)$'` | nada |
| Sin colores sueltos en la interfaz | `grep -n '#[0-9a-fA-F]\{6\}' src/partes_salida/ui/*.py \| grep -v estilo.py` | nada (salvo el blanco del papel) |
| Secretos | `grep -rniE 'password\|contrase' src \| grep -v secreto` | sin valores escritos |

## 3. Dimensiones (con evidencia `fichero:línea`)

- **SEG** datos personales y cifrado: `.claude/rules/seguridad-y-datos.md` punto por punto.
- **UXI** interfaz: `DESIGN.md` (tres zonas, tokens, número justo de campos, teclado, estados vacíos y de error).
- **ROB** robustez: Excel raro (sin cabeceras, columnas cambiadas), ZIP con basura, impresora ausente, SMTP caído, llavero cambiado.
- **TST** pruebas: qué flujo crítico no tiene test; regresiones que no fallarían al revertir.
- **BLD** empaquetado: `.claude/rules/empaquetado.md`.
- **QR** contrato con Android: `android/ESPECIFICACION_QR.md` frente a `firma.py` y `vectores_qr.json`.

## 4. Registrar

En `docs/PENDIENTE.md`, sección «Hallazgos», una fila por hallazgo: `ID` (prefijo de la dimensión + número correlativo, `grep` para el siguiente), gravedad (P0 bloquea el uso · P1 riesgo real · P2 mejora), evidencia, propuesta y estado. Resumen a CarlosFB: cuántos por gravedad y los P0/P1 en una línea cada uno.

## No hacer

Arreglar sin que se pida, inventar evidencia, abrir documentos nuevos de auditoría (todo va a `docs/PENDIENTE.md`).
