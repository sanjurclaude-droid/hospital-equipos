"""Configuración y fixtures compartidas de pytest.

Proporciona una conexión SQLite en memoria (`:memory:`) con el esquema
inicializado y `PRAGMA foreign_keys = ON` activo, para aislar cada prueba.

Depende de `hospital_equipos.db.conexion`, cuyo comportamiento real se
implementa en la Tarea 2.1. Una vez implementada esa tarea, esta fixture
quedará plenamente operativa sin cambios adicionales.
"""

from __future__ import annotations

import sqlite3

import pytest

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema


@pytest.fixture
def conexion() -> sqlite3.Connection:
    """Devuelve una conexión SQLite en memoria con el esquema inicializado.

    La conexión tiene la integridad referencial activada
    (`PRAGMA foreign_keys = ON`) y se cierra automáticamente al finalizar la
    prueba.
    """
    conn = crear_conexion(":memory:")
    inicializar_esquema(conn)
    try:
        yield conn
    finally:
        conn.close()
