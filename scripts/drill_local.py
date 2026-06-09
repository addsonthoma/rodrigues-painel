# -*- coding: utf-8 -*-
"""
DRILL-DOWN LOCAL (executar no PC do escritorio com Chrome aberto e logado no e-SCI).

Le cookies do Chrome automaticamente (via browser_cookie3) e enriquece os MULs/AFs
do painel com: telefone, email, exigencia, prazo, responsavel, valor da multa.

Salva docs/qbQv3yHGdx6ocaYE/drill.json e faz commit no repo.

Como rodar:
    cd PainelGithub
    python scripts/drill_local.py

Como rodar SEMPRE (1x por dia): duplo-clique em scripts/drill_local.bat
"""
import json, os, sys, time, urllib.request, urllib.error
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

# === Dependencia ===
try:
    import browser_cookie3
except ImportError:
    print("\n[!] Instale browser_cookie3 primeiro:")
    print("    pip install browser_cookie3 requests\n")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("\n[!] Instale requests primeiro:")
    print("    pip install requests\n")
    sys.exit(1)

# === Config ===
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG       = "qbQv3yHGdx6ocaYE"
DOCS_DIR   = os.path.join(REPO_ROOT, "docs", SLUG)
DADOS_FP   = os.path.join(DOCS_DIR, "dados.json")
AFS_FP     = os.path.join(DOCS_DIR, "afs.json")
DRILL_FP   = os.path.join(DOCS_DIR, "drill.json")
CACHE_FP   = os.path.join(REPO_ROOT, "scripts", "drill_cache.json")

BASE_URL = "https://esci.cbm.sc.gov.br"
ENDPOINTS = {
    "busca":   "/Safe/Geral/ControllerConsultaGeral/consultaGeralEdificacao/",
    "edif":    "/Safe/Gerencial/ControllerRegistroEdificacoes/carregarDadosEdificacao/",
    "bloco":   "/Safe/Geral/Edificacao/ControllerBloco/carregarDadosBlocoUltimoHomologacaoOuEnquadramento/",
}
PAUSE = 0.3        # 0.5 -> 0.3
TZ_BR = timezone(timedelta(hours=-3))
MAX_PROCESSAR = 50  # so processa N autos por rodada (priorizando os mais recentes)
SAVE_EVERY = 5      # salva parcial a cada 5 autos

# === Sessao com cookies ===
# Modo 1: tentar ler cookies do Chrome automaticamente (precisa admin)
# Modo 2: ler de cookies.txt na pasta scripts/ (sem admin)
COOKIES_TXT = os.path.join(REPO_ROOT, "scripts", "cookies.txt")

def carregar_cookies_arquivo():
    """Le cookies de um arquivo texto formato Netscape ou linha simples."""
    if not os.path.exists(COOKIES_TXT):
        return None
    cookies = {}
    with open(COOKIES_TXT, encoding="utf-8") as f:
        content = f.read().strip()
    # Formato 1: linha "Cookie: nome=valor; nome2=valor2" do DevTools
    if "Cookie:" in content or "; " in content and "=" in content:
        # extrair tudo apos "Cookie:" se houver
        raw = content.split("Cookie:", 1)[-1].strip()
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()
    # Formato 2: Netscape tab-separated
    else:
        for line in content.splitlines():
            if line.startswith("#") or not line.strip(): continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    return cookies if cookies else None

def get_session():
    cookies = None
    # Tentar arquivo primeiro (mais simples, sem admin)
    arq = carregar_cookies_arquivo()
    if arq:
        print(f"[*] Cookies carregados de {COOKIES_TXT} ({len(arq)} cookies).")
        cookies = arq
    else:
        # Tentar browser_cookie3 (pode pedir admin)
        print("[*] Tentando ler cookies do Chrome automaticamente...")
        try:
            cj = browser_cookie3.chrome(domain_name="esci.cbm.sc.gov.br")
            cookies = {c.name: c.value for c in cj}
            if cookies:
                print(f"[*] {len(cookies)} cookies lidos do Chrome.")
        except Exception as e:
            print(f"[!] Falha ao ler do Chrome: {e}")
    if not cookies:
        print("\n[!] Sem cookies! Faca uma destas opcoes:")
        print()
        print("  OPCAO A (mais facil): copiar cookies do DevTools")
        print("    1. No Chrome, vai em https://esci.cbm.sc.gov.br/ (LOGADO)")
        print("    2. F12 -> Application -> Cookies -> esci.cbm.sc.gov.br")
        print("    3. Clica com botao direito em qualquer cookie -> Copy all as JSON")
        print("       (ou copia 1 a 1 manualmente)")
        print("    4. OU mais facil: no console (F12 -> Console), cole isto e Enter:")
        print()
        print("       copy(document.cookie)")
        print()
        print(f"    5. Cole o conteudo em: {COOKIES_TXT}")
        print()
        print("  OPCAO B (admin): rode este script como administrador (botao direito > Run as admin)")
        sys.exit(1)
    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 RodriguesPreventivos drill_local"
    })
    return s

