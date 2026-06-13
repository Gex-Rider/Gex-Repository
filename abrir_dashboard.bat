@echo off
:: ─────────────────────────────────────────────────────
::  GEX DASHBOARD LAUNCHER
::  Abre los 3 dashboards en el navegador por defecto
::  Requiere Python instalado (python --version para verificar)
:: ─────────────────────────────────────────────────────

:: Detectar carpeta donde está este .bat (funciona en C:, E:, cualquier disco)
cd /d "%~dp0"

:: Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no encontrado.
    echo  Instala Python desde https://www.python.org/downloads/
    echo  y marca "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b
)

:: Matar cualquier servidor anterior en puerto 8080 para evitar conflictos
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080 " 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Lanzar servidor en background ANTES de abrir tabs
::  (sin servidor activo el fetch de dashboard_strikes.json falla en file://)
start "GEX HTTP Server" /min python -m http.server 8080

:: Esperar a que el servidor levante antes de abrir tabs
timeout /t 2 /nobreak >nul

:: Abrir los 3 tabs
start "" "http://localhost:8080/gex_table.html"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8080/gex_dashboard.html"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8080/gex_history_v23.html"

:: Informar al usuario
echo.
echo  GEX Server corriendo en http://localhost:8080
echo  La ventana del servidor se minimizo automaticamente.
echo  Para detener el servidor: cierra la ventana "GEX HTTP Server"
echo.
pause
