@echo off
REM Coletor LOCAL agendado - a cada 10 min em horario comercial (PC do escritorio).
REM SYNC ROBUSTO: usa "checkout main + merge (preferindo o remoto)" em vez de rebase.
REM Motivo: rebase conflitava com os commits do bot (ambos mexem em dados/afs.json) e
REM deixava o repo em DETACHED HEAD, travando o painel (bug de 10/06/2026). Merge nunca
REM conflita nem detacha, e o "checkout main" recupera de qualquer estado solto.
REM Roda OCULTO via coletar_oculto.vbs (sem janela na TV).
cd /d "%~dp0\.."
set LOG=scripts\coletar_agendado.log
echo ====== %DATE% %TIME% ====== > "%LOG%"

REM 0) Garante que estamos na branch main (recupera de detached HEAD se houver)
git checkout main >> "%LOG%" 2>&1

REM 1) Sincroniza via MERGE preferindo o remoto (nunca conflita / nunca detacha)
git fetch origin -q >> "%LOG%" 2>&1
git merge -X theirs origin/main -m "sync coletor" >> "%LOG%" 2>&1

REM 2) Coleta multas + AFs (API publica e-SCI, sem login)
python scripts\coletar.py >> "%LOG%" 2>&1
python scripts\coletar_afs.py >> "%LOG%" 2>&1

REM 3) Commit + push (com 1 retry se o origin mudou no meio)
git add docs/qbQv3yHGdx6ocaYE/dados.json docs/qbQv3yHGdx6ocaYE/afs.json scripts/estado.json scripts/estado_afs.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Coleta local automatica" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    if errorlevel 1 (
        git fetch origin -q >> "%LOG%" 2>&1
        git merge -X ours origin/main -m "sync coletor (retry push)" >> "%LOG%" 2>&1
        git push >> "%LOG%" 2>&1
    )
    echo [OK] painel atualizado >> "%LOG%"
) else (
    echo [--] sem mudancas >> "%LOG%"
)
exit /b 0
