@echo off
REM ===================================================================
REM  Leido - modo desarrollo (editar en caliente).
REM
REM  Doble clic aqui y deja la ventana abierta. Mientras este abierta:
REM     - la web se ve en  http://localhost:8777
REM     - al guardar cualquier archivo se reconstruye sola
REM     - el navegador se recarga solo
REM
REM  No hace falta ejecutar actualizar.bat mientras esto corre.
REM  Ctrl+C o cerrar la ventana para parar.
REM ===================================================================
setlocal
cd /d "%~dp0"

set "PY=py -3"
%PY% --version >nul 2>&1
if not errorlevel 1 goto :encontrado

set "PY=python"
%PY% --version >nul 2>&1
if not errorlevel 1 goto :encontrado

set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto :encontrado

echo.
echo [ERROR] No encuentro Python en este ordenador.
echo.
pause
exit /b 1

:encontrado
%PY% tools\servidor.py 8777
pause
