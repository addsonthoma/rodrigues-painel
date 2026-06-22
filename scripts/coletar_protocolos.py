# -*- coding: utf-8 -*-
"""
Coleta os protocolos de ANALISE PPCI/RPCI mais recentes de cada cidade.
Codigo do protocolo: A{prefixo}{N:06d}A  (ex.: A8055007948A) -> N sequencial por cidade.
Busca PUBLICA (sem login) com flagOnlyProtocolo. O maior N = o mais recente.

Saida: docs/qbQv3yHGdx6ocaYE/protocolos.json (consumido pelo painel, aba Protocolos).
Os campos area/data/deferido/anexos sao preenchidos depois pelo drill (processos.projetos).

Uso:
  python scripts/coletar_protocolos.py          # poller: detecta novos + pega os recentes
  python scripts/coletar_protocolos.py 30        # idem, 30 por cidade (backfill)
  python scripts/coletar_protocolos.py calibrar  # (re)descobre o ultimo numero de cada cidade
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLUG = "qbQv3yHGdx6ocaYE"
DOCS_DIR = os.path.join(REPO_ROOT, "docs", SLUG)
ESTADO_FP = os.path.join(REPO_ROOT, "scripts", "estado_protocolos.json")
PROTO_FP = os.path.join(DOCS_DIR, "protocolos.json")

URL = "https://esci.cbm.sc.gov.br/Safe/Geral/ControllerConsultaGeral/consultaGeralEdificacao/"
PAUSE = 0.45
TZ_BR = timezone(timedelta(hours=-3))
QTD_POR_CIDADE = 25  # quantos recentes manter por cidade (default)

def buscar(codigo, max_retries=2):
    payload = {"texto":codigo,"numgCidade":None,"numrQuantidade":50,
               "flagMostrarReExcluido":False,"flagOnlyProtocolo":True}
    for tentativa in range(max_retries + 1):
        req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Content-Type":"application/json;charset=UTF-8"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d[0] if d else None
        except Exception as e:
            if tentativa < max_retries:
                time.sleep(2); continue
            print(f"  ERR {codigo}: {e}", flush=True)
            return None
    return None

def cod(prefixo, n):
    return f"A{prefixo}{n:06d}A"

def existe(prefixo, n):
    return buscar(cod(prefixo, n)) is not None

def calibrar(prefixo):
    """Acha o maior N que existe. NAO assume que numeros baixos existem
    (a numeracao de cada cidade comeca num patamar proprio). Tolera buracos
    pequenos via janela [n-2..n+2]. Exponencial p/ cima -> binaria -> refino."""
    def regiao(n):  # algo existe perto de n? (short-circuit no 1o acerto)
        for k in (n, n-1, n+1, n-2, n+2):
            if k >= 1 and existe(prefixo, k): return True
            time.sleep(PAUSE)
        return False
    # 1) sobe dobrando ate uma regiao vazia que esteja ACIMA de uma existente
    hi, lo, viu = 64, 0, False
    while hi <= 1048576:
        if regiao(hi):
            lo = hi; viu = True
        elif viu:
            break          # passou do topo (lo existe, hi vazio)
        hi *= 2
        time.sleep(PAUSE)
    if not viu:
        return 0           # cidade sem protocolos nesse range
    # 2) binaria entre lo (existe) e hi (vazio)
    while lo + 2 < hi:
        mid = (lo + hi) // 2
        if regiao(mid): lo = mid
        else: hi = mid
        time.sleep(PAUSE)
    # 3) refino: do alto pra baixo, acha o ultimo que EXISTE de fato
    for n in range(hi + 3, lo - 3, -1):
        if n >= 1 and existe(prefixo, n):
            return n
        time.sleep(PAUSE)
    return lo

def carregar(fp, default):
    if os.path.exists(fp):
        try: return json.load(open(fp, encoding="utf-8"))
        except: pass
    return default

def salvar(fp, data):
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    json.dump(data, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def item_de(codigo, r, cidade, detectado):
    return {
        "CodigoProtocolo": codigo,
        "RE": r.get("codgEdificacao") or "",
        "numgEdificacao": r.get("numgEdificacao"),
        "Nome_Edificacao": r.get("nomeEdificacao") or "",
        "Logradouro": r.get("nomeLogradouro") or "",
        "Numero": r.get("codgNumeroEndereco") or "",
        "Bairro": (r.get("nomeCidade","") + " - " + (r.get("nomeBairro","") or "")) if r.get("nomeCidade") else (r.get("nomeBairro","") or ""),
        "Cidade": cidade,
        "Detectado_em": detectado,
    }

def _numProto(it):
    try: return int(it["CodigoProtocolo"][5:11])
    except: return 0

def main():
    modo_calibrar = (len(sys.argv) > 1 and sys.argv[1].lower() == "calibrar")
    qtd = int(sys.argv[1]) if (len(sys.argv) > 1 and sys.argv[1].isdigit()) else QTD_POR_CIDADE

    estado = carregar(ESTADO_FP, {"cidades":{}})
    if not estado.get("cidades"):
        print("[!] estado_protocolos.json sem cidades — abortando.")
        return

    agora_iso = datetime.now(TZ_BR).isoformat(timespec="seconds")
    arquivo_prev = (carregar(PROTO_FP, {"protocolos": {}}).get("protocolos") or {})
    por_cidade = {}

    for cidade, info in estado["cidades"].items():
        prefixo = info["prefixo"]
        prev_ultimo = info.get("ultimo_numero", 0)
        prev_map = {x["CodigoProtocolo"]: x for x in (arquivo_prev.get(cidade) or [])}

        if modo_calibrar or not prev_ultimo:
            print(f"[{cidade}] calibrando...", flush=True)
            prev_ultimo = calibrar(prefixo)
            info["ultimo_numero"] = prev_ultimo
            print(f"[{cidade}] ultimo protocolo = A{prefixo}{prev_ultimo:06d}A", flush=True)

        # detectar NOVOS (acima do ultimo conhecido)
        n = prev_ultimo + 1
        streak = 0; novos = 0
        while streak < 3:
            if buscar(cod(prefixo, n)):
                novos += 1; streak = 0
            else:
                streak += 1
            n += 1; time.sleep(PAUSE)
        if novos:
            info["ultimo_numero"] = prev_ultimo + novos
            print(f"[{cidade}] +{novos} protocolo(s) novo(s). ultimo={info['ultimo_numero']}", flush=True)

        # coletar os 'qtd' mais recentes
        ultimo = info["ultimo_numero"]
        coletadas = []
        faltas = 0
        offset = 0
        while len(coletadas) < qtd and offset < qtd * 3:
            num = ultimo - offset; offset += 1
            if num < 1: break
            codigo = cod(prefixo, num)
            r = buscar(codigo); time.sleep(PAUSE)
            if not r:
                faltas += 1
                if faltas > 8: break  # buraco grande -> para
                continue
            prev_item = prev_map.get(codigo)
            if prev_item and prev_item.get("Detectado_em"):
                det = prev_item["Detectado_em"]
            elif num > prev_ultimo:
                det = agora_iso
            else:
                det = None
            # preserva TODO o enriquecimento ja feito pelo drill (area/data/deferido/anexos/_drillTs...)
            novo_item = item_de(codigo, r, cidade, det)
            if prev_item:
                for k, v in prev_item.items():
                    if k not in novo_item:   # nao sobrescreve os campos-base recem-lidos da API
                        novo_item[k] = v
            coletadas.append(novo_item)

        combinado = {x["CodigoProtocolo"]: x for x in (arquivo_prev.get(cidade) or [])}
        for it in coletadas:
            combinado[it["CodigoProtocolo"]] = it
        por_cidade[cidade] = sorted(combinado.values(), key=_numProto, reverse=True)
        info["ultima_verificacao"] = agora_iso

    payload = {
        "timestamp": agora_iso,
        "cidades": estado["cidades"],
        "protocolos": por_cidade,
        "totais": {c: len(v) for c, v in por_cidade.items()},
        "total_geral": sum(len(v) for v in por_cidade.values()),
    }
    salvar(PROTO_FP, payload)
    salvar(ESTADO_FP, estado)
    print(f"\nTotal protocolos salvos: {payload['total_geral']} em {len(por_cidade)} cidades")

if __name__ == "__main__":
    main()
