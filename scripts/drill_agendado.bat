@echo off
REM Drill agendado - roda sem interacao, loga resultado.
REM Requer: cookies.txt valido (renovar no Chrome de manha) + Chrome logado no e-SCI.
cd /d "%~dp0\.."
set LOG=scripts\drill_agendado.log
echo ====== %DATE% %TIME% ====== >> "%LOG%"

REM garante dependencias
python -c "import browser_cookie3, requests" 2>nul || python -m pip install browser_cookie3 requests --quiet

REM 1) PUXA O PAINEL MAIS RECENTE PRIMEIRO (afs.json/dados.json que o GitHub Actions coletou)
REM    Sem isso o drill rodaria em cima de dados velhos e perderia os AFs novos.
git pull --rebase --autostash >> "%LOG%" 2>&1

REM 2) Roda o drill em cima dos dados FRESCOS
python scripts\drill_local.py >> "%LOG%" 2>&1

REM 3) Agora sim: stage + commit + push (na ordem certa, sem autostash desfazer o stage)
git add docs/qbQv3yHGdx6ocaYE/drill.json scripts/drill_cache.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Drill agendado %DATE%" >> "%LOG%" 2>&1
    git pull --rebase --autostash >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    echo [OK] Drill atualizado e enviado. >> "%LOG%"
) else (
    echo [--] Sem mudancas no drill. >> "%LOG%"
)

REM Sai com sucesso (o git diff --cached --quiet acima retorna 1 por design e
REM nao deve marcar a tarefa agendada como "falha"). O log e a fonte da verdade.
exit /b 0
