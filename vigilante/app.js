// App del vigilante: escanea el QR del parte y dice en grande si el alumno puede salir.
// Sin red (salvo para instalarse y actualizarse) y sin datos del alumnado: solo guarda en el móvil
// las claves públicas y los nombres de los equipos de jefatura dados de alta.

import { ahoraEnMadrid, claveDeQr, verificar, veredicto, VEREDICTO } from "./verificador.js";

const VERSION = "__VERSION__"; // la pone scripts/web_vigilante.py al publicar
const CLAVE_EQUIPOS = "vigilante.equipos";

const $ = (id) => document.getElementById(id);

/* ---------- Equipos de confianza: los QR `PSK1` tal cual, en el almacenamiento del navegador ---------- */

let enMemoria = []; // si el navegador no deja guardar (modo privado), al menos dura la sesión

function leerQrs() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE_EQUIPOS) || "[]");
    return Array.isArray(guardado) ? guardado.filter((x) => typeof x === "string") : [];
  } catch {
    return enMemoria;
  }
}

function guardarQrs(qrs) {
  enMemoria = qrs;
  try {
    localStorage.setItem(CLAVE_EQUIPOS, JSON.stringify(qrs));
  } catch {
    /* queda en memoria */
  }
}

async function equipos() {
  const lista = await Promise.all(leerQrs().map(claveDeQr));
  return new Map(lista.filter(Boolean).map((e) => [e.id, e]));
}

async function alta(texto) {
  const clave = await claveDeQr(texto);
  if (!clave) return null;
  // un equipo que vuelve a darse de alta (otro nombre) sustituye al anterior
  const otros = [];
  for (const qr of leerQrs()) if ((await claveDeQr(qr))?.id !== clave.id) otros.push(qr);
  guardarQrs([...otros, clave.qr]);
  return clave;
}

async function baja(id) {
  const quedan = [];
  for (const qr of leerQrs()) if ((await claveDeQr(qr))?.id !== id) quedan.push(qr);
  guardarQrs(quedan);
}

/* ---------- Tarjeta de resultado ---------- */

const INICIO = { simbolo: "⌁", titulo: "Listo", detalle: ["Pulsa «Escanear parte» y apunta al QR del parte."], color: "secundario" };

function aviso(r, ahora = ahoraEnMadrid()) {
  switch (veredicto(r, ahora)) {
    case VEREDICTO.NO_VALE:
      return { simbolo: "✕", titulo: "NO VALE", detalle: [r.motivo], color: "peligro" };
    case VEREDICTO.OTRO_DIA:
      return { simbolo: "✕", titulo: "OTRO DÍA", detalle: [`El parte es del ${r.salida.fecha}: no vale hoy.`, nia(r)], color: "peligro" };
    case VEREDICTO.TODAVIA_NO:
      return {
        simbolo: "⏱", titulo: "TODAVÍA NO",
        detalle: [`Auténtico, pero sale a las ${r.salida.hora}.`, `${nia(r)} · ${r.equipo}`], color: "aviso",
      };
    default:
      return {
        simbolo: "✓", titulo: "PUEDE SALIR",
        detalle: [`Salida desde las ${r.salida.hora}.`, `${nia(r)} · comprueba la foto del parte.`,
          `Firmado por ${r.equipo} a las ${r.expedido.hora}.`],
        color: "verde",
      };
  }
}

const nia = (r) => `NIA ${r.idAlumno}`;

function mostrar(a) {
  $("tarjeta").className = `tarjeta tarjeta--${a.color}`;
  $("simbolo").textContent = a.simbolo;
  $("titulo").textContent = a.titulo;
  $("detalle").replaceChildren(...a.detalle.map((linea) => {
    const p = document.createElement("p");
    p.textContent = linea;
    return p;
  }));
  $("tarjeta").dataset.veredicto = a.titulo;
}

function vibrar(bien) {
  try {
    navigator.vibrate?.(bien ? 40 : [90, 60, 90]);
  } catch {
    /* sin vibración */
  }
}

