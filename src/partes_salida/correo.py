"""Correo del parte: aviso a la familia y parte para el propio alumno.

Los dos llevan los logos de los ajustes en la cabecera y el parte dentro: como
imagen en el cuerpo (el alumno lo enseña en la puerta desde el móvil) y en PDF
adjunto (por si hay que imprimirlo).
"""

from __future__ import annotations

import html
import io
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from .ajustes import Ajustes, GestorAjustes
from .cifrado import leer_secreto
from .fechas import fecha_larga
from .modelo import Alumno, nombre_propio

VERDE = "#2c7a3a"


@dataclass
class ParteAdjunto:
    """El parte ya dibujado: PNG para verlo en el correo y PDF A6 para imprimirlo."""

    png: bytes
    pdf: bytes
    nombre: str  # sin extensión: «Parte de salida APELLIDOS, Nombre 2026-10-13 12.30»


def nombre_secreto_smtp(usuario: str) -> str:
    return f"smtp:{usuario.strip().lower()}"


def correo_configurado(ajustes: Ajustes) -> bool:
    """Servidor, puerto y remitente escritos en Ajustes → Correo (no vienen de serie)."""
    return bool(ajustes.smtp_servidor.strip() and ajustes.smtp_usuario.strip() and int(ajustes.smtp_puerto) > 0)


FALTA_CONFIGURAR = "falta configurar el servidor de correo en Ajustes → Correo"


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


def asunto(alumno: Alumno, salida: datetime, para_alumno: bool = False) -> str:
    if para_alumno:
        return f"Tu parte de salida · hoy a las {salida:%H:%M}"
    return f"Salida del centro: {alumno.nombre} {alumno.apellido1} · hoy a las {salida:%H:%M}"


def _contactos(a: Ajustes) -> list[tuple[str, str, str]]:
    filas = [
        ("Turno de mañana", a.contacto_manana_email.strip(), a.contacto_manana_tel.strip()),
        ("Turno de tarde", a.contacto_tarde_email.strip(), a.contacto_tarde_tel.strip()),
    ]
    return [f for f in filas if f[1] or f[2]]


def _saludo_y_cuerpo(alumno: Alumno, salida: datetime, para_alumno: bool) -> tuple[str, str]:
    """Saludo y primer párrafo (texto plano, sin negritas)."""
    autorizado = "autorizada" if alumno.es_mujer else "autorizado"
    cuando = f"hoy, {fecha_larga(salida.date())}, a las {salida:%H:%M} h"
    if para_alumno:
        return (f"Hola, {nombre_propio(alumno.nombre)}:",
                f"Jefatura de Estudios te ha {autorizado} a salir del centro {cuando}.")
    hijo = "su hija" if alumno.es_mujer else "su hijo"
    return ("Estimada familia:",
            f"Les comunicamos que {hijo} {alumno.nombre_completo} ha sido {autorizado} por Jefatura de "
            f"Estudios a salir del centro {cuando}.")


def _nota_parte(para_alumno: bool) -> str:
    if para_alumno:
        return ("Aquí tienes tu parte de salida: enséñalo en la puerta desde el móvil. "
                "Solo vale para esta fecha y hora. También va en PDF adjunto por si hay que imprimirlo.")
    return "El parte de salida va en este correo y en PDF adjunto."


def texto_plano(a: Ajustes, alumno: Alumno, salida: datetime, para_alumno: bool = False,
                con_parte: bool = False) -> str:
    saludo, cuerpo = _saludo_y_cuerpo(alumno, salida, para_alumno)
    lineas = [
        saludo,
        "",
        cuerpo,
        "",
        *([_nota_parte(para_alumno), ""] if con_parte else []),
        f"Curso: {alumno.curso} ({alumno.etapa})",
        f"Hora de salida: {salida:%H:%M} h",
        "",
        ("Si tienes cualquier duda, pregunta en Jefatura de Estudios:" if para_alumno else
         "Si tienen cualquier duda, contacten con Jefatura de Estudios:"),
        *[f"  {t}: {' · '.join(p for p in (e, tel) if p)}" for t, e, tel in _contactos(a)],
        "",
        "Atentamente,",
        f"Jefatura de Estudios · {a.centro}",
        "",
        "Mensaje automático: este buzón no recibe respuestas.",
    ]
    return "\n".join(lineas)


