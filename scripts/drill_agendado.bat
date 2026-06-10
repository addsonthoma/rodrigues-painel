@echo off
REM Drill agendado - roda sem interacao, loga resultado.
REM Requer: cookies.txt valido (renovar no Chrome de manha) + Chrome logado no e-SCI.
cd /d "%~dp0\.."
set LOG=scripts\drill_agendado.log
echo ====== %DATE% %TIME% ====== >> "%LOG%"

REM garante dependencias
python -c "import browser_cookie3, requests" 2>nul || python -m pip install browser_cookie3 requests --quiet

REM roda o drill
python scripts\drill_local.py >> "%LOG%" 2>&1

REM se houve mudanca no drill.json, commita e sobe
git add docs/qbQv3yHGdx6ocaYE/drill.json scripts/drill_cache.json
git diff --cached --quiet
if errorlevel 1 (
    git pull --rebase --autostash >> "%LOG%" 2>&1
    git commit -m "Drill agendado %DATE%" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    echo [OK] Drill atualizado e enviado. >> "%LOG%"
) else (
    echo [--] Sem mudancas no drill. >> "%LOG%"
)
