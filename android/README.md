# App del vigilante (Android) — preparada, sin compilar

App para el móvil del vigilante de la puerta: escanea el QR del parte y dice si es **auténtico**, **falso o alterado**, **de otro día** o **todavía no es la hora**. Solo verifica: no firma, no guarda datos del alumnado y no necesita red.

## Estado

| Pieza | Estado |
| --- | --- |
| Contrato del QR | [ESPECIFICACION_QR.md](ESPECIFICACION_QR.md) + [vectores_qr.json](vectores_qr.json) (compartidos con la app de escritorio, que ya los pasa en sus tests) |
| Verificador (Kotlin) | `app/src/main/java/es/epla/vigilante/Verificador.kt`, con su test sobre los vectores |
| Pantalla mínima | `MainActivity.kt` (Compose): escanear un parte y dar de alta equipos |
| Compilación | **Pendiente**: en este equipo no hay JDK. Se compilará en GitHub Actions, como la de escritorio |

## Diseño

- **Escáner**: Google Code Scanner (`play-services-code-scanner`): no pide permiso de cámara ni necesita pantalla propia.
- **Firma**: Ed25519 con BouncyCastle (funciona en cualquier Android desde la 8.0).
- **Equipos de confianza**: cada jefatura enseña el QR de Ajustes → QR y verificación; el vigilante lo escanea una vez con «Dar de alta un equipo». Se guardan en las preferencias del móvil (solo claves públicas y nombres).

## Siguientes pasos

1. Abrir `android/` con Android Studio (genera el *wrapper* de Gradle) o añadir un workflow `android.yml` que compile con `gradle assembleDebug` y pase `gradle test`.
2. Probar con un parte real impreso y con los casos de `vectores_qr.json`.
3. Diseño de la pantalla de resultado (verde / rojo, foto no disponible: se compara con la del parte).
