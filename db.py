"""
Banco de dados SQLite simples — armazena cada menção capturada,
com timestamp e fonte, pra depois calcular contagem por janela.
"""
import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sabytu.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topico TEXT NOT NULL,
            fonte TEXT NOT NULL,
            texto TEXT,
            timestamp REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topico_ts ON mencoes(topico, timestamp)")
    conn.commit()
    return conn


def registrar_mencao(conn, topico, fonte, texto=""):
    conn.execute(
        "INSERT INTO mencoes (topico, fonte, texto, timestamp) VALUES (?, ?, ?, ?)",
        (topico, fonte, texto[:200], time.time()),
    )
    conn.commit()


def contar_mencoes(conn, topico, janela_segundos):
    limite = time.time() - janela_segundos
    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ?",
        (topico, limite),
    )
    return cur.fetchone()[0]


def contar_mencoes_baseline(conn, topico, dias=7):
    """Média de menções por hora nos últimos N dias, pra normalizar o score."""
    limite = time.time() - dias * 86400
    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ?",
        (topico, limite),
    )
    total = cur.fetchone()[0]
    horas = dias * 24
    return total / horas if horas > 0 else 0


def limpar_antigos(conn, dias=14):
    """Remove menções mais velhas que N dias, pra não crescer pra sempre."""
    limite = time.time() - dias * 86400
    conn.execute("DELETE FROM mencoes WHERE timestamp < ?", (limite,))
    conn.commit()
