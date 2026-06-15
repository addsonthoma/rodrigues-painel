# -*- coding: utf-8 -*-
"""
Coleta os 15 AFs mais recentes de cada cidade configurada em estado_afs.json.
Salva em docs/qbQv3yHGdx6ocaYE/afs.json (consumido pelo painel).
Tambem detecta novos AFs (numero > ultimo_numero) e registra em eventos.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG = "qbQv3yHGdx6ocaYE"
DOCS_DIR = os.path.join(REPO_ROOT, "docs", SLUG)
ESTADO_AFS_FP = os.path.join(REPO_ROOT, "scripts", "estado_afs.json")
AFS_FP = os.path.join(DOCS_DIR, "afs.json")

URL = "https://esci.cbm.sc.gov.br/Safe/Geral/ControllerConsultaGeral/consultaGeralEdificacao/"
PAUSE = 0.45
# QTD por cidade: padrao 15 (poller). Passe um numero p/ backfill: `python coletar_afs.py 60`
QTD_POR_CIDADE = int(sys.argv[1]) if (len(sys.argv) > 1 and sys.argv[1].isdigit()) else 15
TZ_BR = timezone(timedelta(hours=-3))

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
                time.sleep(2)
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
    estado = carregar(ESTADO_AFS_FP, {"cidades":{}})
    if not estado.get("cidades"):
        print("estado_afs.json vazio.")
        return
    afs_por_cidade = {}
    agora_iso = datetime.now(TZ_BR).isoformat(timespec="seconds")
    # ARQUIVO: carrega o afs.json atual p/ ACUMULAR historico (nao perde AFs antigos)
    arquivo_prev = (carregar(AFS_FP, {"afs": {}}).get("afs") or {})
    def _numAF(it):
        try: return int(it["CodigoAuto"].split("/")[0][6:12])
        except: return 0

    for cidade, info in estado["cidades"].items():
        prefixo = info["prefixo"].replace("AF","")
        ano = str(info["ano_corrente"])
        prev_ultimo = info["ultimo_numero"]   # numero antes de detectar novos
        prev_map = {x["CodigoAuto"]: x for x in (arquivo_prev.get(cidade) or [])}
        # detectar NOVOS
        n = info["ultimo_numero"] + 1
        streak = 0
        novos_count = 0
        while streak < 2:
            n6 = "%06d" % n
            codigo = f"AF{prefixo}{n6}A/{ano}"
            r = buscar(codigo)
            if r:
                novos_count += 1
                streak = 0
            else:
                streak += 1
            n += 1
            time.sleep(PAUSE)
        if novos_count:
            info["ultimo_numero"] += novos_count
            print(f"[{cidade}] +{novos_count} novos. ultimo={info['ultimo_numero']}", flush=True)
        # coletar os QTD_POR_CIDADE mais recentes
        ultimo = info["ultimo_numero"]
        coletadas = []
        for offset in range(QTD_POR_CIDADE):
            num = ultimo - offset
            if num < 1: break
            n6 = "%06d" % num
            codigo = f"AF{prefixo}{n6}A/{ano}"
            r = buscar(codigo)
            time.sleep(PAUSE)
            if r:
                # Detectado_em: preserva o antigo; novo de verdade (num>prev_ultimo)=agora; backfill antigo=None
                prev_item = prev_map.get(codigo)
                if prev_item and prev_item.get("Detectado_em"):
                    det = prev_item["Detectado_em"]
                elif num > prev_ultimo:
                    det = agora_iso
                else:
                    det = None
                coletadas.append({
                    "CodigoAuto": codigo,
                    "Tipo": "AF",
                    "RE": r.get("codgEdificacao") or "",
                    "Nome_Edificacao": r.get("nomeEdificacao") or "",
                    "Logradouro": r.get("nomeLogradouro") or "",
                    "Numero": r.get("codgNumeroEndereco") or "",
                    "Bairro": (r.get("nomeCidade","") + " - " + (r.get("nomeBairro","") or "")) if r.get("nomeCidade") else (r.get("nomeBairro","") or ""),
                    "Cidade": cidade,
                    "Detectado_em": det
                })
        # ACUMULA: junta o que ja existia no arquivo + o coletado agora (dedupe), ordena desc
        combinado = {x["CodigoAuto"]: x for x in (arquivo_prev.get(cidade) or [])}
        for it in coletadas:
            combinado[it["CodigoAuto"]] = it
        afs_por_cidade[cidade] = sorted(combinado.values(), key=_numAF, reverse=True)
        info["ultima_verificacao"] = agora_iso

    payload = {
        "timestamp": agora_iso,
        "cidades": estado["cidades"],
        "afs": afs_por_cidade,
        "totais": {c: len(v) for c, v in afs_por_cidade.items()},
        "total_geral": sum(len(v) for v in afs_por_cidade.values())
    }
    salvar(AFS_FP, payload)
    salvar(ESTADO_AFS_FP, estado)
    print(f"\nTotal AFs salvos: {payload['total_geral']} em {len(afs_por_cidade)} cidades")

if __name__ == "__main__":
    main()
