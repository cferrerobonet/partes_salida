# App del vigilante (Android)

App para el móvil del vigilante de la puerta: escanea el QR del parte y dice si es **auténtico**, **falso o alterado**, **de otro día** o **todavía no es la hora**. Solo verifica: no firma, no guarda datos del alumnado y no necesita red.

## Estado

| Pieza | Estado |
| --- | --- |
| Contrato del QR | [ESPECIFICACION_QR.md](ESPECIFICACION_QR.md) + [vectores_qr.json](vectores_qr.json) (compartidos con la app de escritorio, que ya los pasa en sus tests) |
| Verificador (Kotlin) | `app/src/main/java/es/epla/vigilante/Verificador.kt`, con su test sobre los vectores |
| Pantalla | `MainActivity.kt` (Compose): tarjeta grande con el veredicto (`Verificador.veredicto`, probado), equipos de confianza (alta y baja) y pantalla siempre encendida |
| Compilación | En GitHub (`compilar.yml`, trabajo «APK del vigilante»): `gradle test assembleRelease`, firmado con la clave fija; el APK va en cada release (`Vigilante-EPLA-X.Y.Z.apk`). Desde el 2026-10-19 |

## Diseño

- **Escáner**: Google Code Scanner (`play-services-code-scanner`): no pide permiso de cámara ni necesita pantalla propia.
- **Firma**: Ed25519 con BouncyCastle (funciona en cualquier Android desde la 8.0).
- **Equipos de confianza**: cada jefatura enseña el QR de Ajustes → QR y verificación; el vigilante lo escanea una vez con «Dar de alta un equipo». Se guardan en las preferencias del móvil (solo claves públicas y nombres).

## Pendiente

- Probar en el móvil del vigilante con un parte real impreso (y con uno de otro día y uno antes de su hora).
