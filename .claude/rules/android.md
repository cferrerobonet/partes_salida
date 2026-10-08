---
paths:
  - "android/**"
  - "src/partes_salida/firma.py"
  - "scripts/generar_vectores_qr.py"
---

# App del vigilante (Android)

- Vive en `android/` dentro de este repositorio para compartir el contrato del QR con la app de escritorio. Estado y pasos: `android/README.md`.
- **El contrato es `android/ESPECIFICACION_QR.md` + `android/vectores_qr.json`**. La app de escritorio los comprueba en `tests/test_seguridad.py` y la Android en `VerificadorTest.kt`. Un cambio en uno exige el otro en la misma tarea.
- La app Android solo verifica: nunca firma ni guarda datos del alumnado. Las claves públicas de cada jefatura se dan de alta escaneando su QR de Ajustes → QR y verificación.
- Compilar la app Android también irá en GitHub (Actions), no en local, cuando se desarrolle.
