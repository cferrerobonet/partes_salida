# Especificación del QR del parte (versión PS2)

Contrato entre la app de escritorio (que firma) y la app del vigilante (web, que verifica). Implementaciones: `src/partes_salida/firma.py` y `vigilante/verificador.js`. Casos de prueba comunes: `vectores_qr.json` (`make vectores`).

## 1. QR impreso en el parte

Texto UTF-8, siete campos separados por `|`:

```
PS2|<id clave>|<id alumno>|<salida>|<expedido>|<compañía>|<firma>
```

| Campo | Formato | Ejemplo |
| --- | --- | --- |
| Prefijo | `PS2` (versión del formato) | `PS2` |
| Id de clave | 8 hex en mayúsculas: primeros 4 bytes de SHA-256 de la clave pública | `7A90B341` |
| Id de alumno | NIA de Educamos (8 dígitos) o `P<ID de persona>` si no tiene NIA | `10519873` |
| Salida | `AAAAMMDDhhmm`, hora local de Madrid | `202610081230` |
| Expedido | `AAAAMMDDhhmm`, hora local | `202610080914` |
| Compañía | ESO y Grado Básico: `SO` sale solo, `SA` sale sola, `AO` acompañado, `AA` acompañada; `-` en las demás etapas | `SA` |
| Firma | Ed25519 (64 bytes) en base64url **sin relleno** sobre los bytes UTF-8 de los seis primeros campos unidos por `|` | `mQ3v…` |

QR con corrección de errores M, impreso a 20 × 20 mm (versión 8 como mucho). No lleva nombre, curso ni datos de la familia: el género de la compañía es lo único que dice del alumno, para que el vigilante lea «SALE SOLA» o «SALE SOLO».

**Formato anterior `PS1`** (hasta la 1.8): seis campos, sin compañía (`PS1|<id clave>|<id alumno>|<salida>|<expedido>|<firma>`, firma sobre los cinco primeros). Se sigue leyendo durante el curso 2026-2027.

## 2. QR de alta de un equipo

Se muestra en Ajustes → QR y verificación de cada instalación:

```
PSK1|<id clave>|<clave pública base64url (32 bytes)>|<nombre del equipo>
```

La app del vigilante lo acepta solo si `id clave` coincide con el SHA-256 de la clave pública.

## 3. Verificación

1. Separar por `|`. Vale `PS2` con 7 campos y una compañía de la lista, o `PS1` con 6; si no → «No es un parte de salida».
2. Buscar la clave por `id clave` entre las dadas de alta → si no está, «Firmado por un equipo desconocido».
3. Verificar la firma Ed25519 sobre todo lo anterior a la última barra → si falla, «Firma no válida: alterado o falso». Cambiar la compañía a mano rompe la firma.
4. Parte auténtico. La app del vigilante añade (con la hora de Madrid, sea cual sea la del móvil):
   - fecha de salida distinta de hoy → «Parte de otro día» (no vale);
   - hora actual anterior a la de salida → «Todavía no: sale a las hh:mm».
   - con compañía (`SO`, `SA`, `AO`, `AA`), una banda bajo «PUEDE SALIR» o «TODAVÍA NO»: «SALE SOLO/SOLA» maciza o «ACOMPAÑADO/A» discreta.

## 4. Cambios del formato

Cualquier cambio sube el prefijo (`PS2`), mantiene la lectura del anterior durante un curso, regenera `vectores_qr.json` y es una versión mayor de las dos apps.
