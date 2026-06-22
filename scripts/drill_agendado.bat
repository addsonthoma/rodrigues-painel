@echo off
REM Drill agendado - roda sem interacao, loga resultado.
REM SYNC ROBUSTO (corrigido 22/06/2026): usa MERGE preferindo o remoto, em vez de
REM "git pull --rebase --autostash". O autostash conflitava com os commits do bot
REM (ambos mexem em dados.json/estado.json), o "stash pop" falhava e DEIXAVA
REM marcadores de conflito (<<<<<<< ======= >>>>>>>) dentro do JSON -> quebrava o
REM painel ("fora do ar"). Merge nunca deixa stash preso. Mesmo padrao do coletar_agendado.bat.
cd /d "%~dp0\.."
set LOG=scripts\drill_agendado.log
echo ====== %DATE% %TIME% ====== >> "%LOG%"

REM garante dependencias
python -c "import browser_cookie3, requests" 2>nul || python -m pip install browser_cookie3 requests --quiet

REM 1) Sincroniza com o remoto via MERGE (nunca conflita / nunca deixa stash preso)
git checkout main >> "%LOG%" 2>&1
git fetch origin -q >> "%LOG%" 2>&1
git merge -X theirs origin/main -m "sync drill" >> "%LOG%" 2>&1

REM 2) Roda o drill em cima dos dados frescos
python scripts\drill_local.py >> "%LOG%" 2>&1

REM 2b) Protocolos de analise PPCI/RPCI: coleta novos + enriquece (area/data/deferido/anexos)
python scripts\coletar_protocolos.py >> "%LOG%" 2>&1
python scripts\drill_protocolos.py >> "%LOG%" 2>&1

REM 3) Commit + push (so os JSONs gerados), com 1 retry se o origin mudou
git add docs/qbQv3yHGdx6ocaYE/drill.json scripts/drill_cache.json docs/qbQv3yHGdx6ocaYE/protocolos.json scripts/estado_protocolos.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Drill agendado %DATE%" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    if errorlevel 1 (
        git fetch origin -q >> "%LOG%" 2>&1
        git merge -X ours origin/main -m "sync drill (retry push)" >> "%LOG%" 2>&1
        git push >> "%LOG%" 2>&1
    )
    echo [OK] Drill atualizado e enviado. >> "%LOG%"
) else (
    echo [--] Sem mudancas no drill. >> "%LOG%"
)

REM Sai com sucesso (o git diff --cached --quiet retorna 1 por design).
exit /b 0
