# Requirements Document

## Introduction

El **Sistema de Gestión de Equipos Médicos del Hospital Santo Tomás** es una aplicación local desarrollada en Python con persistencia en una base de datos relacional SQLite. Su propósito es controlar el inventario de equipos médicos, registrar los departamentos del hospital y los pacientes atendidos, controlar las sesiones de uso de cada equipo por parte de los pacientes y producir consultas avanzadas y reportes de métricas.

El requisito crítico del sistema es el **Indicador de Uso Clínico**, un reporte que analiza el historial de sesiones para determinar el equipo médico más utilizado, calculado por número de sesiones o por horas acumuladas, mostrando el nombre del equipo, su departamento y el total de uso.

Este documento define los requisitos funcionales en formato EARS, derivados del documento de diseño aprobado, y garantiza la trazabilidad con el enfoque técnico en capas (Presentación → Servicios → Repositorios → Base de Datos) y las reglas de integridad referencial establecidas.

## Glossary

- **Sistema**: La aplicación completa de gestión de equipos médicos del Hospital Santo Tomás.
- **Servicio_Departamento**: Componente responsable del registro, consulta y precarga de departamentos.
- **Servicio_Paciente**: Componente responsable del registro y consulta de pacientes.
- **Servicio_Equipo**: Componente responsable del ciclo de vida del inventario de equipos médicos (alta, actualización, cambio de estado, baja).
- **Servicio_Uso**: Componente responsable del registro y consulta de sesiones de uso de equipos.
- **Servicio_Reporte**: Componente responsable de las consultas avanzadas y reportes, incluido el Indicador de Uso Clínico.
- **Interfaz_Consola**: La interfaz de menú de texto interactivo que captura opciones del usuario y muestra resultados.
- **Departamento**: Unidad organizativa del hospital (por ejemplo, "Laboratorio Clínico y Banco de Sangre"). El sistema gestiona 12 departamentos.
- **Paciente**: Persona atendida en el hospital, identificada por una cédula única.
- **Equipo**: Equipo médico del inventario, identificado por un código de inventario único y asignado a un departamento.
- **Sesión_de_Uso**: Registro de un uso de un equipo por un paciente, con fecha/hora de inicio y duración en minutos.
- **Estado_de_Equipo**: Estado operativo de un equipo; uno de "Operativo", "En mantenimiento" o "Fuera de servicio".
- **Criterio_de_Uso**: Base de cálculo del Indicador de Uso Clínico; uno de "sesiones" (número de sesiones) u "horas" (horas acumuladas).
- **Indicador_de_Uso_Clínico**: Reporte crítico que clasifica los equipos por total de uso según el Criterio_de_Uso seleccionado.
- **Integridad_referencial**: Garantía de que toda clave foránea (departamento de un equipo, equipo y paciente de una sesión) referencia una fila existente.

## Requirements

### Requirement 1: Gestión de Departamentos

**User Story:** Como administrador del hospital, quiero registrar y consultar los departamentos del hospital, para organizar el inventario de equipos por unidad organizativa.

#### Acceptance Criteria

