"""Pruebas unitarias de round-trip para la capa de repositorios (Tarea 4.3).

Insertan y recuperan filas de cada tabla verificando que los datos persisten
intactos (mapeo fila↔objeto). También cubren las consultas específicas de cada
repositorio: búsqueda case-insensitive de departamentos, orden por nombre de
pacientes, filtros de equipos y la agregación del Indicador de Uso Clínico.

Requirements: 3.1, 6.1
"""

from __future__ import annotations

import sqlite3

import pytest

from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.modelos.uso import CriterioUso, UsoEquipo
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository


# --------------------------------------------------------------------------- #
# Utilidades de construcción de datos válidos                                  #
# --------------------------------------------------------------------------- #
def _crear_departamento(
    conexion: sqlite3.Connection, nombre: str = "Laboratorio Clínico"
) -> Departamento:
    repo = DepartamentoRepository(conexion)
    return repo.insertar(
        Departamento(id=None, nombre=nombre, descripcion="Área analítica")
    )


def _crear_paciente(
    conexion: sqlite3.Connection, cedula: str = "8-888-8888", nombre: str = "Ana"
) -> Paciente:
    repo = PacienteRepository(conexion)
    return repo.insertar(
        Paciente(
            id=None,
            cedula=cedula,
            nombre=nombre,
            fecha_nacimiento="1990-05-10",
            genero="femenino",
            telefono="61234567",
        )
    )


def _crear_equipo(
    conexion: sqlite3.Connection,
    departamento_id: int,
    codigo: str = "LAB-001",
    nombre: str = "Analizador",
    estado: EstadoEquipo = EstadoEquipo.OPERATIVO,
    numero_serie: str = "SN-001",
) -> Equipo:
    repo = EquipoRepository(conexion)
    return repo.insertar(
        Equipo(
            id=None,
            codigo_inventario=codigo,
            nombre=nombre,
            marca="Sysmex",
            modelo="XN-1000",
            numero_serie=numero_serie,
            fecha_adquisicion="2023-05-10",
            estado=estado,
            departamento_id=departamento_id,
        )
    )


# --------------------------------------------------------------------------- #
# DepartamentoRepository                                                       #
# --------------------------------------------------------------------------- #
def test_departamento_round_trip(conexion: sqlite3.Connection) -> None:
    """Un departamento insertado se recupera intacto por id."""
    repo = DepartamentoRepository(conexion)
    creado = repo.insertar(
        Departamento(id=None, nombre="Radiología", descripcion="Imágenes")
    )

    assert creado.id is not None
    recuperado = repo.obtener_por_id(creado.id)
    assert recuperado == creado


def test_departamento_obtener_por_nombre_case_insensitive(
    conexion: sqlite3.Connection,
) -> None:
    """La búsqueda por nombre no distingue mayúsculas/minúsculas."""
    repo = DepartamentoRepository(conexion)
    creado = repo.insertar(
        Departamento(id=None, nombre="Laboratorio Clínico", descripcion="")
    )

    encontrado = repo.obtener_por_nombre("laboratorio CLÍNICO")
    assert encontrado is not None
    assert encontrado.id == creado.id


def test_departamento_obtener_inexistente_devuelve_none(
    conexion: sqlite3.Connection,
) -> None:
    repo = DepartamentoRepository(conexion)
    assert repo.obtener_por_id(999) is None
    assert repo.obtener_por_nombre("Inexistente") is None


def test_departamento_listar(conexion: sqlite3.Connection) -> None:
    repo = DepartamentoRepository(conexion)
    assert repo.listar() == []
    d1 = repo.insertar(Departamento(id=None, nombre="Uno"))
    d2 = repo.insertar(Departamento(id=None, nombre="Dos"))
    assert repo.listar() == [d1, d2]


