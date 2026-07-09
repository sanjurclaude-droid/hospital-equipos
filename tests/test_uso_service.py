"""Pruebas de UsoService: unitarias y basadas en propiedades.

Cubre el registro de sesiones de uso (integridad referencial de equipo y
paciente, validez de la fecha/hora de inicio y de la duración) y el listado de
sesiones por equipo, ordenado de más reciente a más antigua.

Las pruebas basadas en propiedades usan una conexión SQLite en memoria fresca
por ejemplo para evitar fugas de estado entre las iteraciones de hypothesis.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 10.5, 10.6, 10.8
"""

from __future__ import annotations

import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository
from hospital_equipos.servicios.uso_service import UsoService

# Fecha/hora de inicio válida y claramente pasada (no futura).
_INICIO_VALIDO = "2020-06-01 09:30"


def _servicio(conexion: sqlite3.Connection) -> UsoService:
    return UsoService(
        UsoRepository(conexion),
        EquipoRepository(conexion),
        PacienteRepository(conexion),
    )


def _crear_equipo(conexion: sqlite3.Connection) -> int:
    """Crea un departamento y un equipo, devolviendo el id del equipo."""
    dep = DepartamentoRepository(conexion).insertar(
        Departamento(id=None, nombre="Lab", descripcion="")
    )
    equipo = EquipoRepository(conexion).insertar(
        Equipo(
            id=None,
            codigo_inventario="EQ-001",
            nombre="Monitor",
            marca="Acme",
            modelo="X1",
            numero_serie="SN-1",
            fecha_adquisicion="2023-01-10",
            estado=EstadoEquipo.OPERATIVO,
            departamento_id=dep.id,
        )
    )
    return equipo.id


def _crear_paciente(conexion: sqlite3.Connection) -> int:
    """Crea un paciente y devuelve su id."""
    paciente = PacienteRepository(conexion).insertar(
        Paciente(id=None, cedula="C1", nombre="Ana Pérez")
    )
    return paciente.id


# --------------------------------------------------------------------------- #
# Tarea 9.2 — Property 4: Duración positiva                                     #
# Feature: hospital-equipment-management, Property 4: Duración positiva        #
# Validates: Requirements 6.4, 10.8                                            #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(duracion=st.integers(min_value=-100, max_value=2000))
def test_propiedad_duracion_positiva(duracion: int) -> None:
    """Property 4: toda sesión persistida tiene duración en [1, 1440].

    Si la duración está en el rango válido [1, 1440], la sesión se crea con esa
    duración (positiva). Si está fuera de rango, la operación se rechaza y no se
    crea ninguna sesión. En todo caso, toda sesión persistida tiene duración
    estrictamente positiva.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        equipo_id = _crear_equipo(conexion)
        paciente_id = _crear_paciente(conexion)

        if 1 <= duracion <= 1440:
            uso = servicio.registrar_uso(
                equipo_id, paciente_id, _INICIO_VALIDO, duracion
            )
            assert uso.duracion_minutos == duracion
            assert uso.duracion_minutos > 0
        else:
            with pytest.raises(ValueError):
                servicio.registrar_uso(
                    equipo_id, paciente_id, _INICIO_VALIDO, duracion
                )
            assert servicio.listar_por_equipo(equipo_id) == []

        # Invariante global: toda sesión persistida tiene duración > 0.
        for sesion in servicio.listar_por_equipo(equipo_id):
            assert sesion.duracion_minutos > 0
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 9.3 — Property 2: Integridad referencial de sesiones                    #
# Feature: hospital-equipment-management, Property 2: Integridad referencial   #
# Validates: Requirements 6.2, 6.3, 10.5, 10.6                                 #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(
    equipo_id=st.integers(min_value=1, max_value=10_000),
    paciente_id=st.integers(min_value=1, max_value=10_000),
)
def test_propiedad_integridad_referencial_sesiones(
    equipo_id: int, paciente_id: int
) -> None:
    """Property 2: una sesión solo refiere a un equipo y un paciente existentes.

    Existe exactamente un equipo (id real) y un paciente (id real). Registrar
    una sesión con un ``equipo_id`` o ``paciente_id`` inexistente se rechaza sin
    crear ninguna sesión. Una sesión con ambas referencias válidas sí se crea y
    referencia filas existentes.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        equipo_real = _crear_equipo(conexion)
        paciente_real = _crear_paciente(conexion)
        uso_repo = UsoRepository(conexion)

        if equipo_id != equipo_real or paciente_id != paciente_real:
            with pytest.raises(ValueError):
                servicio.registrar_uso(
                    equipo_id, paciente_id, _INICIO_VALIDO, 30
                )
            # No se creó ninguna sesión (ni para el equipo real ni el inválido).
            assert uso_repo.contar_por_equipo(equipo_real) == 0
            assert uso_repo.contar_por_equipo(equipo_id) == 0

        # Con ambas referencias válidas, la sesión se crea correctamente.
        uso = servicio.registrar_uso(
            equipo_real, paciente_real, _INICIO_VALIDO, 30
        )
        equipo_repo = EquipoRepository(conexion)
        paciente_repo = PacienteRepository(conexion)
        assert equipo_repo.obtener_por_id(uso.equipo_id) is not None
        assert paciente_repo.obtener_por_id(uso.paciente_id) is not None
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 9.4 — Property 6: Consistencia de la métrica de sesiones               #
# Feature: hospital-equipment-management, Property 6: Consistencia de la       #
# métrica de sesiones                                                          #
# Validates: Requirements 6.6, 9.1                                             #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(n=st.integers(min_value=0, max_value=25))
def test_propiedad_conteo_sesiones(n: int) -> None:
    """Property 6: tras N inserciones válidas, ``contar_por_equipo`` == N.

    Para N sesiones válidas registradas sobre un mismo equipo, el conteo de
    sesiones del equipo es exactamente N, y el listado por equipo contiene N
    elementos.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        equipo_id = _crear_equipo(conexion)
        paciente_id = _crear_paciente(conexion)
        uso_repo = UsoRepository(conexion)

        for _ in range(n):
            servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, 30)

        assert uso_repo.contar_por_equipo(equipo_id) == n
        assert len(servicio.listar_por_equipo(equipo_id)) == n
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Pruebas unitarias (complementan las propiedades de la Tarea 9)               #
# --------------------------------------------------------------------------- #
def test_registrar_uso_valido(conexion: sqlite3.Connection) -> None:
    """Requirement 6.1: una sesión con datos válidos se crea con un id."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    uso = servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, 45)
    assert uso.id is not None
    assert uso.duracion_minutos == 45