1. WHEN un usuario solicita registrar un departamento con un nombre que, tras eliminar los espacios iniciales y finales, contiene entre 1 y 100 caracteres y no coincide con el nombre de ningún departamento existente (comparación sin distinción de mayúsculas/minúsculas), THE Servicio_Departamento SHALL crear el departamento, asignarle un identificador único y devolver el identificador asignado.
2. IF un usuario intenta registrar un departamento cuyo nombre, tras eliminar los espacios iniciales y finales, está vacío o contiene únicamente espacios en blanco, THEN THE Servicio_Departamento SHALL rechazar el registro, conservar sin cambios el conjunto actual de departamentos y devolver un mensaje de error que indique que el nombre es obligatorio.
3. IF un usuario intenta registrar un departamento cuyo nombre, tras eliminar los espacios iniciales y finales, supera los 100 caracteres, THEN THE Servicio_Departamento SHALL rechazar el registro, conservar sin cambios el conjunto actual de departamentos y devolver un mensaje de error que indique que se ha excedido la longitud máxima permitida.
4. IF un usuario intenta registrar un departamento con un nombre que coincide con el de un departamento existente (comparación sin distinción de mayúsculas/minúsculas y tras eliminar los espacios iniciales y finales), THEN THE Servicio_Departamento SHALL rechazar el registro, conservar sin cambios el conjunto actual de departamentos y devolver un mensaje de error que indique que el nombre ya existe.
5. WHEN la tabla de departamentos está vacía y se solicita la inicialización, THE Servicio_Departamento SHALL precargar exactamente los 12 departamentos base del hospital, incluido "Laboratorio Clínico y Banco de Sangre", asignando a cada uno un identificador único.
6. IF se solicita la inicialización y la tabla de departamentos ya contiene al menos un departamento, THEN THE Servicio_Departamento SHALL omitir la precarga, conservar sin cambios el conjunto actual de departamentos y devolver un mensaje que indique que la inicialización no es aplicable.
7. WHEN un usuario solicita listar los departamentos y existe al menos un departamento registrado, THE Servicio_Departamento SHALL devolver todos los departamentos registrados, cada uno con su identificador único y su nombre.
8. WHEN un usuario solicita listar los departamentos y no existe ningún departamento registrado, THE Servicio_Departamento SHALL devolver una lista vacía.

### Requirement 2: Gestión de Pacientes

**User Story:** Como personal de admisión, quiero registrar y consultar pacientes con sus datos principales, para asociarlos a las sesiones de uso de equipos.

#### Acceptance Criteria

1. WHEN un usuario solicita registrar un paciente con cédula (de 1 a 20 caracteres alfanuméricos), nombre (de 1 a 100 caracteres), fecha de nacimiento (fecha válida no posterior a la fecha actual), género (uno de los valores válidos definidos: masculino, femenino u otro) y teléfono (de 7 a 15 dígitos), THE Servicio_Paciente SHALL crear el paciente, asignarle un identificador único y devolver dicho identificador.
2. IF un usuario intenta registrar un paciente con una cédula igual a la de un paciente ya existente, THEN THE Servicio_Paciente SHALL rechazar el registro, conservar el estado actual de los pacientes y devolver un mensaje de error que indique que la cédula ya existe.
3. IF un usuario intenta registrar un paciente con cédula vacía, nombre vacío, fecha de nacimiento inválida o posterior a la fecha actual, género fuera de los valores válidos, o teléfono con menos de 7 o más de 15 dígitos, THEN THE Servicio_Paciente SHALL rechazar el registro, conservar el estado actual de los pacientes y devolver un mensaje de error que indique el campo inválido.
4. WHEN un usuario solicita listar los pacientes, THE Servicio_Paciente SHALL devolver todos los pacientes registrados ordenados por nombre en orden ascendente.
5. WHEN un usuario solicita listar los pacientes y no existe ningún paciente registrado, THE Servicio_Paciente SHALL devolver una lista vacía.
6. IF un usuario solicita consultar un paciente por un identificador o cédula que no corresponde a ningún paciente registrado, THEN THE Servicio_Paciente SHALL devolver un mensaje de error que indique que el paciente no existe.

### Requirement 3: Registro de Equipos Médicos

**User Story:** Como técnico de inventario, quiero registrar equipos médicos en su departamento correspondiente, para mantener un inventario completo y trazable.

#### Acceptance Criteria

