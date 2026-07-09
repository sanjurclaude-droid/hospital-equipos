"""Servicio de dominio para la gestión de pacientes.

Aplica las reglas de negocio del registro y consulta de pacientes: validación
de cédula (1–20 caracteres alfanuméricos, única), nombre (1–100 caracteres),
fecha de nacimiento (fecha válida no posterior a la fecha actual), género
(dentro del conjunto {masculino, femenino, otro}) y teléfono (7–15 dígitos).
Delega el acceso a datos en :class:`PacienteRepository`.

Ante cualquier dato inválido, el servicio lanza :class:`ValueError` con un
mensaje claro en español que identifica el campo rechazado y conserva sin
cambios el estado actual de los pacientes (no se realiza ninguna escritura).

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 10.2
"""

from __future__ import annotations

from datetime import date, datetime

from hospital_equipos.modelos.paciente import Paciente
from hospital_equipos.repositorios.paciente_repo import PacienteRepository

_LONGITUD_MAXIMA_CEDULA = 20
_LONGITUD_MAXIMA_NOMBRE = 100
_TELEFONO_MIN_DIGITOS = 7
_TELEFONO_MAX_DIGITOS = 15

# Géneros válidos aceptados por el sistema (comparación en minúsculas).
GENEROS_VALIDOS = ("masculino", "femenino", "otro")


class PacienteService:
    """Lógica de negocio para el registro y consulta de pacientes."""

    def __init__(self, repositorio: PacienteRepository) -> None:
        self._repositorio = repositorio

    def registrar(
        self,
        cedula: str,
        nombre: str,
        fecha_nacimiento: str,
        genero: str,
        telefono: str,
    ) -> Paciente:
        """Registra un paciente tras validar todos sus campos.

        Args:
            cedula: Identificación alfanumérica de 1 a 20 caracteres, única.
            nombre: Nombre del paciente, de 1 a 100 caracteres.
            fecha_nacimiento: Fecha en formato ``YYYY-MM-DD``, no futura.
            genero: Uno de ``masculino``, ``femenino`` u ``otro``.
            telefono: Cadena de solo dígitos, de 7 a 15 caracteres.

        Returns:
            El :class:`Paciente` creado con su identificador asignado.

        Raises:
            ValueError: Si algún campo es inválido o la cédula ya existe. En
                todos los casos no se realiza ninguna escritura.
        """
        cedula_normalizada = self._validar_cedula(cedula)
        nombre_normalizado = self._validar_nombre(nombre)
        fecha_normalizada = self._validar_fecha_nacimiento(fecha_nacimiento)
        genero_normalizado = self._validar_genero(genero)
        telefono_normalizado = self._validar_telefono(telefono)

        # Unicidad de la cédula (Requirements 2.2, 10.2).
        if self._repositorio.obtener_por_cedula(cedula_normalizada) is not None:
            raise ValueError(
                f"Ya existe un paciente con la cédula '{cedula_normalizada}'."
            )

        return self._repositorio.insertar(
            Paciente(
                id=None,
                cedula=cedula_normalizada,
                nombre=nombre_normalizado,
                fecha_nacimiento=fecha_normalizada,
                genero=genero_normalizado,
                telefono=telefono_normalizado,
            )
        )

    def listar(self) -> list[Paciente]:
        """Devuelve todos los pacientes ordenados por nombre ascendente."""
        return self._repositorio.listar()

    def obtener(self, paciente_id: int) -> Paciente | None:
        """Devuelve el paciente con el ``id`` dado, o ``None`` si no existe."""
        return self._repositorio.obtener_por_id(paciente_id)

    def obtener_por_cedula(self, cedula: str) -> Paciente | None:
        """Devuelve el paciente con la cédula dada, o ``None`` si no existe."""
        if cedula is None:
            return None
        return self._repositorio.obtener_por_cedula(cedula.strip())

    # ------------------------------------------------------------------ #
    # Validaciones de campo (privadas)                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_cedula(cedula: str) -> str:
        if cedula is None or not cedula.strip():
            raise ValueError("La cédula es obligatoria.")
        cedula_normalizada = cedula.strip()
        if len(cedula_normalizada) > _LONGITUD_MAXIMA_CEDULA:
            raise ValueError(
                "La cédula excede la longitud máxima permitida de "
                f"{_LONGITUD_MAXIMA_CEDULA} caracteres."
            )
        if not cedula_normalizada.isalnum():
            raise ValueError("La cédula debe contener solo caracteres alfanuméricos.")
        return cedula_normalizada

    @staticmethod
    def _validar_nombre(nombre: str) -> str:
        if nombre is None or not nombre.strip():
            raise ValueError("El nombre del paciente es obligatorio.")
        nombre_normalizado = nombre.strip()
        if len(nombre_normalizado) > _LONGITUD_MAXIMA_NOMBRE:
            raise ValueError(
                "El nombre del paciente excede la longitud máxima permitida de "
                f"{_LONGITUD_MAXIMA_NOMBRE} caracteres."
            )
        return nombre_normalizado

    @staticmethod
    def _validar_fecha_nacimiento(fecha_nacimiento: str) -> str:
        if fecha_nacimiento is None or not fecha_nacimiento.strip():
            raise ValueError("La fecha de nacimiento es obligatoria.")
        fecha_normalizada = fecha_nacimiento.strip()
        try:
            fecha = datetime.strptime(fecha_normalizada, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                "La fecha de nacimiento es inválida; use el formato YYYY-MM-DD."
            ) from exc
        if fecha > date.today():
            raise ValueError(
                "La fecha de nacimiento es inválida; no puede ser posterior a hoy."
            )
        return fecha_normalizada

    @staticmethod
    def _validar_genero(genero: str) -> str:
        if genero is None or not genero.strip():
            raise ValueError("El género es obligatorio.")
        genero_normalizado = genero.strip().lower()
        if genero_normalizado not in GENEROS_VALIDOS:
            raise ValueError(
                "El género es inválido; debe ser uno de: "
                f"{', '.join(GENEROS_VALIDOS)}."
            )
        return genero_normalizado

    @staticmethod
    def _validar_telefono(telefono: str) -> str:
        if telefono is None or not telefono.strip():
            raise ValueError("El teléfono es obligatorio.")
        telefono_normalizado = telefono.strip()
        if not telefono_normalizado.isdigit():
            raise ValueError("El teléfono debe contener solo dígitos.")
        if not (
            _TELEFONO_MIN_DIGITOS
            <= len(telefono_normalizado)
            <= _TELEFONO_MAX_DIGITOS
        ):
            raise ValueError(
                "El teléfono es inválido; debe tener entre "
                f"{_TELEFONO_MIN_DIGITOS} y {_TELEFONO_MAX_DIGITOS} dígitos."
            )
        return telefono_normalizado