def test_registrar_uso_equipo_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.2 / 10.5: equipo inexistente rechazado, sin crear sesión."""
    servicio = _servicio(conexion)
    paciente_id = _crear_paciente(conexion)
    with pytest.raises(ValueError, match="equipo"):
        servicio.registrar_uso(999, paciente_id, _INICIO_VALIDO, 30)


def test_registrar_uso_paciente_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.3 / 10.6: paciente inexistente rechazado, sin crear sesión."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    with pytest.raises(ValueError, match="paciente"):
        servicio.registrar_uso(equipo_id, 999, _INICIO_VALIDO, 30)
    assert servicio.listar_por_equipo(equipo_id) == []


@pytest.mark.parametrize("duracion", [0, -5, 1441, 5000])
def test_registrar_uso_duracion_fuera_de_rango_es_rechazada(
    conexion: sqlite3.Connection, duracion: int
) -> None:
    """Requirement 6.4 / 10.8: duración <=0 o >1440 rechazada."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    with pytest.raises(ValueError, match="duración"):
        servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, duracion)
    assert servicio.listar_por_equipo(equipo_id) == []


@pytest.mark.parametrize("duracion", [1.5, "30", None, True])
def test_registrar_uso_duracion_no_entera_es_rechazada(
    conexion: sqlite3.Connection, duracion
) -> None:
    """Requirement 10.8: duración no entera (float, str, None, bool) rechazada."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    with pytest.raises(ValueError, match="duración"):
        servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, duracion)


def test_registrar_uso_fecha_futura_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.5: fecha/hora de inicio futura rechazada."""
    from datetime import datetime, timedelta

    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    futuro = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    with pytest.raises(ValueError, match="fecha/hora de inicio"):
        servicio.registrar_uso(equipo_id, paciente_id, futuro, 30)
    assert servicio.listar_por_equipo(equipo_id) == []


def test_registrar_uso_fecha_formato_invalido_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.5: fecha/hora con formato inválido rechazada."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    with pytest.raises(ValueError, match="fecha/hora de inicio"):
        servicio.registrar_uso(equipo_id, paciente_id, "01-06-2020 09:30", 30)


def test_listar_por_equipo_ordenado_descendente(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.7: las sesiones se listan de más reciente a más antigua."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    servicio.registrar_uso(equipo_id, paciente_id, "2020-01-01 08:00", 30)
    servicio.registrar_uso(equipo_id, paciente_id, "2021-03-15 12:00", 30)
    servicio.registrar_uso(equipo_id, paciente_id, "2019-07-20 10:00", 30)
    fechas = [u.fecha_inicio for u in servicio.listar_por_equipo(equipo_id)]
    assert fechas == [
        "2021-03-15 12:00",
        "2020-01-01 08:00",
        "2019-07-20 10:00",
    ]


def test_listar_por_equipo_sin_sesiones_es_vacio(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 6.8: un equipo sin sesiones devuelve una colección vacía."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    assert servicio.listar_por_equipo(equipo_id) == []


def test_registrar_uso_incrementa_conteo(conexion: sqlite3.Connection) -> None:
    """Requirement 6.6: cada sesión creada incrementa el conteo del equipo."""
    servicio = _servicio(conexion)
    equipo_id = _crear_equipo(conexion)
    paciente_id = _crear_paciente(conexion)
    uso_repo = UsoRepository(conexion)
    assert uso_repo.contar_por_equipo(equipo_id) == 0
    servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, 30)
    assert uso_repo.contar_por_equipo(equipo_id) == 1
    servicio.registrar_uso(equipo_id, paciente_id, _INICIO_VALIDO, 60)
    assert uso_repo.contar_por_equipo(equipo_id) == 2
