# -*- coding: utf-8 -*-
"""
Manda os leads (multas + AFs + enriquecimento do drill) pro Supabase, pra o
painel COM LOGIN ler com privacidade por vendedor (RLS faz o filtro no banco).

Roda LOCAL. Usa a chave service_role (que IGNORA o RLS pra poder escrever).
A chave fica em scripts/supabase_service_key.txt -> GITIGNORED, NUNCA commitar.

Uso:  python scripts/push_supabase.py
"""
import json, os, sys, urllib.request, urllib.error
from collections import Counter

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG = "qbQv3yHGdx6ocaYE"
DOCS = os.path.join(REPO_ROOT, "docs", SLUG)
KEY_FP = os.path.join(REPO_ROOT, "scripts", "supabase_service_key.txt")

SUPABASE_URL = "https://ziiybllegtdnqwqfaifp.supabase.co"

# Mesma divisao das sub-abas do painel (proximidade da casa)
VENDEDOR = {
    "Brusque": "BANANA", "Guabiruba": "BANANA", "Nova Trento": "BANANA",
    "Gaspar": "BANANA", "Blumenau": "BANANA",
    "Itajai": "GUILHERME", "Navegantes": "GUILHERME",
    "Itapema": "GUILHERME", "Porto Belo": "GUILHERME",
    "Botuvera": "ALINE",
}

def carregar(fp, default):
    if os.path.exists(fp):
        try: return json.load(open(fp, encoding="utf-8"))
        except: pass
    return default

def get_key():
    if not os.path.exists(KEY_FP):
        print(f"\n[!] Falta a chave service_role em:\n    {KEY_FP}\n")
        print("    Supabase -> Project Settings -> API -> 'service_role' (secret) ->")
        print("    copie e cole essa chave nesse arquivo (1 linha). Ela NAO vai pro GitHub.\n")
        sys.exit(1)
    return open(KEY_FP, encoding="utf-8").read().strip()

def build_leads():
    afs   = (carregar(os.path.join(DOCS, "afs.json"), {}).get("afs") or {})
    mul   = (carregar(os.path.join(DOCS, "dados.json"), {}).get("multas") or {})
    drill = (carregar(os.path.join(DOCS, "drill.json"), {}).get("drill") or {})
    leads = []
    def add(item, tipo, cidade):
        cod = item.get("CodigoAuto")
        if not cod: return
        d = drill.get(cod) or {}
        leads.append({
            "codigo_auto": cod, "tipo": tipo, "cidade": cidade,
            "vendedor": VENDEDOR.get(cidade),
            "re": item.get("RE"), "nome_edificacao": item.get("Nome_Edificacao"),
            "logradouro": item.get("Logradouro"), "numero": str(item.get("Numero") or ""),
            "bairro": item.get("Bairro"), "detectado_em": item.get("Detectado_em"),
            "responsavel": d.get("responsavel"), "cpf_cnpj": d.get("cpfCnpj"),
            "celular": d.get("celular"), "email": d.get("email"),
            "exigencias": d.get("exigencias") or [],
            "prazo_dias": d.get("prazoDias"),
            "parcial": bool(d.get("parcial")),
        })
    for cid, lst in mul.items():
        for it in (lst or []): add(it, "MUL", cid)
    for cid, lst in afs.items():
        for it in (lst or []): add(it, "AF", cid)
    return leads

def upsert(leads, key):
    url = f"{SUPABASE_URL}/rest/v1/leads?on_conflict=codigo_auto"
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    enviados = 0
    for i in range(0, len(leads), 500):
        lote = leads[i:i+500]
        req = urllib.request.Request(url, data=json.dumps(lote).encode("utf-8"),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            enviados += len(lote)
            print(f"  [{enviados}/{len(leads)}] enviados...")
        except urllib.error.HTTPError as e:
            print(f"[!] erro HTTP {e.code}: {e.read().decode('utf-8','ignore')[:400]}")
            sys.exit(1)
        except Exception as e:
            print(f"[!] erro: {e}")
            sys.exit(1)
    return enviados

def main():
    key = get_key()
    leads = build_leads()
    if not leads:
        print("[!] Nenhum lead montado (os JSON estao vazios?).")
        return
    print(f"[*] {len(leads)} leads montados. Enviando ao Supabase...")
    n = upsert(leads, key)
    print(f"\n[OK] {n} leads no banco. Por vendedor:")
    for v, q in Counter(l["vendedor"] for l in leads).items():
        print(f"     {v}: {q}")

if __name__ == "__main__":
    main()
