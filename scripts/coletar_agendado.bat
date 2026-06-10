@echo off
REM Coletor LOCAL agendado - roda a cada 10 min em horario comercial (PC do escritorio).
REM Mantem o painel atualizado de forma CONFIAVEL, sem depender do cron do GitHub Actions
REM (que no plano free derruba a maioria das execucoes agendadas).
REM Roda OCULTO via coletar_oculto.vbs (sem janela piscando na TV).
cd /d "%~dp0\.."
set LOG=scripts\coletar_agendado.log
echo ====== %DATE% %TIME% ====== > "%LOG%"

REM 1) sincroniza com o repo (pega commits do bot/drill antes de coletar)
git pull --rebase --autostash >> "%LOG%" 2>&1

REM 2) coleta multas + AFs (API publica e-SCI, sem login)
python scripts\coletar.py >> "%LOG%" 2>&1
python scripts\coletar_afs.py >> "%LOG%" 2>&1

REM 3) sobe pro painel
git add docs/qbQv3yHGdx6ocaYE/dados.json docs/qbQv3yHGdx6ocaYE/afs.json scripts/estado.json scripts/estado_afs.json
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Coleta local automatica" >> "%LOG%" 2>&1
    git pull --rebase --autostash >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    echo [OK] painel atualizado >> "%LOG%"
) else (
    echo [--] sem mudancas >> "%LOG%"
)
exit /b 0
