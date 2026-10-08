@AGENTS.md

## Propio del asistente

- La sesión se abre en esta carpeta (`PARTES DE SALIDA - CÓDIGO FUENTE/`): aquí mandan `AGENTS.md`, `.claude/rules/` y los ganchos de `.claude/settings.json`.
- Salidas largas (suite, logs de la CI) en el subagente `verificador` o filtradas con `tail`/`grep`.
- Para revisar un cambio antes de publicarlo, el subagente `revisor`.
- Tras publicar una versión, `/clear` antes de empezar otra tarea.