async function pintarEquipos() {
  const lista = [...(await equipos()).values()].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  $("recuento").textContent = lista.length === 0 ? "sin equipos" : `${lista.length} equipo${lista.length === 1 ? "" : "s"}`;
  $("aviso-sin-equipos").hidden = lista.length > 0;
  const ul = $("lista-equipos");
  if (lista.length === 0) {
    const li = document.createElement("li");
    li.className = "vacio";
    li.textContent = "Ninguno todavía.";
    ul.replaceChildren(li);
    return;
  }
  ul.replaceChildren(...lista.map((e) => {
    const li = document.createElement("li");
    const datos = document.createElement("div");
    datos.className = "equipo";
    const nombre = document.createElement("div");
    nombre.className = "nombre";
    nombre.textContent = e.nombre;
    const clave = document.createElement("div");
    clave.className = "clave";
    clave.innerHTML = 'Clave <span class="mono"></span>';
    clave.querySelector("span").textContent = e.id;
    datos.append(nombre, clave);
    const quitar = document.createElement("button");
    quitar.type = "button";
    quitar.className = "enlace enlace--peligro";
    quitar.textContent = "Quitar";
    quitar.addEventListener("click", async () => {
      await baja(e.id);
      await pintarEquipos();
    });
    li.append(datos, quitar);
    return li;
  }));
}

/* ---------- Lo que pasa con cada lectura (también lo usan las pruebas) ---------- */

async function procesarParte(texto, ahora) {
  const a = aviso(await verificar(texto, await equipos()), ahora);
  mostrar(a);
  vibrar(a.color === "verde");
  return a;
}

async function procesarAlta(texto) {
  const clave = await alta(texto);
  await pintarEquipos();
  const a = clave
    ? { simbolo: "✓", titulo: "EQUIPO DADO DE ALTA", detalle: [clave.nombre, `Clave ${clave.id}`], color: "verde" }
    : { simbolo: "✕", titulo: "NO ES UN QR DE ALTA", detalle: ["Escanea el QR de Ajustes → QR y verificación."], color: "peligro" };
  mostrar(a);
  vibrar(Boolean(clave));
  return a;
}

/* ---------- Escáner: BarcodeDetector del navegador o, si no lo tiene (iPhone), jsQR ---------- */

let detector; // función (video) → Promise<texto | null>
let escaneando = false;

async function prepararDetector() {
  if (detector) return detector;
  try {
    if ("BarcodeDetector" in window && (await BarcodeDetector.getSupportedFormats()).includes("qr_code")) {
      const bd = new BarcodeDetector({ formats: ["qr_code"] });
      detector = async (video) => (await bd.detect(video))[0]?.rawValue ?? null;
      return detector;
    }
  } catch {
    /* pasa a jsQR */
  }
  await new Promise((ok, mal) => {
    const s = document.createElement("script");
    s.src = "vendor/jsQR.js";
    s.onload = ok;
    s.onerror = () => mal(new Error("No se pudo cargar el lector de QR"));
    document.head.append(s);
  });
  const lienzo = document.createElement("canvas");
  const ctx = lienzo.getContext("2d", { willReadFrequently: true });
  // El QR del parte es denso (49 módulos en 20 mm): reducido con el fotograma entero se pierde si
  // es pequeño. Cada fotograma prueba una pasada: el centro (bajo el marco) a tamaño real, el centro
  // a la mitad (aguanta mejor el desenfoque) o la imagen entera.
  const PASADAS = [[true, 1080], [true, 540], [false, 720]];
  let pasada = 0;
  detector = async (video) => {
    const vw = video.videoWidth, vh = video.videoHeight;
    const [centro, maximo] = PASADAS[pasada++ % PASADAS.length];
    const lado = Math.round(Math.min(vw, vh) * 0.75);
    const [sx, sy, sw, sh] = centro ? [(vw - lado) / 2, (vh - lado) / 2, lado, lado] : [0, 0, vw, vh];
    const escala = Math.min(1, maximo / Math.max(sw, sh));
    lienzo.width = Math.round(sw * escala);
    lienzo.height = Math.round(sh * escala);
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, lienzo.width, lienzo.height);
    const img = ctx.getImageData(0, 0, lienzo.width, lienzo.height);
    return window.jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" })?.data ?? null;
  };
  return detector;
}

