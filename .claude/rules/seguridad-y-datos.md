---
paths:
  - "src/partes_salida/cifrado.py"
  - "src/partes_salida/almacen.py"
  - "src/partes_salida/importar_excel.py"
  - "src/partes_salida/importar_fotos.py"
  - "src/partes_salida/firma.py"
  - "src/partes_salida/correo.py"
  - "src/partes_salida/ajustes.py"
  - ".gitignore"
  - ".githooks/**"
---

# Seguridad y datos personales

Detalle y motivos: `docs/SEGURIDAD_Y_DATOS.md`.

- **Minimización**: del Excel solo se leen las columnas de `importar_excel.COLUMNAS`. Añadir una columna es una decisión (ADR) y un cambio en ese documento; DNI, IBAN, tarjeta sanitaria y direcciones no entran nunca.
- **Todo dato del alumnado se guarda cifrado** con `Cifrador` (AES-256-GCM, clave en el llavero). Nada en claro en disco: ni padrón, ni fotos, ni temporales. Los ZIP se leen en memoria.
- **Nombres de archivo sin datos**: las fotos se guardan con la huella HMAC del identificador.
- **Contraseñas** solo en el llavero (`cifrado.guardar_secreto`), nunca en `ajustes.json`, en el registro ni en el repositorio. La copia de ajustes exportable no lleva ninguna.
- **Firma del QR**: la clave privada no sale del equipo. Cambiar el formato del QR exige actualizar `android/ESPECIFICACION_QR.md` y `android/vectores_qr.json` (`make vectores`).
- **Repositorio público**: `.gitignore` y `.githooks/pre-commit` cierran el paso a `.xls`, `.zip`, `.bin`, `.jpg`, carpetas de datos y la palabra prohibida. No saltarlos con `--no-verify`.
- Registro (`logs/`): sin nombres de alumnos, correos ni teléfonos; como mucho recuentos.
