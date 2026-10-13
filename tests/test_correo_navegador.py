"""El correo HTML abierto en un navegador real (Playwright + Chromium).

Comprueba lo que ve la familia: los logos cargan, el texto va en su género, el
pie con jefatura está y la maqueta no se desborda en un móvil. Deja una captura
en `test-results/correo-*.png` para revisarla a ojo.
"""

import base64
from datetime import datetime
from pathlib import Path

import pytest

from partes_salida.ajustes import GestorAjustes
from partes_salida.correo import construir_mensaje

pytestmark = pytest.mark.navegador
pytest.importorskip("playwright")

SALIDAS = Path(__file__).resolve().parents[1] / "test-results"


def _html_autonomo(msg) -> str:
    """Sustituye `cid:` por los datos de la imagen, como hace un cliente de correo."""
    html = msg.get_body(("html",)).get_content()
    for parte in msg.walk():
        cid = parte.get("Content-ID")
        if cid:
            datos = base64.b64encode(parte.get_payload(decode=True)).decode()
            html = html.replace(f"cid:{cid.strip('<>')}", f"data:image/png;base64,{datos}")
    return html


@pytest.mark.parametrize("ancho", [700, 380])
def test_correo_se_ve_bien(page, datos, alumnos, ancho):
    nerea = next(a for a in alumnos if a.nombre == "NEREA")
    msg = construir_mensaje(GestorAjustes(datos), nerea, datetime(2026, 10, 8, 12, 30), ["x@ejemplo.es"])
    page.set_viewport_size({"width": ancho, "height": 900})
    page.set_content(_html_autonomo(msg))
    assert page.get_by_text("su hija").is_visible()
    assert page.get_by_text("NEREA BELTRÁN ROIG").is_visible()
    assert page.get_by_text("jefaturafpbach@epla.es", exact=False).is_visible()
    logos = page.locator("img")
    assert logos.count() == 2
    for i in range(2):
        assert page.evaluate("(img) => img.naturalWidth", logos.nth(i).element_handle()) > 0
    desborde = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    assert desborde <= 0, "el correo se sale del ancho de la pantalla"
    SALIDAS.mkdir(exist_ok=True)
    page.screenshot(path=str(SALIDAS / f"correo-{ancho}.png"), full_page=True)


def test_correo_del_alumno_con_su_parte_se_ve_en_el_movil(page, contexto):
    """El alumno enseña el parte en la puerta desde el móvil: tiene que verse entero y nítido."""
    from partes_salida.correo import mensajes_del_parte
    from partes_salida.impresion import parte_adjunto
    from partes_salida.parte import DatosParte

    marc = next(a for a in contexto.alumnos if a.nombre == "MARC")
    cuando = datetime(2026, 10, 8, 12, 30)
    datos = DatosParte(marc, contexto.foto(marc.id), cuando, cuando, contexto.firmante.contenido_qr(marc.id, cuando, cuando))
    (msg,) = mensajes_del_parte(contexto.gestor, marc, cuando, [], True, parte_adjunto(datos, contexto))
    page.set_viewport_size({"width": 380, "height": 900})
    page.set_content(_html_autonomo(msg))
    assert page.get_by_text("Hola, Marc:").is_visible()
    parte = page.locator('img[alt="Parte de salida"]')
    assert parte.is_visible() and page.evaluate("(img) => img.naturalWidth", parte.element_handle()) >= 1200
    desborde = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    assert desborde <= 0, "el correo se sale del ancho de la pantalla"
    SALIDAS.mkdir(exist_ok=True)
    page.screenshot(path=str(SALIDAS / "correo-alumno-380.png"), full_page=True)
