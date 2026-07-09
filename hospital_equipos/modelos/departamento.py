"""Modelo del dominio: Departamento."""

from dataclasses import dataclass


@dataclass
class Departamento:
    """Unidad organizativa del hospital que agrupa equipos médicos."""

    id: int | None
    nombre: str
    descripcion: str = ""