1. WHEN un usuario solicita registrar un equipo indicando código de inventario único (texto de 1 a 50 caracteres), nombre (1 a 100 caracteres), marca (1 a 50 caracteres), modelo (1 a 50 caracteres), número de serie (1 a 50 caracteres), fecha de adquisición (fecha válida no posterior a la fecha actual), estado y un departamento existente, THE Servicio_Equipo SHALL crear el equipo, asignarle un identificador único y confirmar el registro exitoso.
2. IF un usuario intenta registrar un equipo con un código de inventario que ya existe, THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error que el código de inventario ya existe.
3. IF un usuario intenta registrar un equipo con un departamento_id que no corresponde a un departamento existente, THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error que el departamento no existe.
4. IF un usuario intenta registrar un equipo con un estado que no pertenece al conjunto {Operativo, En mantenimiento, Fuera de servicio}, THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error que el estado es inválido.
5. WHEN un usuario registra un equipo sin especificar estado, THE Servicio_Equipo SHALL asignar el estado "Operativo" por defecto.
6. IF un usuario intenta registrar un equipo omitiendo o dejando vacío alguno de los campos obligatorios (código de inventario, nombre, marca, modelo, número de serie, fecha de adquisición o departamento), THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error cuál campo obligatorio falta.
7. IF un usuario intenta registrar un equipo con una fecha de adquisición posterior a la fecha actual o con un formato de fecha inválido, THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error que la fecha de adquisición es inválida.
8. IF un usuario intenta registrar un equipo en el que el código de inventario, nombre, marca, modelo o número de serie excede su longitud máxima permitida, THEN THE Servicio_Equipo SHALL rechazar el registro, no crear ningún equipo e indicar mediante un mensaje de error que el campo excede la longitud máxima permitida.

### Requirement 4: Actualización y Cambio de Estado de Equipos

**User Story:** Como técnico de inventario, quiero actualizar los datos y el estado de un equipo, para reflejar su condición operativa real.

#### Acceptance Criteria

1. WHEN un usuario solicita actualizar los campos de un equipo existente con valores válidos (cada campo de texto con longitud entre 1 y 255 caracteres y todos los campos obligatorios no vacíos), THE Servicio_Equipo SHALL aplicar los cambios, persistir el equipo actualizado y devolver el equipo con sus valores actualizados.
2. WHEN un usuario solicita cambiar el estado de un equipo existente a un valor del conjunto {Operativo, En mantenimiento, Fuera de servicio}, THE Servicio_Equipo SHALL actualizar el estado del equipo al nuevo valor y devolver el equipo con el estado actualizado.
3. IF un usuario intenta cambiar el estado de un equipo a un valor fuera del conjunto {Operativo, En mantenimiento, Fuera de servicio}, THEN THE Servicio_Equipo SHALL rechazar el cambio, conservar el estado anterior del equipo sin modificaciones y devolver un mensaje de error que indique que el valor de estado no pertenece al conjunto permitido.
4. IF un usuario intenta actualizar un equipo que no existe, THEN THE Servicio_Equipo SHALL rechazar la operación, no crear ningún equipo nuevo y devolver un mensaje de error que indique que el equipo no existe.
5. IF un usuario solicita actualizar los campos de un equipo existente con valores inválidos (algún campo obligatorio vacío o algún campo de texto con longitud mayor a 255 caracteres), THEN THE Servicio_Equipo SHALL rechazar la actualización, conservar los datos previos del equipo sin modificaciones y devolver un mensaje de error que indique cuáles campos no son válidos.

### Requirement 5: Baja de Equipos con Preservación de Historial

**User Story:** Como administrador de inventario, quiero dar de baja equipos, para retirar del inventario los equipos que ya no se utilizan sin perder el historial de uso.

#### Acceptance Criteria

