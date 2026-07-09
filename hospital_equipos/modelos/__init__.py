"""Modelos del dominio (dataclasses y enums)."""

from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.modelos.uso import CriterioUso, MetricaUso, UsoEquipo

__all__ = [
    "Departamento",
    "Paciente",
    "Equipo",
    "EstadoEquipo",
    "UsoEquipo",
    "CriterioUso",
    "MetricaUso",
]