def texto_html(a: Ajustes, alumno: Alumno, salida: datetime, cid_izq: str | None, cid_der: str | None,
               para_alumno: bool = False, cid_parte: str | None = None) -> str:
    e = html.escape
    hijo = "su hija" if alumno.es_mujer else "su hijo"
    autorizado = "autorizada" if alumno.es_mujer else "autorizado"
    cuando = f"hoy, {e(fecha_larga(salida.date()))}, a las <b>{salida:%H:%M}&nbsp;h</b>"
    if para_alumno:
        saludo = f"Hola, {e(nombre_propio(alumno.nombre))}:"
        cuerpo = f"Jefatura de Estudios te ha {autorizado} a salir del centro {cuando}."
        dudas = "Si tienes cualquier duda, pregunta en Jefatura de Estudios."
    else:
        saludo = "Estimada familia:"
        cuerpo = (f"Les comunicamos que {hijo} <b>{e(alumno.nombre_completo)}</b> ha sido {autorizado} por "
                  f"Jefatura de Estudios a salir del centro {cuando}.")
        dudas = "Si tienen cualquier duda, contacten con Jefatura de Estudios."
    parte = (
        f'<p style="margin:0 0 8px">{e(_nota_parte(para_alumno))}</p>'
        f'<img src="cid:{cid_parte[1:-1]}" width="100%" alt="Parte de salida" '
        f'style="display:block;max-width:560px;border:1px solid #d9e0d5;border-radius:6px;margin:0 0 14px">'
        if cid_parte else ""
    )
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
<p style="margin:0 0 12px">{saludo}</p>
<p style="margin:0 0 14px">{cuerpo}</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="font-size:14px;margin:0 0 14px">
<tr><td style="color:#5a625c;padding:3px 18px 3px 0">Curso</td><td>{e(alumno.curso)} ({e(alumno.etapa)})</td></tr>
<tr><td style="color:#5a625c;padding:3px 18px 3px 0">Hora de salida</td><td><b>{salida:%H:%M} h</b></td></tr></table>
{parte}<div style="background:#f2f6f1;border-radius:6px;padding:10px 12px;font-size:14px">{dudas}{contactos}</div>
<p style="margin:14px 0 0">Atentamente,<br>Jefatura de Estudios · {e(a.centro)}</p>
</td></tr>
<tr><td style="padding:12px 20px;border-top:1px solid #d9e0d5;font-size:12px;color:#5a625c">Mensaje automático: este buzón no recibe respuestas. {e(a.centro)}. Los datos se tratan conforme al RGPD para la comunicación con el alumnado y las familias.</td></tr>
</table></td></tr></table></body></html>"""


def construir_mensaje(
    gestor: GestorAjustes, alumno: Alumno, salida: datetime, destinatarios: list[str],
    parte: ParteAdjunto | None = None, para_alumno: bool = False,
) -> EmailMessage:
    a = gestor.valores
    msg = EmailMessage()
    msg["Subject"] = asunto(alumno, salida, para_alumno)
    msg["From"] = formataddr((a.remitente_nombre, a.smtp_usuario))
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(texto_plano(a, alumno, salida, para_alumno, con_parte=parte is not None))
    logos = [(n, _logo_png(gestor, n)) for n in ("logo_izquierdo", "logo_derecho")]
    if parte:
        logos.append(("parte", parte.png))
    cids = {n: make_msgid(domain="partes-salida") if datos else None for n, datos in logos}
    msg.add_alternative(
        texto_html(a, alumno, salida, cids["logo_izquierdo"], cids["logo_derecho"], para_alumno,
                   cids.get("parte")),
        subtype="html",
    )
    parte_html = msg.get_payload()[1]
    for n, datos in logos:
        if datos:
            parte_html.add_related(datos, "image", "png", cid=cids[n], filename=f"{n}.png")
    if parte:
        msg.add_attachment(parte.pdf, maintype="application", subtype="pdf", filename=f"{parte.nombre}.pdf")
    return msg


def mensajes_del_parte(
    gestor: GestorAjustes, alumno: Alumno, salida: datetime, familia: list[str], al_alumno: bool,
    parte: ParteAdjunto | None,
) -> list[EmailMessage]:
    """Un correo a la familia (si hay a quién) y otro, con su texto, al alumno."""
    mensajes = []
    if familia:
        mensajes.append(construir_mensaje(gestor, alumno, salida, familia, parte))
    if al_alumno and alumno.email:
        mensajes.append(construir_mensaje(gestor, alumno, salida, [alumno.email], parte, para_alumno=True))
    return mensajes


def enviar(mensaje: EmailMessage, ajustes: Ajustes, contrasena: str) -> None:
    if not correo_configurado(ajustes):
        raise ValueError(FALTA_CONFIGURAR[0].upper() + FALTA_CONFIGURAR[1:] + ".")
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
