@echo off
REM ============================================================================
REM  Lanzador de la interfaz grafica (CustomTkinter) para Windows.
REM
REM  1. Detecta el interprete de Python disponible (py o python).
REM  2. Instala las dependencias de requirements.txt (customtkinter) si faltan.
REM  3. Verifica que la dependencia se pueda importar realmente.
REM  4. Ejecuta la aplicacion grafica: python -m hospital_equipos.gui
REM ============================================================================

setlocal enabledelayedexpansion

REM Situarse en la carpeta del script (raiz del repositorio) para que funcione
REM independientemente de desde donde se ejecute.
cd /d "%~dp0"

REM Detectar el lanzador de Python: preferimos "py", si no "python".
where py >nul 2>nul
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py"
)

REM Comprobar que el interprete elegido existe realmente.
where !PY! >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontro un interprete de Python. Instale Python 3.10 o superior
    echo y asegurese de que este disponible en el PATH.
    echo.
    pause
    exit /b 1
)

echo Usando interprete: !PY!
echo Verificando dependencias (customtkinter)...

REM Si customtkinter ya se puede importar, no hace falta instalar nada.
!PY! -c "import customtkinter" >nul 2>nul
if errorlevel 1 (
    echo Falta la dependencia. Instalando desde requirements.txt...
    REM Nota: pip puede mostrar avisos ("notice") y aun asi terminar con exito.
    REM No tratamos esos avisos como errores; solo comprobamos el codigo de salida.
    !PY! -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Aviso: pip devolvio un codigo de salida distinto de cero.
        echo Se intentara verificar la dependencia de todos modos...
    )

    REM Verificacion definitiva: la instalacion es correcta solo si customtkinter
    REM se puede importar. Este es el criterio real de exito, no los avisos de pip.
    !PY! -c "import customtkinter" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo No se pudieron instalar las dependencias. Revise su conexion e intente de nuevo.
        echo.
        pause
        exit /b 1
    )
    echo Dependencias instaladas correctamente.
) else (
    echo Dependencias ya presentes.
)

echo Iniciando la aplicacion grafica...
!PY! -m hospital_equipos.gui
if errorlevel 1 (
    echo.
    echo La aplicacion finalizo con errores.
    echo.
    pause
    exit /b 1
)

endlocal
