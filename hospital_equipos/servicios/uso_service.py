"""Servicio de dominio para el registro y consulta de sesiones de uso.

Aplica las reglas de negocio del registro de sesiones de uso de equipos por
parte de los pacientes:

- **Registro** (:meth:`UsoService.registrar_uso`): valida la existencia del
  equipo y del paciente (integridad referencial), la validez de la fecha/hora
  de inicio (no futura) y la duración (entero entre 1 y 1440 minutos). Crea
  exactamente una sesión.
- **Consulta** (:meth:`UsoService.listar_por_equipo`): devuelve las sesiones de
  un equipo ordenadas de más reciente a más antigua.

Ante cualquier dato inválido, el servicio lanza :class:`ValueError` con un
mensaje claro en español y no crea ninguna sesión. Depende de
:class:`UsoRepository`, :class:`EquipoRepository` (validar equipo) y
:class:`PacienteRepository` (validar paciente), inyectados por el constructor.

Requirements: 6.1-6.8, 10.5, 10.6, 10.8
"""

from __future__ import annotations

from datetime import datetime

from hospital_equipos.modelos.uso import UsoEquipo
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository

# Rango válido de la duración en minutos (Requirements 6.4, 10.8).
_DURACION_MINIMA = 1
_DURACION_MAXIMA = 1440

# Formatos aceptados para la fecha/hora de inicio.
_FORMATOS_FECHA_INICIO = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")


class UsoService:
    """Lógica de negocio para el registro y consulta de sesiones de uso."""

    def __init__(
        self,
        repositorio: UsoRepository,
        equipo_repo: EquipoRepository,
        paciente_repo: PacienteRepository,
    ) -> None:
        """Inicializa el servicio con sus dependencias.

        Args:
            repositorio: Acceso a datos de sesiones de uso.
            equipo_repo: Acceso a datos de equipos (para validar la existencia
                del equipo — integridad referencial).
            paciente_repo: Acceso a datos de pacientes (para validar la
                existencia del paciente — integridad referencial).
        """
        self._repositorio = repositorio
        self._equipo_repo = equipo_repo
        self._paciente_repo = paciente_repo

    def registrar_uso(
        self,
        equipo_id: int,
        paciente_id: int,
        inicio: str,
        duracion_minutos: int,
    ) -> UsoEquipo:
        """Registra una sesión de uso tras validar todos sus campos.

        Args:
            equipo_id: Identificador de un equipo existente.
            paciente_id: Identificador de un paciente existente.
            inicio: Fecha/hora de inicio ``YYYY-MM-DD HH:MM`` (o con segundos),
                válida y no posterior a la fecha/hora actual.
            duracion_minutos: Entero entre 1 y 1440 (ambos inclusive).

        Returns:
            El :class:`UsoEquipo` creado con su identificador asignado.

        Raises:
            ValueError: Si el equipo o el paciente no existen, la fecha/hora es
                inválida o futura, o la duración está fuera de rango. No se crea
                ninguna sesión.
        """
        # Existencia del equipo (Requirements 6.2, 10.5).
        self._validar_id(equipo_id, "equipo")
        if self._equipo_repo.obtener_por_id(equipo_id) is None:
            raise ValueError(f"El equipo con id {equipo_id} no existe.")

        # Existencia del paciente (Requirements 6.3, 10.6).
        self._validar_id(paciente_id, "paciente")
        if self._paciente_repo.obtener_por_id(paciente_id) is None:
            raise ValueError(f"El paciente con id {paciente_id} no existe.")

        # Fecha/hora de inicio: válida y no futura (Requirement 6.5).
        inicio_norm = self._validar_inicio(inicio)

        # Duración: entero entre 1 y 1440 (Requirements 6.4, 10.8).
        duracion_norm = self._validar_duracion(duracion_minutos)

        return self._repositorio.insertar(
            UsoEquipo(
                id=None,
                equipo_id=equipo_id,
                paciente_id=paciente_id,
                fecha_inicio=inicio_norm,
                duracion_minutos=duracion_norm,
            )
        )

    def listar_por_equipo(self, equipo_id: int) -> list[UsoEquipo]:
        """Devuelve las sesiones de un equipo, de más reciente a más antigua.

        Args:
            equipo_id: Identificador del equipo cuyas sesiones se listan.

        Returns:
            Lista de :class:`UsoEquipo` ordenada de forma descendente por
            fecha/hora de inicio; vacía si el equipo no tiene sesiones.
        """
        self._validar_id(equipo_id, "equipo")
        return self._repositorio.listar_por_equipo(equipo_id)

    # ------------------------------------------------------------------ #
    # Validaciones (privadas)                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_inicio(inicio: str) -> str:
        """Valida la fecha/hora de inicio (formato válido y no futura).

        Raises:
            ValueError: Si está ausente, tiene formato inválido o es posterior
                a la fecha/hora actual del sistema.
        """
        if inicio is None or not str(inicio).strip():
            raise ValueError("La fecha/hora de inicio es obligatoria.")
        inicio_normalizado = str(inicio).strip()

        momento: datetime | None = None
        for formato in _FORMATOS_FECHA_INICIO:
            try:
                momento = datetime.strptime(inicio_normalizado, formato)
                break
            except ValueError:
                continue
        if momento is None:
            raise ValueError(
                "La fecha/hora de inicio es inválida; use el formato "
                "YYYY-MM-DD HH:MM."
            )

        if momento > datetime.now():
            raise ValueError(
                "La fecha/hora de inicio es inválida; no puede ser posterior "
                "a la fecha/hora actual."
            )
        return inicio_normalizado

    @staticmethod
    def _validar_duracion(duracion_minutos: int) -> int:
        """Valida que la duración sea un entero entre 1 y 1440.

        Raises:
            ValueError: Si no es un entero o está fuera del rango [1, 1440]. Se
                rechazan explícitamente los booleanos y los valores numéricos no
                enteros (p. ej. flotantes).
        """
        if duracion_minutos is None or isinstance(duracion_minutos, bool):
            raise ValueError(
                "La duración es inválida; debe ser un entero entre "
                f"{_DURACION_MINIMA} y {_DURACION_MAXIMA} minutos."
            )
        if not isinstance(duracion_minutos, int):
            raise ValueError(
                "La duración es inválida; debe ser un entero entre "
                f"{_DURACION_MINIMA} y {_DURACION_MAXIMA} minutos."
            )
        if not (_DURACION_MINIMA <= duracion_minutos <= _DURACION_MAXIMA):
            raise ValueError(
                "La duración es inválida; debe ser un entero entre "
                f"{_DURACION_MINIMA} y {_DURACION_MAXIMA} minutos."
            )
        return duracion_minutos

    @staticmethod
    def _validar_id(identificador: int, etiqueta: str) -> None:
        """Valida que un identificador sea un entero positivo.

        Raises:
            ValueError: Si el identificador es ``None``, booleano, no entero o
                no positivo.
        """
        if (
            identificador is None
            or isinstance(identificador, bool)
            or not isinstance(identificador, int)
            or identificador <= 0
        ):
            raise ValueError(f"El identificador del {etiqueta} no es válido.")