# --------------------------------------------------------------------------- #
# PacienteRepository                                                           #
# --------------------------------------------------------------------------- #
def test_paciente_round_trip(conexion: sqlite3.Connection) -> None:
    """Un paciente insertado se recupera intacto por id y por cédula."""
    repo = PacienteRepository(conexion)
    creado = repo.insertar(
        Paciente(
            id=None,
            cedula="8-123-456",
            nombre="Carlos Mora",
            fecha_nacimiento="1985-01-20",
            genero="masculino",
            telefono="60012345",
        )
    )

    assert creado.id is not None
    assert repo.obtener_por_id(creado.id) == creado
    assert repo.obtener_por_cedula("8-123-456") == creado


def test_paciente_listar_ordenado_por_nombre(
    conexion: sqlite3.Connection,
) -> None:
    """El listado de pacientes se ordena por nombre ascendente."""
    repo = PacienteRepository(conexion)
    _crear_paciente(conexion, cedula="C-1", nombre="Zoraida")
    _crear_paciente(conexion, cedula="C-2", nombre="Ana")
    _crear_paciente(conexion, cedula="C-3", nombre="Marta")

    nombres = [p.nombre for p in repo.listar()]
    assert nombres == ["Ana", "Marta", "Zoraida"]


def test_paciente_obtener_inexistente_devuelve_none(
    conexion: sqlite3.Connection,
) -> None:
    repo = PacienteRepository(conexion)
    assert repo.obtener_por_id(999) is None
    assert repo.obtener_por_cedula("no-existe") is None


# --------------------------------------------------------------------------- #
# EquipoRepository                                                             #
# --------------------------------------------------------------------------- #
def test_equipo_round_trip(conexion: sqlite3.Connection) -> None:
    """Un equipo insertado se recupera intacto y con su estado como enum."""
    dep = _crear_departamento(conexion)
    creado = _crear_equipo(conexion, dep.id)

    assert creado.id is not None
    recuperado = EquipoRepository(conexion).obtener_por_id(creado.id)
    assert recuperado == creado
    assert isinstance(recuperado.estado, EstadoEquipo)
    assert recuperado.estado is EstadoEquipo.OPERATIVO


def test_equipo_obtener_por_codigo(conexion: sqlite3.Connection) -> None:
    dep = _crear_departamento(conexion)
    creado = _crear_equipo(conexion, dep.id, codigo="LAB-XYZ")
    repo = EquipoRepository(conexion)
    assert repo.obtener_por_codigo("LAB-XYZ") == creado
    assert repo.obtener_por_codigo("NO-EXISTE") is None


def test_equipo_actualizar(conexion: sqlite3.Connection) -> None:
    """Actualizar persiste los nuevos valores del equipo."""
    dep = _crear_departamento(conexion)
    repo = EquipoRepository(conexion)
    creado = _crear_equipo(conexion, dep.id)

    modificado = Equipo(
        id=creado.id,
        codigo_inventario=creado.codigo_inventario,
        nombre="Analizador Actualizado",
        marca="Roche",
        modelo="Cobas",
        numero_serie=creado.numero_serie,
        fecha_adquisicion=creado.fecha_adquisicion,
        estado=EstadoEquipo.EN_MANTENIMIENTO,
        departamento_id=dep.id,
    )
    repo.actualizar(modificado)

    recuperado = repo.obtener_por_id(creado.id)
    assert recuperado == modificado
    assert recuperado.estado is EstadoEquipo.EN_MANTENIMIENTO


def test_equipo_eliminar(conexion: sqlite3.Connection) -> None:
    dep = _crear_departamento(conexion)
    repo = EquipoRepository(conexion)
    creado = _crear_equipo(conexion, dep.id)

    repo.eliminar(creado.id)
    assert repo.obtener_por_id(creado.id) is None


def test_equipo_listar_por_departamento(conexion: sqlite3.Connection) -> None:
    dep1 = _crear_departamento(conexion, nombre="Dep 1")
    dep2 = _crear_departamento(conexion, nombre="Dep 2")
    e1 = _crear_equipo(conexion, dep1.id, codigo="A-1", numero_serie="S-1")
    e2 = _crear_equipo(conexion, dep1.id, codigo="A-2", numero_serie="S-2")
    _crear_equipo(conexion, dep2.id, codigo="B-1", numero_serie="S-3")

    repo = EquipoRepository(conexion)
    assert repo.listar_por_departamento(dep1.id) == [e1, e2]
    assert len(repo.listar_por_departamento(dep2.id)) == 1


