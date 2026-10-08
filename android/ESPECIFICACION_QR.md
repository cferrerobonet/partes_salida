# Especificación del QR del parte (versión PS1)

Contrato entre la app de escritorio (que firma) y la app Android del vigilante (que verifica). Implementaciones: `src/partes_salida/firma.py` y `android/app/src/main/java/es/epla/vigilante/Verificador.kt`. Casos de prueba comunes: `vectores_qr.json` (`make vectores`).

## 1. QR impreso en el parte

Texto UTF-8, seis campos separados por `|`:

```
PS1|<id clave>|<id alumno>|<salida>|<expedido>|<firma>
```

| Campo | Formato | Ejemplo |
| --- | --- | --- |
| Prefijo | `PS1` (versión del formato) | `PS1` |
| Id de clave | 8 hex en mayúsculas: primeros 4 bytes de SHA-256 de la clave pública | `7A90B341` |
| Id de alumno | NIA de Educamos (8 dígitos) o `P<ID de persona>` si no tiene NIA | `10519873` |
| Salida | `AAAAMMDDhhmm`, hora local de Madrid | `202610081230` |
| Expedido | `AAAAMMDDhhmm`, hora local | `202610080914` |
| Firma | Ed25519 (64 bytes) en base64url **sin relleno** sobre los bytes UTF-8 de los cinco primeros campos unidos por `|` | `mQ3v…` |

QR con corrección de errores M, impreso a 20 × 20 mm. No lleva nombre, curso ni datos de la familia.

## 2. QR de alta de un equipo

Se muestra en Ajustes → QR y verificación de cada instalación:

```
PSK1|<id clave>|<clave pública base64url (32 bytes)>|<nombre del equipo>
```

La app Android lo acepta solo si `id clave` coincide con el SHA-256 de la clave pública.

## 3. Verificación

1. Separar por `|`; si no hay 6 campos o el prefijo no es `PS1` → «No es un parte de salida».
2. Buscar la clave por `id clave` entre las dadas de alta → si no está, «Firmado por un equipo desconocido».
3. Verificar la firma Ed25519 → si falla, «Firma no válida: alterado o falso».
4. Parte auténtico. La app Android añade:
   - fecha de salida distinta de hoy → «Parte de otro día» (no vale);
   - hora actual anterior a la de salida → «Todavía no: sale a las hh:mm».

## 4. Cambios del formato

Cualquier cambio sube el prefijo (`PS2`), mantiene la lectura del anterior durante un curso, regenera `vectores_qr.json` y es una versión mayor de las dos apps.
