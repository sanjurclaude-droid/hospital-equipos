"""Pruebas de ReporteService: unitarias y basadas en propiedades.

Cubre las consultas avanzadas del sistema:

- Inventario por departamento (existencia, id válido, lista vacía).
- Alerta de mantenimiento (filtro por estado ``En mantenimiento``).
- Indicador de Uso Clínico (criterios SESIONES/HORAS, redondeo, filtro por
  departamento, orden no creciente con desempate determinista, validaciones).

Las pruebas basadas en propiedades usan una conexión SQLite en memoria fresca
por ejemplo para evitar fugas de estado entre las iteraciones de hypothesis.

Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4,
              9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9
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
from hospital_equipos.modelos.uso import CriterioUso, UsoEquipo
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository
from hospital_equipos.servicios.reporte_service import ReporteService

_INICIO_VALIDO = "2020-06-01 09:30"


def _servicio(conexion: sqlite3.Connection) -> ReporteService:
    return ReporteService(
        EquipoRepository(conexion),
        UsoRepository(conexion),
        DepartamentoRepository(conexion),
    )


def _crear_departamento(
    conexion: sqlite3.Connection, nombre: str = "Laboratorio"
) -> int:
    dep = DepartamentoRepository(conexion).insertar(
        Departamento(id=None, nombre=nombre, descripcion="")
    )
    return dep.id


def _crear_paciente(conexion: sqlite3.Connection) -> int:
    paciente = PacienteRepository(conexion).insertar(
        Paciente(id=None, cedula="C1", nombre="Ana Pérez")
    )
    return paciente.id


def _crear_equipo(
    conexion: sqlite3.Connection,
    departamento_id: int,
    indice: int,
    nombre: str,
    estado: EstadoEquipo = EstadoEquipo.OPERATIVO,
) -> int:
    equipo = EquipoRepository(conexion).insertar(
        Equipo(
            id=None,
            codigo_inventario=f"EQ-{indice:04d}",
            nombre=nombre,
            marca="Acme",
            modelo="X1",
            numero_serie=f"SN-{indice:04d}",
            fecha_adquisicion="2023-01-10",
            estado=estado,
            departamento_id=departamento_id,
        )
    )
    return equipo.id


def _registrar_sesiones(
    conexion: sqlite3.Connection,
    equipo_id: int,
    paciente_id: int,
    cantidad: int,
    duracion: int = 30,
) -> None:
    uso_repo = UsoRepository(conexion)
    for _ in range(cantidad):
        uso_repo.insertar(
            UsoEquipo(
                id=None,
                equipo_id=equipo_id,
                paciente_id=paciente_id,
                fecha_inicio=_INICIO_VALIDO,
                duracion_minutos=duracion,
            )
        )


# --------------------------------------------------------------------------- #
# Tarea 11.2 — Property 7: Filtro de mantenimiento                             #
# Feature: hospital-equipment-management, Property 7: Filtro de mantenimiento  #
# Validates: Requirements 8.1                                                  #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(
    estados=st.lists(
        st.sampled_from(list(EstadoEquipo)), min_size=0, max_size=12
    )
)
def test_propiedad_filtro_mantenimiento(estados: list[EstadoEquipo]) -> None:
    """Property 7: ``alerta_mantenimiento`` devuelve exactamente los equipos en
    estado "En mantenimiento".

    Para un conjunto arbitrario de equipos con estados diversos, el resultado
    contiene exactamente los equipos cuyo estado es ``En mantenimiento`` y
    ninguno con otro estado.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)

        ids_en_mantenimiento: set[int] = set()
        for indice, estado in enumerate(estados):
            equipo_id = _crear_equipo(
                conexion, departamento_id, indice, f"Equipo {indice}", estado
            )
            if estado == EstadoEquipo.EN_MANTENIMIENTO:
                ids_en_mantenimiento.add(equipo_id)

        resultado = servicio.alerta_mantenimiento()

        # Todos los devueltos están en mantenimiento.
        assert all(
            eq.estado == EstadoEquipo.EN_MANTENIMIENTO for eq in resultado
        )
        # El conjunto devuelto coincide exactamente con los esperados.
        assert {eq.id for eq in resultado} == ids_en_mantenimiento
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 11.4 — Property 5: Orden del reporte (desempate determinista)          #
# Feature: hospital-equipment-management, Property 5: Orden del reporte        #
# Validates: Requirements 9.3, 9.4                                             #
# --------------------------------------------------------------------------- #
# Nombres de un alfabeto reducido para forzar empates de total_uso y probar el
# desempate alfabético ascendente por nombre de equipo.
_nombres_equipo = st.text(alphabet="AB", min_size=1, max_size=3)


