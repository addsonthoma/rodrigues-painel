# Como publicar no GitHub Pages

Você só precisa fazer isso UMA VEZ. Depois é automático para sempre.

## Pré-requisitos
- Conta no GitHub (você disse que tem)
- Git instalado no PC (`git --version` no terminal pra verificar)

## Passo 1: criar o repositório no GitHub

1. Vá em https://github.com/new
2. Repository name: `rodrigues-painel` (ou outro nome que preferir)
3. **Public** (precisa ser público para o Pages funcionar grátis. A URL é ofuscada, só quem tiver o link entra)
4. NÃO marque "Add a README" / "gitignore" / "license" (já temos esses arquivos)
5. Clique em **Create repository**

## Passo 2: subir os arquivos

No PowerShell, dentro da pasta `PainelGithub`:

```powershell
cd "C:\Users\User\Documents\Rodrigues_Preventivos_Leads\PainelGithub"
git init
git add .
git commit -m "Setup inicial do painel"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/rodrigues-painel.git
git push -u origin main
```

(troque `SEU-USUARIO` pelo seu nome de usuário GitHub)

Se pedir login, autentique com seu usuário + token de acesso pessoal (Settings → Developer settings → Personal access tokens).

## Passo 3: ativar GitHub Pages

1. No repositório, vá em **Settings** (aba do topo)
2. Menu lateral: **Pages**
3. **Source**: "Deploy from a branch"
4. **Branch**: `main` / pasta `/docs`
5. **Save**
6. Aguarde ~1 minuto. A URL aparece no topo da página.

## Passo 4: ativar GitHub Actions (coleta automática)

1. No repositório, aba **Actions**
2. Se aparecer "Workflows aren't being run on this repository", clique em **I understand my workflows, go ahead and enable them**
3. Pronto - o workflow `Polling de multas CBMSC` vai rodar automaticamente a cada 10 min em horário comercial BRT

## Passo 5: testar

Abra a URL: `https://SEU-USUARIO.github.io/rodrigues-painel/qbQv3yHGdx6ocaYE/`

(Pages demora ~5 min na primeira publicação)

## Passo 6: testar a TV

1. Pegue o link e abra direto no navegador da TV smart (digitando ou compartilhando do celular)
2. Tela cheia (geralmente um botão no canto)
3. Pronto

## Forçar uma coleta agora (sem esperar 10 min)

1. Aba **Actions** do seu repositório
2. Clique em "Polling de multas CBMSC" na lista
3. Botão **Run workflow** (direita) → confirma
4. Em ~30s ele roda. Painel atualiza no próximo refresh (60s)

## Trocar a URL secreta

Edite `scripts/coletar.py` linha `SLUG = "..."` + renomeie a pasta `docs/qbQv3yHGdx6ocaYE/` para o mesmo nome + commit + push. Nova URL no ar em ~1 min.

## Custo

R$ 0,00 / mês — GitHub Pages e GitHub Actions são gratuitos para repos públicos sem limite prático.
