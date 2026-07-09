"""Repositorio de acceso a datos para la entidad Departamento.

Encapsula todas las sentencias SQL de la tabla ``departamentos`` usando
consultas parametrizadas (placeholders ``?``) para evitar la inyección SQL, y
traduce entre filas de la base de datos (:class:`sqlite3.Row`) y objetos del
dominio (:class:`~hospital_equipos.modelos.departamento.Departamento`).

Requirements: 1.1, 1.7, 10.3
"""

from __future__ import annotations

import sqlite3

from hospital_equipos.modelos.departamento import Departamento


def _fila_a_departamento(fila: sqlite3.Row) -> Departamento:
    """Convierte una fila de la tabla ``departamentos`` en un ``Departamento``."""
    return Departamento(
        id=fila["id"],
        nombre=fila["nombre"],
        descripcion=fila["descripcion"] or "",
    )


def _py_lower(valor: str | None) -> str | None:
    """Lowercasing Unicode-aware para usar desde SQL.

    La función ``LOWER`` integrada de SQLite solo pliega caracteres ASCII, por
    lo que no maneja acentos (p. ej. ``Í`` → ``í``), comunes en los nombres de
    departamentos en español. Se delega en ``str.lower`` de Python, que sí es
    consciente de Unicode, para garantizar una comparación de nombres
    verdaderamente insensible a mayúsculas/minúsculas.
    """
    return valor.lower() if valor is not None else None


class DepartamentoRepository:
    """Acceso a datos para departamentos (SQL parametrizado)."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion
        # Registrar la función de lowercasing Unicode-aware en la conexión.
        # Registrarla varias veces es idempotente (sobrescribe la anterior).
        conexion.create_function("py_lower", 1, _py_lower)

    def insertar(self, departamento: Departamento) -> Departamento:
        """Inserta un departamento y devuelve el objeto con su ``id`` asignado.

        Args:
            departamento: Departamento a persistir (su ``id`` se ignora).

        Returns:
            Un nuevo :class:`Departamento` con el identificador autogenerado.
        """
        cursor = self._conexion.execute(
            "INSERT INTO departamentos (nombre, descripcion) VALUES (?, ?)",
            (departamento.nombre, departamento.descripcion),
        )
        self._conexion.commit()
        return Departamento(
            id=cursor.lastrowid,
            nombre=departamento.nombre,
            descripcion=departamento.descripcion,
        )

    def obtener_por_id(self, departamento_id: int) -> Departamento | None:
        """Devuelve el departamento con el ``id`` dado, o ``None`` si no existe."""
        fila = self._conexion.execute(
            "SELECT id, nombre, descripcion FROM departamentos WHERE id = ?",
            (departamento_id,),
        ).fetchone()
        return _fila_a_departamento(fila) if fila is not None else None

    def obtener_por_nombre(self, nombre: str) -> Departamento | None:
        """Devuelve el departamento cuyo nombre coincide (sin distinguir mayúsculas).

        La comparación es insensible a mayúsculas/minúsculas mediante
        ``LOWER(...)`` en ambos lados de la comparación.
        """
        fila = self._conexion.execute(
            "SELECT id, nombre, descripcion FROM departamentos "
            "WHERE py_lower(nombre) = py_lower(?)",
            (nombre,),
        ).fetchone()
        return _fila_a_departamento(fila) if fila is not None else None

    def listar(self) -> list[Departamento]:
        """Devuelve todos los departamentos ordenados por ``id`` ascendente."""
        filas = self._conexion.execute(
            "SELECT id, nombre, descripcion FROM departamentos ORDER BY id ASC"
        ).fetchall()
        return [_fila_a_departamento(fila) for fila in filas]
