"""Paquete de la interfaz gráfica de usuario (GUI) con CustomTkinter.

Este paquete añade una interfaz gráfica moderna al Sistema de Gestión de
Equipos Médicos **reutilizando** por completo la capa de servicios existente,
sin modificar la lógica de negocio, los repositorios, la base de datos ni la
aplicación de consola.

Contiene dos piezas principales:

- :mod:`hospital_equipos.gui.controlador`: un controlador de aplicación
  (:class:`~hospital_equipos.gui.controlador.ControladorApp`) **sin ninguna
  dependencia de Tkinter**, que cablea repositorios y servicios y expone
  métodos sencillos que la vista invoca. Al no depender de un display, es
  completamente testeable de forma unitaria.
- :mod:`hospital_equipos.gui.app`: la vista construida con CustomTkinter
  (:class:`~hospital_equipos.gui.app.AplicacionGUI`).

Se ejecuta con ``python -m hospital_equipos.gui``.
"""
