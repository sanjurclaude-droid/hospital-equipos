"""Pruebas unitarias de la Interfaz de Menú de Consola (CLI).

La CLI se prueba de forma aislada inyectando funciones de entrada y salida
(``entrada``/``salida``): la entrada se alimenta con una secuencia guionizada de
respuestas y la salida se captura en una lista, sin depender del ``stdin`` ni
del ``stdout`` reales.

Cubre:

- Selección inválida, no numérica y vacía en el menú principal, sin invocar
  ninguna operación (Requirements 11.2, 11.4).
- Formato de salida campo/valor, un campo por línea (Requirement 11.2).
- Flujo de reintentos ante datos inválidos y cancelación tras 3 intentos
  (Requirements 11.5, 11.6).

Requirements: 11.2, 11.4, 11.5, 11.6
"""

from __future__ import annotations

import sqlite3

import pytest

from hospital_equipos.cli.menu import MenuConsola, construir_menu
from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema


@pytest.fixture
def conexion() -> sqlite3.Connection:
    """Conexión SQLite en memoria con el esquema inicializado."""
    conn = crear_conexion(":memory:")
    inicializar_esquema(conn)
    try:
        yield conn
    finally:
        conn.close()


def _ejecutar_menu(
    conexion: sqlite3.Connection, respuestas: list[str]
) -> list[str]:
    """Ejecuta el menú con respuestas guionizadas y devuelve las líneas de salida."""
    iterador = iter(respuestas)
    salidas: list[str] = []

    def entrada(prompt: str = "") -> str:
        return next(iterador)

    def salida(mensaje: str = "") -> None:
        salidas.append(str(mensaje))

    menu = construir_menu(conexion, entrada=entrada, salida=salida)
    menu.ejecutar()
    return salidas


def _contar(salidas: list[str], subcadena: str) -> int:
    return sum(1 for linea in salidas if subcadena in linea)


def _contar_filas(conexion: sqlite3.Connection, tabla: str) -> int:
    (total,) = conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()
    return total


# --------------------------------------------------------------------------- #
# Requirement 11.4 — Selección inválida / no numérica / vacía                  #
# --------------------------------------------------------------------------- #
def test_selecciones_invalidas_no_invocan_operaciones(
    conexion: sqlite3.Connection,
) -> None:
    """Entradas no numéricas, vacías o fuera de rango se rechazan sin operar."""
    # "abc" (no numérica), "" (vacía), "99" (fuera de rango) y luego "6" salir.
    salidas = _ejecutar_menu(conexion, ["abc", "", "99", "6"])

    assert _contar(salidas, "no válida") == 3
    # Ninguna operación fue invocada: la base de datos permanece vacía.
    assert _contar_filas(conexion, "departamentos") == 0
    assert _contar_filas(conexion, "pacientes") == 0
    # El sistema terminó de forma limpia al seleccionar "Salir".
    assert any("Hasta pronto" in linea for linea in salidas)


def test_salir_inmediato_termina_limpio(conexion: sqlite3.Connection) -> None:
    """Seleccionar "6" (Salir) de inmediato finaliza sin errores."""
    salidas = _ejecutar_menu(conexion, ["6"])
    assert any("Hasta pronto" in linea for linea in salidas)


def test_fin_de_entrada_termina_sin_error(conexion: sqlite3.Connection) -> None:
    """Agotar la entrada (EOF) finaliza el bucle principal sin excepción."""
    salidas = _ejecutar_menu(conexion, [])
    assert any("Entrada finalizada" in linea for linea in salidas)


# --------------------------------------------------------------------------- #
# Requirement 11.2 — Formato de salida campo/valor, un campo por línea         #
# --------------------------------------------------------------------------- #
def test_registro_departamento_muestra_formato_campo_valor(
    conexion: sqlite3.Connection,
) -> None:
    """Tras registrar, el resultado se muestra como 'etiqueta: valor' por línea."""
    respuestas = [
        "1",          # Menú principal -> Departamentos
        "1",          # Submenú -> Registrar departamento
        "Urgencias",  # nombre
        "Atención inmediata",  # descripción
        "4",          # Submenú -> Volver
        "6",          # Menú principal -> Salir
    ]
    salidas = _ejecutar_menu(conexion, respuestas)

    assert "nombre: Urgencias" in salidas
    assert "id: 1" in salidas
    assert "descripción: Atención inmediata" in salidas
    assert _contar_filas(conexion, "departamentos") == 1