1. WHEN un usuario solicita dar de baja un equipo existente que no tiene ninguna sesión de uso asociada, THE Servicio_Equipo SHALL eliminar el equipo del inventario y confirmar la baja exitosa.
2. IF un usuario intenta dar de baja un equipo que tiene una o más sesiones de uso asociadas, THEN THE Servicio_Equipo SHALL rechazar la baja, conservar el equipo y la totalidad de su historial de sesiones sin modificaciones e indicar mediante un mensaje de error que existen sesiones históricas asociadas.
3. IF un usuario intenta dar de baja un equipo que no existe, THEN THE Servicio_Equipo SHALL rechazar la operación, no modificar el inventario e indicar mediante un mensaje de error que el equipo no existe.
4. IF un usuario intenta dar de baja un equipo indicando un identificador ausente, vacío o con formato inválido, THEN THE Servicio_Equipo SHALL rechazar la operación e indicar mediante un mensaje de error que el identificador no es válido.
5. WHEN un equipo es dado de baja correctamente, THE Servicio_Equipo SHALL hacer que las consultas posteriores de ese equipo por su identificador devuelvan un resultado vacío que indique su ausencia en el inventario.

### Requirement 6: Registro de Sesiones de Uso

**User Story:** Como operador clínico, quiero registrar cada uso de un equipo por un paciente, para construir el historial que alimenta los reportes de uso.

#### Acceptance Criteria

1. WHEN un usuario solicita registrar una sesión de uso con un equipo existente, un paciente existente, una fecha/hora de inicio válida no posterior a la fecha/hora actual del sistema, y una duración en minutos numérica mayor que 0 y menor o igual a 1440, THE Servicio_Uso SHALL crear exactamente una sesión de uso con un identificador único y devolver dicho identificador.
2. IF un usuario intenta registrar una sesión de uso con un equipo_id que no corresponde a un equipo existente, THEN THE Servicio_Uso SHALL rechazar el registro sin crear ninguna sesión y devolver un error que indique que el equipo no existe.
3. IF un usuario intenta registrar una sesión de uso con un paciente_id que no corresponde a un paciente existente, THEN THE Servicio_Uso SHALL rechazar el registro sin crear ninguna sesión y devolver un error que indique que el paciente no existe.
4. IF un usuario intenta registrar una sesión de uso con una duración en minutos no numérica, menor o igual a 0, o mayor que 1440, THEN THE Servicio_Uso SHALL rechazar el registro sin crear ninguna sesión y devolver un error que indique que la duración es inválida.
5. IF un usuario intenta registrar una sesión de uso con una fecha/hora de inicio ausente, con formato inválido, o posterior a la fecha/hora actual del sistema, THEN THE Servicio_Uso SHALL rechazar el registro sin crear ninguna sesión y devolver un error que indique que la fecha/hora de inicio es inválida.
6. WHEN una sesión de uso se crea con un identificador único, THE Servicio_Uso SHALL incrementar en uno el total de sesiones asociadas a ese equipo.
7. WHEN un usuario solicita listar las sesiones de un equipo existente que tiene una o más sesiones registradas, THE Servicio_Uso SHALL devolver todas las sesiones asociadas a ese equipo ordenadas por fecha/hora de inicio de más reciente a más antigua.
8. IF un usuario solicita listar las sesiones de un equipo existente que no tiene sesiones registradas, THEN THE Servicio_Uso SHALL devolver una colección vacía sin generar error.

### Requirement 7: Consulta de Inventario por Departamento

**User Story:** Como jefe de departamento, quiero consultar el inventario de equipos de mi departamento, para conocer los recursos disponibles.

#### Acceptance Criteria

1. WHEN un usuario solicita el inventario de un departamento existente que contiene al menos un equipo, THE Servicio_Reporte SHALL devolver la lista de todos los equipos cuyo departamento_id corresponde a ese departamento.
2. WHEN un usuario solicita el inventario de un departamento existente que no contiene equipos, THE Servicio_Reporte SHALL devolver una lista vacía e indicar que el departamento no tiene equipos registrados.
3. IF un usuario solicita el inventario de un departamento que no existe, THEN THE Servicio_Reporte SHALL rechazar la solicitud, indicar mediante un mensaje de error que el departamento no existe y no devolver ningún equipo.
4. IF un usuario solicita el inventario con un identificador de departamento vacío, nulo o con un formato no válido, THEN THE Servicio_Reporte SHALL rechazar la solicitud e indicar mediante un mensaje de error que el identificador de departamento no es válido.

