# -*- coding: utf-8 -*-
"""
Coleta multas do CBMSC e atualiza docs/qbQv3yHGdx6ocaYE/dados.json para o painel GitHub Pages.
Rodado pelo GitHub Actions a cada 10 min em horario comercial.
Sem dependencias externas (so urllib + json).
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG       = "qbQv3yHGdx6ocaYE"   # URL ofuscada
DOCS_DIR   = os.path.join(REPO_ROOT, "docs", SLUG)
ESTADO_FP  = os.path.join(REPO_ROOT, "scripts", "estado.json")
DADOS_FP   = os.path.join(DOCS_DIR, "dados.json")
EVENTOS_FP = os.path.join(REPO_ROOT, "scripts", "eventos.json")

URL = "https://esci.cbm.sc.gov.br/Safe/Geral/ControllerConsultaGeral/consultaGeralEdificacao/"
PAUSE = 0.5
TZ_BR = timezone(timedelta(hours=-3))   # horario de Brasilia

def buscar(codigo, max_retries=2):
    payload = {"texto":codigo,"numgCidade":None,"numrQuantidade":50,"flagMostrarReExcluido":False,"flagOnlyAuto":True}
    for tentativa in range(max_retries + 1):
        req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Content-Type":"application/json;charset=UTF-8"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d[0] if d else None
        except Exception as e:
            if tentativa < max_retries:
                time.sleep(2)  # espera 2s antes de tentar de novo
                continue
            print(f"  ERR {codigo}: {e}", flush=True)
            return None
    return None

def carregar(fp, default):
    if os.path.exists(fp):
        try: return json.load(open(fp, encoding="utf-8"))
        except: pass
    return default

def salvar(fp, data):
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    json.dump(data, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    estado  = carregar(ESTADO_FP, {"cidades":{}})
    eventos = carregar(EVENTOS_FP, {"eventos":[]})
    multas  = carregar(DADOS_FP, {"cidades":{}, "multas":{}, "eventos_recentes":[], "total_geral":0})
    novos_total = 0
    agora_iso = datetime.now(TZ_BR).isoformat(timespec="seconds")

    for cidade, info in estado.get("cidades", {}).items():
        prefixo = info["prefixo"].replace("MUL","")
        ultimo  = info["ultimo_numero"]
        ano     = str(info["ano_corrente"])
        print(f"[{cidade}] verificando a partir de /{ultimo+1}", flush=True)
        n = ultimo + 1
        streak = 0
        novos_cidade = []
        while streak < 2:
            n6 = "%06d" % n
            codigo = f"MUL{prefixo}{n6}A/{ano}"
            r = buscar(codigo)
            if r:
                print(f"  + NOVA {codigo} -> {(r.get('nomeEdificacao') or '')[:50]}", flush=True)
                novos_cidade.append({
                    "CodigoAuto": codigo,
                    "RE": r.get("codgEdificacao") or "",
                    "Nome_Edificacao": r.get("nomeEdificacao") or "",
                    "Logradouro": r.get("nomeLogradouro") or "",
                    "Numero": r.get("codgNumeroEndereco") or "",
                    "Bairro": (r.get("nomeCidade","") + " - " + (r.get("nomeBairro","") or "")) if r.get("nomeCidade") else (r.get("nomeBairro","") or ""),
                    "Cidade": cidade
                })
                eventos["eventos"].insert(0, {
                    "ts": agora_iso,
                    "cidade": cidade,
                    "codigo": codigo,
                    "nome": r.get("nomeEdificacao") or "",
                    "re": r.get("codgEdificacao") or ""
                })
                streak = 0
            else:
                streak += 1
            n += 1
            time.sleep(PAUSE)
        if novos_cidade:
            info["ultimo_numero"] = ultimo + len(novos_cidade)
            novos_total += len(novos_cidade)
            # acrescentar no inicio da lista de multas da cidade
            existentes = multas.get("multas", {}).get(cidade, [])
            multas.setdefault("multas", {})[cidade] = novos_cidade + existentes
        info["ultima_verificacao"] = agora_iso

    eventos["eventos"] = eventos["eventos"][:200]

    # garantir que todas cidades aparecam no JSON do painel
    for cidade in estado.get("cidades", {}):
        multas.setdefault("multas", {}).setdefault(cidade, [])

    cutoff = datetime.now(TZ_BR) - timedelta(days=7)
    eventos_recentes = []
    for ev in eventos.get("eventos", []):
        try:
            ts = datetime.fromisoformat(ev["ts"])
            if ts >= cutoff: eventos_recentes.append(ev)
        except: pass

    payload = {
        "timestamp": agora_iso,
        "cidades": estado.get("cidades", {}),
        "multas": multas.get("multas", {}),
        "totais": {c: len(m) for c, m in multas.get("multas", {}).items()},
        "total_geral": sum(len(m) for m in multas.get("multas", {}).values()),
        "eventos_recentes": eventos_recentes[:50]
    }
    salvar(DADOS_FP, payload)
    salvar(ESTADO_FP, estado)
    salvar(EVENTOS_FP, eventos)
    print(f"\nTOTAL novas multas nesta rodada: {novos_total}", flush=True)
    print(f"Total geral de multas no painel: {payload['total_geral']}", flush=True)

if __name__ == "__main__":
    main()
