"""Aviso a la familia por correo, con los logos de los ajustes en la cabecera."""

from __future__ import annotations

import html
import io
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from .ajustes import Ajustes, GestorAjustes
from .cifrado import leer_secreto
from .fechas import fecha_larga
from .modelo import Alumno

VERDE = "#2c7a3a"


def nombre_secreto_smtp(usuario: str) -> str:
    return f"smtp:{usuario.strip().lower()}"


def contrasena_smtp(ajustes: Ajustes) -> str | None:
    return leer_secreto(nombre_secreto_smtp(ajustes.smtp_usuario))


def _logo_png(gestor: GestorAjustes, nombre: str) -> bytes | None:
    ruta = gestor.ruta_imagen(nombre)
    if not ruta:
        return None
    from PIL import Image

    with Image.open(ruta) as im:
        im = im.convert("RGBA")
        im.thumbnail((600, 140))
        salida = io.BytesIO()
        im.save(salida, "PNG", optimize=True)
        return salida.getvalue()


def asunto(alumno: Alumno, salida: datetime) -> str:
    return f"Salida del centro: {alumno.nombre} {alumno.apellido1} · hoy a las {salida:%H:%M}"


def _contactos(a: Ajustes) -> list[tuple[str, str, str]]:
    filas = [
        ("Turno de mañana", a.contacto_manana_email.strip(), a.contacto_manana_tel.strip()),
        ("Turno de tarde", a.contacto_tarde_email.strip(), a.contacto_tarde_tel.strip()),
    ]
    return [f for f in filas if f[1] or f[2]]


def texto_plano(a: Ajustes, alumno: Alumno, salida: datetime) -> str:
    hijo = "su hija" if alumno.es_mujer else "su hijo"
    autorizado = "autorizada" if alumno.es_mujer else "autorizado"
    lineas = [
        "Estimada familia:",
        "",
        f"Les comunicamos que {hijo} {alumno.nombre_completo} ha sido {autorizado} por Jefatura de "
        f"Estudios a salir del centro hoy, {fecha_larga(salida.date())}, a las {salida:%H:%M} h.",
        "",
        f"Curso: {alumno.curso} ({alumno.etapa})",
        f"Hora de salida: {salida:%H:%M} h",
        "",
        "Si tienen cualquier duda, contacten con Jefatura de Estudios:",
        *[f"  {t}: {' · '.join(p for p in (e, tel) if p)}" for t, e, tel in _contactos(a)],
        "",
        "Atentamente,",
        f"Jefatura de Estudios · {a.centro}",
        "",
        "Mensaje automático: este buzón no recibe respuestas.",
    ]
    return "\n".join(lineas)


def texto_html(a: Ajustes, alumno: Alumno, salida: datetime, cid_izq: str | None, cid_der: str | None) -> str:
    e = html.escape
    hijo = "su hija" if alumno.es_mujer else "su hijo"
    autorizado = "autorizada" if alumno.es_mujer else "autorizado"
    logo = lambda cid, alto, alinear: (  # noqa: E731
        f'<td align="{alinear}"><img src="cid:{cid[1:-1]}" height="{alto}" alt=""></td>' if cid else "<td></td>"
    )
    contactos = "".join(
        f"<br>{e(t)}: " + " · ".join(e(p) for p in (em, tel) if p) for t, em, tel in _contactos(a)
    )
    return f"""<!doctype html><html lang="es"><body style="margin:0;background:#f3f5f1;font-family:Arial,Helvetica,sans-serif;color:#1b1f1c">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f1;padding:20px 8px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border:1px solid #d9e0d5;border-radius:8px">
<tr><td style="padding:14px 20px;border-bottom:4px solid {VERDE}"><table role="presentation" width="100%"><tr>{logo(cid_izq, 56, "left")}{logo(cid_der, 40, "right")}</tr></table></td></tr>
<tr><td style="padding:20px;font-size:15px;line-height:1.55">
<p style="margin:0 0 12px">Estimada familia:</p>
<p style="margin:0 0 14px">Les comunicamos que {hijo} <b>{e(alumno.nombre_completo)}</b> ha sido {autorizado} por Jefatura de Estudios a salir del centro hoy, {e(fecha_larga(salida.date()))}, a las <b>{salida:%H:%M}&nbsp;h</b>.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="font-size:14px;margin:0 0 14px">
<tr><td style="color:#5a625c;padding:3px 18px 3px 0">Curso</td><td>{e(alumno.curso)} ({e(alumno.etapa)})</td></tr>
<tr><td style="color:#5a625c;padding:3px 18px 3px 0">Hora de salida</td><td><b>{salida:%H:%M} h</b></td></tr></table>
<div style="background:#f2f6f1;border-radius:6px;padding:10px 12px;font-size:14px">Si tienen cualquier duda, contacten con Jefatura de Estudios.{contactos}</div>
<p style="margin:14px 0 0">Atentamente,<br>Jefatura de Estudios · {e(a.centro)}</p>
</td></tr>
<tr><td style="padding:12px 20px;border-top:1px solid #d9e0d5;font-size:12px;color:#5a625c">Mensaje automático: este buzón no recibe respuestas. {e(a.centro)}. Los datos se tratan conforme al RGPD para la comunicación con las familias.</td></tr>
</table></td></tr></table></body></html>"""


def construir_mensaje(
    gestor: GestorAjustes, alumno: Alumno, salida: datetime, destinatarios: list[str]
) -> EmailMessage:
    a = gestor.valores
    msg = EmailMessage()
    msg["Subject"] = asunto(alumno, salida)
    msg["From"] = formataddr((a.remitente_nombre, a.smtp_usuario))
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(texto_plano(a, alumno, salida))
    logos = [(n, _logo_png(gestor, n)) for n in ("logo_izquierdo", "logo_derecho")]
    cids = {n: make_msgid(domain="partes-salida") if datos else None for n, datos in logos}
    msg.add_alternative(
        texto_html(a, alumno, salida, cids["logo_izquierdo"], cids["logo_derecho"]), subtype="html"
    )
    parte_html = msg.get_payload()[1]
    for n, datos in logos:
        if datos:
            parte_html.add_related(datos, "image", "png", cid=cids[n], filename=f"{n}.png")
    return msg


def enviar(mensaje: EmailMessage, ajustes: Ajustes, contrasena: str) -> None:
    try:
        import certifi

        contexto = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        contexto = ssl.create_default_context()
    if int(ajustes.smtp_puerto) == 465:
        with smtplib.SMTP_SSL(ajustes.smtp_servidor, 465, timeout=25, context=contexto) as s:
            s.login(ajustes.smtp_usuario, contrasena)
            s.send_message(mensaje)
        return
    with smtplib.SMTP(ajustes.smtp_servidor, int(ajustes.smtp_puerto), timeout=25) as s:
        s.starttls(context=contexto)
        s.login(ajustes.smtp_usuario, contrasena)
        s.send_message(mensaje)