/** Abre la cámara a pantalla completa y resuelve con el primer QR leído, o null si se cancela. */
async function escanear(texto) {
  const capa = $("escaner");
  const video = $("video");
  $("escaner-texto").textContent = texto;
  let flujo;
  try {
    const leer = await prepararDetector();
    flujo = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = flujo;
    capa.hidden = false;
    escaneando = true;
    await video.play();

    const pista = flujo.getVideoTracks()[0];
    const capacidades = pista.getCapabilities?.() ?? {};
    // Enfoque continuo y algo de zoom: el QR se ve grande sin acercar el móvil más de lo que enfoca.
    const ajustes = {};
    if (capacidades.focusMode?.includes("continuous")) ajustes.focusMode = "continuous";
    if (capacidades.zoom?.max >= 2 && capacidades.zoom.min <= 2) ajustes.zoom = 2;
    if (Object.keys(ajustes).length) await pista.applyConstraints({ advanced: [ajustes] }).catch(() => {});
    const linterna = $("linterna");
    let encendida = false;
    linterna.hidden = !capacidades.torch;
    linterna.onclick = async () => {
      encendida = !encendida;
      try {
        await pista.applyConstraints({ advanced: [{ torch: encendida }] });
      } catch {
        linterna.hidden = true;
      }
    };

    return await new Promise((resolver) => {
      let ocupado = false;
      let terminado = false;
      const fin = (valor) => {
        if (terminado) return;
        terminado = true;
        resolver(valor);
      };
      $("cancelar").onclick = () => fin(null);
      const vuelta = async () => {
        if (terminado) return;
        if (!ocupado && video.readyState >= 2) {
          ocupado = true;
          try {
            const leido = await leer(video);
            if (leido) fin(leido);
          } catch {
            /* fotograma ilegible: el siguiente */
          }
          ocupado = false;
        }
        requestAnimationFrame(vuelta);
      };
      requestAnimationFrame(vuelta);
    });
  } catch (e) {
    mostrar({
      simbolo: "✕", titulo: "SIN CÁMARA",
      detalle: [e && e.name === "NotAllowedError"
        ? "Permite el uso de la cámara a esta app en los ajustes del navegador y vuelve a intentarlo."
        : "No se ha podido abrir la cámara del móvil."],
      color: "peligro",
    });
    return null;
  } finally {
    flujo?.getTracks().forEach((t) => t.stop());
    video.srcObject = null;
    capa.hidden = true;
    escaneando = false;
    if (actualizacionPendiente) location.reload();
  }
}

/* ---------- Pantalla siempre encendida mientras la app está abierta ---------- */

let bloqueo;
async function pantallaEncendida() {
  if (document.visibilityState !== "visible" || bloqueo) return;
  try {
    bloqueo = await navigator.wakeLock?.request("screen");
    bloqueo?.addEventListener("release", () => { bloqueo = null; });
  } catch {
    /* el navegador no lo permite ahora: se reintenta al volver */
  }
}

/* ---------- Instalación sin conexión y actualizaciones ---------- */

let actualizacionPendiente = false;

function registrarServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  const habiaControlador = Boolean(navigator.serviceWorker.controller);
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!habiaControlador) return; // primera instalación: nada que recargar
    if (escaneando) actualizacionPendiente = true;
    else location.reload();
  });
  navigator.serviceWorker.register("sw.js").catch(() => { /* sin modo sin conexión */ });
}

/* ---------- Arranque ---------- */

function iniciar() {
  $("version").textContent = VERSION;
  mostrar(INICIO);
  pintarEquipos();

  $("escanear").addEventListener("click", async () => {
    const texto = await escanear("Apunta al QR del parte");
    if (texto !== null) await procesarParte(texto);
  });

  const dialogo = $("equipos");
  $("ver-equipos").addEventListener("click", async () => {
    await pintarEquipos();
    dialogo.showModal();
  });
  $("cerrar-equipos").addEventListener("click", () => dialogo.close());
  $("dar-de-alta").addEventListener("click", async () => {
    dialogo.close();
    const texto = await escanear("Apunta al QR de Ajustes → QR y verificación");
    if (texto !== null) await procesarAlta(texto);
  });

  pantallaEncendida();
  document.addEventListener("visibilitychange", pantallaEncendida);
  navigator.storage?.persist?.().catch(() => {});
  registrarServiceWorker();

  window.vigilante = { procesarParte, procesarAlta, prepararDetector, version: VERSION };
}

iniciar();
