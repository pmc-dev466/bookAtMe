@echo off
REM ===================================================================
REM  BookAtMe! - el unico archivo que necesitas.
REM
REM  Doble clic y elige que quieres hacer. Antes habia tres .bat
REM  distintos y era un lio; esto los sustituye a todos.
REM
REM  OJO al editarlo: solo ASCII y nada de && dentro de parentesis,
REM  o cmd.exe suelta errores que no senalan la linea culpable.
REM ===================================================================
setlocal
cd /d "%~dp0"

REM --- buscar Python ---
set "PY=py -3"
%PY% --version >nul 2>&1
if not errorlevel 1 goto :menu
set "PY=python"
%PY% --version >nul 2>&1
if not errorlevel 1 goto :menu
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto :menu
echo.
echo [ERROR] No encuentro Python en este ordenador.
echo         Instalalo desde python.org marcando "Add python.exe to PATH".
echo.
pause
exit /b 1

:menu
cls
echo.
echo   ===============================================================
echo                          B o o k A t M e !
echo   ===============================================================
echo.
echo     1.  TRABAJAR
echo         Abre la web en el navegador. Al guardar cualquier
echo         archivo se actualiza sola delante de ti.
echo.
echo     2.  PUBLICAR
echo         Sube los cambios a internet. Comprueba antes que
echo         nada este roto, y te pregunta antes de subir.
echo.
echo     3.  COMPROBAR
echo         Revisa que todo este bien, sin publicar nada.
echo.
echo     4.  Salir
echo.
echo   ---------------------------------------------------------------
set "OP="
set /p OP=  Que quieres hacer? (1-4):

if "%OP%"=="1" goto :trabajar
if "%OP%"=="2" goto :publicar
if "%OP%"=="3" goto :comprobar
if "%OP%"=="4" exit /b 0
goto :menu


REM ===================== 1 - TRABAJAR =====================
:trabajar
cls
echo.
echo   Abriendo la web... deja esta ventana abierta.
echo   Al guardar un archivo, la pagina se actualiza sola.
echo.
echo   Ctrl+C para volver.
echo.
start "" http://localhost:8777
%PY% tools\servidor.py 8777
goto :menu


REM ===================== 2 - PUBLICAR =====================
:publicar
cls
echo.
echo   === 1 de 4 - Miniaturas para compartir ===
%PY% tools\generar_og.py
if errorlevel 1 goto :fallo

echo.
echo   === 2 de 4 - Reconstruyendo las paginas ===
%PY% tools\build_site.py
if errorlevel 1 goto :fallo

echo.
echo   === 3 de 4 - Comprobando que nada quedo roto ===
%PY% tools\comprobar_sitio.py
if errorlevel 1 goto :roto

echo.
echo   ===============================================================
echo    Todo correcto. Esto es lo que se va a publicar:
echo   ===============================================================
git status --short
echo.

git diff --quiet HEAD
if not errorlevel 1 goto :nada

set "MSG="
set /p MSG=  Describe el cambio (Enter para "Actualizacion"):
if "%MSG%"=="" set "MSG=Actualizacion"

echo.
set "SI="
set /p SI=  Publicar esto para todo el mundo? (s/n):
if /i not "%SI%"=="s" goto :cancelado

echo.
echo   === 4 de 4 - Subiendo ===
git add -A
git commit -m "%MSG%"
if errorlevel 1 goto :fallo
git push
if errorlevel 1 goto :fallopush

echo.
echo   ===============================================================
echo    PUBLICADO.
echo.
echo    Cloudflare lo esta reconstruyendo ahora mismo. En un par
echo    de minutos estara en:
echo        https://bookatme.pages.dev
echo   ===============================================================
echo.
pause
goto :menu


REM ===================== 3 - COMPROBAR =====================
:comprobar
cls
echo.
echo   === Reconstruyendo y revisando ===
echo.
%PY% tools\generar_og.py
if errorlevel 1 goto :fallo
%PY% tools\build_site.py
if errorlevel 1 goto :fallo
%PY% tools\comprobar_sitio.py
if errorlevel 1 goto :roto
echo.
echo   Todo correcto. No se ha publicado nada.
echo.
pause
goto :menu


REM ===================== avisos =====================
:nada
echo   No hay ningun cambio que publicar: la web ya esta al dia.
echo.
pause
goto :menu

:cancelado
echo.
echo   Cancelado. No se ha subido nada.
echo   Tus cambios siguen en el ordenador, intactos.
echo.
pause
goto :menu

:roto
echo.
echo   ===============================================================
echo    PARADO: la comprobacion ha encontrado fallos.
echo    Arriba salen cuales y en que pagina. NO se ha publicado nada.
echo   ===============================================================
echo.
pause
goto :menu

:fallopush
echo.
echo   ===============================================================
echo    El cambio se guardo, pero fallo al subirlo a GitHub.
echo    Suele ser la sesion caducada. Abre una terminal aqui y
echo    escribe:   git push
echo    Se abrira el navegador para que entres.
echo   ===============================================================
echo.
pause
goto :menu

:fallo
echo.
echo   ===============================================================
echo    Se ha parado por un error. El motivo esta arriba.
echo    NO se ha publicado nada.
echo   ===============================================================
echo.
pause
goto :menu
