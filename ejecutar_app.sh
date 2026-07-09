#!/usr/bin/env bash
# =============================================================================
#  Lanzador de la interfaz gráfica (CustomTkinter) para macOS y Linux.
#
#  1. Detecta el intérprete de Python 3 disponible.
#  2. Instala las dependencias de requirements.txt (customtkinter) si faltan.
#  3. Ejecuta la aplicación gráfica: python -m hospital_equipos.gui
# =============================================================================

set -euo pipefail

# Situarse en la carpeta del script (raíz del repositorio).
cd "$(dirname "$0")"

# Detectar el intérprete de Python 3.
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
else
    echo "No se encontró un intérprete de Python. Instale Python 3.10 o superior."
    exit 1
fi

echo "Verificando dependencias (customtkinter)..."
if ! "$PY" -c "import customtkinter" >/dev/null 2>&1; then
    echo "Instalando dependencias desde requirements.txt..."
    "$PY" -m pip install -r requirements.txt
fi

echo "Iniciando la aplicación gráfica..."
exec "$PY" -m hospital_equipos.gui
