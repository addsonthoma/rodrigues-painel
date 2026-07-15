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
MAX_PROCESSAR = 200 # cobre todos os AFs do painel
SAVE_EVERY = 5      # salva parcial a cada 5 autos
SO_AFS = True       # True = processa so AFs (pendencia mora no AF). False = MUL+AF
FILTRO_HOT = False  # True = so empresas grandes. False = todos

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

def api(s, endpoint_key, payload, max_retries=3):
    url = BASE_URL + ENDPOINTS[endpoint_key]
    # Retry com backoff em erros de rede (e-SCI corta conexao as vezes - ConnectionReset 10054).
    # Sem isso, um soluco de rede derrubava o drill inteiro no meio.
    for attempt in range(max_retries):
        try:
            r = s.post(url, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"  [rede] {e.__class__.__name__} apos {max_retries}x, pulando", flush=True)
            return None
        if r.status_code != 200:
            return None
        # Se a sessao expirou, retorna HTML (login page)
        if r.text.startswith("<"):
            return "EXPIRED"
        try:
            return r.json()
        except Exception:
            return None
    return None

# === Parsers de responsavel (fallback p/ edificacao sem auto no bloco) ===
def parse_contato(contatos):
    """contatos pode vir {} vazio, dict de listas, ou lista. Extrai (celular, email)."""
    cel = email = None
    items = []
    if isinstance(contatos, dict):
        for v in contatos.values():
            if isinstance(v, list): items.extend(v)
            elif isinstance(v, dict): items.append(v)
    elif isinstance(contatos, list):
        items = contatos
    for it in items:
        if not isinstance(it, dict): continue
        val = it.get("descContato") or it.get("valor") or it.get("codgContato")
        s_ = str(val or "").strip()
        if not s_: continue
        if "@" in s_:
            email = email or s_
        else:
            digits = "".join(ch for ch in s_ if ch.isdigit())
            if len(digits) >= 8:
                cel = cel or s_
    return cel, email

def parse_resps_edif(edif):
    """Responsaveis no nivel da edificacao: [{nome, cpfCnpj, celular, email}].
    Serve de fallback quando o AF nao tem auto no bloco (ex.: sem PPCI homologado)."""
    re_ = edif.get("responsaveisEdificacao")
    lst = re_ if isinstance(re_, list) else ([re_] if isinstance(re_, dict) and re_ else [])
    out = []
    for r in lst:
        p = (r or {}).get("pessoa") or {}
        if not p: continue
        cel, email = parse_contato(p.get("contatos"))
        out.append({
            "nome": p.get("nomeCompleto"),
            "cpfCnpj": p.get("codgCpf") or p.get("codgCnpj"),
            "celular": cel,
            "email": email,
        })
    # quem tem contato vem primeiro
    out.sort(key=lambda x: (x.get("celular") is None, x.get("email") is None))
    return out

