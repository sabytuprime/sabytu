"""
Coletor RSS — versão de diagnóstico.
"""
import time
import feedparser
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from topicos import detectar_topicos
from db import get_conn, registrar_mencao

FEEDS = [
    "https://g1.globo.com/rss/g1/",
    "https://rss.uol.com.br/feed/noticias.xml",
    "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
]

FREQUENCIA_SEGUNDOS = 10

ja_visto = set()


def checar_feeds(conn):

    print(">>> Iniciando leitura dos feeds")

    for url in FEEDS:

        print(f">>> Lendo {url}")

        try:
            feed = feedparser.parse(url)
            print(f">>> {len(feed.entries)} notícias encontradas")

        except Exception as e:
            print(f"ERRO RSS {url}: {e}")
            continue

        for entrada in feed.entries[:30]:

            uid = entrada.get("id") or entrada.get("link")

            if not uid or uid in ja_visto:
                continue

            ja_visto.add(uid)

            titulo = entrada.get("title", "")
            resumo = entrada.get("summary", "")

            texto = f"{titulo} {resumo}"

            topicos = detectar_topicos(texto)

            if topicos:
                print(f">>> Detectou {topicos}")

            for topico in topicos:
                print(f">>> Gravando {topico}")
                registrar_mencao(conn, topico, "rss", titulo)

    if len(ja_visto) > 5000:
        ja_visto.clear()


def rodar_loop():

    print("===== COLETOR RSS INICIADO =====")

    while True:

        print("===== NOVA VOLTA =====")

        conn = None

        try:

            print("Abrindo banco...")
            conn = get_conn()

            print("Banco aberto.")

            checar_feeds(conn)

            print("Fim da coleta.")

        except Exception as e:

            print("ERRO GERAL:", e)

        finally:

            if conn:
                conn.close()

        print("Dormindo...\n")

        time.sleep(FREQUENCIA_SEGUNDOS)


if __name__ == "__main__":
    rodar_loop()
