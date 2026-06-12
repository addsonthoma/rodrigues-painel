$ErrorActionPreference = 'SilentlyContinue'
function J($p){ if (Test-Path $p) { Get-Content $p -Raw | ConvertFrom-Json } }
function Fmt($ts){ if ($ts) { ($ts -replace 'T',' ').Substring(0,16) } else { '?' } }

$drill = J "docs\qbQv3yHGdx6ocaYE\drill.json"
$dados = J "docs\qbQv3yHGdx6ocaYE\dados.json"
$dInfo = Get-ScheduledTaskInfo -TaskName 'RodriguesPreventivos_DrillDiario'
$cInfo = Get-ScheduledTaskInfo -TaskName 'RodriguesPreventivos_ColetaPainel10min'

Write-Host ""
Write-Host "====== STATUS DO PAINEL - Rodrigues Preventivos ======" -ForegroundColor Cyan
Write-Host ""
Write-Host "CONTATOS (drill - roda todo dia 08:30)" -ForegroundColor Yellow
if ($drill) {
  $tel = ($drill.drill.PSObject.Properties.Value | Where-Object { $_.celular }).Count
  Write-Host ("  Ultima atualizacao : " + (Fmt $drill.timestamp))
  Write-Host ("  Contatos no painel : " + $drill.total + "  (" + $tel + " com telefone)")
} else { Write-Host "  (drill ainda nao gerou dados)" }
Write-Host ("  Proximo drill      : " + $dInfo.NextRunTime)
Write-Host ""
Write-Host "MULTAS / FISCALIZACOES (coletor - a cada 10 min, 08-18h)" -ForegroundColor Yellow
if ($dados) { Write-Host ("  Ultima coleta      : " + (Fmt $dados.timestamp)) }
Write-Host ("  Proxima coleta     : " + $cInfo.NextRunTime)
Write-Host ""
Write-Host "REGRA SIMPLES:" -ForegroundColor Green
Write-Host "  Se 'Ultima atualizacao' do drill for de HOJE (depois das 08:30)," -ForegroundColor Green
Write-Host "  entao o drill rodou hoje e os contatos estao em dia." -ForegroundColor Green
Write-Host ""