def test_equipo_listar_por_estado(conexion: sqlite3.Connection) -> None:
    dep = _crear_departamento(conexion)
    _crear_equipo(
        conexion, dep.id, codigo="OP-1", numero_serie="S-1",
        estado=EstadoEquipo.OPERATIVO,
    )
    mant = _crear_equipo(
        conexion, dep.id, codigo="MT-1", numero_serie="S-2",
        estado=EstadoEquipo.EN_MANTENIMIENTO,
    )

    repo = EquipoRepository(conexion)
    en_mant = repo.listar_por_estado(EstadoEquipo.EN_MANTENIMIENTO)
    assert en_mant == [mant]


# --------------------------------------------------------------------------- #
# UsoRepository                                                                #
# --------------------------------------------------------------------------- #
def test_uso_round_trip(conexion: sqlite3.Connection) -> None:
    """Una sesión de uso insertada se recupera intacta."""
    dep = _crear_departamento(conexion)
    equipo = _crear_equipo(conexion, dep.id)
    paciente = _crear_paciente(conexion)
    repo = UsoRepository(conexion)

    creado = repo.insertar(
        UsoEquipo(
            id=None,
            equipo_id=equipo.id,
            paciente_id=paciente.id,
            fecha_inicio="2024-06-01 09:30",
            duracion_minutos=45,
        )
    )

    assert creado.id is not None
    sesiones = repo.listar_por_equipo(equipo.id)
    assert sesiones == [creado]


def test_uso_listar_por_equipo_orden_fecha_desc(
    conexion: sqlite3.Connection,
) -> None:
    """Las sesiones se listan de más reciente a más antigua."""
    dep = _crear_departamento(conexion)
    equipo = _crear_equipo(conexion, dep.id)
    paciente = _crear_paciente(conexion)
    repo = UsoRepository(conexion)

    repo.insertar(UsoEquipo(None, equipo.id, paciente.id, "2024-01-01 08:00", 30))
    repo.insertar(UsoEquipo(None, equipo.id, paciente.id, "2024-06-01 08:00", 30))
    repo.insertar(UsoEquipo(None, equipo.id, paciente.id, "2024-03-01 08:00", 30))

    fechas = [s.fecha_inicio for s in repo.listar_por_equipo(equipo.id)]
    assert fechas == [
        "2024-06-01 08:00",
        "2024-03-01 08:00",
        "2024-01-01 08:00",
    ]


def test_uso_contar_por_equipo(conexion: sqlite3.Connection) -> None:
    dep = _crear_departamento(conexion)
    equipo = _crear_equipo(conexion, dep.id)
    paciente = _crear_paciente(conexion)
    repo = UsoRepository(conexion)

    assert repo.contar_por_equipo(equipo.id) == 0
    for _ in range(3):
        repo.insertar(
            UsoEquipo(None, equipo.id, paciente.id, "2024-06-01 09:30", 20)
        )
    assert repo.contar_por_equipo(equipo.id) == 3


def test_uso_listar_equipo_sin_sesiones_devuelve_vacio(
    conexion: sqlite3.Connection,
) -> None:
    dep = _crear_departamento(conexion)
    equipo = _crear_equipo(conexion, dep.id)
    assert UsoRepository(conexion).listar_por_equipo(equipo.id) == []


