---
paths:
  - "*.md"
  - "docs/**"
  - "android/*.md"
  - ".claude/**"
  - ".github/*.md"
---

# Documentación

Mapa de documentos: `docs/README.md`. No crear documentos paralelos ni fechados: se actualizan los que hay.

| Cambio | Documento que se toca en la misma tarea |
| --- | --- |
| Cualquier versión publicada | `CHANGELOG.md` (entrada arriba; es también la nota del release en GitHub) |
| Comportamiento o pantalla | `docs/ESPECIFICACION.md` y, si es visual, `DESIGN.md` y `docs/capturas/` (`make capturas`) |
| Estructura, módulo nuevo, flujo de datos | `docs/ARQUITECTURA.md` |
| Decisión con alternativas | nueva entrada en `docs/DECISIONES.md` (ADR numerado; los anteriores no se reescriben: se marcan como sustituidos) |
| Datos personales, cifrado, firma, correo | `docs/SEGURIDAD_Y_DATOS.md` |
| Compilación, publicación, restauración | `docs/OPERACIONES.md` |
| Formato del QR | `android/ESPECIFICACION_QR.md` y `android/vectores_qr.json` |
| Pendiente, idea o fallo detectado | `docs/PENDIENTE.md` |

- Si solo cambia implementación interna: «sin impacto documental», dicho en el commit o el PR.
- Fuentes de verdad (no copiar cifras vivas en documentos): versión → `pyproject.toml`; columnas leídas → `importar_excel.COLUMNAS`; tokens → `ui/estilo.py`.
- Instrucciones para agentes: `AGENTS.md` es el principal; `CLAUDE.md` solo lo importa; el detalle por zona va en `.claude/rules/` con `paths:`.
- Ficha en la bóveda: `../PARTES DE SALIDA — Índice.md` (fuera del repositorio): la skill `publicar` añade allí la versión publicada.
