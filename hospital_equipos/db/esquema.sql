-- Esquema relacional del Sistema de Gestión de Equipos Médicos
-- Hospital Santo Tomás (SQLite).
--
-- El DDL es idempotente (CREATE TABLE IF NOT EXISTS) y define las 4 tablas
-- del dominio con integridad referencial (claves primarias y foráneas),
-- restricciones de unicidad y comprobaciones (CHECK) de dominio.
--
-- NOTA: la activación de la integridad referencial (PRAGMA foreign_keys = ON)
-- se realiza por conexión en `crear_conexion`, no en este archivo.

CREATE TABLE IF NOT EXISTS departamentos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS pacientes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula           TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    fecha_nacimiento TEXT,
    genero           TEXT,
    telefono         TEXT
);

CREATE TABLE IF NOT EXISTS equipos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_inventario TEXT NOT NULL UNIQUE,
    nombre            TEXT NOT NULL,
    marca             TEXT,
    modelo            TEXT,
    numero_serie      TEXT UNIQUE,
    fecha_adquisicion TEXT,
    estado            TEXT NOT NULL DEFAULT 'Operativo'
                      CHECK (estado IN ('Operativo','En mantenimiento','Fuera de servicio')),
    departamento_id   INTEGER NOT NULL,
    FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
);

CREATE TABLE IF NOT EXISTS uso_equipos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id        INTEGER NOT NULL,
    paciente_id      INTEGER NOT NULL,
    fecha_inicio     TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL CHECK (duracion_minutos > 0),
    FOREIGN KEY (equipo_id)   REFERENCES equipos(id),
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
);

-- Índice para acelerar las agregaciones del Indicador de Uso Clínico.
CREATE INDEX IF NOT EXISTS idx_uso_equipos_equipo_id
    ON uso_equipos(equipo_id);
