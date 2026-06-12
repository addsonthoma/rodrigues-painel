@echo off
REM Duplo-clique para ver quando o drill e o coletor rodaram pela ultima vez.
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\ver_status.ps1"
echo.
pause
