"""Capa de repositorios (acceso a datos con SQL parametrizado)."""

from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository

__all__ = [
    "DepartamentoRepository",
    "PacienteRepository",
    "EquipoRepository",
    "UsoRepository",
]
