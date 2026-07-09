#!/usr/bin/env bash
# =============================================================================
#  Lanzador de la interfaz grafica (CustomTkinter) para macOS y Linux.
#
#  1. Detecta el interprete de Python 3 disponible.
#  2. Instala las dependencias de requirements.txt (customtkinter) si faltan.
#  3. Verifica que la dependencia se pueda importar realmente.
#  4. Ejecuta la aplicacion grafica: python -m hospital_equipos.gui
# =============================================================================

set -eu

# Situarse en la carpeta del script (raiz del repositorio).
cd "$(dirname "$0")"

# Detectar el interprete de Python 3.
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
else
    echo "No se encontro un interprete de Python. Instale Python 3.10 o superior."
    exit 1
fi

echo "Usando interprete: $PY"
echo "Verificando dependencias (customtkinter)..."

if ! "$PY" -c "import customtkinter" >/dev/null 2>&1; then
    echo "Falta la dependencia. Instalando desde requirements.txt..."
    # pip puede mostrar avisos ("notice") y aun asi terminar con exito.
    # No abortamos aqui por esos avisos; la verificacion real es el import.
    if ! "$PY" -m pip install -r requirements.txt; then
        echo "Aviso: pip devolvio un codigo de salida distinto de cero."
        echo "Se intentara verificar la dependencia de todos modos..."
    fi

    # Verificacion definitiva: la instalacion es correcta solo si customtkinter
    # se puede importar. Este es el criterio real de exito, no los avisos de pip.
    if ! "$PY" -c "import customtkinter" >/dev/null 2>&1; then
        echo
        echo "No se pudieron instalar las dependencias. Revise su conexion e intente de nuevo."
        exit 1
    fi
    echo "Dependencias instaladas correctamente."
else
    echo "Dependencias ya presentes."
fi

echo "Iniciando la aplicacion grafica..."
exec "$PY" -m hospital_equipos.gui