### Requirement 8: Alerta de Mantenimiento

**User Story:** Como responsable de mantenimiento, quiero obtener la lista de equipos en mantenimiento, para priorizar las intervenciones técnicas.

#### Acceptance Criteria

1. WHEN un usuario solicita la alerta de mantenimiento, THE Servicio_Reporte SHALL devolver una lista que contenga únicamente los equipos cuyo estado sea exactamente "En mantenimiento", excluyendo todo equipo con cualquier otro estado.
2. WHEN un usuario solicita la alerta de mantenimiento y existe al menos un equipo cuyo estado es "En mantenimiento", THE Servicio_Reporte SHALL incluir, por cada equipo devuelto, su identificador único y su estado.
3. WHEN un usuario solicita la alerta de mantenimiento y no existe ningún equipo cuyo estado es "En mantenimiento", THE Servicio_Reporte SHALL devolver una lista vacía junto con un mensaje que indique que no hay equipos en mantenimiento.
4. IF la fuente de datos de equipos no está disponible o no puede leerse al solicitar la alerta de mantenimiento, THEN THE Servicio_Reporte SHALL devolver un mensaje de error que indique el fallo de acceso a los datos y SHALL no devolver ninguna lista parcial de equipos.

### Requirement 9: Indicador de Uso Clínico (Requisito Crítico)

**User Story:** Como director clínico, quiero identificar el equipo médico más utilizado por número de sesiones o por horas acumuladas, para tomar decisiones de adquisición y asignación de recursos.

#### Acceptance Criteria

1. WHEN un usuario solicita el Indicador de Uso Clínico con criterio "sesiones", THE Servicio_Reporte SHALL calcular por cada equipo el total de uso como el número de sesiones registradas para ese equipo (un entero no negativo).
2. WHEN un usuario solicita el Indicador de Uso Clínico con criterio "horas", THE Servicio_Reporte SHALL calcular por cada equipo el total de uso como la suma de las duraciones en minutos dividida entre 60 y redondeada a 2 decimales.
3. WHEN el Indicador de Uso Clínico produce resultados, THE Servicio_Reporte SHALL ordenar las métricas de forma no creciente por total de uso, de modo que el primer elemento sea el equipo más utilizado.
4. WHEN dos o más equipos tienen el mismo total de uso, THE Servicio_Reporte SHALL desempatar ordenándolos alfabéticamente en orden ascendente por nombre de equipo, para producir un orden determinista.
5. WHEN el Indicador de Uso Clínico produce una métrica de un equipo, THE Servicio_Reporte SHALL incluir el nombre del equipo, el nombre de su departamento y el total de uso.
6. WHERE el usuario especifica un departamento existente al solicitar el Indicador de Uso Clínico, THE Servicio_Reporte SHALL calcular las métricas únicamente sobre los equipos de ese departamento.
7. IF el usuario especifica un departamento que no existe al solicitar el Indicador de Uso Clínico, THEN THE Servicio_Reporte SHALL rechazar la solicitud, no producir métricas e indicar mediante un mensaje de error que el departamento no existe.
8. IF un usuario solicita el Indicador de Uso Clínico con un criterio que no pertenece al conjunto {sesiones, horas}, THEN THE Servicio_Reporte SHALL rechazar la solicitud, no producir métricas e indicar mediante un mensaje de error que el criterio es inválido.
9. WHEN no existen equipos dentro del alcance solicitado, THE Servicio_Reporte SHALL devolver un conjunto de resultados vacío sin generar error.

### Requirement 10: Integridad Referencial y Validación de Datos

**User Story:** Como responsable de calidad de datos, quiero que el sistema garantice la integridad referencial y la validación de datos, para mantener un inventario y un historial consistentes.

#### Acceptance Criteria