# --------------------------------------------------------------------------- #
# Agregación: Indicador de Uso Clínico                                         #
# --------------------------------------------------------------------------- #
def test_agregar_uso_sesiones_orden_desc(conexion: sqlite3.Connection) -> None:
    """El criterio SESIONES cuenta filas y ordena de mayor a menor."""
    dep = _crear_departamento(conexion)
    paciente = _crear_paciente(conexion)
    eq_a = _crear_equipo(conexion, dep.id, codigo="A", nombre="Alfa", numero_serie="S-A")
    eq_b = _crear_equipo(conexion, dep.id, codigo="B", nombre="Beta", numero_serie="S-B")
    repo = UsoRepository(conexion)

    # Beta con 3 sesiones, Alfa con 1.
    repo.insertar(UsoEquipo(None, eq_a.id, paciente.id, "2024-06-01 09:00", 10))
    for _ in range(3):
        repo.insertar(UsoEquipo(None, eq_b.id, paciente.id, "2024-06-01 09:00", 10))

    metricas = repo.agregar_uso_por_equipo(CriterioUso.SESIONES)
    assert [m.equipo_nombre for m in metricas] == ["Beta", "Alfa"]
    assert metricas[0].total_uso == 3
    assert metricas[1].total_uso == 1
    assert metricas[0].departamento_nombre == dep.nombre


def test_agregar_uso_horas_redondeo(conexion: sqlite3.Connection) -> None:
    """El criterio HORAS suma minutos / 60 redondeado a 2 decimales."""
    dep = _crear_departamento(conexion)
    paciente = _crear_paciente(conexion)
    equipo = _crear_equipo(conexion, dep.id)
    repo = UsoRepository(conexion)

    # 45 + 30 = 75 minutos = 1.25 horas.
    repo.insertar(UsoEquipo(None, equipo.id, paciente.id, "2024-06-01 09:00", 45))
    repo.insertar(UsoEquipo(None, equipo.id, paciente.id, "2024-06-01 10:00", 30))

    metricas = repo.agregar_uso_por_equipo(CriterioUso.HORAS)
    assert len(metricas) == 1
    assert metricas[0].total_uso == 1.25


def test_agregar_uso_desempate_alfabetico(conexion: sqlite3.Connection) -> None:
    """Ante empate de total, se desempata alfabéticamente por nombre."""
    dep = _crear_departamento(conexion)
    paciente = _crear_paciente(conexion)
    eq_z = _crear_equipo(conexion, dep.id, codigo="Z", nombre="Zeta", numero_serie="S-Z")
    eq_a = _crear_equipo(conexion, dep.id, codigo="A", nombre="Alfa", numero_serie="S-A")
    repo = UsoRepository(conexion)

    repo.insertar(UsoEquipo(None, eq_z.id, paciente.id, "2024-06-01 09:00", 10))
    repo.insertar(UsoEquipo(None, eq_a.id, paciente.id, "2024-06-01 09:00", 10))

    metricas = repo.agregar_uso_por_equipo(CriterioUso.SESIONES)
    assert [m.equipo_nombre for m in metricas] == ["Alfa", "Zeta"]


def test_agregar_uso_filtro_por_departamento(
    conexion: sqlite3.Connection,
) -> None:
    """El filtro por departamento restringe el alcance del cálculo."""
    dep1 = _crear_departamento(conexion, nombre="Dep 1")
    dep2 = _crear_departamento(conexion, nombre="Dep 2")
    paciente = _crear_paciente(conexion)
    eq1 = _crear_equipo(conexion, dep1.id, codigo="D1", nombre="EnDep1", numero_serie="S-1")
    eq2 = _crear_equipo(conexion, dep2.id, codigo="D2", nombre="EnDep2", numero_serie="S-2")
    repo = UsoRepository(conexion)

    repo.insertar(UsoEquipo(None, eq1.id, paciente.id, "2024-06-01 09:00", 10))
    repo.insertar(UsoEquipo(None, eq2.id, paciente.id, "2024-06-01 09:00", 10))

    metricas = repo.agregar_uso_por_equipo(CriterioUso.SESIONES, dep1.id)
    assert len(metricas) == 1
    assert metricas[0].equipo_nombre == "EnDep1"


def test_agregar_uso_sin_sesiones_devuelve_vacio(
    conexion: sqlite3.Connection,
) -> None:
    """Sin sesiones en el alcance, la agregación devuelve una lista vacía."""
    dep = _crear_departamento(conexion)
    _crear_equipo(conexion, dep.id)
    repo = UsoRepository(conexion)
    assert repo.agregar_uso_por_equipo(CriterioUso.SESIONES) == []
    assert repo.agregar_uso_por_equipo(CriterioUso.HORAS) == []
