"""Pruebas de EquipoService: unitarias y basadas en propiedades.

Cubre el alta (unicidad de código, integridad referencial equipo→departamento,
estados válidos, obligatoriedad/longitudes y fecha de adquisición), la
actualización, el cambio de estado y la baja con preservación de historial.

Requirements: 3.2, 3.3, 3.4, 4.3, 4.4, 4.5, 5.2, 5.3, 5.4, 10.1, 10.4, 10.7
"""

from __future__ import annotations

import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.modelos.equipo import EstadoEquipo
from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.modelos.uso import UsoEquipo
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository
from hospital_equipos.servicios.equipo_service import EquipoService

_ESTADOS_VALIDOS = {e.value for e in EstadoEquipo}


def _servicio(conexion: sqlite3.Connection) -> EquipoService:
    return EquipoService(
        EquipoRepository(conexion),
        DepartamentoRepository(conexion),
        UsoRepository(conexion),
    )


def _crear_departamento(conexion: sqlite3.Connection, nombre: str = "Lab") -> int:
    dep = DepartamentoRepository(conexion).insertar(
        Departamento(id=None, nombre=nombre, descripcion="")
    )
    return dep.id


def _registrar(
    servicio: EquipoService,
    departamento_id: int,
    codigo: str = "EQ-001",
    nombre: str = "Monitor",
    marca: str = "Acme",
    modelo: str = "X1",
    numero_serie: str = "SN-1",
    fecha: str = "2023-01-10",
    estado=None,
):
    return servicio.registrar(
        codigo_inventario=codigo,
        nombre=nombre,
        marca=marca,
        modelo=modelo,
        numero_serie=numero_serie,
        fecha_adquisicion=fecha,
        estado=estado,
        departamento_id=departamento_id,
    )


