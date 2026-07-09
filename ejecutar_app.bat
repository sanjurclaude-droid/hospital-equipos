@echo off
REM ============================================================================
REM  Lanzador de la interfaz grafica (CustomTkinter) para Windows.
REM
REM  1. Detecta el interprete de Python disponible (py o python).
REM  2. Instala las dependencias de requirements.txt (customtkinter) si faltan.
REM  3. Ejecuta la aplicacion grafica: python -m hospital_equipos.gui
REM ============================================================================

setlocal

REM Situarse en la carpeta del script (raiz del repositorio).
cd /d "%~dp0"

REM Detectar el lanzador de Python: preferimos "py", si no "python".
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=python"
)

echo Verificando dependencias (customtkinter)...
%PY% -c "import customtkinter" >nul 2>nul
if not %errorlevel%==0 (
    echo Instalando dependencias desde requirements.txt...
    %PY% -m pip install -r requirements.txt
    if not %errorlevel%==0 (
        echo.
        echo No se pudieron instalar las dependencias. Revise su conexion e intente de nuevo.
        pause
        exit /b 1
    )
)

echo Iniciando la aplicacion grafica...
%PY% -m hospital_equipos.gui
if not %errorlevel%==0 (
    echo.
    echo La aplicacion finalizo con errores.
    pause
    exit /b 1
)

endlocal
