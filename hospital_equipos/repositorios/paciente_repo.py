"""Repositorio de acceso a datos para la entidad Paciente.

Encapsula todas las sentencias SQL de la tabla ``pacientes`` usando consultas
parametrizadas (placeholders ``?``) y traduce entre filas de la base de datos
(:class:`sqlite3.Row`) y objetos del dominio
(:class:`~hospital_equipos.modelos.paciente.Paciente`).

Requirements: 2.1, 2.4, 10.2
"""

from __future__ import annotations

import sqlite3

from hospital_equipos.modelos.paciente import Paciente


def _fila_a_paciente(fila: sqlite3.Row) -> Paciente:
    """Convierte una fila de la tabla ``pacientes`` en un ``Paciente``."""
    return Paciente(
        id=fila["id"],
        cedula=fila["cedula"],
        nombre=fila["nombre"],
        fecha_nacimiento=fila["fecha_nacimiento"] or "",
        genero=fila["genero"] or "",
        telefono=fila["telefono"] or "",
    )


class PacienteRepository:
    """Acceso a datos para pacientes (SQL parametrizado)."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def insertar(self, paciente: Paciente) -> Paciente:
        """Inserta un paciente y devuelve el objeto con su ``id`` asignado.

        Args:
            paciente: Paciente a persistir (su ``id`` se ignora).

        Returns:
            Un nuevo :class:`Paciente` con el identificador autogenerado.
        """
        cursor = self._conexion.execute(
            "INSERT INTO pacientes "
            "(cedula, nombre, fecha_nacimiento, genero, telefono) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                paciente.cedula,
                paciente.nombre,
                paciente.fecha_nacimiento,
                paciente.genero,
                paciente.telefono,
            ),
        )
        self._conexion.commit()
        return Paciente(
            id=cursor.lastrowid,
            cedula=paciente.cedula,
            nombre=paciente.nombre,
            fecha_nacimiento=paciente.fecha_nacimiento,
            genero=paciente.genero,
            telefono=paciente.telefono,
        )

    def obtener_por_id(self, paciente_id: int) -> Paciente | None:
        """Devuelve el paciente con el ``id`` dado, o ``None`` si no existe."""
        fila = self._conexion.execute(
            "SELECT id, cedula, nombre, fecha_nacimiento, genero, telefono "
            "FROM pacientes WHERE id = ?",
            (paciente_id,),
        ).fetchone()
        return _fila_a_paciente(fila) if fila is not None else None

    def obtener_por_cedula(self, cedula: str) -> Paciente | None:
        """Devuelve el paciente con la cédula dada, o ``None`` si no existe."""
        fila = self._conexion.execute(
            "SELECT id, cedula, nombre, fecha_nacimiento, genero, telefono "
            "FROM pacientes WHERE cedula = ?",
            (cedula,),
        ).fetchone()
        return _fila_a_paciente(fila) if fila is not None else None

    def listar(self) -> list[Paciente]:
        """Devuelve todos los pacientes ordenados por ``nombre`` ascendente."""
        filas = self._conexion.execute(
            "SELECT id, cedula, nombre, fecha_nacimiento, genero, telefono "
            "FROM pacientes ORDER BY nombre ASC"
        ).fetchall()
        return [_fila_a_paciente(fila) for fila in filas]
