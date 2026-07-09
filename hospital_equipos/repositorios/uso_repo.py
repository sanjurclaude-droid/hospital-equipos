"""Repositorio de acceso a datos para la entidad UsoEquipo (sesiones de uso).

Encapsula las sentencias SQL de la tabla ``uso_equipos`` usando consultas
parametrizadas (placeholders ``?``) e incluye la agregación que alimenta el
**Indicador de Uso Clínico** (requisito crítico), resuelta con ``JOIN`` +
``GROUP BY`` + ``ORDER BY`` en el motor de la base de datos.

Requirements: 6.1, 6.7, 9.1, 9.2
"""

from __future__ import annotations

import sqlite3

from hospital_equipos.modelos.uso import CriterioUso, MetricaUso, UsoEquipo


def _fila_a_uso(fila: sqlite3.Row) -> UsoEquipo:
    """Convierte una fila de la tabla ``uso_equipos`` en un ``UsoEquipo``."""
    return UsoEquipo(
        id=fila["id"],
        equipo_id=fila["equipo_id"],
        paciente_id=fila["paciente_id"],
        fecha_inicio=fila["fecha_inicio"],
        duracion_minutos=fila["duracion_minutos"],
    )


class UsoRepository:
    """Acceso a datos para las sesiones de uso (SQL parametrizado)."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def insertar(self, uso: UsoEquipo) -> UsoEquipo:
        """Inserta una sesión de uso y devuelve el objeto con su ``id``."""
        cursor = self._conexion.execute(
            "INSERT INTO uso_equipos "
            "(equipo_id, paciente_id, fecha_inicio, duracion_minutos) "
            "VALUES (?, ?, ?, ?)",
            (
                uso.equipo_id,
                uso.paciente_id,
                uso.fecha_inicio,
                uso.duracion_minutos,
            ),
        )
        self._conexion.commit()
        return UsoEquipo(
            id=cursor.lastrowid,
            equipo_id=uso.equipo_id,
            paciente_id=uso.paciente_id,
            fecha_inicio=uso.fecha_inicio,
            duracion_minutos=uso.duracion_minutos,
        )

    def listar_por_equipo(self, equipo_id: int) -> list[UsoEquipo]:
        """Devuelve las sesiones del equipo ordenadas por fecha descendente.

        El orden es por ``fecha_inicio`` de más reciente a más antigua; ante
        empate de fecha se desempata por ``id`` descendente (la más reciente
        insertada primero) para un orden determinista.
        """
        filas = self._conexion.execute(
            "SELECT id, equipo_id, paciente_id, fecha_inicio, duracion_minutos "
            "FROM uso_equipos WHERE equipo_id = ? "
            "ORDER BY fecha_inicio DESC, id DESC",
            (equipo_id,),
        ).fetchall()
        return [_fila_a_uso(fila) for fila in filas]

    def contar_por_equipo(self, equipo_id: int) -> int:
        """Devuelve el número de sesiones registradas para el equipo dado."""
        (total,) = self._conexion.execute(
            "SELECT COUNT(id) FROM uso_equipos WHERE equipo_id = ?",
            (equipo_id,),
        ).fetchone()
        return total

    def agregar_uso_por_equipo(
        self,
        criterio: CriterioUso,
        departamento_id: int | None = None,
    ) -> list[MetricaUso]:
        """Agrega el uso por equipo para el Indicador de Uso Clínico.

        Une ``uso_equipos`` con ``equipos`` y ``departamentos``, agrupa por
        equipo y calcula el total según el criterio:

        - :attr:`CriterioUso.SESIONES`: número de sesiones (``COUNT``).
        - :attr:`CriterioUso.HORAS`: suma de minutos dividida entre 60 y
          redondeada a 2 decimales (``ROUND(SUM(...) / 60.0, 2)``).

        El resultado se ordena de forma no creciente por ``total_uso`` y, ante
        empates, alfabéticamente ascendente por nombre de equipo (desempate
        determinista, requisito 9.4).

        Args:
            criterio: Base de cálculo (SESIONES u HORAS).
            departamento_id: Si se indica, restringe el cálculo a los equipos de
                ese departamento; si es ``None`` incluye todos.

        Returns:
            Lista de :class:`MetricaUso` ordenada; vacía si no hay equipos con
            sesiones en el alcance solicitado.
        """
        if criterio == CriterioUso.HORAS:
            expresion_total = "ROUND(SUM(u.duracion_minutos) / 60.0, 2)"
        else:
            expresion_total = "COUNT(u.id)"

        consulta = (
            f"SELECT e.nombre AS equipo, d.nombre AS departamento, "
            f"{expresion_total} AS total_uso "
            "FROM uso_equipos u "
            "JOIN equipos e       ON e.id = u.equipo_id "
            "JOIN departamentos d ON d.id = e.departamento_id "
            "WHERE (? IS NULL OR e.departamento_id = ?) "
            "GROUP BY e.id "
            "ORDER BY total_uso DESC, e.nombre ASC"
        )
        filas = self._conexion.execute(
            consulta, (departamento_id, departamento_id)
        ).fetchall()
        return [
            MetricaUso(
                equipo_nombre=fila["equipo"],
                departamento_nombre=fila["departamento"],
                total_uso=fila["total_uso"],
                criterio=criterio,
            )
            for fila in filas
        ]