@settings(max_examples=100)
@given(
    especificaciones=st.lists(
        st.tuples(_nombres_equipo, st.integers(min_value=0, max_value=4)),
        min_size=1,
        max_size=6,
    ),
    criterio=st.sampled_from(list(CriterioUso)),
)
def test_propiedad_orden_indicador(
    especificaciones: list[tuple[str, int]], criterio: CriterioUso
) -> None:
    """Property 5: el Indicador de Uso Clínico se ordena de forma no creciente
    por total_uso; ante empates, alfabéticamente ascendente por nombre.

    Para cualquier historial de sesiones, cada par consecutivo del resultado
    cumple ``total_uso[i] >= total_uso[i+1]`` y, si son iguales, el nombre de
    equipo no decrece (``nombre[i] <= nombre[i+1]``).
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)
        paciente_id = _crear_paciente(conexion)

        for indice, (nombre, cantidad) in enumerate(especificaciones):
            equipo_id = _crear_equipo(
                conexion, departamento_id, indice, nombre
            )
            _registrar_sesiones(conexion, equipo_id, paciente_id, cantidad)

        resultado = servicio.indicador_uso_clinico(criterio, departamento_id)

        for anterior, siguiente in zip(resultado, resultado[1:]):
            assert anterior.total_uso >= siguiente.total_uso
            if anterior.total_uso == siguiente.total_uso:
                assert anterior.equipo_nombre <= siguiente.equipo_nombre
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 11.5 — Property 6: Consistencia de la métrica de sesiones              #
# Feature: hospital-equipment-management, Property 6: Consistencia de la       #
# métrica de sesiones                                                          #
# Validates: Requirements 9.1                                                  #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(
    conteos=st.lists(
        st.integers(min_value=0, max_value=10), min_size=1, max_size=6
    )
)
def test_propiedad_metrica_sesiones(conteos: list[int]) -> None:
    """Property 6: con criterio SESIONES, el total_uso de cada equipo es igual
    al número real de sesiones insertadas para ese equipo.

    Cada equipo recibe un nombre único (índice), por lo que la métrica puede
    emparejarse sin ambigüedad. Los equipos sin sesiones no aparecen en el
    resultado (alcance vacío para ese equipo).
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)
        paciente_id = _crear_paciente(conexion)

        esperado: dict[str, int] = {}
        for indice, cantidad in enumerate(conteos):
            nombre = f"Equipo-{indice:04d}"
            equipo_id = _crear_equipo(
                conexion, departamento_id, indice, nombre
            )
            _registrar_sesiones(conexion, equipo_id, paciente_id, cantidad)
            if cantidad > 0:
                esperado[nombre] = cantidad

        resultado = servicio.indicador_uso_clinico(
            CriterioUso.SESIONES, departamento_id
        )

        obtenido = {m.equipo_nombre: m.total_uso for m in resultado}
        assert obtenido == esperado
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 11.6 — Pruebas unitarias del indicador (criterios y casos límite)      #
# --------------------------------------------------------------------------- #
def test_indicador_horas_redondeo_a_dos_decimales(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.2: HORAS = suma de minutos / 60 redondeada a 2 decimales."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    paciente_id = _crear_paciente(conexion)
    equipo_id = _crear_equipo(conexion, departamento_id, 0, "Analizador")

    # 20 + 20 + 10 = 50 minutos => 50 / 60 = 0.8333... => 0.83
    _registrar_sesiones(conexion, equipo_id, paciente_id, 1, duracion=20)
    _registrar_sesiones(conexion, equipo_id, paciente_id, 1, duracion=20)
    _registrar_sesiones(conexion, equipo_id, paciente_id, 1, duracion=10)

    resultado = servicio.indicador_uso_clinico(CriterioUso.HORAS)
    assert len(resultado) == 1
    assert resultado[0].equipo_nombre == "Analizador"
    assert resultado[0].departamento_nombre == "Laboratorio"
    assert resultado[0].total_uso == 0.83


def test_indicador_sesiones_incluye_nombre_y_departamento(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.1 / 9.5: cada métrica incluye nombre, departamento y total."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    paciente_id = _crear_paciente(conexion)
    equipo_id = _crear_equipo(conexion, departamento_id, 0, "Monitor")
    _registrar_sesiones(conexion, equipo_id, paciente_id, 3)

    resultado = servicio.indicador_uso_clinico(CriterioUso.SESIONES)
    assert len(resultado) == 1
    assert resultado[0].equipo_nombre == "Monitor"
    assert resultado[0].departamento_nombre == "Laboratorio"
    assert resultado[0].total_uso == 3


def test_indicador_filtro_por_departamento(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.6: el filtro restringe el cálculo al departamento indicado."""
    servicio = _servicio(conexion)
    dep_a = _crear_departamento(conexion, "Departamento A")
    dep_b = _crear_departamento(conexion, "Departamento B")
    paciente_id = _crear_paciente(conexion)

    equipo_a = _crear_equipo(conexion, dep_a, 0, "Equipo A")
    equipo_b = _crear_equipo(conexion, dep_b, 1, "Equipo B")
    _registrar_sesiones(conexion, equipo_a, paciente_id, 2)
    _registrar_sesiones(conexion, equipo_b, paciente_id, 5)

    resultado = servicio.indicador_uso_clinico(CriterioUso.SESIONES, dep_a)
    assert len(resultado) == 1
    assert resultado[0].equipo_nombre == "Equipo A"
    assert resultado[0].total_uso == 2


def test_indicador_departamento_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.7: un departamento inexistente se rechaza sin métricas."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="departamento"):
        servicio.indicador_uso_clinico(CriterioUso.SESIONES, 999)


def test_indicador_criterio_invalido_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.8: un criterio fuera del conjunto se rechaza sin métricas."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="criterio"):
        servicio.indicador_uso_clinico("promedio")


def test_indicador_alcance_vacio_devuelve_lista_vacia(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 9.9: sin equipos con sesiones, devuelve vacío sin error."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    # Equipo sin sesiones registradas.
    _crear_equipo(conexion, departamento_id, 0, "Sin uso")
    assert servicio.indicador_uso_clinico(CriterioUso.SESIONES) == []
    assert servicio.indicador_uso_clinico(CriterioUso.HORAS, departamento_id) == []


# --------------------------------------------------------------------------- #
# Pruebas unitarias — Inventario por departamento y alerta de mantenimiento    #
# --------------------------------------------------------------------------- #
def test_inventario_por_departamento_con_equipos(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 7.1: devuelve todos los equipos del departamento."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    _crear_equipo(conexion, departamento_id, 0, "Equipo 0")
    _crear_equipo(conexion, departamento_id, 1, "Equipo 1")

    resultado = servicio.inventario_por_departamento(departamento_id)
    assert {eq.nombre for eq in resultado} == {"Equipo 0", "Equipo 1"}


def test_inventario_por_departamento_sin_equipos_es_vacio(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 7.2: un departamento sin equipos devuelve lista vacía."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    assert servicio.inventario_por_departamento(departamento_id) == []


def test_inventario_por_departamento_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 7.3: un departamento inexistente se rechaza."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="no existe"):
        servicio.inventario_por_departamento(999)


@pytest.mark.parametrize("id_invalido", [0, -1, None, "abc", 3.5, True])
def test_inventario_por_departamento_id_invalido_es_rechazado(
    conexion: sqlite3.Connection, id_invalido
) -> None:
    """Requirement 7.4: un identificador inválido se rechaza."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="no es válido"):
        servicio.inventario_por_departamento(id_invalido)


def test_alerta_mantenimiento_solo_en_mantenimiento(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 8.1 / 8.2: solo equipos en 'En mantenimiento'."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    _crear_equipo(
        conexion, departamento_id, 0, "Operativo", EstadoEquipo.OPERATIVO
    )
    _crear_equipo(
        conexion, departamento_id, 1, "En Mant", EstadoEquipo.EN_MANTENIMIENTO
    )
    _crear_equipo(
        conexion, departamento_id, 2, "Fuera", EstadoEquipo.FUERA_DE_SERVICIO
    )

    resultado = servicio.alerta_mantenimiento()
    assert len(resultado) == 1
    assert resultado[0].nombre == "En Mant"
    assert resultado[0].estado == EstadoEquipo.EN_MANTENIMIENTO


def test_alerta_mantenimiento_sin_equipos_es_vacio(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 8.3: sin equipos en mantenimiento, devuelve lista vacía."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    _crear_equipo(
        conexion, departamento_id, 0, "Operativo", EstadoEquipo.OPERATIVO
    )
    assert servicio.alerta_mantenimiento() == []
