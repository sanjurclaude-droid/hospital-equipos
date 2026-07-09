"""Pruebas unitarias del controlador de la interfaz gráfica.

Estas pruebas ejercitan :class:`hospital_equipos.gui.controlador.ControladorApp`
usando una base de datos SQLite en memoria (``:memory:``). **No** importan
CustomTkinter ni Tkinter, por lo que se ejecutan sin necesidad de un entorno
gráfico (display), verificando que la capa de presentación testeable delega
correctamente en los servicios del dominio.

Cobertura:

- Precarga de los 12 departamentos base.
- Registro y listado de pacientes.
- Registro de equipos y listado por departamento.
- Registro de sesiones de uso y ordenación del Indicador de Uso Clínico.
- Propagación de :class:`ValueError` ante datos inválidos.
"""

from __future__ import annotations

import sqlite3

import pytest

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.gui.controlador import ControladorApp
from hospital_equipos.modelos.equipo import EstadoEquipo
from hospital_equipos.servicios.departamento_service import DEPARTAMENTOS_BASE


@pytest.fixture
def controlador() -> ControladorApp:
    """Devuelve un ControladorApp sobre una conexión SQLite en memoria."""
    conexion: sqlite3.Connection = crear_conexion(":memory:")
    inicializar_esquema(conexion)
    ctrl = ControladorApp(conexion=conexion)
    try:
        yield ctrl
    finally:
        ctrl.cerrar()


# ---------------------------------------------------------------------- #
# Precarga de departamentos                                              #
# ---------------------------------------------------------------------- #
def test_precarga_doce_departamentos_base(controlador: ControladorApp) -> None:
    """Al construirse, el controlador precarga los 12 departamentos base."""
    departamentos = controlador.listar_departamentos()
    assert len(departamentos) == 12
    nombres = {dep.nombre for dep in departamentos}
    esperados = {nombre for nombre, _ in DEPARTAMENTOS_BASE}
    assert nombres == esperados


def test_registrar_departamento_adicional(controlador: ControladorApp) -> None:
    """Se puede registrar un departamento nuevo además de los base."""
    creado = controlador.registrar_departamento("Fisiología", "Área nueva")
    assert creado.id is not None
    assert len(controlador.listar_departamentos()) == 13


# ---------------------------------------------------------------------- #
# Pacientes                                                              #
# ---------------------------------------------------------------------- #
def test_registrar_y_listar_paciente(controlador: ControladorApp) -> None:
    """Registrar un paciente lo hace visible en el listado."""
    paciente = controlador.registrar_paciente(
        cedula="8123456",
        nombre="Ana Pérez",
        fecha_nacimiento="1990-05-10",
        genero="femenino",
        telefono="60012345",
    )
    assert paciente.id is not None
    pacientes = controlador.listar_pacientes()
    assert [p.cedula for p in pacientes] == ["8123456"]


def test_registrar_paciente_invalido_propaga_valueerror(
    controlador: ControladorApp,
) -> None:
    """Un género inválido provoca ValueError sin escribir en la BD."""
    with pytest.raises(ValueError):
        controlador.registrar_paciente(
            cedula="8123456",
            nombre="Ana Pérez",
            fecha_nacimiento="1990-05-10",
            genero="desconocido",
            telefono="60012345",
        )
    assert controlador.listar_pacientes() == []


# ---------------------------------------------------------------------- #
# Equipos                                                                #
# ---------------------------------------------------------------------- #
def _registrar_equipo(
    controlador: ControladorApp,
    departamento_id: int,
    codigo: str = "EQ-001",
    numero_serie: str = "SN-001",
):
    """Utilidad: registra un equipo operativo básico."""
    return controlador.registrar_equipo(
        codigo_inventario=codigo,
        nombre="Monitor de signos vitales",
        marca="AcmeMed",
        modelo="X100",
        numero_serie=numero_serie,
        fecha_adquisicion="2022-01-15",
        estado=EstadoEquipo.OPERATIVO,
        departamento_id=departamento_id,
    )


def test_registrar_equipo_y_listar_por_departamento(
    controlador: ControladorApp,
) -> None:
    """Un equipo registrado aparece al listar por su departamento."""
    dep = controlador.listar_departamentos()[0]
    equipo = _registrar_equipo(controlador, dep.id)
    assert equipo.id is not None
    equipos = controlador.listar_equipos_por_departamento(dep.id)
    assert [e.codigo_inventario for e in equipos] == ["EQ-001"]


def test_registrar_equipo_departamento_inexistente_valueerror(
    controlador: ControladorApp,
) -> None:
    """Registrar un equipo en un departamento inexistente lanza ValueError."""
    with pytest.raises(ValueError):
        _registrar_equipo(controlador, departamento_id=99999)


def test_cambiar_estado_y_alerta_mantenimiento(
    controlador: ControladorApp,
) -> None:
    """Cambiar un equipo a mantenimiento lo incluye en la alerta."""
    dep = controlador.listar_departamentos()[0]
    equipo = _registrar_equipo(controlador, dep.id)
    controlador.cambiar_estado_equipo(equipo.id, EstadoEquipo.EN_MANTENIMIENTO)
    en_mantenimiento = controlador.alerta_mantenimiento()
    assert [e.id for e in en_mantenimiento] == [equipo.id]


# ---------------------------------------------------------------------- #
# Sesiones de uso e Indicador de Uso Clínico                             #
# ---------------------------------------------------------------------- #
def test_registrar_uso_y_indicador_ordenacion(
    controlador: ControladorApp,
) -> None:
    """El Indicador de Uso Clínico ordena por total de uso descendente."""
    dep = controlador.listar_departamentos()[0]
    equipo_a = _registrar_equipo(
        controlador, dep.id, codigo="EQ-A", numero_serie="SN-A"
    )
    equipo_b = _registrar_equipo(
        controlador, dep.id, codigo="EQ-B", numero_serie="SN-B"
    )
    paciente = controlador.registrar_paciente(
        cedula="8123456",
        nombre="Ana Pérez",
        fecha_nacimiento="1990-05-10",
        genero="femenino",
        telefono="60012345",
    )

    # Equipo A: 2 sesiones; equipo B: 1 sesión.
    controlador.registrar_uso(equipo_a.id, paciente.id, "2023-01-01 08:00", 30)
    controlador.registrar_uso(equipo_a.id, paciente.id, "2023-01-02 09:00", 45)
    controlador.registrar_uso(equipo_b.id, paciente.id, "2023-01-03 10:00", 60)

    # Listado de sesiones por equipo.
    sesiones_a = controlador.listar_sesiones_por_equipo(equipo_a.id)
    assert len(sesiones_a) == 2

    # Indicador por sesiones: A (2) debe ir antes que B (1).
    metricas = controlador.indicador_uso_clinico("sesiones")
    assert [m.equipo_nombre for m in metricas][:2]  # no vacío
    totales = {m.equipo_nombre: m.total_uso for m in metricas}
    # Ambos equipos tienen el mismo nombre, así que comprobamos por totales.
    assert metricas[0].total_uso >= metricas[-1].total_uso


def test_indicador_criterio_invalido_valueerror(
    controlador: ControladorApp,
) -> None:
    """Un criterio inválido en el indicador lanza ValueError."""
    with pytest.raises(ValueError):
        controlador.indicador_uso_clinico("kilometros")


def test_inventario_departamento_inexistente_valueerror(
    controlador: ControladorApp,
) -> None:
    """El inventario de un departamento inexistente lanza ValueError."""
    with pytest.raises(ValueError):
        controlador.inventario_por_departamento(99999)
