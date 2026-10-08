"""Genera `android/vectores_qr.json`: casos de QR válidos y falsos para la app del vigilante.

    ~/.venvs/partes-salida/bin/python scripts/generar_vectores_qr.py

Usa una clave de PRUEBA fija (semilla pública en este archivo), nunca la de un
equipo real. La app Android y `tests/test_seguridad.py` comprueban estos mismos
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
    otro = Firmante(Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))))
    casos = [
        {"descripcion": "Parte auténtico", "qr": bueno, "valido": True,
         "id_alumno": "10519873", "salida": "2026-10-08T12:30", "expedido": "2026-10-08T09:14"},
        {"descripcion": "Alumno sin NIA (id de persona)", "valido": True,
         "qr": f.contenido_qr("P90012", salida, expedido), "id_alumno": "P90012",
         "salida": "2026-10-08T12:30", "expedido": "2026-10-08T09:14"},
        {"descripcion": "Hora de salida cambiada a mano", "qr": bueno.replace("202610081230", "202610081430"),
         "valido": False},
        {"descripcion": "NIA cambiado", "qr": bueno.replace("10519873", "10519874"), "valido": False},
        {"descripcion": "Firma recortada", "qr": bueno[:-4], "valido": False},
        {"descripcion": "Firmado por un equipo que no está dado de alta",
         "qr": otro.contenido_qr("10519873", salida, expedido), "valido": False},
        {"descripcion": "Texto que no es un parte", "qr": "https://epla.es", "valido": False},
    ]
    vectores = {
        "formato": "PS1|<id clave>|<id alumno>|<salida AAAAMMDDhhmm>|<expedido AAAAMMDDhhmm>|<firma Ed25519 base64url>",
        "aviso": "Clave de PRUEBA con semilla pública: no sirve para firmar partes reales.",
        "id_clave": f.id_clave,
        "clave_publica": b64url(f.publica),
        "qr_de_clave": f.qr_de_clave("Equipo de prueba"),
        "casos": casos,
    }
    destino = RAIZ / "android" / "vectores_qr.json"
    destino.write_text(json.dumps(vectores, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(casos)} casos en {destino}")


if __name__ == "__main__":
    main()
