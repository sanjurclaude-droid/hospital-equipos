"""Gestión de la conexión SQLite e inicialización del esquema.

Este módulo encapsula la creación de conexiones a la base de datos SQLite y la
inicialización idempotente del esquema relacional definido en ``esquema.sql``.

Cada conexión creada mediante :func:`crear_conexion` tiene activada la
integridad referencial (``PRAGMA foreign_keys = ON``) y usa
:class:`sqlite3.Row` como ``row_factory`` para permitir el acceso a las
columnas por nombre.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Ruta al archivo DDL ubicado junto a este módulo.
_RUTA_ESQUEMA = Path(__file__).with_name("esquema.sql")


def crear_conexion(ruta: str) -> sqlite3.Connection:
    """Abre una conexión SQLite configurada.

    Args:
        ruta: Ruta al archivo de base de datos, o ``":memory:"`` para una base
            de datos en memoria (usada en las pruebas).

    Returns:
        Una conexión SQLite con la integridad referencial activada
        (``PRAGMA foreign_keys = ON``) y ``row_factory = sqlite3.Row``.
    """
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def inicializar_esquema(conexion: sqlite3.Connection) -> None:
    """Crea el esquema de la base de datos de forma idempotente.

    Lee el DDL desde ``esquema.sql`` y lo ejecuta. Como todas las sentencias
    usan ``CREATE TABLE IF NOT EXISTS`` / ``CREATE INDEX IF NOT EXISTS``, la
    operación puede invocarse varias veces sin efectos secundarios.

    Args:
        conexion: Conexión SQLite abierta sobre la que crear el esquema.
    """
    ddl = _RUTA_ESQUEMA.read_text(encoding="utf-8")
    conexion.executescript(ddl)
    conexion.commit()
