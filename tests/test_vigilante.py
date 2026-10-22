"""La web del vigilante (`vigilante/`) tal como se publica, abierta en Chromium.

El contrato es `vigilante/vectores_qr.json`: el verificador del navegador tiene que dar los mismos
resultados que `firma.py` (ver `test_seguridad.py`), con el Ed25519 del navegador y con la
librería de respaldo (la de los móviles que no lo traen). Deja capturas en
`test-results/vigilante-*.png` para revisarlas a ojo.
"""

from __future__ import annotations

import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import expect
from scripts.web_vigilante import montar

RAIZ = Path(__file__).resolve().parents[1]
VECTORES = json.loads((RAIZ / "vigilante" / "vectores_qr.json").read_text(encoding="utf-8"))
SALIDAS = RAIZ / "test-results"
AUTENTICO = VECTORES["casos"][0]["qr"]  # sale el 08/10/2026 a las 12:30


@pytest.fixture(scope="module")
def sitio(tmp_path_factory):
    return montar(tmp_path_factory.mktemp("web") / "_site", "0.0.0-prueba")


@pytest.fixture(scope="module")
def url(sitio):
    class Silencioso(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".webmanifest": "application/manifest+json"}

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(sitio)))
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/"
    servidor.shutdown()


def test_lo_publicado_es_lo_que_guarda_el_service_worker(sitio):
    """Si un archivo falta en la lista del service worker, la app no funciona sin conexión."""
    sw = (sitio / "sw.js").read_text(encoding="utf-8")
    lista = re.search(r"const ARCHIVOS = \[(.*?)\];", sw, re.S).group(1)
    guardados = {a for a in re.findall(r'"([^"]+)"', lista) if a != "./"}
    publicados = {
        p.relative_to(sitio).as_posix()
        for p in sitio.rglob("*")
        if p.is_file() and p.name != "sw.js" and p.suffix in {".html", ".css", ".js", ".png", ".svg", ".ttf", ".webmanifest"}
    }
    assert guardados == publicados
    assert "__VERSION__" not in sw and "__VERSION__" not in (sitio / "app.js").read_text(encoding="utf-8")
    assert not (sitio / "vectores_qr.json").exists() and not (sitio / "ESPECIFICACION_QR.md").exists()


def _verificar_vectores(page, motor: str) -> list[str]:
    return page.evaluate(
        """async ([vectores, motor]) => {
            const v = await import('./verificador.js');
            const equipo = await v.claveDeQr(vectores.qr_de_clave);
            if (!equipo || equipo.id !== vectores.id_clave) return ['el QR de alta no da la clave de prueba'];
            const claves = new Map([[equipo.id, equipo]]);
            const fallos = [];
            for (const caso of vectores.casos) {
                const r = await v.verificar(caso.qr, claves, motor);
                if (r.autentico !== caso.valido) fallos.push(caso.descripcion);
                else if (caso.valido) {
                    const [d, h] = caso.salida.split('T');
                    const [a, m, dia] = d.split('-');
                    if (r.idAlumno !== caso.id_alumno || r.salida.fecha !== `${dia}/${m}/${a}` || r.salida.hora !== h)
                        fallos.push(caso.descripcion + ' (datos)');
                }
            }
            return fallos;
        }""",
        [VECTORES, motor],
    )


@pytest.mark.navegador
@pytest.mark.parametrize("motor", ["nativo", "js"])
def test_vectores_del_qr_en_el_navegador(page, url, motor):
    page.goto(url)
    assert _verificar_vectores(page, motor) == []


