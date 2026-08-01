"""
Sabytu — API pública do radar.
Expõe /api/radar com contagem real de menções por tópico, normalizada
contra a média histórica do próprio tópico (score 0-100 "de buzz",
sem nenhuma fórmula proprietária aqui — 100% defensável e auditável).
"""
import threading
import time
import os
import sys
import faulthandler

faulthandler.enable()
faulthandler.dump_traceback_later(20, repeat=True, file=sys.stderr)

from flask import Flask, jsonify, request

from db import get_conn, contar_mencoes, contar_mencoes_baseline, limpar_antigos, calcular_aceleracao, registrar_mencao, detectar_convergencia
from topicos import TOPICOS
from collectors.wikipedia_baseline import carregar_baseline, atualizar_baselines
from collectors.rss_collector import rodar_loop as rodar_rss
from collectors.bluesky_collector import rodar_loop as rodar_bluesky
from collectors.mercadolivre_collector import rodar_loop as rodar_consumo
from collectors.amazon_collector import rodar_loop as rodar_consumo2

app = Flask(__name__)

JANELA_AGORA_SEGUNDOS = 60 * 60  # última hora, é o que aparece como "score agora"


def calcular_score(contagem_agora, baseline_hora):
    """
    Score 0-100 simples e honesto: quanto a contagem da última hora
    está acima/abaixo da média histórica por hora do próprio tópico.
    Sem entropia, sem aceleração — só proporção real, defensável.
    """
    if baseline_hora <= 0:
        return min(100, contagem_agora * 10)
    razao = contagem_agora / baseline_hora
    score = min(100, int(razao * 20))
    return score


@app.route("/api/radar")
def api_radar():
    conn = None
    try:
        conn = get_conn()
        resultado = []

        for slug, info in TOPICOS.items():
            contagem_hora = contar_mencoes(conn, slug, JANELA_AGORA_SEGUNDOS)
            baseline_hora = contar_mencoes_baseline(conn, slug, dias=7)
            score = calcular_score(contagem_hora, baseline_hora)
            acelerando = calcular_aceleracao(conn, slug)
            convergencia = detectar_convergencia(conn, slug)

            resultado.append({
                "slug": slug,
                "nome": info["nome"],
                "emoji": info["emoji"],
                "score": score,
                "mencoes_ultima_hora": contagem_hora,
                "media_historica_hora": round(baseline_hora, 1),
                "acelerando": acelerando,
                "convergencia": convergencia,
            })

        resultado.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "atualizado_em": time.time(),
            "topicos": resultado,
        })
    except Exception as e:
        print(f"[erro /api/radar] {e}")
        return jsonify({"atualizado_em": time.time(), "topicos": [], "aviso": "temporariamente indisponivel"}), 200
    finally:
        if conn:
            conn.close()


@app.route("/api/status")
def api_status():
    """Endpoint de diagnóstico — útil pra você conferir se os coletores estão vivos."""
    conn = None
    try:
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) FROM mencoes").fetchone()[0]
        ultima = conn.execute("SELECT MAX(timestamp) FROM mencoes").fetchone()[0]
        return jsonify({
            "total_mencoes_registradas": total,
            "ultima_mencao_ha_segundos": (time.time() - ultima) if ultima else None,
        })
    except Exception as e:
        print(f"[erro /api/status] {e}")
        return jsonify({"erro": "temporariamente indisponivel"}), 200
    finally:
        if conn:
            conn.close()


@app.route("/api/coleta-agente", methods=["POST"])
def api_coleta_agente():
    """
    Endpoint pra receber dado coletado por agente externo (ex: Cowork
    lendo páginas de Tendências do Mercado Livre, YouTube Em Alta etc).
    Mesmo padrão dos coletores automáticos — grava como menção real,
    com fonte identificada, pra manter rastreabilidade de onde veio.
    """
    conn = None
    try:
        data = request.get_json(force=True, silent=True) or {}
        topico = (data.get("topico") or "").strip().lower()
        texto = (data.get("texto") or "").strip()
        fonte = (data.get("fonte") or "agente_externo").strip()

        if topico not in TOPICOS:
            return jsonify({"ok": False, "erro": f"topico '{topico}' nao existe na watchlist"}), 400
        if not texto:
            return jsonify({"ok": False, "erro": "texto vazio"}), 400

        conn = get_conn()
        registrar_mencao(conn, topico, fonte, texto)
        return jsonify({"ok": True, "topico": topico, "fonte": fonte})
    except Exception as e:
        print(f"[erro /api/coleta-agente] {e}")
        return jsonify({"ok": False, "erro": "temporariamente indisponivel"}), 200
    finally:
        if conn:
            conn.close()


@app.route("/api/inscrever", methods=["POST"])
def api_inscrever():
    conn = None
    try:
        data = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            return jsonify({"ok": False, "erro": "email invalido"}), 400
        conn = get_conn()
        conn.execute("INSERT INTO inscricoes (email, timestamp) VALUES (?, ?)", (email, time.time()))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"[erro /api/inscrever] {e}")
        return jsonify({"ok": False, "erro": "temporariamente indisponivel"}), 200
    finally:
        if conn:
            conn.close()


@app.route("/")
def home():
    return jsonify({"status": "ok", "servico": "Sabytu Radar API"})


def iniciar_coletores_em_background():
    """
    Roda os coletores em threads separadas dentro do mesmo processo web.
    """
    threading.Thread(target=rodar_rss, daemon=True).start()
    # DESLIGADO TEMPORARIAMENTE para isolar crash (exit 139 / segfault) —
    # suspeito é o volume alto do firehose do Bluesky processado via websockets.
    # threading.Thread(target=rodar_bluesky, daemon=True).start()
    threading.Thread(target=rodar_consumo, daemon=True).start()
    threading.Thread(target=rodar_consumo2, daemon=True).start()

    def loop_wiki_e_limpeza():
        while True:
            try:
                atualizar_baselines()
            except Exception as e:
                print(f"[erro baseline wiki] {e}")
            conn = None
            try:
                conn = get_conn()
                limpar_antigos(conn)
            except Exception as e:
                print(f"[erro limpeza] {e}")
            finally:
                if conn:
                    conn.close()
            time.sleep(24 * 3600)  # 1x por dia

    threading.Thread(target=loop_wiki_e_limpeza, daemon=True).start()


iniciar_coletores_em_background()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