def test_listar_pacientes_vacio_muestra_mensaje(
    conexion: sqlite3.Connection,
) -> None:
    """Listar sin registros muestra un mensaje y no falla."""
    respuestas = ["2", "2", "3", "6"]  # Pacientes -> Listar -> Volver -> Salir
    salidas = _ejecutar_menu(conexion, respuestas)
    assert any("No hay pacientes" in linea for linea in salidas)


# --------------------------------------------------------------------------- #
# Requirements 11.5 / 11.6 — Reintentos y cancelación                          #
# --------------------------------------------------------------------------- #
def test_reintento_exitoso_conserva_los_demas_datos(
    conexion: sqlite3.Connection,
) -> None:
    """Un género inválido se re-solicita; al corregirlo, el registro tiene éxito.

    Los demás campos ya introducidos (cédula, nombre, fecha, teléfono) se
    conservan; solo se vuelve a pedir el dato rechazado.
    """
    respuestas = [
        "2",             # Pacientes
        "1",             # Registrar paciente
        "123",           # cédula
        "Ana Pérez",     # nombre
        "2000-01-01",    # fecha de nacimiento
        "xxx",           # género inválido -> será rechazado
        "1234567",       # teléfono
        "femenino",      # reintento del género (válido)
        "3",             # Submenú -> Volver
        "6",             # Salir
    ]
    salidas = _ejecutar_menu(conexion, respuestas)

    assert any("Dato rechazado -> género" in linea for linea in salidas)
    assert any("Paciente registrado correctamente" in linea for linea in salidas)
    # El paciente se creó con los datos conservados y el género corregido.
    assert _contar_filas(conexion, "pacientes") == 1
    fila = conexion.execute(
        "SELECT cedula, nombre, genero FROM pacientes"
    ).fetchone()
    assert fila["cedula"] == "123"
    assert fila["nombre"] == "Ana Pérez"
    assert fila["genero"] == "femenino"


def test_cancelacion_tras_tres_reintentos(
    conexion: sqlite3.Connection,
) -> None:
    """Tres reintentos fallidos cancelan la operación y vuelven al menú."""
    respuestas = [
        "2",             # Pacientes
        "1",             # Registrar paciente
        "123",           # cédula
        "Ana Pérez",     # nombre
        "2000-01-01",    # fecha de nacimiento
        "xxx",           # género inválido (intento 0)
        "1234567",       # teléfono
        "yyy",           # reintento 1 (inválido)
        "zzz",           # reintento 2 (inválido)
        "www",           # reintento 3 (inválido)
        "3",             # Submenú -> Volver (tras cancelar)
        "6",             # Salir
    ]
    salidas = _ejecutar_menu(conexion, respuestas)

    assert any("Reintento 1 de 3" in linea for linea in salidas)
    assert any("Reintento 3 de 3" in linea for linea in salidas)
    assert any("cancelada" in linea for linea in salidas)
    # No se creó ningún paciente.
    assert _contar_filas(conexion, "pacientes") == 0


def test_valor_no_numerico_en_id_se_reintenta_como_campo(
    conexion: sqlite3.Connection,
) -> None:
    """Un id de departamento no numérico se detecta y se re-solicita ese campo."""
    respuestas = [
        "3",             # Equipos
        "1",             # Registrar equipo
        "EQ-001",        # código de inventario
        "Monitor",       # nombre
        "Acme",          # marca
        "X1",            # modelo
        "SN-001",        # número de serie
        "2023-01-10",    # fecha de adquisición
        "",              # estado (enter = Operativo)
        "no-numero",     # id de departamento inválido (no numérico)
        "abc",           # reintento 1 (inválido)
        "def",           # reintento 2 (inválido)
        "ghi",           # reintento 3 (inválido)
        "7",             # Submenú -> Volver
        "6",             # Salir
    ]
    salidas = _ejecutar_menu(conexion, respuestas)

    assert any(
        "Dato rechazado -> id del departamento" in linea for linea in salidas
    )
    assert any("cancelada" in linea for linea in salidas)
    assert _contar_filas(conexion, "equipos") == 0


# --------------------------------------------------------------------------- #
# Construcción del menú                                                        #
# --------------------------------------------------------------------------- #
def test_construir_menu_devuelve_instancia(
    conexion: sqlite3.Connection,
) -> None:
    """``construir_menu`` cablea las capas y devuelve un ``MenuConsola``."""
    menu = construir_menu(conexion, entrada=lambda p="": "6", salida=lambda m="": None)
    assert isinstance(menu, MenuConsola)
