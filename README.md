# Painel de Multas CBMSC - Rodrigues Preventivos

Painel em tempo real das multas (Autos de Infração) do Corpo de Bombeiros Militar de SC, com coleta automática via GitHub Actions e exibição em qualquer TV/navegador.

## URL do painel (depois do deploy)

```
https://SEU-USUARIO.github.io/NOME-DO-REPO/qbQv3yHGdx6ocaYE/
```

(troque `SEU-USUARIO` e `NOME-DO-REPO`)

## Estrutura

```
docs/qbQv3yHGdx6ocaYE/  - painel publicado (URL ofuscada)
  index.html            - frontend (auto-refresh a cada 60s)
  dados.json            - dados consumidos pelo painel
scripts/
  coletar.py            - script Python que chama a API CBMSC
  estado.json           - controle do último código de cada cidade
  eventos.json          - histórico de detecções
.github/workflows/
  poll.yml              - GitHub Actions: roda coletar.py a cada 10 min em horário comercial BRT
```

## Como funciona

1. **GitHub Actions** (gratuito) roda `scripts/coletar.py` a cada 10 minutos das 08:00 às 18:00 BRT (seg-sex)
2. O script tenta o **próximo número** de cada cidade no portal e-SCI CBMSC
3. Se achar nova multa: atualiza `docs/qbQv3yHGdx6ocaYE/dados.json` + faz commit/push
4. O painel HTML (já carregado na TV) busca o JSON a cada 60s
5. Quando detecta código novo: **banner vermelho desce com som "ding"** e marca a linha em laranja

## Adicionar/remover cidade

Edite `scripts/estado.json`. Cada cidade tem `prefixo` (4 dígitos), `ultimo_numero`, `ano_corrente`. O script vai testar `ultimo_numero + 1` em diante.

## Mudar URL ofuscada

1. Renomeie a pasta `docs/qbQv3yHGdx6ocaYE/` para outro slug (qualquer string)
2. Edite `scripts/coletar.py` linha 11: `SLUG = "novo-slug"`
3. Commit + push
