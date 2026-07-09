"""Punto de entrada de la interfaz gráfica.

Permite ejecutar la GUI con:

    python -m hospital_equipos.gui

Crea la ventana principal (:class:`~hospital_equipos.gui.app.AplicacionGUI`),
que a su vez construye el controlador, inicializa la base de datos ``hospital.db``
y precarga los departamentos base, e inicia el bucle principal de la interfaz.

La aplicación de consola (``python -m hospital_equipos.main``) sigue funcionando
sin cambios; esta GUI es una capa de presentación adicional que reutiliza los
mismos servicios.
"""

from __future__ import annotations


def main() -> None:
    """Crea la aplicación gráfica e inicia su bucle principal."""
    # La importación se realiza dentro de la función para que este módulo no
    # dependa de un display en el momento de importarse (p. ej. al inspeccionar
    # el paquete en entornos sin entorno gráfico).
    from hospital_equipos.gui.app import crear_app

    app = crear_app()
    app.mainloop()


if __name__ == "__main__":
    main()
