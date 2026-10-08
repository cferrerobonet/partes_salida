# Documentación de Partes de salida

Cada documento tiene un dueño temático: un cambio actualiza el suyo en la misma tarea (tabla en `.claude/rules/documentacion.md`). No se crean documentos paralelos ni fechados.

| Documento | Responde a | Se actualiza cuando… |
| --- | --- | --- |
| [ESPECIFICACION.md](ESPECIFICACION.md) | ¿Qué hace y cómo debe comportarse? Usuarios, casos de uso, reglas y criterios de aceptación | cambia un comportamiento o una pantalla |
| [ARQUITECTURA.md](ARQUITECTURA.md) | ¿Cómo está hecha? Capas, módulos, flujo de datos, hilos, almacenamiento | se añade un módulo o cambia un flujo |
| [../DESIGN.md](../DESIGN.md) | ¿Cómo se ve? Tokens, tipografía, ventanas, parte impreso, correo | cambia algo visible |
| [SEGURIDAD_Y_DATOS.md](SEGURIDAD_Y_DATOS.md) | ¿Qué datos se tratan y cómo se protegen? | cambia el tratamiento de datos, el cifrado, la firma o el correo |
| [DECISIONES.md](DECISIONES.md) | ¿Por qué es así y no de otra forma? (ADR) | se toma una decisión con alternativas |
| [OPERACIONES.md](OPERACIONES.md) | ¿Cómo se instala, publica, restaura y diagnostica? | cambia la compilación, la publicación o el soporte |
| [PENDIENTE.md](PENDIENTE.md) | ¿Qué falta? Hoja de ruta, datos pendientes y hallazgos | aparece o se cierra algo |
| [../CHANGELOG.md](../CHANGELOG.md) | ¿Qué cambió en cada versión? | se publica una versión |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | ¿Cómo se trabaja? Entorno, ramas, commits, PR | cambia el flujo de trabajo |
| [../android/ESPECIFICACION_QR.md](../android/ESPECIFICACION_QR.md) | Contrato del QR entre escritorio y Android | cambia el formato del QR |
| [capturas/](capturas/) | Capturas con datos ficticios (`make capturas`) | cambia una pantalla |

Instrucciones para asistentes de código: [../AGENTS.md](../AGENTS.md) y `.claude/rules/`.
