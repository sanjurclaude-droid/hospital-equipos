"""Repositorio de acceso a datos para la entidad Equipo.

Encapsula todas las sentencias SQL de la tabla ``equipos`` usando consultas
parametrizadas (placeholders ``?``) y traduce entre filas de la base de datos
(:class:`sqlite3.Row`) y objetos del dominio
(:class:`~hospital_equipos.modelos.equipo.Equipo`).

El campo ``estado`` se persiste como texto (el valor del enum
:class:`~hospital_equipos.modelos.equipo.EstadoEquipo`) y se reconstruye como
enum al leer.

Requirements: 3.1, 7.1, 8.1, 10.1, 10.4
"""

from __future__ import annotations

import sqlite3

from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo


def _estado_a_texto(estado: EstadoEquipo | str) -> str:
    """Normaliza un estado (enum o texto) a su representación textual."""
    if isinstance(estado, EstadoEquipo):
        return estado.value
    return str(estado)


def _fila_a_equipo(fila: sqlite3.Row) -> Equipo:
    """Convierte una fila de la tabla ``equipos`` en un ``Equipo``."""
    return Equipo(
        id=fila["id"],
        codigo_inventario=fila["codigo_inventario"],
        nombre=fila["nombre"],
        marca=fila["marca"] or "",
        modelo=fila["modelo"] or "",
        numero_serie=fila["numero_serie"] or "",
        fecha_adquisicion=fila["fecha_adquisicion"] or "",
        estado=EstadoEquipo(fila["estado"]),
        departamento_id=fila["departamento_id"],
    )


class EquipoRepository:
    """Acceso a datos para equipos médicos (SQL parametrizado)."""

    _COLUMNAS = (
        "id, codigo_inventario, nombre, marca, modelo, numero_serie, "
        "fecha_adquisicion, estado, departamento_id"
    )

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def insertar(self, equipo: Equipo) -> Equipo:
        """Inserta un equipo y devuelve el objeto con su ``id`` asignado."""
        cursor = self._conexion.execute(
            "INSERT INTO equipos "
            "(codigo_inventario, nombre, marca, modelo, numero_serie, "
            "fecha_adquisicion, estado, departamento_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                equipo.codigo_inventario,
                equipo.nombre,
                equipo.marca,
                equipo.modelo,
                equipo.numero_serie,
                equipo.fecha_adquisicion,
                _estado_a_texto(equipo.estado),
                equipo.departamento_id,
            ),
        )
        self._conexion.commit()
        return Equipo(
            id=cursor.lastrowid,
            codigo_inventario=equipo.codigo_inventario,
            nombre=equipo.nombre,
            marca=equipo.marca,
            modelo=equipo.modelo,
            numero_serie=equipo.numero_serie,
            fecha_adquisicion=equipo.fecha_adquisicion,
            estado=EstadoEquipo(_estado_a_texto(equipo.estado)),
            departamento_id=equipo.departamento_id,
        )

    def obtener_por_id(self, equipo_id: int) -> Equipo | None:
        """Devuelve el equipo con el ``id`` dado, o ``None`` si no existe."""
        fila = self._conexion.execute(
            f"SELECT {self._COLUMNAS} FROM equipos WHERE id = ?",
            (equipo_id,),
        ).fetchone()
        return _fila_a_equipo(fila) if fila is not None else None

    def obtener_por_codigo(self, codigo_inventario: str) -> Equipo | None:
        """Devuelve el equipo con el código de inventario dado, o ``None``."""
        fila = self._conexion.execute(
            f"SELECT {self._COLUMNAS} FROM equipos WHERE codigo_inventario = ?",
            (codigo_inventario,),
        ).fetchone()
        return _fila_a_equipo(fila) if fila is not None else None

    def actualizar(self, equipo: Equipo) -> Equipo:
        """Actualiza todos los campos del equipo identificado por su ``id``.

        Args:
            equipo: Equipo con el ``id`` a actualizar y los nuevos valores.

        Returns:
            El mismo :class:`Equipo` (con su estado normalizado a enum).
        """
        self._conexion.execute(
            "UPDATE equipos SET "
            "codigo_inventario = ?, nombre = ?, marca = ?, modelo = ?, "
            "numero_serie = ?, fecha_adquisicion = ?, estado = ?, "
            "departamento_id = ? "
            "WHERE id = ?",
            (
                equipo.codigo_inventario,
                equipo.nombre,
                equipo.marca,
                equipo.modelo,
                equipo.numero_serie,
                equipo.fecha_adquisicion,
                _estado_a_texto(equipo.estado),
                equipo.departamento_id,
                equipo.id,
            ),
        )
        self._conexion.commit()
        return Equipo(
            id=equipo.id,
            codigo_inventario=equipo.codigo_inventario,
            nombre=equipo.nombre,
            marca=equipo.marca,
            modelo=equipo.modelo,
            numero_serie=equipo.numero_serie,
            fecha_adquisicion=equipo.fecha_adquisicion,
            estado=EstadoEquipo(_estado_a_texto(equipo.estado)),
            departamento_id=equipo.departamento_id,
        )

    def eliminar(self, equipo_id: int) -> None:
        """Elimina el equipo con el ``id`` dado del inventario."""
        self._conexion.execute(
            "DELETE FROM equipos WHERE id = ?", (equipo_id,)
        )
        self._conexion.commit()

    def listar_por_departamento(self, departamento_id: int) -> list[Equipo]:
        """Devuelve los equipos del departamento dado, ordenados por ``id``."""
        filas = self._conexion.execute(
            f"SELECT {self._COLUMNAS} FROM equipos "
            "WHERE departamento_id = ? ORDER BY id ASC",
            (departamento_id,),
        ).fetchall()
        return [_fila_a_equipo(fila) for fila in filas]

    def listar_por_estado(self, estado: EstadoEquipo | str) -> list[Equipo]:
        """Devuelve los equipos cuyo estado coincide, ordenados por ``id``."""
        filas = self._conexion.execute(
            f"SELECT {self._COLUMNAS} FROM equipos "
            "WHERE estado = ? ORDER BY id ASC",
            (_estado_a_texto(estado),),
        ).fetchall()
        return [_fila_a_equipo(fila) for fila in filas]