@pytest.mark.navegador
def test_veredicto_y_hora_de_madrid(page, url):
    page.goto(url)
    r = page.evaluate(
        """async ([qr, alta]) => {
            const v = await import('./verificador.js');
            const equipo = await v.claveDeQr(alta);
            const res = await v.verificar(qr, new Map([[equipo.id, equipo]]));
            return {
                antes: v.veredicto(res, '202610081229'),
                justo: v.veredicto(res, '202610081230'),
                tarde: v.veredicto(res, '202610081945'),
                otroDia: v.veredicto(res, '202610091230'),
                falso: v.veredicto({autentico: false, motivo: 'x'}, '202610081230'),
                invierno: v.ahoraEnMadrid(new Date('2026-01-15T11:00:00Z')),
                verano: v.ahoraEnMadrid(new Date('2026-07-15T10:00:00Z')),
                fechaImposible: v.fechaDeQr('202602301200'),
            };
        }""",
        [AUTENTICO, VECTORES["qr_de_clave"]],
    )
    assert r == {
        "antes": "TODAVIA_NO",
        "justo": "PUEDE_SALIR",
        "tarde": "PUEDE_SALIR",
        "otroDia": "OTRO_DIA",
        "falso": "NO_VALE",
        "invierno": "202601151200",
        "verano": "202607151200",
        "fechaImposible": None,
    }


def _tarjeta(page) -> tuple[str, str, str]:
    return (
        page.locator("#titulo").inner_text(),
        page.locator("#tarjeta").get_attribute("class"),
        page.locator("#detalle").inner_text(),
    )


@pytest.mark.navegador
def test_pantalla_del_vigilante_en_el_movil(page, url):
    errores: list[str] = []
    page.on("pageerror", lambda e: errores.append(str(e)))
    page.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    page.set_viewport_size({"width": 390, "height": 760})
    page.goto(url)
    expect(page.locator("#version")).not_to_be_empty()
    assert page.locator("#aviso-sin-equipos").is_visible()
    assert page.locator("#recuento").inner_text() == "sin equipos"
    SALIDAS.mkdir(exist_ok=True)
    page.screenshot(path=str(SALIDAS / "vigilante-inicio.png"))

    page.evaluate("t => window.vigilante.procesarAlta(t)", "esto no es un QR de alta")
    assert _tarjeta(page)[0] == "NO ES UN QR DE ALTA"
    page.evaluate("t => window.vigilante.procesarAlta(t)", VECTORES["qr_de_clave"])
    assert _tarjeta(page)[0] == "EQUIPO DADO DE ALTA"
    assert page.locator("#recuento").inner_text() == "1 equipo"
    assert not page.locator("#aviso-sin-equipos").is_visible()

    casos = {
        "puede-salir": (AUTENTICO, "202610081300", "PUEDE SALIR", "verde", "NIA 10519873 · comprueba la foto"),
        "todavia-no": (AUTENTICO, "202610081200", "TODAVÍA NO", "aviso", "sale a las 12:30"),
        "otro-dia": (AUTENTICO, "202610091300", "OTRO DÍA", "peligro", "08/10/2026"),
        "no-vale": (VECTORES["casos"][2]["qr"], "202610081300", "NO VALE", "peligro", "alterado o es falso"),
    }
    for nombre, (qr, ahora, titulo, color, texto) in casos.items():
        page.evaluate("([t, a]) => window.vigilante.procesarParte(t, a)", [qr, ahora])
        t, clase, detalle = _tarjeta(page)
        assert t == titulo and f"tarjeta--{color}" in clase and texto in detalle, nombre
        page.screenshot(path=str(SALIDAS / f"vigilante-{nombre}.png"))

    desborde = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    assert desborde <= 0, "la pantalla se sale de lado en el móvil"

    # Los equipos se quedan en el móvil al volver a abrir la app, y se pueden quitar.
    page.reload()
    expect(page.locator("#version")).not_to_be_empty()
    expect(page.locator("#recuento")).to_have_text("1 equipo")
    page.get_by_role("button", name="Equipos de confianza").click()
    assert page.locator("#lista-equipos").get_by_text("Equipo de prueba").is_visible()
    assert page.locator("#lista-equipos").get_by_text("56475AA7").is_visible()
    page.screenshot(path=str(SALIDAS / "vigilante-equipos.png"))
    page.get_by_role("button", name="Quitar").click()
    expect(page.locator("#recuento")).to_have_text("sin equipos")
    page.get_by_role("button", name="Cerrar").click()
    page.evaluate("([t, a]) => window.vigilante.procesarParte(t, a)", [AUTENTICO, "202610081300"])
    assert _tarjeta(page)[0] == "NO VALE" and "equipo desconocido" in _tarjeta(page)[2]

    assert errores == [], errores


