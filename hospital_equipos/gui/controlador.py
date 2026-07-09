"""Controlador de aplicación para la interfaz gráfica (capa de Presentación).

Este módulo define :class:`ControladorApp`, una fachada **sin ninguna
dependencia de Tkinter/CustomTkinter** que cablea los repositorios y los
servicios del dominio sobre una conexión SQLite y expone métodos sencillos que
la vista gráfica invoca directamente.

El controlador **reutiliza** la capa de servicios existente sin modificarla: se
limita a delegar en ella y a dejar que los :class:`ValueError` de validación se
propaguen hacia la vista, que es la encargada de mostrarlos al usuario. Al no
depender de ningún display, esta capa es completamente testeable de forma
unitaria (por ejemplo, con una base de datos SQLite en memoria).

Responsabilidades:

- Construir (o recibir) la conexión SQLite e inicializar el esquema.
- Precargar los 12 departamentos base (idempotente).
- Ofrecer operaciones de alto nivel para departamentos, pacientes, equipos,
  sesiones de uso y reportes, delegando en los servicios correspondientes.
"""

from __future__ import annotations

import sqlite3

from hospital_equipos.db.conexion import crear_conexion, inicializar_esquema
from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.modelos.uso import CriterioUso, MetricaUso, UsoEquipo
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.paciente_repo import PacienteRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository
from hospital_equipos.servicios.departamento_service import DepartamentoService
from hospital_equipos.servicios.equipo_service import EquipoService
from hospital_equipos.servicios.paciente_service import PacienteService
from hospital_equipos.servicios.reporte_service import ReporteService
from hospital_equipos.servicios.uso_service import UsoService

# Ruta por defecto del archivo de base de datos usado por la GUI (igual que la
# aplicación de consola, para compartir los mismos datos persistentes).
_RUTA_BD_POR_DEFECTO = "hospital.db"