def api(s, endpoint_key, payload):
    url = BASE_URL + ENDPOINTS[endpoint_key]
    r = s.post(url, json=payload, timeout=20)
    if r.status_code != 200:
        return None
    # Se a sessao expirou, retorna HTML (login page)
    if r.text.startswith("<"):
        return "EXPIRED"
    try:
        return r.json()
    except Exception:
        return None

# === Drill por edificacao ===
def drill_edificacao(s, codg_edif, numg_edif):
    """Retorna lista de autos (AF+MUL) com responsavel, exigencias, prazos."""
    edif = api(s, "edif", {"numgEdificacao": numg_edif})
    if edif == "EXPIRED": return "EXPIRED"
    if not edif or not isinstance(edif, dict):
        return []
    blocos = edif.get("bloco") or []
    autos = []
    for bloco in blocos:
        numg_bloco = bloco.get("numgBloco")
        if not numg_bloco: continue
        dados = api(s, "bloco", {"numgBloco": numg_bloco, "numgAreaEspecifica": None, "numgEmpresa": None})
        if dados == "EXPIRED": return "EXPIRED"
        if not dados: continue
        # estrutura: dados["autos"]["FISCALIZACAO"] e ["INFRACAO"]
        autos_dict = dados.get("autos", {}) or {}
        for tipo, lista in autos_dict.items():
            for a in (lista or []):
                resp = (a.get("pai") or {}).get("responsavel") or {}
                pend = a.get("pendenciaObra") or []
                exigencias = []
                prazo_min = None
                for p in pend:
                    eo = (p.get("exigenciaObra") or {})
                    desc = eo.get("descExigenciaObra")
                    if desc and desc not in exigencias:
                        exigencias.append(desc)
                    pc = p.get("prazoParaConclusao")
                    if pc is not None and (prazo_min is None or pc < prazo_min):
                        prazo_min = pc
                autos.append({
                    "tipo": tipo,                    # FISCALIZACAO ou INFRACAO
                    "codgAuto": a.get("codgAuto"),
                    "numgAuto": a.get("numgAuto"),
                    "cidade": a.get("nomeCidade"),
                    "responsavel": resp.get("nomeResponsavel"),
                    "cpfCnpj": resp.get("codgCpfCnpjResponsavel"),
                    "celular": resp.get("celular"),
                    "email": resp.get("email"),
                    "endereco_responsavel": resp.get("endereco"),
                    "exigencias": exigencias,
                    "dataPrazo": a.get("dataPrazo"),
                    "prazoDias": prazo_min,
                    "bombeiroAutuacao": a.get("bombeiroAutuacao"),
                    "bloco": bloco.get("nomeBloco"),
                })
        time.sleep(PAUSE)
    return autos

def buscar_numg_edif(s, codg_auto):
    """Recupera numgEdificacao a partir do codigo do auto (AF.../MUL...)."""
    # API publica (so precisa cookies da mesma sessao por seguranca)
    res = api(s, "busca", {"texto": codg_auto, "numgCidade": None, "numrQuantidade": 50, "flagMostrarReExcluido": False, "flagOnlyAuto": True})
    if res == "EXPIRED": return None
    if not res or not isinstance(res, list) or not res: return None
    return res[0].get("numgEdificacao"), res[0].get("codgEdificacao")

# === Cache ===
def carregar_cache():
    if os.path.exists(CACHE_FP):
        try: return json.load(open(CACHE_FP, encoding="utf-8"))
        except: pass
    return {}

