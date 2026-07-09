"""Pruebas unitarias de la capa de base de datos (conexión y esquema).

Validan la Tarea 2.1:
- ``PRAGMA foreign_keys`` está activo tras crear la conexión.
- Las 4 tablas del dominio existen tras inicializar el esquema.
- La integridad referencial rechaza inserciones con FK inválidas.
- El CHECK ``duracion_minutos > 0`` rechaza duraciones no positivas.

Requirements: 10.4, 10.5, 10.8
"""

from __future__ import annotations

import sqlite3

import pytest

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema

TABLAS_ESPERADAS = {"departamentos", "pacientes", "equipos", "uso_equipos"}


def test_pragma_foreign_keys_activo(conexion: sqlite3.Connection) -> None:
    """La conexión debe tener la integridad referencial activada."""
    (valor,) = conexion.execute("PRAGMA foreign_keys").fetchone()
    assert valor == 1


def test_row_factory_es_row() -> None:
    """La conexión debe usar ``sqlite3.Row`` como ``row_factory``."""
    conn = crear_conexion(":memory:")
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()


def test_existen_las_cuatro_tablas(conexion: sqlite3.Connection) -> None:
    """Tras inicializar el esquema deben existir las 4 tablas del dominio."""
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    nombres = {fila["name"] for fila in filas}
    assert TABLAS_ESPERADAS.issubset(nombres)


def test_inicializar_esquema_es_idempotente(
    conexion: sqlite3.Connection,
) -> None:
    """Ejecutar la inicialización dos veces no debe producir errores."""
    inicializar_esquema(conexion)  # segunda invocación
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    nombres = {fila["name"] for fila in filas}
    assert TABLAS_ESPERADAS.issubset(nombres)


def test_indice_uso_equipos_existe(conexion: sqlite3.Connection) -> None:
    """Debe existir el índice sobre uso_equipos(equipo_id)."""
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    ).fetchall()
    nombres = {fila["name"] for fila in filas}
    assert "idx_uso_equipos_equipo_id" in nombres


def test_fk_invalida_es_rechazada(conexion: sqlite3.Connection) -> None:
    """Insertar un equipo con departamento_id inexistente debe fallar por FK."""
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "INSERT INTO equipos "
            "(codigo_inventario, nombre, departamento_id) "
            "VALUES (?, ?, ?)",
            ("EQ-001", "Monitor", 999),
        )


def test_fk_sesion_invalida_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Una sesión con equipo_id/paciente_id inexistentes debe fallar por FK."""
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "INSERT INTO uso_equipos "
            "(equipo_id, paciente_id, fecha_inicio, duracion_minutos) "
            "VALUES (?, ?, ?, ?)",
            (999, 999, "2024-06-01 09:30", 30),
        )


def test_check_duracion_no_positiva_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Una duración <= 0 debe violar el CHECK (duracion_minutos > 0)."""
    # Preparar filas válidas para aislar la violación al CHECK y no a la FK.
    conexion.execute(
        "INSERT INTO departamentos (nombre) VALUES (?)", ("Laboratorio",)
    )
    conexion.execute(
        "INSERT INTO equipos "
        "(codigo_inventario, nombre, departamento_id) VALUES (?, ?, ?)",
        ("EQ-001", "Analizador", 1),
    )
    conexion.execute(
        "INSERT INTO pacientes (cedula, nombre) VALUES (?, ?)",
        ("8-888-8888", "Ana Pérez"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute(
            "INSERT INTO uso_equipos "
            "(equipo_id, paciente_id, fecha_inicio, duracion_minutos) "
            "VALUES (?, ?, ?, ?)",
            (1, 1, "2024-06-01 09:30", 0),
        )
