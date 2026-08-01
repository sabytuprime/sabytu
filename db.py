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
            topico TEXT,
            fonte TEXT,
            texto TEXT,
            timestamp REAL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails_cadastrados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            timestamp REAL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            timestamp REAL
        )
    """)

    conn.commit()

    print("BANCO OK")

    return conn


def registrar_mencao(conn, topico, fonte, texto=""):
    try:
        conn.execute(
            "INSERT INTO mencoes(topico,fonte,texto,timestamp) VALUES (?,?,?,?)",
            (topico, fonte, texto[:200], time.time())
        )
        conn.commit()
        print("GRAVOU", topico)

    except Exception as e:
        print("ERRO:", e)


def registrar_email(conn, email):
    try:
        conn.execute(
            "INSERT OR IGNORE INTO emails_cadastrados(email,timestamp) VALUES(?,?)",
            (email.lower().strip(), time.time())
        )
        conn.commit()
        return True
    except:
        return False


def contar_mencoes(conn, topico, janela_segundos):
    limite = time.time() - janela_segundos
    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico=? AND timestamp>=?",
        (topico, limite)
    )
    return cur.fetchone()[0]


def contar_mencoes_baseline(conn, topico, dias=7):
    limite = time.time() - dias * 86400
    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico=? AND timestamp>=?",
        (topico, limite)
    )
    total = cur.fetchone()[0]
    return total / (dias * 24)


def limpar_antigos(conn, dias=14):
    limite = time.time() - dias * 86400
    conn.execute(
        "DELETE FROM mencoes WHERE timestamp<?",
        (limite,)
    )
    conn.commit()


def calcular_aceleracao(conn, topico, janela_min=30):
    return False


def detectar_convergencia(conn, topico, janela_horas=6):
    return False
