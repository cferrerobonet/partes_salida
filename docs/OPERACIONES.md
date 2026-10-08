# Operaciones: instalar, publicar, restaurar y diagnosticar

## 1. Instalar en un equipo de jefatura

1. Descargar de [Releases](https://github.com/cferrerobonet/partes_salida/releases/latest) el DMG (macOS) o el instalador `.exe` (Windows; sin permisos de administrador, el `.zip` portable).
2. **macOS**: arrastrar a Aplicaciones. Si dice «está dañada», una vez: `xattr -dr com.apple.quarantine "/Applications/Partes de salida.app"` (lo explica el `LÉEME` del DMG). La primera vez el sistema puede pedir permiso para usar el llavero: «Permitir siempre».
3. Abrir y seguir **Ajustes**:
   - **Datos del alumnado**: arrastrar el Excel de Educamos y después los ZIP de fotos; confirmar las fotos parecidas.
   - **Sello y firma**: subir el sello de la etapa y la firma (fondo blanco; se quita solo).
   - **Logos e identidad**: dejar los de serie o cambiarlos.
   - **Correo**: escribir la contraseña de `no_contestar@aplicaciones.epla.es` (nota de la bóveda «GUARDIAS DE PATIO — Configuración Infraestructura») y enviar un **correo de prueba** a una dirección propia.
   - **Impresión**: elegir la impresora de la bandeja A6, «Imprimir directamente» e **Imprimir parte de prueba**; corregir el ajuste fino si sale desplazado.
   - **QR y verificación**: poner el nombre del equipo (p. ej. «Jefatura de Estudios de FP»).
   - **General**: «Abrir la app en segundo plano» al iniciar sesión.

## 2. Uso diario

Buscar → comprobar → ⌘P / Ctrl+P. La app queda en la barra de menús o la bandeja: cerrar la ventana no la cierra; «Salir» desde el icono.

## 3. Actualizar el alumnado

Cuando cambie la matrícula (inicio de curso, altas): en Educamos, **Datos → Import/Export → Exportación de datos de alumnos → Exportar**, y arrastrar el Excel a Ajustes → Datos del alumnado (la «?» lo recuerda). Sustituye el padrón y borra las fotos de las bajas. Fotos nuevas: arrastrar los ZIP; sustituyen a las que había y añaden las que faltaban.

Al terminar cada importación, aceptar **enviar el archivo a la papelera** y vaciarla: el original tiene datos sensibles y la app ya los guarda cifrados.

**Fin de curso**: Ajustes → Datos del alumnado → «Vaciar todos los datos del alumnado» y, en septiembre, importar de nuevo.

## 4. Restaurar o cambiar de equipo

Instalar → importar Excel y ZIP → (opcional) Ajustes → General → **Importar ajustes** desde la copia exportada → escribir de nuevo la contraseña del correo. No hay más datos que recuperar.

## 5. Publicar una versión (desarrollo)

Skill `publicar` (`.claude/skills/publicar/SKILL.md`): versión en `pyproject.toml` y `src/partes_salida/__init__.py`, `CHANGELOG.md`, `scripts/qa.sh todo`, commit con ficheros concretos, push, etiqueta `vX.Y.Z`. GitHub Actions (`compilar.yml`) pasa las pruebas, compila, **arranca la app compilada** en Windows y macOS y adjunta al release:

- `PartesSalida_vX.Y.Z_macOS.dmg`
- `PartesDeSalida-X.Y.Z-Windows-Setup.exe`
- `PartesDeSalida-X.Y.Z-Windows-Portable.zip`

Los equipos ven el aviso de versión nueva al abrir la app y la instalan con un clic. **No se compila en local.**

Compilación manual sin publicar: GitHub → Actions → Compilar → Run workflow (los instaladores quedan como artefactos).

## 6. Diagnóstico

| Síntoma | Qué mirar |
| --- | --- |
| La app no abre | Registro: macOS `~/Library/Application Support/PartesSalida/logs/app_*.log`, Windows `%APPDATA%\PartesSalida\logs\app_*.log` y `faulthandler.log` |
| «Los datos guardados no se pueden abrir…» | El llavero cambió (equipo restaurado, perfil nuevo): reimportar Excel y ZIP |
| El correo no sale | Ajustes → Correo → correo de prueba; revisar contraseña y puerto 587. El parte ya impreso vale: avisar por teléfono |
| El parte sale desplazado o cortado | Ajustes → Impresión → ajuste fino y parte de prueba; comprobar que la bandeja está en A6 horizontal |
| Una foto no aparece | El nombre del archivo debe ser `APELLIDOS, NOMBRE` como en Educamos; las casi iguales se confirman al importar |
| No avisa de versiones nuevas | Red o límite de GitHub: Ajustes → General → Buscar actualizaciones |

## 7. Desarrollo local

```bash
make venv && make ganchos      # una vez
make run                       # abrir la app
scripts/qa.sh todo             # antes de publicar
make capturas                  # capturas con datos ficticios
```

El entorno vive en `~/.venvs/partes-salida`, fuera de iCloud. Los datos reales de prueba están fuera del repositorio, en `../Material de pruebas` (solo en el equipo de desarrollo).