1. IF se intenta crear o actualizar un equipo con un código de inventario (cadena de 1 a 50 caracteres) que ya esté asignado a otro equipo, THEN THE Sistema SHALL rechazar la operación, conservar los datos del equipo existente sin modificarlos e indicar un error que señale la violación de unicidad del código de inventario.
2. IF se intenta crear o actualizar un paciente con una cédula que ya esté asignada a otro paciente, THEN THE Sistema SHALL rechazar la operación, conservar los datos del paciente existente sin modificarlos e indicar un error que señale la violación de unicidad de la cédula.
3. IF se intenta crear o actualizar un departamento con un nombre (cadena de 1 a 100 caracteres, comparado sin distinción entre mayúsculas y minúsculas) que ya esté asignado a otro departamento, THEN THE Sistema SHALL rechazar la operación, conservar los datos del departamento existente sin modificarlos e indicar un error que señale la violación de unicidad del nombre.
4. IF se intenta crear o actualizar un equipo cuyo departamento_id no referencia a un departamento existente, THEN THE Sistema SHALL rechazar la operación, no crear ni modificar el registro del equipo e indicar un error de referencia inválida al departamento.
5. IF se intenta crear o actualizar una sesión de uso cuyo equipo_id no referencia a un equipo existente, THEN THE Sistema SHALL rechazar la operación, no crear ni modificar la sesión e indicar un error de referencia inválida al equipo.
6. IF se intenta crear o actualizar una sesión de uso cuyo paciente_id no referencia a un paciente existente, THEN THE Sistema SHALL rechazar la operación, no crear ni modificar la sesión e indicar un error de referencia inválida al paciente.
7. IF se intenta asignar a un equipo un estado que no pertenezca al conjunto {Operativo, En mantenimiento, Fuera de servicio}, THEN THE Sistema SHALL rechazar la operación, conservar el estado anterior del equipo e indicar un error de estado no válido.
8. IF se intenta registrar una sesión de uso cuya duración en minutos no sea un número entero comprendido entre 1 y 1440 (ambos inclusive), THEN THE Sistema SHALL rechazar la operación, no crear la sesión e indicar un error de duración no válida.

### Requirement 11: Interfaz de Menú de Consola

**User Story:** Como usuario del sistema, quiero interactuar mediante un menú de texto en consola, para operar el sistema sin necesidad de un entorno gráfico.

#### Acceptance Criteria

1. WHEN el sistema inicia, THE Interfaz_Consola SHALL mostrar un menú de texto en el que cada una de las opciones (gestión de departamentos, pacientes, equipos, sesiones de uso, reportes y salir) se presenta en una línea independiente precedida por un identificador numérico entero único y consecutivo comenzando en 1.
2. WHEN un usuario introduce un identificador numérico que corresponde a una opción existente del menú, THE Interfaz_Consola SHALL invocar la operación asociada y mostrar el resultado en un formato de texto delimitado por etiquetas de campo y valor, un campo por línea.
3. WHEN la operación invocada finaliza y muestra su resultado, THE Interfaz_Consola SHALL volver a mostrar el menú principal completo descrito en el criterio 1.
4. IF un usuario introduce un identificador que no corresponde a ninguna opción del menú, o introduce un valor no numérico, o introduce una entrada vacía (sin caracteres o solo espacios), THEN THE Interfaz_Consola SHALL mostrar un mensaje indicando que la selección no es válida y volver a mostrar el menú principal completo, sin invocar ninguna operación.
5. WHEN una operación de servicio rechaza una solicitud por un dato inválido, THE Interfaz_Consola SHALL mostrar un mensaje de error que identifique el dato rechazado y el motivo del rechazo, conservar los demás datos ya introducidos por el usuario y solicitar nuevamente únicamente el dato rechazado, permitiendo hasta 3 reintentos.
6. IF el usuario agota los 3 reintentos permitidos sin proporcionar un dato válido, THEN THE Interfaz_Consola SHALL cancelar la operación en curso, indicar que la operación fue cancelada y volver a mostrar el menú principal completo.
