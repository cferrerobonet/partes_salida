"""Búsqueda tolerante: sin tildes, en cualquier orden, palabras a medias y erratas."""

from __future__ import annotations

from .modelo import Alumno, clave_nombre


class Buscador:
    def __init__(self, alumnos: list[Alumno]):
        ordenados = sorted(alumnos, key=lambda a: (a.clave_foto, a.id))
        self._entradas = [(a, clave_nombre(a.nombre_completo).replace(",", "").split()) for a in ordenados]

    def buscar(
        self,
        texto: str = "",
        etapa: str = "",
        clase: str = "",
        etapas_visibles: set[str] | None = None,
    ) -> list[Alumno]:
        base = [
            (a, palabras)
            for a, palabras in self._entradas
            if (not etapa or a.etapa_codigo == etapa)
            and (not clase or a.clase == clase)
            and (etapas_visibles is None or a.etapa_codigo in etapas_visibles)
        ]
        toks = clave_nombre(texto).replace(",", " ").split()
        if not toks:
            return [a for a, _ in base]
        exactos = [a for a, palabras in base if all(any(w.startswith(t) for w in palabras) for t in toks)]
        if exactos:
            return exactos
        from rapidfuzz import fuzz

        puntuados = []
        for a, palabras in base:
            nota = sum(max((fuzz.ratio(t, w) for w in palabras), default=0) for t in toks) / len(toks)
            if nota >= 78:
                puntuados.append((-nota, a.clave_foto, a))
        puntuados.sort(key=lambda x: (x[0], x[1]))
        return [a for *_, a in puntuados[:60]]
