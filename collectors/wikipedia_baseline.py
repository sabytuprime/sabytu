"""
Coletor de baseline Wikipedia — roda 1x por dia, guarda a média de
pageviews dos últimos 30 dias de cada tópico que tem artigo mapeado.
Serve só de CONTEXTO ("isso é mais que o normal?"), não é a fonte
de tempo real (essa é Bluesky + RSS).
"""
import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topicos import TOPICOS

BASELINE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wiki_baseline.json")
HEADERS = {"User-Agent": "SabytuRadar/1.0 (contato@sabytu.com)"}


def coletar_baseline_termo(termo, dias=30, lang="pt"):
    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(days=dias)
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{lang}.wikipedia/all-access/user/{termo}/daily/"
        f"{inicio.strftime('%Y%m%d')}/{fim.strftime('%Y%m%d')}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        dados = r.json().get("items", [])
        if not dados:
            return None
        media = sum(d["views"] for d in dados) / len(dados)
        ultimo = dados[-1]["views"]
        return {"media_diaria": media, "ultimo_dia": ultimo}
    except Exception as e:
        print(f"  [erro wiki] {termo}: {e}")
        return None


def atualizar_baselines():
    resultado = {}
    for slug, info in TOPICOS.items():
        if not info.get("wiki"):
            continue
        dado = coletar_baseline_termo(info["wiki"])
        if dado:
            resultado[slug] = dado
            print(f"  [wiki] {slug}: média {dado['media_diaria']:.0f}/dia")

    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump({"atualizado_em": time.time(), "dados": resultado}, f)

    return resultado


def carregar_baseline():
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH) as f:
        return json.load(f).get("dados", {})


if __name__ == "__main__":
    atualizar_baselines()