def salvar_cache(c):
    json.dump(c, open(CACHE_FP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# === Main ===
def main():
    s = get_session()

    # Carregar todos os autos atuais do painel
    print("[*] Lendo painel atual...")
    todos = []
    if os.path.exists(DADOS_FP):
        d = json.load(open(DADOS_FP, encoding="utf-8"))
        for cid, lst in (d.get("multas") or {}).items():
            for m in lst:
                todos.append({"codgAuto": m["CodigoAuto"], "cidade": cid, "tipo": "MUL", "nome": m["Nome_Edificacao"]})
    if os.path.exists(AFS_FP):
        d = json.load(open(AFS_FP, encoding="utf-8"))
        for cid, lst in (d.get("afs") or {}).items():
            for a in lst:
                todos.append({"codgAuto": a["CodigoAuto"], "cidade": cid, "tipo": "AF", "nome": a["Nome_Edificacao"]})

    # Ordenar por numero do auto DESC (mais novos primeiro)
    def num_auto(c):
        try: return int(c["codgAuto"].split("/")[0][7:13])
        except: return 0
    todos.sort(key=num_auto, reverse=True)
    total_inicial = len(todos)
    if MAX_PROCESSAR and len(todos) > MAX_PROCESSAR:
        todos = todos[:MAX_PROCESSAR]
    print(f"[*] {total_inicial} autos no painel, processando os {len(todos)} mais recentes.")

    # cache para nao re-baixar
    cache = carregar_cache()
    drill_data = {}        # {codgAuto: dados_drill}
    edif_to_autos = {}     # {numgEdificacao: [autos_drill]}

    processados = 0
    cache_hits = 0
    expired = False
    t0 = time.time()

    def salvar_parcial():
        out = {
            "timestamp": datetime.now(TZ_BR).isoformat(timespec="seconds"),
            "total": len(drill_data),
            "expired": expired,
            "drill": drill_data
        }
        os.makedirs(DOCS_DIR, exist_ok=True)
        json.dump(out, open(DRILL_FP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        salvar_cache(cache)

    # Primeiro, popular do cache (gratis, sem chamadas)
    for item in todos:
        codg = item["codgAuto"]
        if codg in cache and cache[codg].get("_ts") and (time.time() - cache[codg]["_ts"]) < 7*86400:
            drill_data[codg] = cache[codg]
            cache_hits += 1
    print(f"[*] Cache: {cache_hits} ja conhecidos.")

    # Agora processar os que faltam
    pendentes = [it for it in todos if it["codgAuto"] not in drill_data]
    print(f"[*] A processar: {len(pendentes)} novos.\n")

    for idx, item in enumerate(pendentes, 1):
        codg = item["codgAuto"]
        elapsed = time.time() - t0
        rate = processados / elapsed if elapsed > 0 and processados > 0 else 0
        eta = ((len(pendentes) - idx) / rate) if rate > 0 else 0
        print(f"[{idx}/{len(pendentes)}] {codg} {item['nome'][:35]:35s}", end=" ", flush=True)

        r = buscar_numg_edif(s, codg)
        if r is None:
            print("skip(404)")
            continue
        numg_edif, codg_edif = r
        if not numg_edif:
            print("skip(no numg)")
            continue

        if numg_edif not in edif_to_autos:
            autos = drill_edificacao(s, codg_edif, numg_edif)
            if autos == "EXPIRED":
                print("\n[!] SESSAO EXPIRADA. Faca login no Chrome e refaca cookies.txt.")
                expired = True
                break
            edif_to_autos[numg_edif] = autos

        achou_principal = False
        for a in edif_to_autos[numg_edif]:
            cache_entry = dict(a); cache_entry["_ts"] = time.time()
            if a.get("codgAuto"):
                cache[a["codgAuto"]] = cache_entry
                drill_data[a["codgAuto"]] = cache_entry
                if a.get("codgAuto") == codg:
                    achou_principal = True
                    ex = (a.get("exigencias") or ["—"])[0]
                    tel = a.get("celular") or "—"
                    print(f"OK | {tel} | {ex[:30]}")
        if not achou_principal:
            print("(sem auto correspondente)")

        processados += 1
        if processados % SAVE_EVERY == 0:
            salvar_parcial()
            print(f"   [salvo parcial: {len(drill_data)} no JSON, ~{eta:.0f}s restantes]")
        time.sleep(PAUSE)

    salvar_cache(cache)

    # Salvar drill.json final
    salvar_parcial()
    total_segs = time.time() - t0
    print(f"\n[OK] {len(drill_data)} autos enriquecidos em {total_segs:.0f}s ({cache_hits} do cache, {processados} novos).")
    print(f"     {DRILL_FP}")
    if expired:
        print("\n[AVISO] Sessao expirou no meio. Faltam autos pra processar - rode de novo apos login.")

if __name__ == "__main__":
    main()
