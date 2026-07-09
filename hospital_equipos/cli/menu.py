"""Interfaz de menú de consola (capa de Presentación).

Implementa el menú de texto interactivo del sistema y el enrutamiento de las
operaciones hacia la capa de servicios. La consola es completamente **testeable**
gracias a la inyección de las funciones de entrada y salida (``entrada`` y
``salida``), lo que permite alimentar entradas guionizadas y capturar la salida
sin depender del ``stdin``/``stdout`` reales.

Responsabilidades principales:

- Mostrar un menú principal numerado consecutivamente desde 1 (Requirement 11.1).
- Invocar la operación asociada a una opción válida y mostrar el resultado en
  formato campo/valor, un campo por línea (Requirement 11.2).
- Volver a mostrar el menú tras cada operación (Requirement 11.3).
- Rechazar selecciones inválidas, no numéricas o vacías sin invocar ninguna
  operación (Requirement 11.4).
- Ante el rechazo de un servicio por dato inválido, mostrar el dato y el motivo,
  conservar los demás datos ya introducidos y volver a solicitar únicamente el
  dato rechazado, permitiendo hasta 3 reintentos; cancelar la operación al
  agotarlos (Requirements 11.5, 11.6).

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Optional

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

# Número máximo de reintentos permitidos por operación (Requirement 11.5/11.6).
_MAX_REINTENTOS = 3


@dataclass
class CampoEntrada:
    """Descriptor de un campo a capturar en una operación.

    Attributes:
        clave: Nombre interno del campo (clave del diccionario de valores).
        etiqueta: Nombre legible mostrado al usuario.
        coincidencias: Subcadenas (en minúsculas) que, de aparecer en el mensaje
            de error de un servicio, identifican a este campo como el rechazado.
        opcional: Si es ``True``, un valor vacío se conserva como cadena vacía y
            no se considera obligatorio en la captura.
    """

    clave: str
    etiqueta: str
    coincidencias: tuple[str, ...] = ()
    opcional: bool = False


class OperacionCancelada(Exception):
    """Señala que la operación en curso debe cancelarse (p. ej. por EOF)."""


class MenuConsola:
    """Menú de texto interactivo cableado a los servicios del dominio."""

    def __init__(
        self,
        departamento_service: DepartamentoService,
        paciente_service: PacienteService,
        equipo_service: EquipoService,
        uso_service: UsoService,
        reporte_service: ReporteService,
        entrada: Callable[..., str] = input,
        salida: Callable[..., None] = print,
    ) -> None:
        """Inicializa la consola con los servicios y las E/S inyectables.

        Args:
            departamento_service: Servicio de departamentos.
            paciente_service: Servicio de pacientes.
            equipo_service: Servicio de equipos.
            uso_service: Servicio de sesiones de uso.
            reporte_service: Servicio de reportes.
            entrada: Callable que devuelve la entrada del usuario (por defecto
                :func:`input`). Recibe opcionalmente un ``prompt``.
            salida: Callable que muestra una línea de salida (por defecto
                :func:`print`).
        """
        self._dep = departamento_service
        self._pac = paciente_service
        self._equ = equipo_service
        self._uso = uso_service
        self._rep = reporte_service
        self._entrada = entrada
        self._salida = salida

    # ------------------------------------------------------------------ #
    # Bucle principal                                                     #
    # ------------------------------------------------------------------ #
    def ejecutar(self) -> None:
        """Ejecuta el bucle del menú principal hasta que el usuario salga."""
        while True:
            self._mostrar_menu_principal()
            try:
                opcion = self._leer("Seleccione una opción: ").strip()
            except EOFError:
                self._salida("")
                self._salida("Entrada finalizada. Saliendo del sistema.")
                return

            if not opcion.isdigit():
                self._salida(
                    "Selección no válida: debe introducir el número de una "
                    "opción del menú."
                )
                continue

            numero = int(opcion)
            if numero == 1:
                self._menu_departamentos()
            elif numero == 2:
                self._menu_pacientes()
            elif numero == 3:
                self._menu_equipos()
            elif numero == 4:
                self._menu_sesiones()
            elif numero == 5:
                self._menu_reportes()
            elif numero == 6:
                self._salida("Saliendo del sistema. Hasta pronto.")
                return
            else:
                self._salida(
                    "Selección no válida: la opción indicada no existe en el "
                    "menú."
                )

    def _mostrar_menu_principal(self) -> None:
        """Muestra el menú principal numerado consecutivamente desde 1."""
        self._salida("")
        self._salida("===== Sistema de Gestión de Equipos Médicos =====")
        self._salida("1. Departamentos")
        self._salida("2. Pacientes")
        self._salida("3. Equipos")
        self._salida("4. Sesiones de uso")
        self._salida("5. Reportes")
        self._salida("6. Salir")

    # ------------------------------------------------------------------ #
    # Submenú: Departamentos                                              #
    # ------------------------------------------------------------------ #
    def _menu_departamentos(self) -> None:
        self._ejecutar_submenu(
            "--- Departamentos ---",
            [
                ("Registrar departamento", self._registrar_departamento),
                ("Listar departamentos", self._listar_departamentos),
                ("Consultar departamento por id", self._consultar_departamento),
            ],
        )

    def _registrar_departamento(self) -> None:
        campos = [
            CampoEntrada("nombre", "nombre", ("nombre",)),
            CampoEntrada(
                "descripcion", "descripción", ("descripción", "descripcion"),
                opcional=True,
            ),
        ]

        def operacion(valores: dict[str, str]) -> Departamento:
            return self._dep.registrar(
                valores["nombre"], valores.get("descripcion", "")
            )

        resultado = self._capturar_y_ejecutar(
            "registrar departamento", campos, operacion
        )
        if resultado is not None:
            self._salida("Departamento registrado correctamente:")
            self._mostrar_departamento(resultado)

    def _listar_departamentos(self) -> None:
        departamentos = self._dep.listar()
        if not departamentos:
            self._salida("No hay departamentos registrados.")
            return
        self._mostrar_lista(departamentos, self._mostrar_departamento)

    def _consultar_departamento(self) -> None:
        identificador = self._leer_id_opcional("id del departamento")
        if identificador is None:
            return
        departamento = self._dep.obtener(identificador)
        if departamento is None:
            self._salida(f"No existe un departamento con id {identificador}.")
            return
        self._mostrar_departamento(departamento)

    # ------------------------------------------------------------------ #
    # Submenú: Pacientes                                                  #
    # ------------------------------------------------------------------ #
    def _menu_pacientes(self) -> None:
        self._ejecutar_submenu(
            "--- Pacientes ---",
            [
                ("Registrar paciente", self._registrar_paciente),
                ("Listar pacientes", self._listar_pacientes),
                ("Consultar paciente por id", self._consultar_paciente),
            ],
        )

    def _registrar_paciente(self) -> None:
        campos = [
            CampoEntrada("cedula", "cédula", ("cédula", "cedula")),
            CampoEntrada("nombre", "nombre", ("nombre",)),
            CampoEntrada(
                "fecha_nacimiento",
                "fecha de nacimiento (YYYY-MM-DD)",
                ("fecha de nacimiento",),
            ),
            CampoEntrada(
                "genero", "género (masculino/femenino/otro)",
                ("género", "genero"),
            ),
            CampoEntrada("telefono", "teléfono", ("teléfono", "telefono")),
        ]

        def operacion(valores: dict[str, str]) -> Paciente:
            return self._pac.registrar(
                valores["cedula"],
                valores["nombre"],
                valores["fecha_nacimiento"],
                valores["genero"],
                valores["telefono"],
            )

        resultado = self._capturar_y_ejecutar(
            "registrar paciente", campos, operacion
        )
        if resultado is not None:
            self._salida("Paciente registrado correctamente:")
            self._mostrar_paciente(resultado)

    def _listar_pacientes(self) -> None:
        pacientes = self._pac.listar()
        if not pacientes:
            self._salida("No hay pacientes registrados.")
            return
        self._mostrar_lista(pacientes, self._mostrar_paciente)

    def _consultar_paciente(self) -> None:
        identificador = self._leer_id_opcional("id del paciente")
        if identificador is None:
            return
        paciente = self._pac.obtener(identificador)
        if paciente is None:
            self._salida(f"No existe un paciente con id {identificador}.")
            return
        self._mostrar_paciente(paciente)

    # ------------------------------------------------------------------ #
    # Submenú: Equipos                                                    #
    # ------------------------------------------------------------------ #
    def _menu_equipos(self) -> None:
        self._ejecutar_submenu(
            "--- Equipos ---",
            [
                ("Registrar equipo", self._registrar_equipo),
                ("Consultar equipo por id", self._consultar_equipo),
                ("Listar equipos por departamento", self._listar_equipos_departamento),
                ("Actualizar equipo", self._actualizar_equipo),
                ("Cambiar estado de equipo", self._cambiar_estado_equipo),
                ("Dar de baja equipo", self._dar_de_baja_equipo),
            ],
        )

    def _registrar_equipo(self) -> None:
        campos = [
            CampoEntrada(
                "codigo_inventario",
                "código de inventario",
                ("código de inventario", "codigo de inventario"),
            ),
            CampoEntrada("nombre", "nombre", ("nombre",)),
            CampoEntrada("marca", "marca", ("marca",)),
            CampoEntrada("modelo", "modelo", ("modelo",)),
            CampoEntrada(
                "numero_serie", "número de serie",
                ("número de serie", "numero de serie"),
            ),
            CampoEntrada(
                "fecha_adquisicion",
                "fecha de adquisición (YYYY-MM-DD)",
                ("fecha de adquisición", "fecha de adquisicion"),
            ),
            CampoEntrada(
                "estado",
                f"estado [{self._opciones_estado()}] (enter = Operativo)",
                ("estado",),
                opcional=True,
            ),
            CampoEntrada(
                "departamento_id", "id del departamento", ("departamento",)
            ),
        ]

        def operacion(valores: dict[str, str]) -> Equipo:
            departamento_id = self._a_entero(
                valores["departamento_id"], "id del departamento"
            )
            estado = valores.get("estado", "").strip() or None
            return self._equ.registrar(
                codigo_inventario=valores["codigo_inventario"],
                nombre=valores["nombre"],
                marca=valores["marca"],
                modelo=valores["modelo"],
                numero_serie=valores["numero_serie"],
                fecha_adquisicion=valores["fecha_adquisicion"],
                estado=estado,
                departamento_id=departamento_id,
            )

        resultado = self._capturar_y_ejecutar(
            "registrar equipo", campos, operacion
        )
        if resultado is not None:
            self._salida("Equipo registrado correctamente:")
            self._mostrar_equipo(resultado)

    def _consultar_equipo(self) -> None:
        identificador = self._leer_id_opcional("id del equipo")
        if identificador is None:
            return
        equipo = self._equ.obtener(identificador)
        if equipo is None:
            self._salida(f"No existe un equipo con id {identificador}.")
            return
        self._mostrar_equipo(equipo)

    def _listar_equipos_departamento(self) -> None:
        identificador = self._leer_id_opcional("id del departamento")
        if identificador is None:
            return
        equipos = self._equ.listar_por_departamento(identificador)
        if not equipos:
            self._salida(
                f"El departamento {identificador} no tiene equipos registrados."
            )
            return
        self._mostrar_lista(equipos, self._mostrar_equipo)

    def _actualizar_equipo(self) -> None:
        identificador = self._leer_id_opcional("id del equipo a actualizar")
        if identificador is None:
            return
        if self._equ.obtener(identificador) is None:
            self._salida(f"No existe un equipo con id {identificador}.")
            return

        self._salida(
            "Deje un campo vacío (enter) para conservar su valor actual."
        )
        campos = [
            CampoEntrada(
                "codigo_inventario", "código de inventario",
                ("código de inventario", "codigo de inventario"),
                opcional=True,
            ),
            CampoEntrada("nombre", "nombre", ("nombre",), opcional=True),
            CampoEntrada("marca", "marca", ("marca",), opcional=True),
            CampoEntrada("modelo", "modelo", ("modelo",), opcional=True),
            CampoEntrada(
                "numero_serie", "número de serie",
                ("número de serie", "numero de serie"),
                opcional=True,
            ),
            CampoEntrada(
                "fecha_adquisicion", "fecha de adquisición (YYYY-MM-DD)",
                ("fecha de adquisición", "fecha de adquisicion"),
                opcional=True,
            ),
            CampoEntrada(
                "estado", f"estado [{self._opciones_estado()}]",
                ("estado",), opcional=True,
            ),
            CampoEntrada(
                "departamento_id", "id del departamento",
                ("departamento",), opcional=True,
            ),
        ]

        def operacion(valores: dict[str, str]) -> Equipo:
            cambios: dict[str, object] = {}
            for clave in (
                "codigo_inventario",
                "nombre",
                "marca",
                "modelo",
                "numero_serie",
                "fecha_adquisicion",
                "estado",
            ):
                valor = valores.get(clave, "").strip()
                if valor:
                    cambios[clave] = valor
            dep = valores.get("departamento_id", "").strip()
            if dep:
                cambios["departamento_id"] = self._a_entero(
                    dep, "id del departamento"
                )
            if not cambios:
                raise ValueError(
                    "No se indicó ningún campo para actualizar."
                )
            return self._equ.actualizar(identificador, **cambios)

        resultado = self._capturar_y_ejecutar(
            "actualizar equipo", campos, operacion
        )
        if resultado is not None:
            self._salida("Equipo actualizado correctamente:")
            self._mostrar_equipo(resultado)

    def _cambiar_estado_equipo(self) -> None:
        campos = [
            CampoEntrada("equipo_id", "id del equipo", ("equipo",)),
            CampoEntrada(
                "estado", f"nuevo estado [{self._opciones_estado()}]",
                ("estado",),
            ),
        ]

        def operacion(valores: dict[str, str]) -> Equipo:
            equipo_id = self._a_entero(valores["equipo_id"], "id del equipo")
            return self._equ.cambiar_estado(equipo_id, valores["estado"])

        resultado = self._capturar_y_ejecutar(
            "cambiar estado", campos, operacion
        )
        if resultado is not None:
            self._salida("Estado actualizado correctamente:")
            self._mostrar_equipo(resultado)

    def _dar_de_baja_equipo(self) -> None:
        campos = [CampoEntrada("equipo_id", "id del equipo", ("equipo",))]

        def operacion(valores: dict[str, str]) -> str:
            equipo_id = self._a_entero(valores["equipo_id"], "id del equipo")
            self._equ.dar_de_baja(equipo_id)
            return f"El equipo con id {equipo_id} fue dado de baja."

        resultado = self._capturar_y_ejecutar(
            "dar de baja equipo", campos, operacion
        )
        if resultado is not None:
            self._salida(resultado)

    # ------------------------------------------------------------------ #
    # Submenú: Sesiones de uso                                            #
    # ------------------------------------------------------------------ #
    def _menu_sesiones(self) -> None:
        self._ejecutar_submenu(
            "--- Sesiones de uso ---",
            [
                ("Registrar sesión de uso", self._registrar_uso),
                ("Listar sesiones por equipo", self._listar_sesiones),
            ],
        )

    def _registrar_uso(self) -> None:
        campos = [
            CampoEntrada("equipo_id", "id del equipo", ("equipo",)),
            CampoEntrada("paciente_id", "id del paciente", ("paciente",)),
            CampoEntrada(
                "inicio", "fecha/hora de inicio (YYYY-MM-DD HH:MM)",
                ("fecha/hora de inicio",),
            ),
            CampoEntrada(
                "duracion", "duración en minutos (1-1440)",
                ("duración", "duracion"),
            ),
        ]

        def operacion(valores: dict[str, str]) -> UsoEquipo:
            equipo_id = self._a_entero(valores["equipo_id"], "id del equipo")
            paciente_id = self._a_entero(
                valores["paciente_id"], "id del paciente"
            )
            duracion = self._a_entero(valores["duracion"], "duración")
            return self._uso.registrar_uso(
                equipo_id, paciente_id, valores["inicio"], duracion
            )

        resultado = self._capturar_y_ejecutar(
            "registrar sesión de uso", campos, operacion
        )
        if resultado is not None:
            self._salida("Sesión de uso registrada correctamente:")
            self._mostrar_uso(resultado)

    def _listar_sesiones(self) -> None:
        identificador = self._leer_id_opcional("id del equipo")
        if identificador is None:
            return
        sesiones = self._uso.listar_por_equipo(identificador)
        if not sesiones:
            self._salida(
                f"El equipo {identificador} no tiene sesiones registradas."
            )
            return
        self._mostrar_lista(sesiones, self._mostrar_uso)

    # ------------------------------------------------------------------ #
    # Submenú: Reportes                                                   #
    # ------------------------------------------------------------------ #
    def _menu_reportes(self) -> None:
        self._ejecutar_submenu(
            "--- Reportes ---",
            [
                ("Inventario por departamento", self._reporte_inventario),
                ("Alerta de mantenimiento", self._reporte_mantenimiento),
                ("Indicador de uso clínico", self._reporte_indicador),
            ],
        )

    def _reporte_inventario(self) -> None:
        campos = [
            CampoEntrada(
                "departamento_id", "id del departamento", ("departamento",)
            )
        ]

        def operacion(valores: dict[str, str]) -> list[Equipo]:
            departamento_id = self._a_entero(
                valores["departamento_id"], "id del departamento"
            )
            return self._rep.inventario_por_departamento(departamento_id)

        resultado = self._capturar_y_ejecutar(
            "inventario por departamento", campos, operacion
        )
        if resultado is None:
            return
        if not resultado:
            self._salida("El departamento no tiene equipos registrados.")
            return
        self._mostrar_lista(resultado, self._mostrar_equipo)

    def _reporte_mantenimiento(self) -> None:
        equipos = self._rep.alerta_mantenimiento()
        if not equipos:
            self._salida("No hay equipos en mantenimiento.")
            return
        self._mostrar_lista(equipos, self._mostrar_equipo)

    def _reporte_indicador(self) -> None:
        campos = [
            CampoEntrada(
                "criterio", "criterio (sesiones/horas)", ("criterio",)
            ),
            CampoEntrada(
                "departamento_id",
                "id del departamento (enter = todos)",
                ("departamento",),
                opcional=True,
            ),
        ]

        def operacion(valores: dict[str, str]) -> list[MetricaUso]:
            dep = valores.get("departamento_id", "").strip()
            departamento_id = (
                self._a_entero(dep, "id del departamento") if dep else None
            )
            return self._rep.indicador_uso_clinico(
                valores["criterio"], departamento_id
            )

        resultado = self._capturar_y_ejecutar(
            "indicador de uso clínico", campos, operacion
        )
        if resultado is None:
            return
        if not resultado:
            self._salida(
                "No hay equipos con sesiones en el alcance solicitado."
            )
            return
        self._mostrar_lista(resultado, self._mostrar_metrica)

    # ------------------------------------------------------------------ #
    # Infraestructura de submenús                                         #
    # ------------------------------------------------------------------ #
    def _ejecutar_submenu(
        self, titulo: str, acciones: list[tuple[str, Callable[[], None]]]
    ) -> None:
        """Muestra un submenú numerado y ejecuta la acción seleccionada.

        La última opción es siempre "Volver". Las selecciones inválidas, no
        numéricas o vacías se rechazan sin invocar ninguna acción, y el submenú
        se vuelve a mostrar (Requirements 11.3, 11.4).
        """
        opcion_volver = len(acciones) + 1
        while True:
            self._salida("")
            self._salida(titulo)
            for indice, (etiqueta, _) in enumerate(acciones, start=1):
                self._salida(f"{indice}. {etiqueta}")
            self._salida(f"{opcion_volver}. Volver")

            try:
                opcion = self._leer("Seleccione una opción: ").strip()
            except EOFError:
                return

            if not opcion.isdigit():
                self._salida(
                    "Selección no válida: debe introducir el número de una "
                    "opción del menú."
                )
                continue

            numero = int(opcion)
            if numero == opcion_volver:
                return
            if 1 <= numero <= len(acciones):
                _, accion = acciones[numero - 1]
                try:
                    accion()
                except OperacionCancelada:
                    self._salida("Operación cancelada.")
            else:
                self._salida(
                    "Selección no válida: la opción indicada no existe en el "
                    "menú."
                )

    # ------------------------------------------------------------------ #
    # Captura de datos con reintentos (Requirements 11.5, 11.6)           #
    # ------------------------------------------------------------------ #
    def _capturar_y_ejecutar(
        self,
        nombre_operacion: str,
        campos: list[CampoEntrada],
        operacion: Callable[[dict[str, str]], object],
    ):
        """Captura los campos, ejecuta la operación y gestiona los reintentos.

        Captura inicialmente todos los campos. Ante un :class:`ValueError` del
        servicio, identifica el campo rechazado a partir del mensaje, muestra el
        dato y el motivo, conserva los demás valores y vuelve a solicitar
        únicamente ese campo, permitiendo hasta :data:`_MAX_REINTENTOS`
        reintentos. Al agotarlos, cancela la operación (Requirement 11.6).

        Args:
            nombre_operacion: Nombre legible de la operación (para los mensajes).
            campos: Descriptores de los campos a capturar.
            operacion: Callable que recibe el diccionario de valores capturados y
                ejecuta la operación del servicio, devolviendo su resultado.

        Returns:
            El resultado de la operación si tiene éxito, o ``None`` si se cancela.
        """
        try:
            valores = {campo.clave: self._leer_campo(campo) for campo in campos}
        except OperacionCancelada:
            self._salida(f"Operación '{nombre_operacion}' cancelada.")
            return None

        for intento in range(_MAX_REINTENTOS + 1):
            try:
                return operacion(valores)
            except ValueError as error:
                campo = self._identificar_campo(str(error), campos)
                etiqueta = campo.etiqueta if campo is not None else "dato"
                valor_rechazado = (
                    valores.get(campo.clave, "") if campo is not None else ""
                )
                self._salida(
                    f"Dato rechazado -> {etiqueta}: '{valor_rechazado}'"
                )
                self._salida(f"Motivo: {error}")

                if intento >= _MAX_REINTENTOS or campo is None:
                    break

                self._salida(
                    f"Reintento {intento + 1} de {_MAX_REINTENTOS}."
                )
                try:
                    valores[campo.clave] = self._leer_campo(campo)
                except OperacionCancelada:
                    break

        self._salida(
            f"Operación '{nombre_operacion}' cancelada: se agotaron los "
            f"{_MAX_REINTENTOS} reintentos o la entrada fue interrumpida."
        )
        return None

    def _identificar_campo(
        self, mensaje: str, campos: list[CampoEntrada]
    ) -> Optional[CampoEntrada]:
        """Devuelve el campo cuyo texto de coincidencia aparece en el mensaje."""
        mensaje_min = mensaje.lower()
        for campo in campos:
            if any(clave in mensaje_min for clave in campo.coincidencias):
                return campo
        return None

    def _leer_campo(self, campo: CampoEntrada) -> str:
        """Solicita el valor de un único campo al usuario."""
        return self._leer(f"{campo.etiqueta}: ")

    # ------------------------------------------------------------------ #
    # Utilidades de entrada                                               #
    # ------------------------------------------------------------------ #
    def _leer(self, prompt: str = "") -> str:
        """Lee una línea de entrada, convirtiendo ``StopIteration`` en EOF."""
        try:
            return self._entrada(prompt)
        except StopIteration as exc:  # entrada guionizada agotada (tests)
            raise EOFError from exc

    def _leer_id_opcional(self, etiqueta: str) -> Optional[int]:
        """Lee y convierte un identificador entero; ``None`` si es inválido.

        Muestra un mensaje y devuelve ``None`` si la entrada no es un entero o
        si la entrada se interrumpe (EOF).
        """
        try:
            valor = self._leer(f"{etiqueta}: ").strip()
        except EOFError:
            return None
        try:
            return self._a_entero(valor, etiqueta)
        except ValueError as error:
            self._salida(f"Selección no válida: {error}")
            return None

    @staticmethod
    def _a_entero(valor: str, etiqueta: str) -> int:
        """Convierte una cadena a entero o lanza un ``ValueError`` descriptivo.

        El mensaje incluye la etiqueta para que el campo pueda identificarse en
        el flujo de reintentos.
        """
        try:
            return int(str(valor).strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"El campo {etiqueta} debe ser un número entero."
            ) from exc

    @staticmethod
    def _opciones_estado() -> str:
        """Devuelve los estados válidos separados por barras, para los prompts."""
        return " / ".join(estado.value for estado in EstadoEquipo)

    # ------------------------------------------------------------------ #
    # Formateo de salida (campo/valor, un campo por línea)                #
    # ------------------------------------------------------------------ #
    def _mostrar_campos(self, pares: list[tuple[str, object]]) -> None:
        """Muestra pares (etiqueta, valor), un campo por línea."""
        for etiqueta, valor in pares:
            self._salida(f"{etiqueta}: {valor}")

    def _mostrar_lista(self, elementos, mostrar_uno: Callable) -> None:
        """Muestra una colección, separando cada elemento con una línea."""
        for indice, elemento in enumerate(elementos):
            if indice > 0:
                self._salida("---")
            mostrar_uno(elemento)

    def _mostrar_departamento(self, departamento: Departamento) -> None:
        self._mostrar_campos(
            [
                ("id", departamento.id),
                ("nombre", departamento.nombre),
                ("descripción", departamento.descripcion),
            ]
        )

    def _mostrar_paciente(self, paciente: Paciente) -> None:
        self._mostrar_campos(
            [
                ("id", paciente.id),
                ("cédula", paciente.cedula),
                ("nombre", paciente.nombre),
                ("fecha de nacimiento", paciente.fecha_nacimiento),
                ("género", paciente.genero),
                ("teléfono", paciente.telefono),
            ]
        )

    def _mostrar_equipo(self, equipo: Equipo) -> None:
        self._mostrar_campos(
            [
                ("id", equipo.id),
                ("código de inventario", equipo.codigo_inventario),
                ("nombre", equipo.nombre),
                ("marca", equipo.marca),
                ("modelo", equipo.modelo),
                ("número de serie", equipo.numero_serie),
                ("fecha de adquisición", equipo.fecha_adquisicion),
                ("estado", equipo.estado.value),
                ("departamento_id", equipo.departamento_id),
            ]
        )

    def _mostrar_uso(self, uso: UsoEquipo) -> None:
        self._mostrar_campos(
            [
                ("id", uso.id),
                ("equipo_id", uso.equipo_id),
                ("paciente_id", uso.paciente_id),
                ("fecha de inicio", uso.fecha_inicio),
                ("duración (minutos)", uso.duracion_minutos),
            ]
        )

    def _mostrar_metrica(self, metrica: MetricaUso) -> None:
        self._mostrar_campos(
            [
                ("equipo", metrica.equipo_nombre),
                ("departamento", metrica.departamento_nombre),
                ("total de uso", metrica.total_uso),
                ("criterio", metrica.criterio.value),
            ]
        )


def construir_menu(
    conexion: sqlite3.Connection,
    entrada: Callable[..., str] = input,
    salida: Callable[..., None] = print,
) -> MenuConsola:
    """Cablea repositorios y servicios sobre una conexión y devuelve el menú.

    Esta función centraliza el cableado de las capas para que sea reutilizable
    tanto por el punto de entrada (:mod:`hospital_equipos.main`) como por las
    pruebas de la CLI.

    Args:
        conexion: Conexión SQLite ya inicializada (esquema creado).
        entrada: Callable de entrada del usuario (por defecto :func:`input`).
        salida: Callable de salida (por defecto :func:`print`).

    Returns:
        Una instancia de :class:`MenuConsola` lista para ejecutarse.
    """
    departamento_repo = DepartamentoRepository(conexion)
    paciente_repo = PacienteRepository(conexion)
    equipo_repo = EquipoRepository(conexion)
    uso_repo = UsoRepository(conexion)

    departamento_service = DepartamentoService(departamento_repo)
    paciente_service = PacienteService(paciente_repo)
    equipo_service = EquipoService(equipo_repo, departamento_repo, uso_repo)
    uso_service = UsoService(uso_repo, equipo_repo, paciente_repo)
    reporte_service = ReporteService(equipo_repo, uso_repo, departamento_repo)

    return MenuConsola(
        departamento_service,
        paciente_service,
        equipo_service,
        uso_service,
        reporte_service,
        entrada=entrada,
        salida=salida,
    )
