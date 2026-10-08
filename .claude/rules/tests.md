---
paths:
  - "tests/**"
  - "pyproject.toml"
  - "scripts/qa.sh"
---

# Tests

Operativa y diagnóstico: skill `tests`.

- **Barrera antes que test**: `tests/conftest.py` da a cada test su carpeta de datos (`PARTES_SALIDA_DATOS`) y apaga el llavero real (`PARTES_SALIDA_SIN_LLAVERO=1`). Un test que pueda tocar red, SMTP, impresora o llavero los sustituye con `monkeypatch` (ver `test_interfaz.py`); nunca envía un correo de verdad ni imprime.
- **Datos ficticios siempre**: `tests/ficticios.py`. Nada real en el repositorio (público). Los datos reales de `../Material de pruebas` solo se usan en local con el marcador `datos_reales`, que se salta solo si la carpeta no existe.
- Marcadores: `ui` (pytest-qt, sin pantalla), `navegador` (Playwright con Chromium: correo HTML), `datos_reales`.
- **Una prueba de regresión debe fallar al revertir el arreglo**: comprobarlo y decirlo.
- Una prueba que vigila un invariante (`test_seguridad.py`, `test_proyecto.py`) no se relaja: se corrige el código o el documento.
- No citar recuentos de tests en ningún documento: cambian con cada versión.
- `android/vectores_qr.json` es el contrato con la app del vigilante: si cambia el formato del QR, `make vectores` y los dos lados en verde.