# --------------------------------------------------------------------------- #
# Tarea 8.2 — Property 3: Estados válidos                                       #
# Feature: hospital-equipment-management, Property 3: Estados válidos          #
# Validates: Requirements 3.4, 10.7                                            #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(
    estado_texto=st.text(min_size=0, max_size=30),
    indice_valido=st.integers(min_value=0, max_value=len(EstadoEquipo) - 1),
    usar_valido=st.booleans(),
)
def test_propiedad_estados_validos(
    estado_texto: str, indice_valido: int, usar_valido: bool
) -> None:
    """Property 3: el estado persistido siempre pertenece al enum.

    Si se registra con un estado válido (o vacío→"Operativo"), el equipo se
    crea con un estado del conjunto permitido. Si se registra con un estado
    fuera del conjunto, la operación se rechaza y no se crea ningún equipo.

    Se usa una conexión SQLite en memoria fresca por ejemplo para evitar fugas
    de estado entre las iteraciones de hypothesis.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)

        if usar_valido:
            estado = list(EstadoEquipo)[indice_valido]
            equipo = _registrar(servicio, departamento_id, estado=estado)
            assert equipo.estado.value in _ESTADOS_VALIDOS
        else:
            # Un texto fuera del conjunto (y no vacío) debe ser rechazado.
            if estado_texto.strip() and estado_texto.strip() not in _ESTADOS_VALIDOS:
                with pytest.raises(ValueError):
                    _registrar(servicio, departamento_id, estado=estado_texto)
                assert servicio.obtener(1) is None
            else:
                equipo = _registrar(servicio, departamento_id, estado=estado_texto)
                assert equipo.estado.value in _ESTADOS_VALIDOS

        # Invariante global: todo equipo persistido tiene un estado válido.
        for eq in servicio.listar_por_departamento(departamento_id):
            assert eq.estado.value in _ESTADOS_VALIDOS
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 8.3 — Property 1: Unicidad de código de inventario                     #
# Feature: hospital-equipment-management, Property 1: Unicidad de              #
# códigos/cédulas/nombres                                                      #
# Validates: Requirements 3.2, 10.1                                            #
# --------------------------------------------------------------------------- #
_codigos = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=50,
).filter(lambda s: bool(s.strip()) and len(s.strip()) <= 50)


@settings(max_examples=100)
@given(codigos=st.lists(_codigos, min_size=1, max_size=6, unique=True))
def test_propiedad_unicidad_codigo_inventario(codigos: list[str]) -> None:
    """Property 1: no pueden coexistir dos equipos con el mismo código.

    Para cualquier conjunto de códigos, registrar cada uno y un segundo intento
    con el mismo código (distinto número de serie) debe ser rechazado; el
    conjunto de códigos persistidos debe ser único.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)

        for indice, codigo in enumerate(codigos):
            _registrar(
                servicio,
                departamento_id,
                codigo=codigo,
                numero_serie=f"SN-{indice}",
            )
            with pytest.raises(ValueError):
                _registrar(
                    servicio,
                    departamento_id,
                    codigo=codigo,
                    numero_serie=f"SN-dup-{indice}",
                )

        persistidos = [
            e.codigo_inventario
            for e in servicio.listar_por_departamento(departamento_id)
        ]
        assert len(persistidos) == len(set(persistidos))
        assert set(persistidos) == {c.strip() for c in codigos}
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 8.4 — Property 2: Integridad referencial equipo→departamento           #
# Feature: hospital-equipment-management, Property 2: Integridad referencial   #
# Validates: Requirements 3.3, 10.4                                            #
# --------------------------------------------------------------------------- #
@settings(max_examples=100)
@given(
    departamento_id_invalido=st.integers(min_value=1, max_value=10_000),
)
def test_propiedad_integridad_referencial_equipo_departamento(
    departamento_id_invalido: int,
) -> None:
    """Property 2: un equipo solo puede referir a un departamento existente.

    Registrar un equipo con un ``departamento_id`` inexistente se rechaza y no
    crea ningún equipo. Todo equipo persistido referencia un departamento real.
    """
    conexion = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    try:
        servicio = _servicio(conexion)
        departamento_id = _crear_departamento(conexion)

        # El id válido es 'departamento_id' (=1); cualquier otro es inexistente.
        if departamento_id_invalido != departamento_id:
            with pytest.raises(ValueError):
                _registrar(servicio, departamento_id_invalido)
            assert servicio.listar_por_departamento(departamento_id_invalido) == []

        # Registro con departamento existente sí funciona.
        equipo = _registrar(servicio, departamento_id, codigo="EQ-OK")
        dep_repo = DepartamentoRepository(conexion)
        assert dep_repo.obtener_por_id(equipo.departamento_id) is not None
    finally:
        conexion.close()


# --------------------------------------------------------------------------- #
# Tarea 8.7 — Pruebas unitarias (actualización, estado y baja)                 #
# --------------------------------------------------------------------------- #
def test_registrar_estado_por_defecto_operativo(conexion: sqlite3.Connection) -> None:
    """Requirement 3.5: sin estado, se asigna 'Operativo' por defecto."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id, estado=None)
    assert equipo.estado == EstadoEquipo.OPERATIVO


def test_registrar_codigo_duplicado_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 3.2 / 10.1: código de inventario duplicado rechazado."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    _registrar(servicio, departamento_id, codigo="EQ-1", numero_serie="SN-A")
    with pytest.raises(ValueError, match="ya existe"):
        _registrar(servicio, departamento_id, codigo="EQ-1", numero_serie="SN-B")
    assert len(servicio.listar_por_departamento(departamento_id)) == 1


def test_registrar_departamento_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 3.3 / 10.4: departamento inexistente rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="departamento"):
        _registrar(servicio, 999)


def test_registrar_estado_invalido_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 3.4 / 10.7: estado fuera del enum rechazado."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    with pytest.raises(ValueError, match="estado"):
        _registrar(servicio, departamento_id, estado="Averiado")


def test_registrar_campo_obligatorio_vacio_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 3.6: campo obligatorio vacío rechazado."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    with pytest.raises(ValueError, match="nombre"):
        _registrar(servicio, departamento_id, nombre="   ")


def test_registrar_fecha_futura_es_rechazada(conexion: sqlite3.Connection) -> None:
    """Requirement 3.7: fecha de adquisición futura rechazada."""
    from datetime import date, timedelta

    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    manana = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="fecha de adquisición"):
        _registrar(servicio, departamento_id, fecha=manana)


def test_registrar_codigo_demasiado_largo_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 3.8: código que excede 50 caracteres rechazado."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    with pytest.raises(ValueError, match="longitud máxima"):
        _registrar(servicio, departamento_id, codigo="X" * 51)


def test_actualizar_equipo_inexistente_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 4.4: actualizar un equipo inexistente rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="no existe"):
        servicio.actualizar(123, nombre="Nuevo")


def test_actualizar_valores_validos(conexion: sqlite3.Connection) -> None:
    """Requirement 4.1: actualización con valores válidos persiste cambios."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id)
    actualizado = servicio.actualizar(equipo.id, nombre="Monitor UCI")
    assert actualizado.nombre == "Monitor UCI"
    assert servicio.obtener(equipo.id).nombre == "Monitor UCI"


