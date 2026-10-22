// Verificación del QR del parte (contrato en ESPECIFICACION_QR.md; casos comunes en vectores_qr.json).
// Solo verifica: no firma, no guarda datos del alumnado y no usa la red.

import { verifyAsync } from "./vendor/noble-ed25519.js";

export const MOTIVOS = {
  NO_ES_PARTE: "No es un parte de salida",
  DESCONOCIDO: "Firmado por un equipo desconocido",
  FIRMA: "Firma no válida: el parte está alterado o es falso",
};

/** Lo que ve el vigilante: el resultado de la firma y la hora del parte, juntos. */
export const VEREDICTO = {
  PUEDE_SALIR: "PUEDE_SALIR",
  TODAVIA_NO: "TODAVIA_NO",
  OTRO_DIA: "OTRO_DIA",
  NO_VALE: "NO_VALE",
};

/** base64url sin relleno, estricto (como `Base64.getUrlDecoder()`): null si no es válido. */
export function deB64url(texto) {
  if (typeof texto !== "string" || !/^[A-Za-z0-9_-]*$/.test(texto) || texto.length % 4 === 1) return null;
  const b64 = texto.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((texto.length + 3) % 4);
  try {
    const bin = atob(b64);
    return Uint8Array.from(bin, (c) => c.charCodeAt(0));
  } catch {
    return null;
  }
}

/** Primeros 4 bytes de SHA-256 de la clave pública, en hexadecimal mayúsculas. */
export async function idDeClave(publica) {
  const resumen = new Uint8Array(await crypto.subtle.digest("SHA-256", publica));
  return Array.from(resumen.slice(0, 4), (b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

/** `PSK1|id|clave|nombre` → equipo `{id, publica, nombre, qr}`, o null si no es un QR de alta válido. */
export async function claveDeQr(texto) {
  const partes = String(texto).trim().split("|");
  if (partes.length !== 4 || partes[0] !== "PSK1") return null;
  const publica = deB64url(partes[2]);
  if (!publica || publica.length !== 32 || (await idDeClave(publica)) !== partes[1]) return null;
  return { id: partes[1], publica, nombre: partes[3], qr: String(texto).trim() };
}

let motorNativo; // undefined: sin probar · true/false: el navegador sabe (o no) Ed25519

/**
 * Firma Ed25519. `motor`: "auto" (WebCrypto del navegador y, si no lo tiene, noble-ed25519),
 * "nativo" o "js" (para las pruebas).
 */
export async function firmaValida(publica, mensaje, firma, motor = "auto") {
  if (motor !== "js" && motorNativo !== false) {
    try {
      const clave = await crypto.subtle.importKey("raw", publica, { name: "Ed25519" }, false, ["verify"]);
      motorNativo = true;
      return await crypto.subtle.verify({ name: "Ed25519" }, clave, firma, mensaje);
    } catch (e) {
      if (motor === "nativo") throw e;
      // Navegador sin Ed25519 en WebCrypto: en adelante, directamente noble-ed25519.
      // Cualquier otro error (clave rara): esta vez decide noble-ed25519.
      if (e && e.name === "NotSupportedError") motorNativo = false;
    }
  }
  try {
    return await verifyAsync(firma, mensaje, publica);
  } catch {
    return false;
  }
}

const FECHA = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$/;

/** `AAAAMMDDhhmm` → `{texto, fecha: "dd/mm/aaaa", hora: "hh:mm"}`, o null si no es una fecha real. */
export function fechaDeQr(texto) {
  const m = FECHA.exec(texto);
  if (!m) return null;
  const [a, mes, d, h, min] = m.slice(1).map(Number);
  const dia = new Date(Date.UTC(a, mes - 1, d));
  if (dia.getUTCMonth() !== mes - 1 || dia.getUTCDate() !== d || h > 23 || min > 59) return null;
  return { texto, fecha: `${m[3]}/${m[2]}/${m[1]}`, hora: `${m[4]}:${m[5]}` };
}

/**
 * Verifica el texto leído. `claves`: Map id → equipo. Devuelve
 * `{autentico: true, idAlumno, salida, expedido, equipo}` o `{autentico: false, motivo}`.
 */
export async function verificar(texto, claves, motor = "auto") {
  const partes = String(texto).trim().split("|");
  if (partes.length !== 6 || partes[0] !== "PS1") return { autentico: false, motivo: MOTIVOS.NO_ES_PARTE };
  const equipo = claves.get(partes[1]);
  if (!equipo) return { autentico: false, motivo: MOTIVOS.DESCONOCIDO };
  const firma = deB64url(partes[5]);
  const mensaje = new TextEncoder().encode(partes.slice(0, 5).join("|"));
  const valida = firma !== null && firma.length === 64 && (await firmaValida(equipo.publica, mensaje, firma, motor));
  const salida = fechaDeQr(partes[3]);
  const expedido = fechaDeQr(partes[4]);
  if (!valida || !salida || !expedido) return { autentico: false, motivo: MOTIVOS.FIRMA };
  return { autentico: true, idAlumno: partes[2], salida, expedido, equipo: equipo.nombre };
}

const RELOJ = new Intl.DateTimeFormat("es-ES", {
  timeZone: "Europe/Madrid",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** La hora de Madrid como `AAAAMMDDhhmm` (el QR va en hora local del centro, sea cual sea la del móvil). */
export function ahoraEnMadrid(fecha = new Date()) {
  const p = Object.fromEntries(RELOJ.formatToParts(fecha).map((x) => [x.type, x.value]));
  return `${p.year}${p.month}${p.day}${p.hour}${p.minute}`;
}

/** Firma buena, de hoy y ya es la hora → puede salir. `ahora`: `AAAAMMDDhhmm`. */
export function veredicto(resultado, ahora) {
  if (!resultado.autentico) return VEREDICTO.NO_VALE;
  const salida = resultado.salida.texto;
  if (salida.slice(0, 8) !== ahora.slice(0, 8)) return VEREDICTO.OTRO_DIA;
  if (ahora < salida) return VEREDICTO.TODAVIA_NO;
  return VEREDICTO.PUEDE_SALIR;
}
