"""Pruebas de PacienteService: unitarias y basadas en propiedades.

Cubre las validaciones de registro (cédula, nombre, fecha de nacimiento,
género y teléfono), la unicidad de la cédula, el listado ordenado por nombre y
la consulta.

Requirements: 2.2, 2.3, 2.4, 2.5, 10.2
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.servicios.paciente_service import PacienteService


def _servicio(conexion: sqlite3.Connection) -> PacienteService:
    return PacienteService(PacienteRepository(conexion))


def _registrar(
    servicio: PacienteService,
    cedula: str = "888888888",
    nombre: str = "Ana Pérez",
    fecha_nacimiento: str = "1990-05-10",
    genero: str = "femenino",
    telefono: str = "61234567",
):
    return servicio.registrar(cedula, nombre, fecha_nacimiento, genero, telefono)


# --------------------------------------------------------------------------- #
# Prueba basada en propiedades (Tarea 6.2)                                     #
# Feature: hospital-equipment-management, Property 1: Unicidad de              #
# códigos/cédulas/nombres                                                      #
# Validates: Requirements 2.2, 10.2                                            #
# --------------------------------------------------------------------------- #
# Cédulas alfanuméricas únicas de 1 a 20 caracteres.
_cedulas = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=20,
).filter(lambda s: s.isalnum())


@settings(max_examples=100)
@given(cedulas=st.lists(_cedulas, min_size=1, max_size=8, unique=True))
def test_propiedad_unicidad_cedula(cedulas: list[str]) -> None:
    """Property 1: no pueden coexistir dos pacientes con la misma cédula.

    Para cualquier conjunto de cédulas, registrar cada una y luego un segundo
    intento con la misma cédula debe ser rechazado; el conjunto de cédulas
    persistidas debe ser único.

    Se usa una conexión SQLite en memoria fresca por ejemplo para evitar fugas
    de estado entre las iteraciones de hypothesis.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)

        for indice, cedula in enumerate(cedulas):
            _registrar(servicio, cedula=cedula, nombre=f"Paciente {indice}")
            with pytest.raises(ValueError):
                _registrar(servicio, cedula=cedula, nombre="Duplicado")

        persistidas = [p.cedula for p in servicio.listar()]
        assert len(persistidas) == len(set(persistidas))
        assert set(persistidas) == set(cedulas)
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Pruebas unitarias (Tarea 6.3)                                                #
# --------------------------------------------------------------------------- #
def test_registrar_paciente_valido(conexion: sqlite3.Connection) -> None:
    """Requirement 2.1: un paciente con datos válidos se registra."""
    servicio = _servicio(conexion)
    creado = _registrar(servicio)
    assert creado.id is not None
    assert creado.cedula == "888888888"


def test_cedula_duplicada_es_rechazada(conexion: sqlite3.Connection) -> None:
    """Requirement 2.2 / 10.2: cédula duplicada rechazada, estado conservado."""
    servicio = _servicio(conexion)
    _registrar(servicio, cedula="A123", nombre="Ana")
    with pytest.raises(ValueError, match="Ya existe"):
        _registrar(servicio, cedula="A123", nombre="Otro")
    assert len(servicio.listar()) == 1


def test_cedula_vacia_es_rechazada(conexion: sqlite3.Connection) -> None:
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="cédula"):
        _registrar(servicio, cedula="   ")
    assert servicio.listar() == []


def test_nombre_vacio_es_rechazado(conexion: sqlite3.Connection) -> None:
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="nombre"):
        _registrar(servicio, nombre="")
    assert servicio.listar() == []


def test_fecha_nacimiento_futura_es_rechazada(conexion: sqlite3.Connection) -> None:
    """Requirement 2.3: una fecha de nacimiento futura es rechazada."""
    servicio = _servicio(conexion)
    manana = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="fecha de nacimiento"):
        _registrar(servicio, fecha_nacimiento=manana)
    assert servicio.listar() == []


def test_fecha_nacimiento_formato_invalido_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="fecha de nacimiento"):
        _registrar(servicio, fecha_nacimiento="10/05/1990")
    assert servicio.listar() == []


def test_genero_invalido_es_rechazado(conexion: sqlite3.Connection) -> None:
    """Requirement 2.3: un género fuera del conjunto válido es rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="género"):
        _registrar(servicio, genero="no-binario-x")
    assert servicio.listar() == []


@pytest.mark.parametrize("telefono", ["123456", "1234567890123456", "abc4567"])
def test_telefono_fuera_de_rango_es_rechazado(
    conexion: sqlite3.Connection, telefono: str
) -> None:
    """Requirement 2.3: teléfono con menos de 7 o más de 15 dígitos, o no numérico."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="teléfono|teléfono"):
        _registrar(servicio, telefono=telefono)
    assert servicio.listar() == []


def test_listar_ordenado_por_nombre(conexion: sqlite3.Connection) -> None:
    """Requirement 2.4: el listado se ordena por nombre ascendente."""
    servicio = _servicio(conexion)
    _registrar(servicio, cedula="C1", nombre="Zoraida")
    _registrar(servicio, cedula="C2", nombre="Ana")
    _registrar(servicio, cedula="C3", nombre="Marta")
    assert [p.nombre for p in servicio.listar()] == ["Ana", "Marta", "Zoraida"]


def test_listar_vacio_devuelve_lista_vacia(conexion: sqlite3.Connection) -> None:
    """Requirement 2.5: sin pacientes, el listado es vacío."""
    assert _servicio(conexion).listar() == []


def test_obtener_inexistente_devuelve_none(conexion: sqlite3.Connection) -> None:
    """Requirement 2.6: consultar un paciente inexistente devuelve None."""
    servicio = _servicio(conexion)
    assert servicio.obtener(999) is None
    assert servicio.obtener_por_cedula("no-existe") is None


def test_genero_se_normaliza_a_minusculas(conexion: sqlite3.Connection) -> None:
    servicio = _servicio(conexion)
    creado = _registrar(servicio, genero="MASCULINO")
    assert creado.genero == "masculino"
