# -*- coding: utf-8 -*-
"""
Enriquece os protocolos de protocolos.json com area / data / deferido / anexos,
puxando de processos.projetos da edificacao (endpoint logado, mesmo do drill).

Casa pelo codgProtocolo. Drila cada numgEdificacao UMA vez (varios protocolos
podem ser do mesmo predio). Salva de volta em protocolos.json.

Cookies: scripts/cookies.txt (mesmo do drill_local). Uso: python scripts/drill_protocolos.py
"""
import json, os, sys, time, requests
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG = "qbQv3yHGdx6ocaYE"
PROTO_FP = os.path.join(REPO_ROOT, "docs", SLUG, "protocolos.json")
ENRICH_FP = os.path.join(REPO_ROOT, "docs", SLUG, "protocolos_enrich.json")
COOKIES_TXT = os.path.join(REPO_ROOT, "scripts", "cookies.txt")
BASE = "https://esci.cbm.sc.gov.br"
EP = {
    "edif":  "/Safe/Gerencial/ControllerRegistroEdificacoes/carregarDadosEdificacao/",
    "bloco": "/Safe/Geral/Edificacao/ControllerBloco/carregarDadosBlocoUltimoHomologacaoOuEnquadramento/",
    "docsAnalise": "/Safe/Analise/ControllerAnaliseProjeto/carregarDocumentosSolicitacaoAnalise/",
}
PAUSE = 0.3
TZ_BR = timezone(timedelta(hours=-3))

def load_cookies():
    if not os.path.exists(COOKIES_TXT): return None
    content = open(COOKIES_TXT, encoding="utf-8").read().strip()
    raw = content.split("Cookie:", 1)[-1].strip()
    ck = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1); ck[k.strip()] = v.strip()
    return ck or None

def cookies_do_chrome():
    """Le o cookie fresco direto do Chrome logado no e-SCI (mesma automacao do drill_local)."""
    try:
        import browser_cookie3
        cj = browser_cookie3.chrome(domain_name="esci.cbm.sc.gov.br")
        ck = {c.name: c.value for c in cj}
        return ck or None
    except Exception as e:
        print(f"[!] browser_cookie3 (Chrome) falhou: {e}")
        return None

def get_session():
    # 1) cookie fresco do Chrome logado (automatico); 2) fallback cookies.txt
    ck = cookies_do_chrome()
    if ck:
        print(f"[*] {len(ck)} cookies lidos do Chrome (e-SCI, fresco).")
    else:
        ck = load_cookies()
        if ck: print(f"[*] Cookies de {COOKIES_TXT}.")
    if not ck:
        print("[!] Sem cookies: Chrome nao logado no e-SCI e cookies.txt vazio.")
        sys.exit(1)
    s = requests.Session(); s.cookies.update(ck)
    s.headers.update({"Content-Type":"application/json;charset=UTF-8",
                      "Accept":"application/json, text/plain, */*",
                      "User-Agent":"Mozilla/5.0 RodriguesPreventivos drill_protocolos"})
    return s

def api(s, key, payload, max_retries=3):
    url = BASE + EP[key]
    for attempt in range(max_retries):
        try:
            r = s.post(url, json=payload, timeout=30)
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1: time.sleep(2*(attempt+1)); continue
            return None
        if r.status_code != 200: return None
        if r.text.startswith("<"): return "EXPIRED"
        try: return r.json()
        except Exception: return None
    return None

def _date(v):
    if isinstance(v, dict): v = v.get("date")
    if not v: return None
    return str(v)[:10]   # YYYY-MM-DD

