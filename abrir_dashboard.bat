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

:: Esperar 1 segundo y abrir los 3 tabs
timeout /t 1 /nobreak >nul
start "" "http://localhost:8080/gex_table.html"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8080/gex_dashboard.html"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8080/gex_history_v19.html"


:: Lanzar servidor (bloquea esta ventana — minimizala, no la cierres)
echo.
echo  GEX Server corriendo en http://localhost:8080
echo  Minimiza esta ventana. NO la cierres.
echo  Para detener el servidor presiona Ctrl+C
echo.
python -m http.server 8080