def test_actualizar_campo_vacio_conserva_datos_previos(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 4.5: valor inválido rechazado y datos previos conservados."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id, nombre="Original")
    with pytest.raises(ValueError):
        servicio.actualizar(equipo.id, nombre="   ")
    assert servicio.obtener(equipo.id).nombre == "Original"


def test_actualizar_texto_demasiado_largo_es_rechazado(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 4.5: campo de más de 255 caracteres rechazado."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id)
    with pytest.raises(ValueError, match="longitud máxima"):
        servicio.actualizar(equipo.id, nombre="N" * 256)


def test_cambiar_estado_valido(conexion: sqlite3.Connection) -> None:
    """Requirement 4.2: cambiar estado a valor válido actualiza el equipo."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id)
    actualizado = servicio.cambiar_estado(
        equipo.id, EstadoEquipo.EN_MANTENIMIENTO
    )
    assert actualizado.estado == EstadoEquipo.EN_MANTENIMIENTO


def test_cambiar_estado_invalido_conserva_estado_previo(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 4.3 / 10.7: estado inválido rechazado, estado previo intacto."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id, estado=EstadoEquipo.OPERATIVO)
    with pytest.raises(ValueError, match="estado"):
        servicio.cambiar_estado(equipo.id, "Roto")
    assert servicio.obtener(equipo.id).estado == EstadoEquipo.OPERATIVO


def test_dar_de_baja_sin_historial_es_exitosa(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 5.1 / 5.5: baja sin sesiones elimina el equipo."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id)
    servicio.dar_de_baja(equipo.id)
    assert servicio.obtener(equipo.id) is None


def test_dar_de_baja_con_historial_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 5.2: baja con sesiones asociadas rechazada, historial intacto."""
    servicio = _servicio(conexion)
    departamento_id = _crear_departamento(conexion)
    equipo = _registrar(servicio, departamento_id)

    # Crear un paciente y una sesión de uso asociada al equipo.
    paciente = PacienteRepository(conexion).insertar(
        Paciente(id=None, cedula="C1", nombre="Ana")
    )
    UsoRepository(conexion).insertar(
        UsoEquipo(
            id=None,
            equipo_id=equipo.id,
            paciente_id=paciente.id,
            fecha_inicio="2024-01-01 10:00",
            duracion_minutos=30,
        )
    )

    with pytest.raises(ValueError, match="sesiones históricas"):
        servicio.dar_de_baja(equipo.id)
    assert servicio.obtener(equipo.id) is not None


def test_dar_de_baja_inexistente_es_rechazada(
    conexion: sqlite3.Connection,
) -> None:
    """Requirement 5.3: baja de un equipo inexistente rechazada."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="no existe"):
        servicio.dar_de_baja(555)


@pytest.mark.parametrize("id_invalido", [0, -1, None, "abc", 3.5, True])
def test_dar_de_baja_id_invalido_es_rechazada(
    conexion: sqlite3.Connection, id_invalido
) -> None:
    """Requirement 5.4: identificador inválido rechazado."""
    servicio = _servicio(conexion)
    with pytest.raises(ValueError, match="no es válido"):
        servicio.dar_de_baja(id_invalido)
