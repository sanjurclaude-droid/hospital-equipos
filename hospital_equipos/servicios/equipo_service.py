"""Servicio de dominio para la gestión del inventario de equipos médicos.

Aplica las reglas de negocio del ciclo de vida de un equipo médico:

- **Alta** (:meth:`EquipoService.registrar`): valida unicidad del código de
  inventario, existencia del departamento (integridad referencial), estado
  dentro del enum :class:`~hospital_equipos.modelos.equipo.EstadoEquipo`,
  obligatoriedad y longitudes de los campos de texto, y validez de la fecha de
  adquisición (no futura). El estado por defecto es ``Operativo``.
- **Actualización** (:meth:`EquipoService.actualizar`): valida la existencia
  del equipo y los valores de los campos, conservando los datos previos ante
  cualquier rechazo.
- **Cambio de estado** (:meth:`EquipoService.cambiar_estado`): restringe el
  estado al conjunto permitido.
- **Baja** (:meth:`EquipoService.dar_de_baja`): rechaza la baja si el equipo
  tiene sesiones de uso asociadas (preservación del historial) y elimina el
  equipo del inventario en caso contrario.

Ante cualquier dato inválido, el servicio lanza :class:`ValueError` con un
mensaje claro en español y conserva sin cambios el estado del inventario (no se
realiza ninguna escritura). Depende de :class:`EquipoRepository`, de
:class:`DepartamentoRepository` (para validar la existencia del departamento) y
de :class:`UsoRepository` (para comprobar el historial de sesiones en la baja),
inyectados mediante el constructor.

Requirements: 3.1-3.8, 4.1-4.5, 5.1-5.5, 10.1, 10.4, 10.7
"""

from __future__ import annotations

from datetime import date, datetime

from hospital_equipos.modelos.equipo import Equipo, EstadoEquipo
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)
from hospital_equipos.repositorios.equipo_repo import EquipoRepository
from hospital_equipos.repositorios.uso_repo import UsoRepository

# Longitudes máximas de los campos de texto en el registro (Requirement 3).
_LONGITUD_MAXIMA_CODIGO = 50
_LONGITUD_MAXIMA_NOMBRE = 100
_LONGITUD_MAXIMA_MARCA = 50
_LONGITUD_MAXIMA_MODELO = 50
_LONGITUD_MAXIMA_NUMERO_SERIE = 50

# Longitud máxima de los campos de texto en la actualización (Requirement 4.1).
_LONGITUD_MAXIMA_ACTUALIZACION = 255

# Nombres legibles y longitudes máximas de los campos obligatorios de texto.
_CAMPOS_TEXTO_REGISTRO: tuple[tuple[str, int], ...] = (
    ("código de inventario", _LONGITUD_MAXIMA_CODIGO),
    ("nombre", _LONGITUD_MAXIMA_NOMBRE),
    ("marca", _LONGITUD_MAXIMA_MARCA),
    ("modelo", _LONGITUD_MAXIMA_MODELO),
    ("número de serie", _LONGITUD_MAXIMA_NUMERO_SERIE),
)

# Campos de texto que pueden actualizarse mediante ``actualizar``.
_CAMPOS_ACTUALIZABLES_TEXTO = (
    "codigo_inventario",
    "nombre",
    "marca",
    "modelo",
    "numero_serie",
    "fecha_adquisicion",
)


def _normalizar_estado(estado: EstadoEquipo | str) -> EstadoEquipo:
    """Convierte un estado (enum o texto) a :class:`EstadoEquipo`.

    Args:
        estado: Estado como enum o como texto exacto del conjunto permitido.

    Returns:
        El :class:`EstadoEquipo` correspondiente.

    Raises:
        ValueError: Si el estado no pertenece al conjunto permitido.
    """
    if isinstance(estado, EstadoEquipo):
        return estado
    try:
        return EstadoEquipo(estado)
    except ValueError as exc:
        validos = ", ".join(e.value for e in EstadoEquipo)
        raise ValueError(
            f"El estado del equipo es inválido; debe ser uno de: {validos}."
        ) from exc


