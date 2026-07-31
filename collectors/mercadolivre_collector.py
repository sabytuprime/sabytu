"""
Coletor Mercado Livre — duas páginas públicas, sem login, sem API paga.

- /mais-vendidos: reflete venda real, muda com mais frequência -> 3h
- tendencias.mercadolivre.com.br: atualiza só semanalmente -> 1x/dia

IMPORTANTE: o nome "Mercado Livre" nunca aparece pro usuário final —
fica só como identificação interna de fonte no banco de dados, igual
"bluesky" ou "rss". O site nunca cita a plataforma de origem.
"""
import re
import time
import sys
import os

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topicos import detectar_topicos
from db import get_conn, registrar_mencao

HEADERS = {"User-Agent": "Mozilla/5.0 (SabytuRadar/1.0; contato@sabytu.com)"}

URL_MAIS_VENDIDOS = "https://www.mercadolivre.com.br/mais-vendidos"
URL_TENDENCIAS = "https://tendencias.mercadolivre.com.br/"

FREQ_MAIS_VENDIDOS_SEG = 3 * 3600   # a cada 3h — página reflete venda real, muda mais rápido
FREQ_TENDENCIAS_SEG = 24 * 3600     # 1x/dia — a própria página só atualiza semanalmente


def _texto_da_pagina(url):
    """Baixa a página e devolve só o texto visível, sem tags HTML."""
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  [erro {r.status_code}] {url}")
        return ""
    html = r.text
    # remove scripts/styles inteiros primeiro (não é texto pro usuário)
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    # remove tags restantes, deixa só texto
    texto = re.sub(r"<[^>]+>", " ", html)
    return texto


def _extrair_json_tendencias(url):
    """
    A página de tendências embute os dados estruturados dentro de um
    script de analytics (melidata event_data). Extrai isso direto —
    mais preciso que só pegar texto solto da página.
    """
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return ""
    m = re.search(r'"most_growth":(\[.*?\]).*?"most_desired":(\[.*?\]).*?"most_popular":(\[.*?\])', r.text, re.DOTALL)
    if not m:
        return ""
    # junta os 3 blocos de keyword num texto só, pra rodar detectar_topicos em cima
    keywords = re.findall(r'"keyword":"([^"]+)"', m.group(0))
    return " . ".join(keywords)


def coletar_mais_vendidos(conn):
    print("  [ML] checando mais-vendidos...")
    texto = _texto_da_pagina(URL_MAIS_VENDIDOS)
    if not texto:
        return
    topicos_achados = detectar_topicos(texto)
    for topico in topicos_achados:
        registrar_mencao(conn, topico, "fonte_consumo_1", f"detectado em ranking de vendas")
        print(f"    -> '{topico}' confirmado")


def coletar_tendencias(conn):
    print("  [ML] checando tendencias de busca...")
    texto = _extrair_json_tendencias(URL_TENDENCIAS)
    if not texto:
        # fallback: tenta pegar texto solto da página se o JSON não bateu
        texto = _texto_da_pagina(URL_TENDENCIAS)
    if not texto:
        return
    topicos_achados = detectar_topicos(texto)
    for topico in topicos_achados:
        registrar_mencao(conn, topico, "fonte_consumo_2", f"detectado em tendencia de busca")
        print(f"    -> '{topico}' confirmado")


def rodar_loop():
    print("Coletor de consumo (fonte externa) iniciado.")
    ultima_mais_vendidos = 0
    ultima_tendencias = 0

    while True:
        agora = time.time()
        try:
            conn = get_conn()

            if agora - ultima_mais_vendidos >= FREQ_MAIS_VENDIDOS_SEG:
                coletar_mais_vendidos(conn)
                ultima_mais_vendidos = agora

            if agora - ultima_tendencias >= FREQ_TENDENCIAS_SEG:
                coletar_tendencias(conn)
                ultima_tendencias = agora

        except Exception as e:
            print(f"[erro coletor consumo] {e} — tentando de novo no próximo ciclo")

        time.sleep(600)  # checa a cada 10 min se já é hora de rodar algum dos dois


if __name__ == "__main__":
    rodar_loop()
