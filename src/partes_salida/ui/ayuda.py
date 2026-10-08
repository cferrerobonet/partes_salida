"""Ayudas de la importación: de dónde sale cada archivo y qué hacer con él después.

Los textos están aquí, juntos, para cambiarlos sin tocar la ventana de Ajustes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from . import estilo
from .componentes import boton, etiqueta


@dataclass
class Ayuda:
    titulo: str
    pasos: list[str]
    aviso: str = ""
    notas: list[str] = field(default_factory=list)


AYUDA_EXCEL = Ayuda(
    titulo="Cómo descargar el Excel de Educamos",
    pasos=[
        "Entra en <b>Educamos</b>.",
        "Abre el menú <b>Datos</b> → <b>Import/Export</b>.",
        "Elige <b>Exportación de datos de alumnos</b>.",
        "Pulsa <b>Exportar</b> y descarga el archivo (<i>ExportacionDatosAlumnos.xls</i>).",
        "Arrástralo a esta zona o pulsa <b>Importar Excel…</b>",
    ],
    aviso=(
        "El Excel trae datos muy sensibles (DNI, IBAN, salud, direcciones). La app guarda solo lo necesario y lo "
        "cifra; al terminar te ofrece <b>enviar el archivo a la papelera</b>. Después vacía la papelera: "
        "conservarlo vulneraría el RGPD."
    ),
    notas=[
        "Importar un Excel nuevo <b>sustituye a todo el alumnado anterior</b>: el archivo es el colegio entero.",
        "Las fotos de quien sigue en el centro se conservan; las de las bajas se borran solas.",
    ],
)

AYUDA_FOTOS = Ayuda(
    titulo="Cómo preparar las fotos",
    pasos=[
        "Reúne las fotos en un <b>ZIP</b> (o en varios). Da igual cómo estén repartidas en carpetas y subcarpetas.",
        "Cada foto debe llamarse como el alumno en Educamos: <b>APELLIDOS, NOMBRE</b> "
        "(por ejemplo <i>GARCÍA LÓPEZ, LUCÍA.png</i>), en PNG o JPG. Tildes y mayúsculas dan igual.",
        "Arrastra el ZIP a esta zona o pulsa <b>Importar ZIP…</b>",
        "Si el nombre de una foto casi coincide (una tilde, una errata), la app te la enseña para que la confirmes. "
        "Las que no son de nadie se ignoran.",
    ],
    aviso=(
        "La app descomprime en memoria, reduce y <b>cifra cada foto</b>. El ZIP ya no hace falta: al terminar te "
        "ofrece <b>enviarlo a la papelera</b>. Vacíala después."
    ),
    notas=[
        "Volver a importar fotos <b>sustituye las que ya tenía</b> un alumno y <b>añade</b> las nuevas.",
    ],
)


class DialogoAyuda(QDialog):
    def __init__(self, ayuda: Ayuda, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Ayuda")
        self.setMinimumWidth(560)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(26, 22, 26, 20)
        capa.setSpacing(14)
        titulo = QLabel(ayuda.titulo)
        titulo.setFont(estilo.fuente(24, QFont.Weight.Bold, estilo.TITULAR))
        capa.addWidget(titulo)

        pasos = QGridLayout()
        pasos.setHorizontalSpacing(12)
        pasos.setVerticalSpacing(10)
        for i, texto in enumerate(ayuda.pasos, start=1):
            numero = QLabel(str(i))
            numero.setFixedSize(26, 26)
            numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
            numero.setStyleSheet(
                f"background:{estilo.T['accent']};color:{estilo.T['accent_ink']};border-radius:13px;font-weight:700;"
            )
            pasos.addWidget(numero, i, 0, Qt.AlignmentFlag.AlignTop)
            linea = QLabel(texto)
            linea.setWordWrap(True)
            linea.setTextFormat(Qt.TextFormat.RichText)
            pasos.addWidget(linea, i, 1)
        pasos.setColumnStretch(1, 1)
        capa.addLayout(pasos)

        if ayuda.aviso:
            caja = QFrame()
            caja.setStyleSheet(f"QFrame {{ background:{estilo.T['warn_soft']}; border-radius:9px; }}")
            fila = QHBoxLayout(caja)
            fila.setContentsMargins(14, 12, 14, 12)
            texto = QLabel(f"<b>Protección de datos.</b> {ayuda.aviso}")
            texto.setWordWrap(True)
            texto.setStyleSheet(f"color:{estilo.T['warn']};")
            fila.addWidget(texto)
            capa.addWidget(caja)
        if ayuda.notas:
            n = etiqueta("<br>".join(f"• {nota}" for nota in ayuda.notas), "muted", envolver=True)
            n.setTextFormat(Qt.TextFormat.RichText)
            capa.addWidget(n)

        botones = QHBoxLayout()
        botones.addStretch(1)
        entendido = boton("Entendido", primario=True)
        entendido.setDefault(True)
        entendido.clicked.connect(self.accept)
        botones.addWidget(entendido)
        capa.addLayout(botones)
