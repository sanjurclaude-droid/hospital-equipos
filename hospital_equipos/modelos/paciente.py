"""Modelo del dominio: Paciente."""

from dataclasses import dataclass


@dataclass
class Paciente:
    """Persona atendida en el hospital, identificada por una cédula única."""

    id: int | None
    cedula: str
    nombre: str
    fecha_nacimiento: str = ""
    genero: str = ""
    telefono: str = ""
