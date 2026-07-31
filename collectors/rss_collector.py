"""
Coletor de RSS — portais brasileiros. Roda em loop, checa manchetes
novas a cada FREQUENCIA_SEGUNDOS e registra menção de tópico da watchlist.
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
    "http://globoesporte.globo.com/ESP/Noticia/Rss/0,,AS0-4271,00.xml",  # esporte dedicado — mais denso pra futebol/Brasileirão
]

FREQUENCIA_SEGUNDOS = 180  # checa a cada 3 min
ja_visto = set()  # ids de manchete já processadas (evita duplicar)


def checar_feeds(conn):
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  [erro RSS] {url}: {e}")
            continue

        for entrada in feed.entries[:30]:
            uid = entrada.get("id") or entrada.get("link")
            if not uid or uid in ja_visto:
                continue
            ja_visto.add(uid)

            titulo = entrada.get("title", "")
            resumo = entrada.get("summary", "")
            texto = f"{titulo} {resumo}"

            topicos_achados = detectar_topicos(texto)
            for topico in topicos_achados:
                registrar_mencao(conn, topico, "rss", titulo)
                print(f"  [RSS] '{topico}' <- {titulo[:60]}")

    # evita crescer pra sempre em memória
    if len(ja_visto) > 5000:
        ja_visto.clear()


def rodar_loop():
    print("Coletor RSS iniciado.")
    while True:
        try:
            conn = get_conn()
            checar_feeds(conn)
        except Exception as e:
            print(f"[erro rodar_loop RSS] {e} — tentando de novo em breve")
        time.sleep(FREQUENCIA_SEGUNDOS)


if __name__ == "__main__":
    rodar_loop()
