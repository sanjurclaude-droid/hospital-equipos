"""Servicio de dominio para la gestión de departamentos.

Aplica las reglas de negocio del registro y consulta de departamentos
(validación de longitud, obligatoriedad y unicidad case-insensitive del
nombre) y coordina la precarga de los 12 departamentos base del hospital,
delegando el acceso a datos en :class:`DepartamentoRepository`.

Ante cualquier dato inválido, el servicio lanza :class:`ValueError` con un
mensaje claro en español y conserva sin cambios el conjunto actual de
departamentos (no se realiza ninguna escritura).

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 10.3
"""

from __future__ import annotations

from hospital_equipos.modelos.departamento import Departamento
from hospital_equipos.repositorios.departamento_repo import (
    DepartamentoRepository,
)

# Longitud máxima permitida para el nombre de un departamento.
_LONGITUD_MAXIMA_NOMBRE = 100

# Los 12 departamentos base del Hospital Santo Tomás. El primero es el
# Laboratorio Clínico y Banco de Sangre descrito en el diseño; los restantes
# son unidades organizativas hospitalarias habituales.
DEPARTAMENTOS_BASE: list[tuple[str, str]] = [
    (
        "Laboratorio Clínico y Banco de Sangre",
        "Área analítica de alta rotación donde se procesan muestras biológicas "
        "para tamizaje, diagnóstico y seguimiento patológico.",
    ),
    ("Urgencias", "Atención inmediata de pacientes en estado crítico o agudo."),
    (
        "Radiología e Imágenes Diagnósticas",
        "Estudios de imagen: rayos X, tomografía, resonancia y ecografía.",
    ),
    (
        "Cuidados Intensivos",
        "Monitorización y soporte vital de pacientes en estado crítico.",
    ),
    ("Quirófano y Cirugía", "Intervenciones quirúrgicas programadas y de urgencia."),
    ("Cardiología", "Diagnóstico y tratamiento de enfermedades cardiovasculares."),
    ("Pediatría", "Atención médica integral de recién nacidos, niños y adolescentes."),
    ("Ginecología y Obstetricia", "Salud de la mujer, embarazo y parto."),
    ("Oncología", "Diagnóstico y tratamiento de enfermedades oncológicas."),
    ("Neurología", "Atención de trastornos del sistema nervioso."),
    ("Rehabilitación y Fisioterapia", "Recuperación funcional y terapia física."),
    ("Farmacia Hospitalaria", "Dispensación y control de medicamentos e insumos."),
]

assert len(DEPARTAMENTOS_BASE) == 12, "Deben definirse exactamente 12 departamentos base"


class DepartamentoService:
    """Lógica de negocio para el registro y consulta de departamentos."""

    def __init__(self, repositorio: DepartamentoRepository) -> None:
        self._repositorio = repositorio

    def registrar(self, nombre: str, descripcion: str = "") -> Departamento:
        """Registra un departamento tras validar su nombre.

        El nombre se normaliza eliminando los espacios iniciales y finales. Debe
        contener entre 1 y 100 caracteres y no coincidir (sin distinguir
        mayúsculas/minúsculas) con el de ningún departamento existente.

        Args:
            nombre: Nombre del departamento a registrar.
            descripcion: Descripción opcional del departamento.

        Returns:
            El :class:`Departamento` creado con su identificador asignado.

        Raises:
            ValueError: Si el nombre está vacío, excede los 100 caracteres o ya
                existe. En todos los casos no se realiza ninguna escritura.
        """
        if nombre is None:
            raise ValueError("El nombre del departamento es obligatorio.")

        nombre_normalizado = nombre.strip()

        if not nombre_normalizado:
            raise ValueError("El nombre del departamento es obligatorio.")

        if len(nombre_normalizado) > _LONGITUD_MAXIMA_NOMBRE:
            raise ValueError(
                "El nombre del departamento excede la longitud máxima permitida "
                f"de {_LONGITUD_MAXIMA_NOMBRE} caracteres."
            )

        if self._repositorio.obtener_por_nombre(nombre_normalizado) is not None:
            raise ValueError(
                f"Ya existe un departamento con el nombre '{nombre_normalizado}'."
            )

        descripcion_normalizada = descripcion.strip() if descripcion else ""
        return self._repositorio.insertar(
            Departamento(
                id=None,
                nombre=nombre_normalizado,
                descripcion=descripcion_normalizada,
            )
        )

    def listar(self) -> list[Departamento]:
        """Devuelve todos los departamentos registrados (lista vacía si no hay)."""
        return self._repositorio.listar()

    def obtener(self, departamento_id: int) -> Departamento | None:
        """Devuelve el departamento con el ``id`` dado, o ``None`` si no existe."""
        return self._repositorio.obtener_por_id(departamento_id)

    def inicializar_departamentos_base(self) -> str:
        """Precarga los 12 departamentos base solo si la tabla está vacía.

        Si ya existe al menos un departamento, se omite la precarga y se
        conserva sin cambios el conjunto actual.

        Returns:
            Un mensaje indicando si la precarga se realizó o se omitió.
        """
        if self._repositorio.listar():
            return (
                "La inicialización no es aplicable: ya existen departamentos "
                "registrados; la precarga fue omitida."
            )

        for nombre, descripcion in DEPARTAMENTOS_BASE:
            self._repositorio.insertar(
                Departamento(id=None, nombre=nombre, descripcion=descripcion)
            )

        return f"Se precargaron {len(DEPARTAMENTOS_BASE)} departamentos base."
