@echo off
REM Drill-down LOCAL dos autos do painel CBMSC.
REM Le cookies do Chrome (precisa estar LOGADO no e-SCI antes de rodar).
REM Depois faz commit/push automatico pro repo do painel.

cd /d "%~dp0\.."

echo === DRILL-DOWN CBMSC - Rodrigues Preventivos ===
echo.

REM Instalar dependencias se faltarem (so na 1a vez)
python -c "import browser_cookie3, requests" 2>nul
if errorlevel 1 (
    echo Instalando dependencias necessarias...
    python -m pip install browser_cookie3 requests --quiet
)

REM Rodar drill
python scripts/drill_local.py
if errorlevel 1 (
    echo.
    echo [!] Falhou. Verifique que o Chrome esta aberto e voce esta logado no e-SCI.
    pause
    exit /b 1
)

REM Commit e push se houve mudancas
echo.
echo === Subindo para o GitHub ===
git add docs/%~n1 docs/qbQv3yHGdx6ocaYE/drill.json scripts/drill_cache.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Drill-down atualizado %DATE% %TIME:~0,5%"
    git push
    echo.
    echo [OK] Painel atualizado! TV vai pegar a mudanca em ~60s.
) else (
    echo Sem novidades para subir.
)

pause
