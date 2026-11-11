"""Genera `vigilante/vectores_qr.json`: casos de QR válidos y falsos para la app del vigilante.

    ~/.venvs/partes-salida/bin/python scripts/generar_vectores_qr.py

Usa una clave de PRUEBA fija (semilla pública en este archivo), nunca la de un
equipo real. La web del vigilante (`tests/test_vigilante.py`) y `tests/test_seguridad.py` comprueban estos mismos
casos: si cambia el formato del QR, se regenera y ambos lados deben seguir en verde.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from partes_salida.firma import Firmante, b64url  # noqa: E402

SEMILLA_DE_PRUEBA = bytes(range(32))


def main() -> None:
    f = Firmante(Ed25519PrivateKey.from_private_bytes(SEMILLA_DE_PRUEBA))
    salida, expedido = datetime(2026, 10, 8, 12, 30), datetime(2026, 10, 8, 9, 14)
    bueno = f.contenido_qr("10519873", salida, expedido)
    sola = f.contenido_qr("10519873", salida, expedido, "SA")
    otro = Firmante(Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))))
    datos = {"salida": "2026-10-08T12:30", "expedido": "2026-10-08T09:14"}

    def valido(descripcion: str, qr: str, id_alumno: str = "10519873", compania: str = "-") -> dict:
        return {"descripcion": descripcion, "qr": qr, "valido": True, "id_alumno": id_alumno, **datos,
                "compania": compania}

    casos = [
        valido("Parte auténtico (etapa sin compañía)", bueno),
        valido("Alumno sin NIA (id de persona)", f.contenido_qr("P90012", salida, expedido), "P90012"),
        {"descripcion": "Hora de salida cambiada a mano", "qr": bueno.replace("202610081230", "202610081430"),
         "valido": False},
        {"descripcion": "NIA cambiado", "qr": bueno.replace("10519873", "10519874"), "valido": False},
        {"descripcion": "Firma recortada", "qr": bueno[:-4], "valido": False},
        {"descripcion": "Firmado por un equipo que no está dado de alta",
         "qr": otro.contenido_qr("10519873", salida, expedido), "valido": False},
        {"descripcion": "Texto que no es un parte", "qr": "https://epla.es", "valido": False},
        *(valido(f"ESO o Grado Básico: {texto}", f.contenido_qr("10519873", salida, expedido, c), compania=c)
          for c, texto in (("SO", "sale solo"), ("SA", "sale sola"), ("AO", "acompañado"), ("AA", "acompañada"))),
        {"descripcion": "«Sale sola» cambiado a mano por «acompañada»", "qr": sola.replace("|SA|", "|AA|"),
         "valido": False},
        {"descripcion": "Compañía que no existe", "qr": sola.replace("|SA|", "|XX|"), "valido": False},
        {"descripcion": "Prefijo PS2 sin el campo de compañía",
         "qr": f.firmar(["PS2", f.id_clave, "10519873", "202610081230", "202610080914"]), "valido": False},
        valido("Parte antiguo PS1 (se lee durante el curso 2026-2027)",
               f.firmar(["PS1", f.id_clave, "10519873", "202610081230", "202610080914"])),
        {"descripcion": "PS1 con un campo de más", "valido": False,
         "qr": f.firmar(["PS1", f.id_clave, "10519873", "202610081230", "202610080914", "SA"])},
    ]
    vectores = {
        "formato": "PS2|<id clave>|<id alumno>|<salida AAAAMMDDhhmm>|<expedido AAAAMMDDhhmm>|<compañía SO SA AO AA ->|<firma Ed25519 base64url>",
        "formato_anterior": "PS1|<id clave>|<id alumno>|<salida>|<expedido>|<firma> (se lee durante el curso 2026-2027)",
        "aviso": "Clave de PRUEBA con semilla pública: no sirve para firmar partes reales.",
        "id_clave": f.id_clave,
        "clave_publica": b64url(f.publica),
        "qr_de_clave": f.qr_de_clave("Equipo de prueba"),
        "casos": casos,
    }
    destino = RAIZ / "vigilante" / "vectores_qr.json"
    destino.write_text(json.dumps(vectores, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(casos)} casos en {destino}")


if __name__ == "__main__":
    main()