def projetos_da_edif(s, numg):
    """Retorna {codgProtocolo: enriquecimento} de todos os projetos da edificacao."""
    out = {}
    edif = api(s, "edif", {"numgEdificacao": numg})
    if edif == "EXPIRED": return "EXPIRED"
    if not isinstance(edif, dict): return out
    for bloco in (edif.get("bloco") or []):
        nb = bloco.get("numgBloco")
        if not nb: continue
        d = api(s, "bloco", {"numgBloco": nb, "numgAreaEspecifica": None, "numgEmpresa": None})
        if d == "EXPIRED": return "EXPIRED"
        if not isinstance(d, dict): continue
        for p in ((d.get("processos") or {}).get("projetos") or []):
            cod = p.get("codgProtocolo")
            if not cod: continue
            sit = (p.get("situacao") or {})
            # RELATORIO de indeferimento (NAO o atestado de aprovacao): so docs com categoria de relatorio
            relat = [{"id": dc.get("numgDocumento"), "nome": dc.get("nomeOriginal") or dc.get("nomeDocumento")}
                     for dc in (p.get("documentos") or [])
                     if dc.get("numgDocumento") and dc.get("codgCategoriaRelatorio")]
            # ANEXOS do projeto submetido (PPCI, matricula, ART...) via solicitacao de analise
            anexos = []
            nsp = p.get("numgSolicitacaoProjeto")
            if nsp:
                da = api(s, "docsAnalise", {"numgSolicitacaoProjeto": nsp})
                if da == "EXPIRED": return "EXPIRED"
                if isinstance(da, list):
                    for dc in da:
                        if not dc.get("numgDocumento"): continue
                        anexos.append({
                            "id": dc.get("numgDocumento"),
                            "nome": dc.get("nomeOriginal") or dc.get("nomeDocumento"),
                            "desc": dc.get("descDocumento"),
                        })
                time.sleep(PAUSE)
            out[cod] = {
                "area": p.get("numrAreaTotalSolicitacao"),
                "data": _date(p.get("dataProtocolo")),
                "deferido": bool(p.get("flagDeferido")),
                "situacao": sit.get("descSituacao"),
                "codgSituacao": sit.get("codgSituacao"),
                "cassado": bool(p.get("flagCassado")),
                "anulado": bool(p.get("flagAnulado")),
                "suspenso": bool(p.get("flagSuspenso")),
                "numgProcesso": p.get("numgProcesso"),
                "numgSolicitacaoProjeto": nsp,
                "qtdAnexos": len(anexos),
                "anexos": anexos,        # arquivos de projeto submetidos
                "relatorio": relat,      # relatorio de indeferimento (quando houver)
                "_drillTs": datetime.now(TZ_BR).isoformat(timespec="seconds"),
            }
        time.sleep(PAUSE)
    return out

def _fresco(enr, horas=18):
    if not enr: return False
    ts = enr.get("_drillTs")
    if not ts: return False
    try:
        t = datetime.fromisoformat(ts)
        return (datetime.now(TZ_BR) - t).total_seconds() < horas * 3600
    except Exception:
        return False

def main():
    force = "--force" in sys.argv
    if not os.path.exists(PROTO_FP):
        print("[!] protocolos.json nao existe ainda. Rode coletar_protocolos.py antes."); return
    por_cidade = (json.load(open(PROTO_FP, encoding="utf-8")).get("protocolos") or {})
    # enriquecimento mora em arquivo PROPRIO (a nuvem nunca escreve aqui -> nunca conflita)
    enrich = {}
    if os.path.exists(ENRICH_FP):
        try: enrich = json.load(open(ENRICH_FP, encoding="utf-8")).get("enrich") or {}
        except Exception: enrich = {}

    edif_map = {}; total = 0
    for cidade, lst in por_cidade.items():
        for it in lst:
            total += 1
            ne = it.get("numgEdificacao")
            if ne: edif_map.setdefault(ne, []).append(it)
    print(f"[*] {total} protocolos em {len(edif_map)} edificacoes. Drilando -> protocolos_enrich.json")

    def salvar_enrich():
        json.dump({"timestamp": datetime.now(TZ_BR).isoformat(timespec="seconds"), "enrich": enrich},
                  open(ENRICH_FP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    s = get_session()
    feitos = 0; enriquecidos = 0; pulados = 0
    for ne, itens in edif_map.items():
        # pula edificacao ja enriquecida e fresca (<18h), salvo --force
        if not force and all(_fresco(enrich.get(it["CodigoProtocolo"])) for it in itens):
            pulados += 1; continue
        res = projetos_da_edif(s, ne)
        if res == "EXPIRED":
            print("[!] COOKIE EXPIRADO — renove scripts/cookies.txt e rode de novo.")
            break
        for it in itens:
            er = res.get(it["CodigoProtocolo"])
            if er:
                enrich[it["CodigoProtocolo"]] = er; enriquecidos += 1
        feitos += 1
        if feitos % 10 == 0:
            salvar_enrich()
            print(f"  [{feitos}/{len(edif_map)} edif] {enriquecidos} enriquecidos (parcial salvo)")

    salvar_enrich()
    print(f"\n[OK] {enriquecidos}/{total} protocolos enriquecidos -> protocolos_enrich.json | {pulados} edif. puladas.")

if __name__ == "__main__":
    main()
