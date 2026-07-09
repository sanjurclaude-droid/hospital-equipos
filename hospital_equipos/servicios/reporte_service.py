"""Servicio de dominio para consultas avanzadas y reportes de métricas.

Reúne las consultas de reporte del sistema, incluido el requisito crítico del
proyecto: el **Indicador de Uso Clínico**.

- **Inventario por departamento**
  (:meth:`ReporteService.inventario_por_departamento`): devuelve los equipos de
  un departamento existente; lista vacía si el departamento no tiene equipos.
- **Alerta de mantenimiento** (:meth:`ReporteService.alerta_mantenimiento`):
  devuelve únicamente los equipos cuyo estado es exactamente
  ``En mantenimiento``.
- **Indicador de Uso Clínico** (:meth:`ReporteService.indicador_uso_clinico`):
  clasifica los equipos por total de uso según el criterio SESIONES (conteo) u
  HORAS (suma de minutos / 60 redondeada a 2 decimales), con desempate
  determinista alfabético ascendente por nombre de equipo, opcionalmente
  restringido a un departamento existente.

La validación de la existencia del departamento y de la validez del criterio se
realiza en esta capa de servicio, lanzando :class:`ValueError` con mensajes
claros en español ante cualquier dato inválido y sin producir métricas
parciales. Depende de :class:`EquipoRepository`, :class:`UsoRepository` y
:class:`DepartamentoRepository`, inyectados mediante el constructor.

Requirements: 7.1-7.4, 8.1-8.4, 9.1-9.9
"""

from __future__ import annotations

from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.modelos.uso import CriterioUso, MetricaUso
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository


def _normalizar_criterio(criterio: CriterioUso | str) -> CriterioUso:
    """Convierte un criterio (enum o texto) a :class:`CriterioUso`.

    Args:
        criterio: Criterio como enum o como texto exacto del conjunto permitido.

    Returns:
        El :class:`CriterioUso` correspondiente.

    Raises:
        ValueError: Si el criterio no pertenece al conjunto {sesiones, horas}.
    """
    if isinstance(criterio, CriterioUso):
        return criterio
    try:
        return CriterioUso(criterio)
    except ValueError as exc:
        validos = ", ".join(c.value for c in CriterioUso)
        raise ValueError(
            f"El criterio es inválido; debe ser uno de: {validos}."
        ) from exc


class ReporteService:
    """Lógica de negocio para consultas avanzadas y reportes de métricas."""

    def __init__(
        self,
        equipo_repo: EquipoRepository,
        uso_repo: UsoRepository,
        departamento_repo: DepartamentoRepository,
    ) -> None:
        """Inicializa el servicio con sus dependencias.

        Args:
            equipo_repo: Acceso a datos de equipos (inventario y alerta de
                mantenimiento).
            uso_repo: Acceso a datos de sesiones de uso (agregación del
                Indicador de Uso Clínico).
            departamento_repo: Acceso a datos de departamentos (para validar la
                existencia del departamento en las consultas que lo requieren).
        """
        self._equipo_repo = equipo_repo
        self._uso_repo = uso_repo
        self._departamento_repo = departamento_repo

    # ------------------------------------------------------------------ #
    # Inventario por departamento (Tarea 11.1)                            #
    # ------------------------------------------------------------------ #
    def inventario_por_departamento(self, departamento_id: int) -> list[Equipo]:
        """Devuelve el inventario de equipos de un departamento existente.

        Args:
            departamento_id: Identificador de un departamento existente.

        Returns:
            Lista de :class:`Equipo` del departamento; lista vacía si el
            departamento existe pero no tiene equipos registrados.

        Raises:
            ValueError: Si el identificador es inválido (Requirement 7.4) o el
                departamento no existe (Requirement 7.3). No se devuelve ningún
                equipo.
        """
        self._validar_id_departamento(departamento_id)
        if self._departamento_repo.obtener_por_id(departamento_id) is None:
            raise ValueError(
                f"El departamento con id {departamento_id} no existe."
            )
        return self._equipo_repo.listar_por_departamento(departamento_id)

    # ------------------------------------------------------------------ #
    # Alerta de mantenimiento (Tarea 11.1)                                #
    # ------------------------------------------------------------------ #
    def alerta_mantenimiento(self) -> list[Equipo]:
        """Devuelve los equipos cuyo estado es exactamente ``En mantenimiento``.

        Returns:
            Lista de :class:`Equipo` en mantenimiento, excluyendo todo equipo
            con cualquier otro estado; lista vacía si no hay ninguno.
        """
        return self._equipo_repo.listar_por_estado(
            EstadoEquipo.EN_MANTENIMIENTO
        )

    # ------------------------------------------------------------------ #
    # Indicador de Uso Clínico — requisito crítico (Tarea 11.3)           #
    # ------------------------------------------------------------------ #
    def indicador_uso_clinico(
        self,
        criterio: CriterioUso | str,
        departamento_id: int | None = None,
    ) -> list[MetricaUso]:
        """Calcula el Indicador de Uso Clínico (equipo más utilizado).

        Por cada equipo con sesiones en el alcance solicitado, calcula el total
        de uso según el criterio:

        - :attr:`CriterioUso.SESIONES`: número de sesiones registradas.
        - :attr:`CriterioUso.HORAS`: suma de las duraciones en minutos dividida
          entre 60 y redondeada a 2 decimales.

        El resultado se ordena de forma no creciente por ``total_uso`` y, ante
        empates, alfabéticamente ascendente por nombre de equipo (desempate
        determinista). Cada :class:`MetricaUso` incluye el nombre del equipo, el
        nombre de su departamento y el total de uso.

        Args:
            criterio: Base de cálculo (SESIONES u HORAS).
            departamento_id: Si se indica, restringe el cálculo a los equipos de
                ese departamento existente; si es ``None`` incluye todos.

        Returns:
            Lista de :class:`MetricaUso` ordenada; vacía (sin error) si no hay
            equipos con sesiones en el alcance solicitado (Requirement 9.9).

        Raises:
            ValueError: Si el criterio es inválido (Requirement 9.8) o si se
                indica un departamento que no existe (Requirement 9.7). En
                ambos casos no se producen métricas.
        """
        # Validación del criterio (Requirement 9.8).
        criterio_norm = _normalizar_criterio(criterio)

        # Validación del departamento opcional (Requirements 9.6, 9.7).
        if departamento_id is not None:
            self._validar_id_departamento(departamento_id)
            if self._departamento_repo.obtener_por_id(departamento_id) is None:
                raise ValueError(
                    f"El departamento con id {departamento_id} no existe."
                )

        return self._uso_repo.agregar_uso_por_equipo(
            criterio_norm, departamento_id
        )

    # ------------------------------------------------------------------ #
    # Validaciones (privadas)                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_id_departamento(departamento_id: int) -> None:
        """Valida que el identificador de departamento sea un entero positivo.

        Raises:
            ValueError: Si el identificador es ``None``, booleano, no entero o
                no positivo (Requirements 7.4, 9.7).
        """
        if (
            departamento_id is None
            or isinstance(departamento_id, bool)
            or not isinstance(departamento_id, int)
            or departamento_id <= 0
        ):
            raise ValueError(
                "El identificador de departamento no es válido."
            )
