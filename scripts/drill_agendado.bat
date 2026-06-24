@echo off
REM ===================================================================
REM PC = SO ENRIQUECIMENTO (precisa do cookie do e-SCI).
REM A COLETA (multas/AFs/protocolos, publica) roda na NUVEM (GitHub Actions),
REM 24/7, sem depender deste PC. Aqui so geramos os arquivos de ENRIQUECIMENTO:
REM   drill.json (contatos/pendencias dos AFs) e protocolos_enrich.json
REM   (deferido/area/anexos dos protocolos).
REM Esses arquivos sao DISJUNTOS dos da nuvem -> push nunca conflita.
REM ===================================================================
cd /d "%~dp0\.."
set LOG=scripts\drill_agendado.log
echo ====== %DATE% %TIME% ====== >> "%LOG%"

python -c "import browser_cookie3, requests" 2>nul || python -m pip install browser_cookie3 requests --quiet

REM 1) Pega a coleta mais fresca da nuvem (merge preferindo o remoto; nunca detacha)
git checkout main >> "%LOG%" 2>&1
git fetch origin -q >> "%LOG%" 2>&1
git merge -X theirs origin/main -m "sync (puxa coleta da nuvem)" >> "%LOG%" 2>&1

REM 2) Enriquece em cima dos dados frescos
python scripts\drill_local.py >> "%LOG%" 2>&1
python scripts\drill_protocolos.py >> "%LOG%" 2>&1

REM 3) Commit + push SO dos arquivos de enriquecimento (disjuntos da nuvem),
REM    com rebase+retry caso a nuvem tenha empurrado no meio
git add docs/qbQv3yHGdx6ocaYE/drill.json docs/qbQv3yHGdx6ocaYE/protocolos_enrich.json scripts/drill_cache.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Enriquecimento PC %DATE% %TIME%" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    if errorlevel 1 (
        git pull --rebase origin main >> "%LOG%" 2>&1
        git push >> "%LOG%" 2>&1
    )
    echo [OK] Enriquecimento enviado. >> "%LOG%"
) else (
    echo [--] Sem mudancas no enriquecimento. >> "%LOG%"
)

REM Sai com sucesso (git diff --cached --quiet retorna 1 por design quando ha mudanca).
exit /b 0
