"""Modelos del dominio: UsoEquipo, el enum CriterioUso y MetricaUso."""

from dataclasses import dataclass
from enum import Enum


class CriterioUso(str, Enum):
    """Base de cálculo del Indicador de Uso Clínico."""

    SESIONES = "sesiones"  # número de sesiones registradas
    HORAS = "horas"        # horas acumuladas de uso


@dataclass
class UsoEquipo:
    """Sesión de uso de un equipo por parte de un paciente."""

    id: int | None
    equipo_id: int
    paciente_id: int
    fecha_inicio: str
    duracion_minutos: int


@dataclass
class MetricaUso:
    """Métrica agregada de uso de un equipo para el Indicador de Uso Clínico."""

    equipo_nombre: str
    departamento_nombre: str
    total_uso: float  # nº de sesiones o total de horas según criterio
    criterio: CriterioUso
