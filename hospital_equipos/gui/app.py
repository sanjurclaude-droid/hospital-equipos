"""Vista de la interfaz gráfica moderna con CustomTkinter (capa de Presentación).

Construye una interfaz gráfica de escritorio para el Sistema de Gestión de
Equipos Médicos. La vista **no contiene lógica de negocio**: delega todas las
operaciones en :class:`~hospital_equipos.gui.controlador.ControladorApp`, que a
su vez reutiliza la capa de servicios existente. Ante cualquier
:class:`ValueError` de validación, se muestra un diálogo de error amigable y se
conservan los datos introducidos.

Estructura de la interfaz:

- Barra lateral izquierda con navegación entre secciones: Departamentos,
  Pacientes, Equipos, Sesiones de Uso y Reportes.
- Área principal de contenido que intercambia el marco (frame) de la sección
  seleccionada.
- Las tablas se renderizan con :class:`tkinter.ttk.Treeview` embebido en un
  :class:`customtkinter.CTkFrame`, ya que CustomTkinter no incluye una tabla
  nativa.

La ejecución del bucle principal (``mainloop``) requiere un entorno con display;
la construcción de la ventana se realiza en :meth:`AplicacionGUI.__init__`.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from hospital_equipos.gui.controlador import ControladorApp
from hospital_equipos.modelos.equipo import EstadoEquipo
from hospital_equipos.modelos.uso import CriterioUso

# Configuración global de apariencia y tema de color de CustomTkinter.
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Ruta del archivo de base de datos usado por la GUI (compartido con la consola).
_RUTA_BD = "hospital.db"

# Géneros ofrecidos en el formulario de pacientes.
_GENEROS = ("masculino", "femenino", "otro")


class AplicacionGUI(ctk.CTk):
    """Ventana principal de la aplicación gráfica.

    Cablea la vista con un :class:`ControladorApp` (que reutiliza los
    servicios), construye la barra lateral de navegación y el área de contenido,
    y gestiona el intercambio de secciones.
    """

    def __init__(self, controlador: ControladorApp | None = None) -> None:
        """Inicializa la ventana, el controlador y la interfaz.

        Args:
            controlador: Controlador de aplicación a usar. Si es ``None`` se
                crea uno nuevo sobre la base de datos ``hospital.db``.
        """
        super().__init__()

        self._controlador = controlador or ControladorApp(ruta_bd=_RUTA_BD)

        self.title("Sistema de Gestión de Equipos Médicos — Hospital Santo Tomás")
        self.geometry("1100x680")
        self.minsize(900, 560)

        # Layout raíz: columna 0 = barra lateral, columna 1 = contenido.
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_barra_lateral()

        # Contenedor del área principal de contenido.
        self._contenido = ctk.CTkFrame(self, corner_radius=0)
        self._contenido.grid(row=0, column=1, sticky="nsew")
        self._contenido.grid_columnconfigure(0, weight=1)
        self._contenido.grid_rowconfigure(0, weight=1)

        self._frame_actual: ctk.CTkFrame | None = None

        # Sección inicial.
        self.mostrar_departamentos()

    # ------------------------------------------------------------------ #
    # Barra lateral de navegación                                         #
    # ------------------------------------------------------------------ #
    def _construir_barra_lateral(self) -> None:
        """Construye la barra lateral con los botones de navegación."""
        barra = ctk.CTkFrame(self, width=220, corner_radius=0)
        barra.grid(row=0, column=0, sticky="nsew")
        barra.grid_rowconfigure(7, weight=1)

        titulo = ctk.CTkLabel(
            barra,
            text="Equipos Médicos",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        titulo.grid(row=0, column=0, padx=20, pady=(24, 4))

        subtitulo = ctk.CTkLabel(
            barra,
            text="Hospital Santo Tomás",
            font=ctk.CTkFont(size=12),
        )
        subtitulo.grid(row=1, column=0, padx=20, pady=(0, 20))

        secciones = [
            ("Departamentos", self.mostrar_departamentos),
            ("Pacientes", self.mostrar_pacientes),
            ("Equipos", self.mostrar_equipos),
            ("Sesiones de Uso", self.mostrar_sesiones),
            ("Reportes", self.mostrar_reportes),
        ]
        for indice, (etiqueta, comando) in enumerate(secciones, start=2):
            boton = ctk.CTkButton(barra, text=etiqueta, command=comando)
            boton.grid(row=indice, column=0, padx=20, pady=8, sticky="ew")

        # Selector de apariencia en la parte inferior.
        selector = ctk.CTkOptionMenu(
            barra,
            values=["System", "Light", "Dark"],
            command=self._cambiar_apariencia,
        )
        selector.grid(row=8, column=0, padx=20, pady=20, sticky="s")
        selector.set("System")

    @staticmethod
    def _cambiar_apariencia(modo: str) -> None:
        """Cambia el modo de apariencia global de la interfaz."""
        ctk.set_appearance_mode(modo)

    # ------------------------------------------------------------------ #
    # Utilidades de UI                                                    #
    # ------------------------------------------------------------------ #
    def _limpiar_contenido(self) -> ctk.CTkFrame:
        """Destruye el marco actual y devuelve uno nuevo limpio."""
        if self._frame_actual is not None:
            self._frame_actual.destroy()
        marco = ctk.CTkFrame(self._contenido, corner_radius=0)
        marco.grid(row=0, column=0, sticky="nsew")
        marco.grid_columnconfigure(0, weight=1)
        self._frame_actual = marco
        return marco

    @staticmethod
    def _crear_tabla(padre: tk.Widget, columnas: list[str]) -> ttk.Treeview:
        """Crea una tabla (Treeview) con barra de desplazamiento vertical.

        Args:
            padre: Widget contenedor.
            columnas: Nombres de las columnas de la tabla.

        Returns:
            El :class:`ttk.Treeview` configurado.
        """
        contenedor = ctk.CTkFrame(padre)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        tabla = ttk.Treeview(
            contenedor, columns=columnas, show="headings", height=12
        )
        for columna in columnas:
            tabla.heading(columna, text=columna)
            tabla.column(columna, width=140, anchor="w")

        scroll = ttk.Scrollbar(
            contenedor, orient="vertical", command=tabla.yview
        )
        tabla.configure(yscrollcommand=scroll.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        # Estilo mínimo del Treeview para integrarlo con el tema.
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Treeview", rowheight=26, font=("", 11))
        estilo.configure("Treeview.Heading", font=("", 11, "bold"))

        contenedor.tabla = tabla  # type: ignore[attr-defined]
        return contenedor

    @staticmethod
    def _rellenar_tabla(contenedor: ctk.CTkFrame, filas: list[tuple]) -> None:
        """Vacía y rellena una tabla con las filas indicadas."""
        tabla: ttk.Treeview = contenedor.tabla  # type: ignore[attr-defined]
        for item in tabla.get_children():
            tabla.delete(item)
        for fila in filas:
            tabla.insert("", "end", values=fila)

    def _error(self, mensaje: str) -> None:
        """Muestra un diálogo de error amigable."""
        messagebox.showerror("Operación no válida", mensaje)

    def _info(self, mensaje: str) -> None:
        """Muestra un diálogo informativo."""
        messagebox.showinfo("Operación completada", mensaje)

    def _titulo_seccion(self, marco: ctk.CTkFrame, texto: str) -> None:
        """Añade un título de sección en la parte superior del marco."""
        etiqueta = ctk.CTkLabel(
            marco, text=texto, font=ctk.CTkFont(size=22, weight="bold")
        )
        etiqueta.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

    def _opciones_departamentos(self) -> dict[str, int]:
        """Devuelve un mapa "id - nombre" -> id de los departamentos."""
        opciones: dict[str, int] = {}
        for dep in self._controlador.listar_departamentos():
            opciones[f"{dep.id} - {dep.nombre}"] = dep.id
        return opciones

    # ------------------------------------------------------------------ #
    # Sección: Departamentos                                              #
    # ------------------------------------------------------------------ #
    def mostrar_departamentos(self) -> None:
        """Muestra la sección de gestión de departamentos."""
        marco = self._limpiar_contenido()
        self._titulo_seccion(marco, "Departamentos")
        marco.grid_rowconfigure(2, weight=1)

        # Formulario de registro.
        formulario = ctk.CTkFrame(marco)
        formulario.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        formulario.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(formulario, text="Nombre:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_nombre = ctk.CTkEntry(formulario, placeholder_text="Nombre")
        entrada_nombre.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Descripción:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_desc = ctk.CTkEntry(formulario, placeholder_text="Descripción")
        entrada_desc.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        tabla = self._crear_tabla(marco, ["ID", "Nombre", "Descripción"])
        tabla.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        def refrescar() -> None:
            filas = [
                (dep.id, dep.nombre, dep.descripcion)
                for dep in self._controlador.listar_departamentos()
            ]
            self._rellenar_tabla(tabla, filas)

        def registrar() -> None:
            try:
                self._controlador.registrar_departamento(
                    entrada_nombre.get(), entrada_desc.get()
                )
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Departamento registrado correctamente.")
            entrada_nombre.delete(0, "end")
            entrada_desc.delete(0, "end")
            refrescar()

        ctk.CTkButton(formulario, text="Registrar", command=registrar).grid(
            row=2, column=1, padx=10, pady=(8, 12), sticky="e"
        )
        refrescar()

    # ------------------------------------------------------------------ #
    # Sección: Pacientes                                                  #
    # ------------------------------------------------------------------ #
    def mostrar_pacientes(self) -> None:
        """Muestra la sección de gestión de pacientes."""
        marco = self._limpiar_contenido()
        self._titulo_seccion(marco, "Pacientes")
        marco.grid_rowconfigure(2, weight=1)

        formulario = ctk.CTkFrame(marco)
        formulario.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        formulario.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(formulario, text="Cédula:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_cedula = ctk.CTkEntry(formulario, placeholder_text="Cédula")
        entrada_cedula.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Nombre:").grid(
            row=0, column=2, padx=10, pady=8, sticky="w"
        )
        entrada_nombre = ctk.CTkEntry(formulario, placeholder_text="Nombre")
        entrada_nombre.grid(row=0, column=3, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Fecha nac. (YYYY-MM-DD):").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_fecha = ctk.CTkEntry(formulario, placeholder_text="1990-05-10")
        entrada_fecha.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Género:").grid(
            row=1, column=2, padx=10, pady=8, sticky="w"
        )
        combo_genero = ctk.CTkComboBox(formulario, values=list(_GENEROS))
        combo_genero.grid(row=1, column=3, padx=10, pady=8, sticky="ew")
        combo_genero.set("masculino")

        ctk.CTkLabel(formulario, text="Teléfono:").grid(
            row=2, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_telefono = ctk.CTkEntry(formulario, placeholder_text="60012345")
        entrada_telefono.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        tabla = self._crear_tabla(
            marco,
            ["ID", "Cédula", "Nombre", "Fecha nac.", "Género", "Teléfono"],
        )
        tabla.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        def refrescar() -> None:
            filas = [
                (
                    p.id,
                    p.cedula,
                    p.nombre,
                    p.fecha_nacimiento,
                    p.genero,
                    p.telefono,
                )
                for p in self._controlador.listar_pacientes()
            ]
            self._rellenar_tabla(tabla, filas)

        def registrar() -> None:
            try:
                self._controlador.registrar_paciente(
                    cedula=entrada_cedula.get(),
                    nombre=entrada_nombre.get(),
                    fecha_nacimiento=entrada_fecha.get(),
                    genero=combo_genero.get(),
                    telefono=entrada_telefono.get(),
                )
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Paciente registrado correctamente.")
            for entrada in (
                entrada_cedula,
                entrada_nombre,
                entrada_fecha,
                entrada_telefono,
            ):
                entrada.delete(0, "end")
            refrescar()

        ctk.CTkButton(formulario, text="Registrar", command=registrar).grid(
            row=2, column=3, padx=10, pady=(8, 12), sticky="e"
        )
        refrescar()

    # ------------------------------------------------------------------ #
    # Sección: Equipos                                                    #
    # ------------------------------------------------------------------ #
    def mostrar_equipos(self) -> None:
        """Muestra la sección de gestión del inventario de equipos."""
        marco = self._limpiar_contenido()
        self._titulo_seccion(marco, "Equipos")
        marco.grid_rowconfigure(3, weight=1)

        opciones_dep = self._opciones_departamentos()
        valores_dep = list(opciones_dep.keys())

        # Selector de departamento para filtrar el listado.
        barra_sel = ctk.CTkFrame(marco)
        barra_sel.grid(row=1, column=0, padx=20, pady=(4, 8), sticky="ew")
        ctk.CTkLabel(barra_sel, text="Departamento:").grid(
            row=0, column=0, padx=10, pady=8
        )
        combo_dep = ctk.CTkComboBox(barra_sel, values=valores_dep, width=340)
        combo_dep.grid(row=0, column=1, padx=10, pady=8)
        if valores_dep:
            combo_dep.set(valores_dep[0])

        tabla = self._crear_tabla(
            marco,
            [
                "ID",
                "Código",
                "Nombre",
                "Marca",
                "Modelo",
                "N.º serie",
                "Fecha adq.",
                "Estado",
            ],
        )
        tabla.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        def dep_seleccionado() -> int | None:
            return opciones_dep.get(combo_dep.get())

        def refrescar() -> None:
            dep_id = dep_seleccionado()
            if dep_id is None:
                self._rellenar_tabla(tabla, [])
                return
            filas = [
                (
                    e.id,
                    e.codigo_inventario,
                    e.nombre,
                    e.marca,
                    e.modelo,
                    e.numero_serie,
                    e.fecha_adquisicion,
                    e.estado.value,
                )
                for e in self._controlador.listar_equipos_por_departamento(
                    dep_id
                )
            ]
            self._rellenar_tabla(tabla, filas)

        ctk.CTkButton(barra_sel, text="Actualizar lista", command=refrescar).grid(
            row=0, column=2, padx=10, pady=8
        )

        # Formulario de alta de equipos.
        formulario = ctk.CTkFrame(marco)
        formulario.grid(row=2, column=0, padx=20, pady=8, sticky="ew")
        for col in (1, 3):
            formulario.grid_columnconfigure(col, weight=1)

        campos: dict[str, ctk.CTkEntry] = {}
        etiquetas = [
            ("codigo_inventario", "Código:"),
            ("nombre", "Nombre:"),
            ("marca", "Marca:"),
            ("modelo", "Modelo:"),
            ("numero_serie", "N.º serie:"),
            ("fecha_adquisicion", "Fecha adq. (YYYY-MM-DD):"),
        ]
        for indice, (clave, etiqueta) in enumerate(etiquetas):
            fila, col = divmod(indice, 2)
            ctk.CTkLabel(formulario, text=etiqueta).grid(
                row=fila, column=col * 2, padx=10, pady=6, sticky="w"
            )
            entrada = ctk.CTkEntry(formulario)
            entrada.grid(
                row=fila, column=col * 2 + 1, padx=10, pady=6, sticky="ew"
            )
            campos[clave] = entrada

        ctk.CTkLabel(formulario, text="Estado:").grid(
            row=3, column=0, padx=10, pady=6, sticky="w"
        )
        combo_estado = ctk.CTkComboBox(
            formulario, values=[e.value for e in EstadoEquipo]
        )
        combo_estado.grid(row=3, column=1, padx=10, pady=6, sticky="ew")
        combo_estado.set(EstadoEquipo.OPERATIVO.value)

        def registrar() -> None:
            dep_id = dep_seleccionado()
            if dep_id is None:
                self._error("Seleccione un departamento válido.")
                return
            try:
                self._controlador.registrar_equipo(
                    codigo_inventario=campos["codigo_inventario"].get(),
                    nombre=campos["nombre"].get(),
                    marca=campos["marca"].get(),
                    modelo=campos["modelo"].get(),
                    numero_serie=campos["numero_serie"].get(),
                    fecha_adquisicion=campos["fecha_adquisicion"].get(),
                    estado=combo_estado.get(),
                    departamento_id=dep_id,
                )
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Equipo registrado correctamente.")
            for entrada in campos.values():
                entrada.delete(0, "end")
            refrescar()

        # Acciones sobre un equipo seleccionado (por ID de la tabla).
        acciones = ctk.CTkFrame(formulario)
        acciones.grid(
            row=4, column=0, columnspan=4, padx=6, pady=(10, 6), sticky="ew"
        )
        ctk.CTkLabel(acciones, text="ID equipo:").grid(
            row=0, column=0, padx=8, pady=6
        )
        entrada_id = ctk.CTkEntry(acciones, width=80)
        entrada_id.grid(row=0, column=1, padx=8, pady=6)

        combo_nuevo_estado = ctk.CTkComboBox(
            acciones, values=[e.value for e in EstadoEquipo], width=170
        )
        combo_nuevo_estado.grid(row=0, column=2, padx=8, pady=6)
        combo_nuevo_estado.set(EstadoEquipo.EN_MANTENIMIENTO.value)

        def _leer_id() -> int | None:
            try:
                return int(entrada_id.get().strip())
            except (ValueError, TypeError):
                self._error("El ID del equipo debe ser un número entero.")
                return None

        def cambiar_estado() -> None:
            equipo_id = _leer_id()
            if equipo_id is None:
                return
            try:
                self._controlador.cambiar_estado_equipo(
                    equipo_id, combo_nuevo_estado.get()
                )
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Estado actualizado correctamente.")
            refrescar()

        def dar_de_baja() -> None:
            equipo_id = _leer_id()
            if equipo_id is None:
                return
            try:
                self._controlador.dar_de_baja_equipo(equipo_id)
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Equipo dado de baja correctamente.")
            refrescar()

        def actualizar() -> None:
            equipo_id = _leer_id()
            if equipo_id is None:
                return
            cambios = {
                clave: entrada.get().strip()
                for clave, entrada in campos.items()
                if entrada.get().strip()
            }
            if not cambios:
                self._error("Indique al menos un campo para actualizar.")
                return
            try:
                self._controlador.actualizar_equipo(equipo_id, **cambios)
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Equipo actualizado correctamente.")
            refrescar()

        ctk.CTkButton(formulario, text="Registrar", command=registrar).grid(
            row=3, column=3, padx=10, pady=6, sticky="e"
        )
        ctk.CTkButton(acciones, text="Cambiar estado", command=cambiar_estado).grid(
            row=0, column=3, padx=8, pady=6
        )
        ctk.CTkButton(acciones, text="Actualizar", command=actualizar).grid(
            row=0, column=4, padx=8, pady=6
        )
        ctk.CTkButton(acciones, text="Dar de baja", command=dar_de_baja).grid(
            row=0, column=5, padx=8, pady=6
        )

        combo_dep.configure(command=lambda _valor: refrescar())
        refrescar()

    # ------------------------------------------------------------------ #
    # Sección: Sesiones de Uso                                            #
    # ------------------------------------------------------------------ #
    def mostrar_sesiones(self) -> None:
        """Muestra la sección de registro y consulta de sesiones de uso."""
        marco = self._limpiar_contenido()
        self._titulo_seccion(marco, "Sesiones de Uso")
        marco.grid_rowconfigure(3, weight=1)

        formulario = ctk.CTkFrame(marco)
        formulario.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        formulario.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(formulario, text="ID equipo:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_equipo = ctk.CTkEntry(formulario)
        entrada_equipo.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="ID paciente:").grid(
            row=0, column=2, padx=10, pady=8, sticky="w"
        )
        entrada_paciente = ctk.CTkEntry(formulario)
        entrada_paciente.grid(row=0, column=3, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Inicio (YYYY-MM-DD HH:MM):").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        entrada_inicio = ctk.CTkEntry(
            formulario, placeholder_text="2023-01-01 08:00"
        )
        entrada_inicio.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(formulario, text="Duración (min):").grid(
            row=1, column=2, padx=10, pady=8, sticky="w"
        )
        entrada_duracion = ctk.CTkEntry(formulario, placeholder_text="30")
        entrada_duracion.grid(row=1, column=3, padx=10, pady=8, sticky="ew")

        # Barra de consulta de sesiones por equipo.
        barra = ctk.CTkFrame(marco)
        barra.grid(row=2, column=0, padx=20, pady=(4, 8), sticky="ew")
        ctk.CTkLabel(barra, text="Listar sesiones del equipo ID:").grid(
            row=0, column=0, padx=10, pady=8
        )
        entrada_listar = ctk.CTkEntry(barra, width=100)
        entrada_listar.grid(row=0, column=1, padx=10, pady=8)

        tabla = self._crear_tabla(
            marco,
            ["ID", "Equipo", "Paciente", "Inicio", "Duración (min)"],
        )
        tabla.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        def _entero(valor: str, etiqueta: str) -> int:
            try:
                return int(valor.strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"El campo {etiqueta} debe ser un número entero."
                ) from exc

        def listar() -> None:
            try:
                equipo_id = _entero(entrada_listar.get(), "ID equipo")
            except ValueError as error:
                self._error(str(error))
                return
            try:
                sesiones = self._controlador.listar_sesiones_por_equipo(
                    equipo_id
                )
            except ValueError as error:
                self._error(str(error))
                return
            filas = [
                (
                    s.id,
                    s.equipo_id,
                    s.paciente_id,
                    s.fecha_inicio,
                    s.duracion_minutos,
                )
                for s in sesiones
            ]
            self._rellenar_tabla(tabla, filas)

        def registrar() -> None:
            try:
                equipo_id = _entero(entrada_equipo.get(), "ID equipo")
                paciente_id = _entero(entrada_paciente.get(), "ID paciente")
                duracion = _entero(entrada_duracion.get(), "duración")
                self._controlador.registrar_uso(
                    equipo_id,
                    paciente_id,
                    entrada_inicio.get(),
                    duracion,
                )
            except ValueError as error:
                self._error(str(error))
                return
            self._info("Sesión de uso registrada correctamente.")
            entrada_inicio.delete(0, "end")
            entrada_duracion.delete(0, "end")
            entrada_listar.delete(0, "end")
            entrada_listar.insert(0, str(equipo_id))
            listar()

        ctk.CTkButton(formulario, text="Registrar sesión", command=registrar).grid(
            row=2, column=3, padx=10, pady=(8, 12), sticky="e"
        )
        ctk.CTkButton(barra, text="Listar", command=listar).grid(
            row=0, column=2, padx=10, pady=8
        )

    # ------------------------------------------------------------------ #
    # Sección: Reportes                                                   #
    # ------------------------------------------------------------------ #
    def mostrar_reportes(self) -> None:
        """Muestra la sección de reportes y consultas avanzadas."""
        marco = self._limpiar_contenido()
        self._titulo_seccion(marco, "Reportes")
        marco.grid_rowconfigure(3, weight=1)

        opciones_dep = self._opciones_departamentos()
        valores_dep = list(opciones_dep.keys())
        valores_dep_opcional = ["(Todos)"] + valores_dep

        controles = ctk.CTkFrame(marco)
        controles.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(controles, text="Departamento:").grid(
            row=0, column=0, padx=10, pady=8
        )
        combo_dep = ctk.CTkComboBox(controles, values=valores_dep, width=320)
        combo_dep.grid(row=0, column=1, padx=10, pady=8)
        if valores_dep:
            combo_dep.set(valores_dep[0])

        tabla = self._crear_tabla(marco, ["Col1", "Col2", "Col3", "Col4"])
        tabla.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        def _reconfigurar_columnas(columnas: list[str]) -> None:
            arbol: ttk.Treeview = tabla.tabla  # type: ignore[attr-defined]
            arbol.configure(columns=columnas)
            for columna in columnas:
                arbol.heading(columna, text=columna)
                arbol.column(columna, width=180, anchor="w")

        def dep_seleccionado() -> int | None:
            return opciones_dep.get(combo_dep.get())

        def inventario() -> None:
            dep_id = dep_seleccionado()
            if dep_id is None:
                self._error("Seleccione un departamento válido.")
                return
            try:
                equipos = self._controlador.inventario_por_departamento(dep_id)
            except ValueError as error:
                self._error(str(error))
                return
            _reconfigurar_columnas(["ID", "Código", "Nombre", "Estado"])
            filas = [
                (e.id, e.codigo_inventario, e.nombre, e.estado.value)
                for e in equipos
            ]
            self._rellenar_tabla(tabla, filas)

        def mantenimiento() -> None:
            equipos = self._controlador.alerta_mantenimiento()
            _reconfigurar_columnas(["ID", "Código", "Nombre", "Departamento"])
            filas = [
                (e.id, e.codigo_inventario, e.nombre, e.departamento_id)
                for e in equipos
            ]
            self._rellenar_tabla(tabla, filas)

        # Indicador de Uso Clínico (requisito crítico).
        ctk.CTkLabel(controles, text="Criterio:").grid(
            row=1, column=0, padx=10, pady=8
        )
        combo_criterio = ctk.CTkComboBox(
            controles, values=[c.value for c in CriterioUso]
        )
        combo_criterio.grid(row=1, column=1, padx=10, pady=8, sticky="w")
        combo_criterio.set(CriterioUso.SESIONES.value)

        combo_dep_ind = ctk.CTkComboBox(
            controles, values=valores_dep_opcional, width=320
        )
        combo_dep_ind.grid(row=1, column=2, padx=10, pady=8)
        combo_dep_ind.set("(Todos)")

        def indicador() -> None:
            seleccion = combo_dep_ind.get()
            dep_id = None if seleccion == "(Todos)" else opciones_dep.get(seleccion)
            try:
                metricas = self._controlador.indicador_uso_clinico(
                    combo_criterio.get(), dep_id
                )
            except ValueError as error:
                self._error(str(error))
                return
            _reconfigurar_columnas(
                ["Equipo", "Departamento", "Total", "Criterio"]
            )
            filas = [
                (m.equipo_nombre, m.departamento_nombre, m.total_uso, m.criterio.value)
                for m in metricas
            ]
            self._rellenar_tabla(tabla, filas)
            if not filas:
                self._info(
                    "No hay equipos con sesiones en el alcance solicitado."
                )

        botones = ctk.CTkFrame(marco)
        botones.grid(row=2, column=0, padx=20, pady=8, sticky="ew")
        ctk.CTkButton(
            botones, text="Inventario por departamento", command=inventario
        ).grid(row=0, column=0, padx=8, pady=8)
        ctk.CTkButton(
            botones, text="Alerta de mantenimiento", command=mantenimiento
        ).grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkButton(
            botones, text="Indicador de Uso Clínico", command=indicador
        ).grid(row=0, column=2, padx=8, pady=8)


def crear_app() -> AplicacionGUI:
    """Crea y devuelve una instancia de :class:`AplicacionGUI`.

    Se aísla la creación para facilitar su uso desde el punto de entrada
    (:mod:`hospital_equipos.gui.__main__`).
    """
    return AplicacionGUI()