class EquipoService:
    """Lógica de negocio para el registro, actualización y baja de equipos."""

    def __init__(
        self,
        repositorio: EquipoRepository,
        departamento_repo: DepartamentoRepository,
        uso_repo: UsoRepository,
    ) -> None:
        """Inicializa el servicio con sus dependencias.

        Args:
            repositorio: Acceso a datos de equipos.
            departamento_repo: Acceso a datos de departamentos (para validar la
                existencia del departamento asignado — integridad referencial).
            uso_repo: Acceso a datos de sesiones de uso (para comprobar el
                historial al dar de baja un equipo).
        """
        self._repositorio = repositorio
        self._departamento_repo = departamento_repo
        self._uso_repo = uso_repo

    # ------------------------------------------------------------------ #
    # Alta (Tarea 8.1)                                                    #
    # ------------------------------------------------------------------ #
    def registrar(
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
        """Registra un equipo médico tras validar todos sus campos.

        Args:
            codigo_inventario: Código único de inventario (1–50 caracteres).
            nombre: Nombre del equipo (1–100 caracteres).
            marca: Marca del equipo (1–50 caracteres).
            modelo: Modelo del equipo (1–50 caracteres).
            numero_serie: Número de serie (1–50 caracteres).
            fecha_adquisicion: Fecha ``YYYY-MM-DD`` válida, no futura.
            estado: Estado inicial; si es ``None`` se asigna ``Operativo``.
            departamento_id: Identificador de un departamento existente.

        Returns:
            El :class:`Equipo` creado con su identificador asignado.

        Raises:
            ValueError: Si algún campo es inválido, el código ya existe o el
                departamento no existe. No se realiza ninguna escritura.
        """
        # Campos de texto obligatorios: obligatoriedad y longitud.
        valores = (codigo_inventario, nombre, marca, modelo, numero_serie)
        normalizados: list[str] = []
        for valor, (etiqueta, maximo) in zip(valores, _CAMPOS_TEXTO_REGISTRO):
            normalizados.append(self._validar_campo_texto(valor, etiqueta, maximo))
        (
            codigo_norm,
            nombre_norm,
            marca_norm,
            modelo_norm,
            numero_serie_norm,
        ) = normalizados

        # Fecha de adquisición: obligatoria, válida y no futura.
        fecha_norm = self._validar_fecha_adquisicion(fecha_adquisicion)

        # Estado: por defecto "Operativo"; debe pertenecer al enum.
        if estado is None or (isinstance(estado, str) and not estado.strip()):
            estado_norm = EstadoEquipo.OPERATIVO
        else:
            estado_norm = _normalizar_estado(estado)

        # Departamento: obligatorio y debe existir (integridad referencial).
        if departamento_id is None:
            raise ValueError("El departamento es obligatorio.")
        if self._departamento_repo.obtener_por_id(departamento_id) is None:
            raise ValueError(
                f"El departamento con id {departamento_id} no existe."
            )

        # Unicidad del código de inventario (Requirements 3.2, 10.1).
        if self._repositorio.obtener_por_codigo(codigo_norm) is not None:
            raise ValueError(
                f"El código de inventario '{codigo_norm}' ya existe."
            )

        return self._repositorio.insertar(
            Equipo(
                id=None,
                codigo_inventario=codigo_norm,
                nombre=nombre_norm,
                marca=marca_norm,
                modelo=modelo_norm,
                numero_serie=numero_serie_norm,
                fecha_adquisicion=fecha_norm,
                estado=estado_norm,
                departamento_id=departamento_id,
            )
        )

    # ------------------------------------------------------------------ #
    # Actualización y cambio de estado (Tarea 8.5)                        #
    # ------------------------------------------------------------------ #
    def actualizar(self, equipo_id: int, **campos) -> Equipo:
        """Actualiza los campos indicados de un equipo existente.

        Solo se modifican los campos presentes en ``campos``. Cada campo de
        texto debe tener longitud entre 1 y 255 caracteres y no estar vacío; el
        estado debe pertenecer al conjunto permitido; el ``departamento_id``, si
        se indica, debe referir a un departamento existente. Ante cualquier
        rechazo, los datos previos del equipo se conservan sin modificaciones.

        Args:
            equipo_id: Identificador del equipo a actualizar.
            **campos: Campos a modificar (``codigo_inventario``, ``nombre``,
                ``marca``, ``modelo``, ``numero_serie``, ``fecha_adquisicion``,
                ``estado``, ``departamento_id``).

        Returns:
            El :class:`Equipo` con sus valores actualizados.

        Raises:
            ValueError: Si el equipo no existe, algún campo es inválido, el
                código de inventario resultante colisiona con otro equipo o el
                departamento indicado no existe.
        """
        self._validar_id(equipo_id)
        equipo = self._repositorio.obtener_por_id(equipo_id)
        if equipo is None:
            raise ValueError(f"El equipo con id {equipo_id} no existe.")

        desconocidos = set(campos) - (
            set(_CAMPOS_ACTUALIZABLES_TEXTO) | {"estado", "departamento_id"}
        )
        if desconocidos:
            raise ValueError(
                "Campos no reconocidos para actualizar: "
                f"{', '.join(sorted(desconocidos))}."
            )

        nuevos: dict[str, object] = {}

        # Campos de texto (longitud 1–255, no vacíos).
        for nombre_campo in _CAMPOS_ACTUALIZABLES_TEXTO:
            if nombre_campo in campos:
                etiqueta = nombre_campo.replace("_", " ")
                nuevos[nombre_campo] = self._validar_campo_texto(
                    campos[nombre_campo],
                    etiqueta,
                    _LONGITUD_MAXIMA_ACTUALIZACION,
                )

        # Código de inventario: si cambia, debe seguir siendo único.
        if "codigo_inventario" in nuevos:
            codigo_nuevo = nuevos["codigo_inventario"]
            existente = self._repositorio.obtener_por_codigo(codigo_nuevo)
            if existente is not None and existente.id != equipo_id:
                raise ValueError(
                    f"El código de inventario '{codigo_nuevo}' ya existe."
                )

        # Estado (dentro del conjunto permitido).
        if "estado" in campos:
            nuevos["estado"] = _normalizar_estado(campos["estado"])

        # Departamento (debe existir — integridad referencial).
        if "departamento_id" in campos:
            departamento_id = campos["departamento_id"]
            if departamento_id is None:
                raise ValueError("El departamento es obligatorio.")
            if self._departamento_repo.obtener_por_id(departamento_id) is None:
                raise ValueError(
                    f"El departamento con id {departamento_id} no existe."
                )
            nuevos["departamento_id"] = departamento_id

        equipo_actualizado = Equipo(
            id=equipo.id,
            codigo_inventario=nuevos.get(
                "codigo_inventario", equipo.codigo_inventario
            ),
            nombre=nuevos.get("nombre", equipo.nombre),
            marca=nuevos.get("marca", equipo.marca),
            modelo=nuevos.get("modelo", equipo.modelo),
            numero_serie=nuevos.get("numero_serie", equipo.numero_serie),
            fecha_adquisicion=nuevos.get(
                "fecha_adquisicion", equipo.fecha_adquisicion
            ),
            estado=nuevos.get("estado", equipo.estado),
            departamento_id=nuevos.get("departamento_id", equipo.departamento_id),
        )
        return self._repositorio.actualizar(equipo_actualizado)

    def cambiar_estado(
        self, equipo_id: int, nuevo_estado: EstadoEquipo | str
    ) -> Equipo:
        """Cambia el estado de un equipo existente a un valor válido.

        Args:
            equipo_id: Identificador del equipo.
            nuevo_estado: Nuevo estado (enum o texto del conjunto permitido).

        Returns:
            El :class:`Equipo` con su estado actualizado.

        Raises:
            ValueError: Si el equipo no existe o el estado no pertenece al
                conjunto permitido. El estado anterior se conserva sin cambios.
        """
        self._validar_id(equipo_id)
        equipo = self._repositorio.obtener_por_id(equipo_id)
        if equipo is None:
            raise ValueError(f"El equipo con id {equipo_id} no existe.")

        estado_norm = _normalizar_estado(nuevo_estado)
        equipo.estado = estado_norm
        return self._repositorio.actualizar(equipo)

    # ------------------------------------------------------------------ #
    # Baja preservando historial (Tarea 8.6)                              #
    # ------------------------------------------------------------------ #
    def dar_de_baja(self, equipo_id: int) -> None:
        """Da de baja (elimina) un equipo si no tiene sesiones asociadas.

        Args:
            equipo_id: Identificador del equipo a dar de baja.

        Raises:
            ValueError: Si el identificador es inválido, el equipo no existe o
                el equipo tiene una o más sesiones de uso asociadas (en cuyo
                caso se conserva el equipo y su historial para preservar los
                reportes).
        """
        self._validar_id(equipo_id)

        equipo = self._repositorio.obtener_por_id(equipo_id)
        if equipo is None:
            raise ValueError(f"El equipo con id {equipo_id} no existe.")

        if self._uso_repo.contar_por_equipo(equipo_id) > 0:
            raise ValueError(
                "No se puede dar de baja el equipo porque existen sesiones "
                "históricas asociadas; el equipo y su historial se conservan."
            )

        self._repositorio.eliminar(equipo_id)

    # ------------------------------------------------------------------ #
    # Consultas de apoyo                                                  #
    # ------------------------------------------------------------------ #
    def obtener(self, equipo_id: int) -> Equipo | None:
        """Devuelve el equipo con el ``id`` dado, o ``None`` si no existe."""
        return self._repositorio.obtener_por_id(equipo_id)

    def listar_por_departamento(self, departamento_id: int) -> list[Equipo]:
        """Devuelve los equipos del departamento dado."""
        return self._repositorio.listar_por_departamento(departamento_id)

    def listar_en_mantenimiento(self) -> list[Equipo]:
        """Devuelve los equipos cuyo estado es ``En mantenimiento``."""
        return self._repositorio.listar_por_estado(EstadoEquipo.EN_MANTENIMIENTO)

    # ------------------------------------------------------------------ #
    # Validaciones (privadas)                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_campo_texto(valor: str, etiqueta: str, maximo: int) -> str:
        """Valida obligatoriedad y longitud de un campo de texto.

        Args:
            valor: Valor a validar.
            etiqueta: Nombre legible del campo (para el mensaje de error).
            maximo: Longitud máxima permitida.

        Returns:
            El valor normalizado (sin espacios iniciales ni finales).

        Raises:
            ValueError: Si el valor está vacío o excede la longitud máxima.
        """
        if valor is None or not str(valor).strip():
            raise ValueError(f"El campo '{etiqueta}' es obligatorio.")
        normalizado = str(valor).strip()
        if len(normalizado) > maximo:
            raise ValueError(
                f"El campo '{etiqueta}' excede la longitud máxima permitida de "
                f"{maximo} caracteres."
            )
        return normalizado

    @staticmethod
    def _validar_fecha_adquisicion(fecha_adquisicion: str) -> str:
        """Valida que la fecha de adquisición sea válida y no futura.

        Raises:
            ValueError: Si la fecha está ausente, tiene formato inválido o es
                posterior a la fecha actual.
        """
        if fecha_adquisicion is None or not str(fecha_adquisicion).strip():
            raise ValueError("La fecha de adquisición es obligatoria.")
        fecha_normalizada = str(fecha_adquisicion).strip()
        try:
            fecha = datetime.strptime(fecha_normalizada, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                "La fecha de adquisición es inválida; use el formato YYYY-MM-DD."
            ) from exc
        if fecha > date.today():
            raise ValueError(
                "La fecha de adquisición es inválida; no puede ser posterior a hoy."
            )
        return fecha_normalizada

    @staticmethod
    def _validar_id(equipo_id: int) -> None:
        """Valida que el identificador de equipo sea un entero positivo.

        Raises:
            ValueError: Si el identificador es ``None``, no es entero o no es
                positivo. Se rechazan explícitamente los booleanos.
        """
        if equipo_id is None or isinstance(equipo_id, bool) or not isinstance(
            equipo_id, int
        ):
            raise ValueError("El identificador del equipo no es válido.")
        if equipo_id <= 0:
            raise ValueError("El identificador del equipo no es válido.")