# === Drill por edificacao ===
def drill_edificacao(s, codg_edif, numg_edif):
    """Retorna (autos, resps_edif): autos do bloco + responsaveis da edificacao (fallback)."""
    edif = api(s, "edif", {"numgEdificacao": numg_edif})
    if edif == "EXPIRED": return "EXPIRED"
    if not edif or not isinstance(edif, dict):
        return ([], [])
    resps_edif = parse_resps_edif(edif)
    blocos = edif.get("bloco") or []
    autos = []
    for bloco in blocos:
        numg_bloco = bloco.get("numgBloco")
        if not numg_bloco: continue
        dados = api(s, "bloco", {"numgBloco": numg_bloco, "numgAreaEspecifica": None, "numgEmpresa": None})
        if dados == "EXPIRED": return "EXPIRED"
        if not dados: continue
        # estrutura: dados["autos"]["FISCALIZACAO"] (AF direto) e ["INFRACAO"] (com sub-MUL aninhada)
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
                base_auto = {
                    "tipo": tipo,
                    "areaTotal": dados.get("numrAreaTotal"),      # m2 da edificacao (mesma fonte da aba Protocolos)
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
                }
                # Adicionar o auto principal (se tem codgAuto)
                if a.get("codgAuto"):
                    autos.append(dict(base_auto, codgAuto=a.get("codgAuto"), numgAuto=a.get("numgAuto")))
                # NOVO: descer em sub-autos (INFRACAO normalmente tem .autos[] com a MUL real)
                for sub in (a.get("autos") or []):
                    if sub.get("codgAuto"):
                        autos.append(dict(base_auto, codgAuto=sub.get("codgAuto"), numgAuto=sub.get("numgAuto"), tipo=sub.get("codgTipoAuto") or tipo))
        time.sleep(PAUSE)
    return (autos, resps_edif)

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
    if os.path.exists(DADOS_FP) and not SO_AFS:
        d = json.load(open(DADOS_FP, encoding="utf-8"))
        for cid, lst in (d.get("multas") or {}).items():
            for m in lst:
                todos.append({"codgAuto": m["CodigoAuto"], "cidade": cid, "tipo": "MUL", "nome": m["Nome_Edificacao"]})
    if os.path.exists(AFS_FP):
        d = json.load(open(AFS_FP, encoding="utf-8"))
        for cid, lst in (d.get("afs") or {}).items():
            for a in lst:
                todos.append({"codgAuto": a["CodigoAuto"], "cidade": cid, "tipo": "AF", "nome": a["Nome_Edificacao"]})

    # FILTRO QUENTE: so empresas grandes (LTDA, EIRELI, industria, comercio, posto, construtora, etc)
    KEYWORDS_HOT = [
        " LTDA", " EIRELI", " EPP", " ME", " S/A", " S.A", " S A",
        "INDUSTRIA", "INDÚSTRIA", "COMERCIO", "COMÉRCIO", "TEXTIL", "TÊXTIL",
        "GALP", "POSTO", "ATACAD", "SHOP", "CENTER", "DISTRIB",
        "CONSTRUTORA", "ADMINISTRAD", "PARTICIPA", "INCORPORA", "EMPREEND",
        "MALHA", "FIACAO", "TINTURARIA", "CONFEC", "RECICL", "TRANSPORTAD",
        "CONDOMINIO", "RESIDENCIAL", "EDIFICIO", "EDIFÍCIO", "PRÉDIO",
        "CERAMICA", "CERÂMICA", "MOVEIS", "MÓVEIS", "MARMORARIA",
        "ESQUADRIA", "TECELAGEM", "AUTO PE", "REFLORESTAD", "ASSOCIA",
        "FUNDO DE", "IMOV", "IMÓV", "HOTEL", "POUSADA", "CLUB"
    ]
    def eh_hot(nome):
        n = (nome or "").upper()
        return any(kw in n for kw in KEYWORDS_HOT)
    if FILTRO_HOT:
        todos_hot = [t for t in todos if eh_hot(t["nome"])]
        print(f"[*] {len(todos)} autos no painel, {len(todos_hot)} sao hot leads (empresas/predios).")
        todos = todos_hot
    else:
        print(f"[*] {len(todos)} autos no painel ({'so AFs' if SO_AFS else 'MUL+AF'}), sem filtro hot.")

    # Ordenar dentro de cada cidade por numero DESC, depois pegar N por cidade (round-robin)
    def num_auto(c):
        try: return int(c["codgAuto"].split("/")[0][7:13])
        except: return 0
    por_cidade = {}
    for x in todos:
        por_cidade.setdefault(x["cidade"], []).append(x)
    for cid in por_cidade:
        por_cidade[cid].sort(key=num_auto, reverse=True)

    total_inicial = len(todos)
    # round-robin: 1 de cada cidade, depois 2 de cada, ate atingir MAX_PROCESSAR
    selecionados = []
    if MAX_PROCESSAR:
        # quantos por cidade = teto(MAX / qtd_cidades)
        per_cidade = max(1, MAX_PROCESSAR // max(1, len(por_cidade)))
        for cid, lst in por_cidade.items():
            selecionados.extend(lst[:per_cidade])
        # se sobrou espaco, completar com restos
        restantes = MAX_PROCESSAR - len(selecionados)
        if restantes > 0:
            for cid, lst in por_cidade.items():
                extras = lst[per_cidade:per_cidade+restantes]
                selecionados.extend(extras)
                restantes -= len(extras)
                if restantes <= 0: break
        todos = selecionados[:MAX_PROCESSAR]
    print(f"[*] {total_inicial} autos no painel ({len(por_cidade)} cidades), processando {len(todos)} ({per_cidade if MAX_PROCESSAR else 'todos'} por cidade).")

    # cache para nao re-baixar
    cache = carregar_cache()
    # ACUMULA: comeca com TODO o cache (preserva MULs/AFs enriquecidos em rodadas anteriores)
    drill_data = {k: dict(v) for k, v in cache.items()}
    edif_to_autos = {}     # {numgEdificacao: [autos_drill]}
    edif_to_resp  = {}     # {numgEdificacao: [resps_edif]} (fallback p/ AF sem auto no bloco)

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
        if codg in cache and cache[codg].get("_ts") and (time.time() - cache[codg]["_ts"]) < 7*86400 and not cache[codg].get("parcial") and ("areaTotal" in cache[codg]):
            drill_data[codg] = cache[codg]
            cache_hits += 1
    print(f"[*] Cache: {cache_hits} ja conhecidos.")

    # Agora processar os que faltam
    # re-processa tambem quem ainda nao tem areaTotal (backfill da metragem, 2026-07-15)
    pendentes = [it for it in todos if it["codgAuto"] not in drill_data
                 or drill_data[it["codgAuto"]].get("parcial")
                 or "areaTotal" not in drill_data[it["codgAuto"]]]
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
            res_drill = drill_edificacao(s, codg_edif, numg_edif)
            if res_drill == "EXPIRED":
                print("\n[!] SESSAO EXPIRADA. Faca login no Chrome e refaca cookies.txt.")
                expired = True
                break
            autos, resps_edif = res_drill
            edif_to_autos[numg_edif] = autos
            edif_to_resp[numg_edif] = resps_edif

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
            # FALLBACK: edificacao sem auto no bloco (ex.: AF novo sem PPCI homologado).
            # Pega ao menos o responsavel da edificacao. Marca 'parcial' p/ re-tentar
            # nas proximas rodadas (auto-cura quando a edificacao ganhar processo).
            resps = edif_to_resp.get(numg_edif) or []
            r0 = resps[0] if resps else {}
            fb = {
                "tipo": item["tipo"], "cidade": item["cidade"],
                "responsavel": r0.get("nome"), "cpfCnpj": r0.get("cpfCnpj"),
                "celular": r0.get("celular"), "email": r0.get("email"),
                "exigencias": [], "prazoDias": None,
                "nota": "Edificacao sem processo homologado — pendencia so no PDF do AF (botao e-SCI)",
                "parcial": True, "codgAuto": codg, "_ts": time.time(),
            }
            drill_data[codg] = fb
            cache[codg] = fb
            nm = (r0.get("nome") or "?")[:25]
            print(f"PARCIAL (resp: {nm})")

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
