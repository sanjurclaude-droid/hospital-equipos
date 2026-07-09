"""Pruebas de DepartamentoService: unitarias y basadas en propiedades.

Cubre las validaciones de registro (obligatoriedad, longitud, unicidad
case-insensitive), el listado, la consulta y la precarga idempotente de los 12
departamentos base.

Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 10.3
"""

from __future__ import annotations

import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.servicios.departamento_service import (
    DEPARTAMENTOS_BASE,
    DepartamentoService,
)


def _servicio(conexion: sqlite3.Connection) -> DepartamentoService:
    return DepartamentoService(DepartamentoRepository(conexion))


# --------------------------------------------------------------------------- #
# Prueba basada en propiedades (Tarea 5.2)                                     #
# Feature: hospital-equipment-management, Property 1: Unicidad de              #
# códigos/cédulas/nombres                                                      #
# Validates: Requirements 1.4, 10.3                                            #
# --------------------------------------------------------------------------- #
# Nombres cuya versión normalizada (trim + lower) es única e independiente del
# caso, para poder generar variantes de mayúsculas/minúsculas sin colisiones.
_nombres_base = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=97, max_codepoint=122
    ),
    min_size=1,
    max_size=20,
).map(str.lower)


@settings(max_examples=100)
@given(nombres=st.lists(_nombres_base, min_size=1, max_size=8, unique=True))
def test_propiedad_unicidad_nombres_case_insensitive(nombres: list[str]) -> None:
    """Property 1: no pueden coexistir dos departamentos con el mismo nombre.

    Para cualquier conjunto de nombres, registrar cada nombre y luego un
    segundo intento con una variante de mayúsculas/minúsculas (y espacios) del
    mismo nombre debe ser rechazado, y el conjunto de nombres normalizados de
    los departamentos persistidos debe ser único.

    Se usa una conexión SQLite en memoria fresca por ejemplo para evitar fugas
    de estado entre las iteraciones de hypothesis.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)

        for nombre in nombres:
            servicio.registrar(nombre)
            # Un segundo registro con distinto caso/espacios debe ser rechazado.
            for variante in (nombre.upper(), f"  {nombre}  "):
                with pytest.raises(ValueError):
                    servicio.registrar(variante)

        persistidos = [d.nombre.strip().lower() for d in servicio.listar()]
        assert len(persistidos) == len(set(persistidos))
        assert set(persistidos) == set(nombres)
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Pruebas unitarias (Tarea 5.3)                                                #
# --------------------------------------------------------------------------- #
def test_registrar_nombre_vacio_es_rechazado(conexion: sqlite3.Connection) -> None:
    """Requirement 1.2: nombre vacío es rechazado y no altera el estado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="obligatorio"):
        servicio.registrar("")
    assert servicio.listar() == []


def test_registrar_nombre_solo_espacios_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.2: nombre con solo espacios es rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="obligatorio"):
        servicio.registrar("     ")
    assert servicio.listar() == []


def test_registrar_nombre_demasiado_largo_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.3: nombre de más de 100 caracteres es rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="longitud máxima"):
        servicio.registrar("A" * 101)
    assert servicio.listar() == []


def test_registrar_nombre_longitud_limite_es_aceptado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.1: un nombre de exactamente 100 caracteres es válido."""
    servicio = _servicio(conexion)
    creado = servicio.registrar("A" * 100)
    assert creado.id is not None


def test_registrar_duplicado_case_insensitive_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.4 / 10.3: nombre duplicado (sin distinguir caso) rechazado."""
    servicio = _servicio(conexion)
    servicio.registrar("Cardiología")
    with pytest.raises(ValueError, match="Ya existe"):
        servicio.registrar("  cardiología  ")
    assert len(servicio.listar()) == 1


def test_registrar_normaliza_espacios(conexion: sqlite3.Connection) -> None:
    """El nombre se persiste sin espacios iniciales ni finales."""
    servicio = _servicio(conexion)
    creado = servicio.registrar("  Neurología  ")
    assert creado.nombre == "Neurología"


def test_listar_vacio_devuelve_lista_vacia(conexion: sqlite3.Connection) -> None:
    """Requirement 1.8: sin departamentos, el listado es vacío."""
    assert _servicio(conexion).listar() == []


def test_obtener_inexistente_devuelve_none(conexion: sqlite3.Connection) -> None:
    assert _servicio(conexion).obtener(999) is None


def test_inicializar_precarga_doce_departamentos(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.5: se precargan exactamente 12 departamentos base."""
    servicio = _servicio(conexion)
    mensaje = servicio.inicializar_departamentos_base()

    departamentos = servicio.listar()
    assert len(departamentos) == 12
    nombres = [d.nombre for d in departamentos]
    assert "Laboratorio Clínico y Banco de Sangre" in nombres
    assert "12" in mensaje


def test_inicializar_es_idempotente_en_segunda_invocacion(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.6: si ya hay datos, la segunda invocación omite la precarga."""
    servicio = _servicio(conexion)
    servicio.inicializar_departamentos_base()

    mensaje = servicio.inicializar_departamentos_base()
    assert "omitida" in mensaje
    assert len(servicio.listar()) == 12


def test_inicializar_omitida_si_tabla_no_vacia(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 1.6: con un departamento previo, la precarga se omite."""
    servicio = _servicio(conexion)
    servicio.registrar("Departamento Manual")

    mensaje = servicio.inicializar_departamentos_base()
    assert "omitida" in mensaje
    assert len(servicio.listar()) == 1


def test_departamentos_base_definidos_son_doce() -> None:
    """La lista de departamentos base contiene exactamente 12 entradas únicas."""
    nombres = [nombre for nombre, _ in DEPARTAMENTOS_BASE]
    assert len(nombres) == 12
    assert len(set(nombres)) == 12
