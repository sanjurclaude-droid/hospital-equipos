"""Modelo del dominio: Equipo y el enum EstadoEquipo."""

from dataclasses import dataclass
from enum import Enum


class EstadoEquipo(str, Enum):
    """Estados operativos válidos de un equipo médico."""

    OPERATIVO = "Operativo"
    EN_MANTENIMIENTO = "En mantenimiento"
    FUERA_DE_SERVICIO = "Fuera de servicio"


@dataclass
class Equipo:
    """Equipo médico del inventario, asignado a un departamento."""

    id: int | None
    codigo_inventario: str
    nombre: str
    marca: str
    modelo: str
    numero_serie: str
    fecha_adquisicion: str
    estado: EstadoEquipo
    departamento_id: int
