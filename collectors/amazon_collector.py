"""
Coletor Amazon — página pública de mais vendidos, sem login, sem API paga.

Mesma lógica do coletor de Mercado Livre: texto da página, comparado
contra a watchlist de tópicos. Fonte identificada internamente como
"fonte_consumo_3" — o nome da plataforma nunca aparece pro usuário.
"""
import re
import time
import sys
import os

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topicos import detectar_topicos
from db import get_conn, registrar_mencao

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SabytuRadar/1.0"
}

URL_MAIS_VENDIDOS = "https://www.amazon.com.br/gp/bestsellers"

FREQ_SEG = 5 * 3600  # a cada 5h — equilíbrio entre prudência de acesso e resolução temporal pro Delt-IEt


def _texto_da_pagina(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  [erro {r.status_code}] {url}")
        return ""
    html = r.text
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL)
    texto = re.sub(r"<[^>]+>", " ", html)
    return texto


def coletar_mais_vendidos(conn):
    print("  [AMZ] checando mais-vendidos...")
    texto = _texto_da_pagina(URL_MAIS_VENDIDOS)
    if not texto:
        return
    topicos_achados = detectar_topicos(texto)
    for topico in topicos_achados:
        registrar_mencao(conn, topico, "fonte_consumo_3", "detectado em ranking de vendas")
        print(f"    -> '{topico}' confirmado")


def rodar_loop():
    print("Coletor de consumo 2 (fonte externa) iniciado.")
    ultima = 0
    while True:
        agora = time.time()
        conn = None
        try:
            if agora - ultima >= FREQ_SEG:
                conn = get_conn()
                coletar_mais_vendidos(conn)
                ultima = agora
        except Exception as e:
            print(f"[erro coletor consumo 2] {e} — tentando de novo no próximo ciclo")
        finally:
            if conn:
                conn.close()
        time.sleep(600)


if __name__ == "__main__":
    rodar_loop()
