import time
import os
from flask import Flask, jsonify

from db import get_conn

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "servico": "Sabytu"
    })


@app.route("/api/status")
def status():
    conn = None

    try:
        conn = get_conn()

        total = conn.execute(
            "SELECT COUNT(*) FROM mencoes"
        ).fetchone()[0]

        return jsonify({
            "status": "ok",
            "mencoes": total
        })

    except Exception as e:
        print(e)
        return jsonify({
            "status": "erro",
            "erro": str(e)
        }), 500

    finally:
        if conn:
            conn.close()


@app.route("/api/radar")
def radar():
    return jsonify({
        "status": "ok",
        "topicos": []
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
