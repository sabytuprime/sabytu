"""
Coletor Bluesky Jetstream — conexão ao vivo, filtra posts em português,
registra menção de cada tópico da watchlist encontrado no texto.
Reconecta sozinho se a conexão cair (streaming não é 100% estável).
"""
import asyncio
import json
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topicos import detectar_topicos
from db import get_conn, registrar_mencao

import websockets

JETSTREAM_URL = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"


async def coletar():
    posts_vistos = 0
    posts_pt = 0
    ultimo_log = time.time()
    ultima_renovacao_conn = time.time()
    RENOVAR_CONN_A_CADA_SEG = 600  # 10 min — evita segurar o WAL aberto por horas

    while True:  # loop de reconexão
        conn = None
        try:
            conn = get_conn()
            async with websockets.connect(JETSTREAM_URL, max_size=2*1024*1024) as ws:
                print("Bluesky Jetstream conectado.")
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if evt.get("kind") != "commit":
                        continue
                    commit = evt.get("commit", {})
                    if commit.get("operation") != "create":
                        continue
                    record = commit.get("record", {})
                    if record.get("$type") != "app.bsky.feed.post":
                        continue

                    posts_vistos += 1

                    langs = record.get("langs", [])
                    if "pt" not in langs:
                        continue
                    posts_pt += 1

                    texto = record.get("text", "")
                    if not texto:
                        continue

                    for topico in detectar_topicos(texto):
                        registrar_mencao(conn, topico, "bluesky", texto)

                    if time.time() - ultimo_log > 60:
                        print(f"  [Bluesky] {posts_vistos} posts, {posts_pt} em pt")
                        ultimo_log = time.time()

                    # renova a conexão periodicamente, mesmo sem reconectar
                    # o websocket — evita segurar o WAL aberto por horas
                    if time.time() - ultima_renovacao_conn > RENOVAR_CONN_A_CADA_SEG:
                        conn.close()
                        conn = get_conn()
                        ultima_renovacao_conn = time.time()

        except Exception as e:
            print(f"  [Bluesky] conexão caiu ({e}), reconectando em 5s...")
            await asyncio.sleep(5)
        finally:
            # ESSENCIAL: fecha a conexão antes de reconectar — sem isso,
            # cada reconexão vazava uma conexão SQLite pra sempre, e isso
            # travava o WAL, causando "database is locked" com o tempo.
            if conn:
                conn.close()


def rodar_loop():
    asyncio.run(coletar())


if __name__ == "__main__":
    rodar_loop()