class ControladorApp:
    """Fachada testeable que conecta la vista gráfica con los servicios.

    Cablea repositorios y servicios sobre una conexión SQLite, precarga los
    departamentos base y expone métodos de alto nivel. No importa Tkinter ni
    CustomTkinter, por lo que puede ejercitarse sin un entorno gráfico.
    """

    def __init__(
        self,
        conexion: sqlite3.Connection | None = None,
        ruta_bd: str = _RUTA_BD_POR_DEFECTO,
    ) -> None:
        """Inicializa el controlador cableando todas las capas.

        Args:
            conexion: Conexión SQLite ya abierta. Si es ``None`` se crea una
                nueva conexión sobre ``ruta_bd`` (útil en producción). En las
                pruebas puede inyectarse una conexión en memoria (``:memory:``).
            ruta_bd: Ruta del archivo de base de datos usada solo cuando
                ``conexion`` es ``None``.
        """
        if conexion is None:
            conexion = crear_conexion(ruta_bd)
        self._conexion = conexion

        # Inicialización idempotente del esquema relacional.
        inicializar_esquema(self._conexion)

        # Cableado de repositorios.
        self._departamento_repo = DepartamentoRepository(self._conexion)
        self._paciente_repo = PacienteRepository(self._conexion)
        self._equipo_repo = EquipoRepository(self._conexion)
        self._uso_repo = UsoRepository(self._conexion)

        # Cableado de servicios (reutilización directa de la capa de negocio).
        self._departamento_service = DepartamentoService(self._departamento_repo)
        self._paciente_service = PacienteService(self._paciente_repo)
        self._equipo_service = EquipoService(
            self._equipo_repo, self._departamento_repo, self._uso_repo
        )
        self._uso_service = UsoService(
            self._uso_repo, self._equipo_repo, self._paciente_repo
        )
        self._reporte_service = ReporteService(
            self._equipo_repo, self._uso_repo, self._departamento_repo
        )

        # Precarga de los 12 departamentos base (solo si la tabla está vacía).
        self._mensaje_precarga = (
            self._departamento_service.inicializar_departamentos_base()
        )

    # ------------------------------------------------------------------ #
    # Conexión / ciclo de vida                                            #
    # ------------------------------------------------------------------ #
    @property
    def conexion(self) -> sqlite3.Connection:
        """Devuelve la conexión SQLite subyacente."""
        return self._conexion

    @property
    def mensaje_precarga(self) -> str:
        """Devuelve el mensaje generado por la precarga de departamentos."""
        return self._mensaje_precarga

    def cerrar(self) -> None:
        """Cierra la conexión SQLite subyacente."""
        self._conexion.close()

    # ------------------------------------------------------------------ #
    # Departamentos                                                       #
    # ------------------------------------------------------------------ #
    def listar_departamentos(self) -> list[Departamento]:
        """Devuelve todos los departamentos registrados."""
        return self._departamento_service.listar()

    def registrar_departamento(
        self, nombre: str, descripcion: str = ""
    ) -> Departamento:
        """Registra un departamento delegando en el servicio.

        Raises:
            ValueError: Si el nombre es inválido o ya existe (se propaga).
        """
        return self._departamento_service.registrar(nombre, descripcion)

    def obtener_departamento(self, departamento_id: int) -> Departamento | None:
        """Devuelve el departamento con el ``id`` dado, o ``None``."""
        return self._departamento_service.obtener(departamento_id)

    # ------------------------------------------------------------------ #
    # Pacientes                                                           #
    # ------------------------------------------------------------------ #
    def listar_pacientes(self) -> list[Paciente]:
        """Devuelve todos los pacientes ordenados por nombre."""
        return self._paciente_service.listar()

    def registrar_paciente(
        self,
        cedula: str,
        nombre: str,
        fecha_nacimiento: str,
        genero: str,
        telefono: str,
    ) -> Paciente:
        """Registra un paciente delegando en el servicio.

        Raises:
            ValueError: Si algún campo es inválido o la cédula ya existe.
        """
        return self._paciente_service.registrar(
            cedula, nombre, fecha_nacimiento, genero, telefono
        )

    def obtener_paciente(self, paciente_id: int) -> Paciente | None:
        """Devuelve el paciente con el ``id`` dado, o ``None``."""
        return self._paciente_service.obtener(paciente_id)

    # ------------------------------------------------------------------ #
    # Equipos                                                             #
    # ------------------------------------------------------------------ #
    def listar_equipos_por_departamento(
        self, departamento_id: int
    ) -> list[Equipo]:
        """Devuelve los equipos de un departamento."""
        return self._equipo_service.listar_por_departamento(departamento_id)

    def registrar_equipo(
        self,
        codigo_inventario: str,
        nombre: str,
        marca: str,
        modelo: str,
        numero_serie: str,
        fecha_adquisicion: str,
        estado: EstadoEquipo | str | None = None,
        departamento_id: int | None = None,
    ) -> Equipo:
        """Registra un equipo delegando en el servicio.

        Raises:
            ValueError: Si algún campo es inválido, el código ya existe o el
                departamento no existe (se propaga).
        """
        return self._equipo_service.registrar(
            codigo_inventario=codigo_inventario,
            nombre=nombre,
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie,
            fecha_adquisicion=fecha_adquisicion,
            estado=estado,
            departamento_id=departamento_id,
        )

    def actualizar_equipo(self, equipo_id: int, **campos) -> Equipo:
        """Actualiza los campos indicados de un equipo existente.

        Raises:
            ValueError: Si el equipo no existe o algún campo es inválido.
        """
        return self._equipo_service.actualizar(equipo_id, **campos)

    def cambiar_estado_equipo(
        self, equipo_id: int, estado: EstadoEquipo | str
    ) -> Equipo:
        """Cambia el estado de un equipo existente.

        Raises:
            ValueError: Si el equipo no existe o el estado es inválido.
        """
        return self._equipo_service.cambiar_estado(equipo_id, estado)

    def dar_de_baja_equipo(self, equipo_id: int) -> None:
        """Da de baja un equipo si no tiene sesiones asociadas.

        Raises:
            ValueError: Si el equipo no existe o tiene sesiones históricas.
        """
        self._equipo_service.dar_de_baja(equipo_id)

    def obtener_equipo(self, equipo_id: int) -> Equipo | None:
        """Devuelve el equipo con el ``id`` dado, o ``None``."""
        return self._equipo_service.obtener(equipo_id)

    # ------------------------------------------------------------------ #
    # Sesiones de uso                                                     #
    # ------------------------------------------------------------------ #
    def registrar_uso(
        self,
        equipo_id: int,
        paciente_id: int,
        inicio: str,
        duracion_minutos: int,
    ) -> UsoEquipo:
        """Registra una sesión de uso delegando en el servicio.

        Raises:
            ValueError: Si el equipo o el paciente no existen, la fecha/hora es
                inválida o la duración está fuera de rango (se propaga).
        """
        return self._uso_service.registrar_uso(
            equipo_id, paciente_id, inicio, duracion_minutos
        )

    def listar_sesiones_por_equipo(self, equipo_id: int) -> list[UsoEquipo]:
        """Devuelve las sesiones de un equipo (de más reciente a más antigua)."""
        return self._uso_service.listar_por_equipo(equipo_id)

    # ------------------------------------------------------------------ #
    # Reportes                                                            #
    # ------------------------------------------------------------------ #
    def inventario_por_departamento(self, departamento_id: int) -> list[Equipo]:
        """Devuelve el inventario de equipos de un departamento existente.

        Raises:
            ValueError: Si el identificador es inválido o el departamento no
                existe (se propaga).
        """
        return self._reporte_service.inventario_por_departamento(departamento_id)

    def alerta_mantenimiento(self) -> list[Equipo]:
        """Devuelve los equipos cuyo estado es ``En mantenimiento``."""
        return self._reporte_service.alerta_mantenimiento()

    def indicador_uso_clinico(
        self,
        criterio: CriterioUso | str,
        departamento_id: int | None = None,
    ) -> list[MetricaUso]:
        """Calcula el Indicador de Uso Clínico (equipo más utilizado).

        Raises:
            ValueError: Si el criterio es inválido o el departamento indicado no
                existe (se propaga).
        """
        return self._reporte_service.indicador_uso_clinico(
            criterio, departamento_id
        )
