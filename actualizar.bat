@echo off
REM ===================================================================
REM  Leido - reconstruir la web entera.
REM
REM  Dos formas de usarlo:
REM     - doble clic en este archivo
REM     - desde PowerShell:  .\actualizar.bat
REM
REM  Hace las tres cosas en orden y se para en cuanto una falla:
REM     1. dibuja las miniaturas de compartir y los iconos
REM     2. regenera las paginas HTML desde datos/libros.json
REM     3. comprueba que no haya quedado nada roto
REM
REM  Existe porque PowerShell 5 no admite encadenar con && y porque la
REM  ruta de Python cambia de un ordenador a otro.
REM
REM  OJO al editarlo: solo caracteres ASCII y nada de && dentro de
REM  parentesis. cmd.exe se atraganta con ambas cosas y suelta errores
REM  que no vienen a cuento.
REM ===================================================================
setlocal
cd /d "%~dp0"

REM --- buscar un Python que funcione, por orden de preferencia --------
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
echo         Instalalo desde python.org marcando "Add python.exe to PATH".
echo.
pause
exit /b 1

:encontrado
echo.
echo === 1 de 3 - Miniaturas para compartir e iconos ===
%PY% tools\generar_og.py
if errorlevel 1 goto :fallo

echo.
echo === 2 de 3 - Generando las paginas ===
%PY% tools\build_site.py
if errorlevel 1 goto :fallo

echo.
echo === 3 de 3 - Comprobando que nada quedo roto ===
%PY% tools\comprobar_sitio.py
if errorlevel 1 goto :roto

echo.
echo ===================================================
echo  LISTO. La web esta al dia y sin fallos.
echo  Ya puedes publicarla.
echo ===================================================
echo.
pause
exit /b 0

:roto
echo.
echo ===================================================
echo  ATENCION: la web se ha generado, pero arriba
echo  aparecen fallos. Conviene mirarlos antes de
echo  publicar.
echo ===================================================
echo.
pause
exit /b 1

:fallo
echo.
echo ===================================================
echo  Se ha parado por un error. El motivo esta arriba.
echo  No se ha generado todo.
echo ===================================================
echo.
pause
exit /b 1
