"""Punto de entrada de la aplicación (Tarea 12.3).

Realiza el cableado completo de las capas del sistema:

1. Crea la conexión a la base de datos ``hospital.db``.
2. Inicializa el esquema relacional de forma idempotente.
3. Precarga los 12 departamentos base del hospital (solo si la tabla está
   vacía).
4. Instancia repositorios y servicios y arranca el menú de consola.

Requirements: 1.5, 11.1
"""

from __future__ import annotations

from hospital_equipos.cli.menu import construir_menu
from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.servicios.departamento_service import DepartamentoService

# Ruta del archivo de base de datos SQLite de la aplicación.
_RUTA_BD = "hospital.db"


def main() -> None:
    """Inicia la aplicación de consola con el cableado completo de las capas."""
    conexion = crear_conexion(_RUTA_BD)
    try:
        inicializar_esquema(conexion)

        # Precarga de los 12 departamentos base (idempotente: se omite si ya
        # existen departamentos registrados) — Requirement 1.5.
        departamento_service = DepartamentoService(
            DepartamentoRepository(conexion)
        )
        mensaje_precarga = departamento_service.inicializar_departamentos_base()
        print(mensaje_precarga)

        menu = construir_menu(conexion, entrada=input, salida=print)
        menu.ejecutar()
    finally:
        conexion.close()


if __name__ == "__main__":
    main()