@pytest.mark.navegador
def test_funciona_sin_conexion(page, url):
    page.goto(url)
    page.evaluate("() => navigator.serviceWorker.ready")
    page.reload()
    page.evaluate("async () => { while (!navigator.serviceWorker.controller) await new Promise(r => setTimeout(r, 50)); }")
    page.context.set_offline(True)
    try:
        page.reload()
        expect(page.locator("#version")).not_to_be_empty()
        assert page.locator("h1").inner_text() == "Vigilante EPLA"
        assert _verificar_vectores(page, "auto") == []
        fuentes_cargadas = page.evaluate("() => document.fonts.ready.then(f => [...f].filter(x => x.status === 'loaded').length)")
        assert fuentes_cargadas >= 1
    finally:
        page.context.set_offline(False)


def _video_con_qr(texto: str, destino: Path) -> Path:
    """Vídeo Y4M (el formato de la cámara simulada de Chromium) que enseña un QR en el centro."""
    import segno

    lado_px, ancho, alto = 6, 640, 480
    matriz = [list(fila) for fila in segno.make(texto, error="m").matrix]
    n = len(matriz) + 8  # zona de silencio
    lumas = bytearray(b"\xeb" * (ancho * alto))
    x0, y0 = (ancho - n * lado_px) // 2, (alto - n * lado_px) // 2
    for f, fila in enumerate(matriz):
        for c, negro in enumerate(fila):
            if negro:
                for dy in range(lado_px):
                    inicio = (y0 + (f + 4) * lado_px + dy) * ancho + x0 + (c + 4) * lado_px
                    lumas[inicio : inicio + lado_px] = b"\x10" * lado_px
    croma = b"\x80" * (ancho * alto // 4)
    with destino.open("wb") as video:
        video.write(f"YUV4MPEG2 W{ancho} H{alto} F10:1 Ip A1:1 C420jpeg\n".encode())
        for _ in range(10):
            video.write(b"FRAME\n" + bytes(lumas) + croma + croma)
    return destino


@pytest.mark.navegador
@pytest.mark.parametrize("que", ["alta", "parte"])
def test_lee_el_qr_con_la_camara(playwright, url, tmp_path, que):
    """De punta a punta: el botón abre la cámara, lee el QR y la tarjeta da el resultado."""
    texto = VECTORES["qr_de_clave"] if que == "alta" else AUTENTICO
    video = _video_con_qr(texto, tmp_path / "qr.y4m")
    navegador = playwright.chromium.launch(
        args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
              f"--use-file-for-fake-video-capture={video}"])
    try:
        pagina = navegador.new_page(viewport={"width": 390, "height": 760})
        pagina.context.grant_permissions(["camera"])
        errores: list[str] = []  # aquí la CSP de index.html sí se aplica: cualquier bloqueo sale como error
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        pagina.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pagina.goto(url)
        expect(pagina.locator("#version")).not_to_be_empty()
        if que == "alta":
            pagina.get_by_role("button", name="Equipos de confianza").click()
            pagina.get_by_role("button", name="Dar de alta").click()
            expect(pagina.locator("#titulo")).to_have_text("EQUIPO DADO DE ALTA", timeout=20000)
            assert pagina.locator("#recuento").inner_text() == "1 equipo"
        else:
            pagina.get_by_role("button", name="Escanear parte").click()
            # Sin equipos dados de alta, un parte auténtico tampoco vale: lo que importa es que se leyó.
            expect(pagina.locator("#titulo")).to_have_text("NO VALE", timeout=20000)
            assert "equipo desconocido" in pagina.locator("#detalle").inner_text()
        assert pagina.locator("#escaner").is_hidden()
        assert errores == [], errores
    finally:
        navegador.close()
