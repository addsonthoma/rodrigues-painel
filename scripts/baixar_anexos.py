# -*- coding: utf-8 -*-
"""
Baixa os anexos (PDFs do projeto) de um protocolo e zipa, pra analise detalhada.
Usa os ids de anexo ja gravados em protocolos.json (campo 'anexos', do drill).
Download: GET .../ControllerDocumento/downloadDocumento/?documento={id} (logado).

Uso:
  python scripts/baixar_anexos.py A8055007979A      # 1 protocolo
  python scripts/baixar_anexos.py Brusque           # todos os protocolos da cidade (com anexo)
  python scripts/baixar_anexos.py deferidos         # todos os protocolos DEFERIDOS (com anexo)
  python scripts/baixar_anexos.py deferidos Brusque # deferidos de Brusque

Saida: anexos_protocolos/{CodigoProtocolo}.zip  (pasta gitignored)
Cookies: scripts/cookies.txt (mesmo do drill).
"""
import json, os, sys, time, zipfile, io, requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG = "qbQv3yHGdx6ocaYE"
PROTO_FP = os.path.join(REPO_ROOT, "docs", SLUG, "protocolos.json")
COOKIES_TXT = os.path.join(REPO_ROOT, "scripts", "cookies.txt")
OUT_DIR = os.path.join(REPO_ROOT, "anexos_protocolos")
BASE = "https://esci.cbm.sc.gov.br"
DL = BASE + "/Safe/Geral/Tecnico/ControllerDocumento/downloadDocumento/?documento="

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

def get_session():
    ck = load_cookies()
    if not ck:
        print(f"[!] Sem cookies em {COOKIES_TXT}."); sys.exit(1)
    s = requests.Session(); s.cookies.update(ck)
    s.headers.update({"User-Agent": "Mozilla/5.0 RodriguesPreventivos baixar_anexos",
                      "Accept": "*/*"})
    return s

def safe_name(nome, idx, doc_id):
    nome = (nome or f"anexo_{doc_id}.pdf").replace("/", "_").replace("\\", "_").strip()
    if not nome.lower().endswith(".pdf") and "." not in nome:
        nome += ".pdf"
    return f"{idx:02d}_{nome}"

def selecionar(data, args):
    por_cidade = data.get("protocolos") or {}
    so_deferidos = "deferidos" in [a.lower() for a in args]
    cidades_arg = [a for a in args if a.lower() != "deferidos"]
    codigos_arg = [a for a in cidades_arg if a.upper().startswith("A") and a[1:5].isdigit()]
    cidades_filtro = [a for a in cidades_arg if a not in codigos_arg]
    sel = []
    for cidade, lst in por_cidade.items():
        if cidades_filtro and cidade not in cidades_filtro: continue
        for p in lst:
            if codigos_arg and p.get("CodigoProtocolo") not in codigos_arg: continue
            if so_deferidos and not p.get("deferido"): continue
            if not (p.get("anexos") or []): continue
            sel.append(p)
    return sel

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    if not os.path.exists(PROTO_FP):
        print("[!] protocolos.json nao existe. Rode coletar_protocolos.py + drill_protocolos.py antes."); return
    data = json.load(open(PROTO_FP, encoding="utf-8"))
    alvos = selecionar(data, args)
    if not alvos:
        print("[!] Nenhum protocolo com anexo bateu o filtro. (rode drill_protocolos.py p/ popular os anexos?)")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    s = get_session()
    print(f"[*] {len(alvos)} protocolo(s) com anexo. Baixando...")
    feitos = 0
    for p in alvos:
        cod = p["CodigoProtocolo"]
        anexos = p.get("anexos") or []
        zip_fp = os.path.join(OUT_DIR, f"{cod}.zip")
        buf = io.BytesIO()
        ok = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # um indice txt com os dados do lead
            info = (f"Protocolo: {cod}\nEdificacao: {p.get('Nome_Edificacao','')}\n"
                    f"Endereco: {p.get('Logradouro','')} {p.get('Numero','')} - {p.get('Cidade','')}\n"
                    f"Area: {p.get('area','')} m2 | Data: {p.get('data','')} | Situacao: {p.get('situacao','')}\n"
                    f"Deferido: {p.get('deferido')}\n")
            zf.writestr("_LEAD.txt", info)
            for i, a in enumerate(anexos, 1):
                doc_id = a.get("id")
                if not doc_id: continue
                try:
                    r = s.get(DL + str(doc_id), timeout=60)
                    if r.status_code == 200 and not r.content[:15].startswith(b"<"):
                        zf.writestr(safe_name(a.get("nome"), i, doc_id), r.content)
                        ok += 1
                    else:
                        print(f"    ! anexo {doc_id} de {cod}: HTTP {r.status_code} (cookie expirado?)")
                except Exception as e:
                    print(f"    ! anexo {doc_id} de {cod}: {e}")
                time.sleep(0.3)
        if ok:
            with open(zip_fp, "wb") as f:
                f.write(buf.getvalue())
            feitos += 1
            print(f"  [{cod}] {ok}/{len(anexos)} anexo(s) -> {os.path.relpath(zip_fp, REPO_ROOT)}")
        else:
            print(f"  [{cod}] nenhum anexo baixado.")
    print(f"\n[OK] {feitos} zip(s) em {os.path.relpath(OUT_DIR, REPO_ROOT)}/")

if __name__ == "__main__":
    main()
