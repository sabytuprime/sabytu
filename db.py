import sqlite3
import os
import time
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sabytu.db")

_inicializado = False
_lock = threading.Lock()


def _inicializar_schema():
    global _inicializado

    with _lock:
        if _inicializado:
            return

        print("Inicializando schema...")

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH, timeout=15)

        try:
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS mencoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topico TEXT NOT NULL,
                fonte TEXT NOT NULL,
                texto TEXT,
                timestamp REAL NOT NULL
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS emails_cadastrados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                timestamp REAL NOT NULL
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                timestamp REAL NOT NULL
            )
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_topico_ts
            ON mencoes(topico, timestamp)
            """)

            conn.commit()
            print("Schema criado.")

            _inicializado = True

        finally:
            conn.close()


def get_conn():
    if not _inicializado:
        _inicializar_schema()

    conn = sqlite3.connect(
        DB_PATH,
        timeout=15,
        check_same_thread=False
    )

    conn.execute("PRAGMA busy_timeout=15000")

    return conn


def registrar_email(conn, email):
    try:
        conn.execute(
            "INSERT INTO emails_cadastrados(email,timestamp) VALUES(?,?)",
            (email.strip().lower(), time.time())
        )
        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return True

    except Exception as e:
        print(e)
        return False


def registrar_mencao(conn, topico, fonte, texto=""):
    try:
        conn.execute(
            "INSERT INTO mencoes(topico,fonte,texto,timestamp) VALUES(?,?,?,?)",
            (topico, fonte, texto[:200], time.time())
        )
        conn.commit()
        print(f"GRAVOU: {topico} ({fonte})")

    except Exception as e:
        print("ERRO:", e)


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


def detectar_convergencia(conn, topico, janela_horas=6):

    limite = time.time() - janela_horas * 3600

    cur = conn.execute("""
        SELECT COUNT(DISTINCT fonte)
        FROM mencoes
        WHERE topico=?
        AND timestamp>=?
    """, (topico, limite))

    return cur.fetchone()[0] >= 2


def calcular_aceleracao(conn, topico, janela_min=30):

    agora = time.time()
    janela = janela_min * 60

    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico=? AND timestamp>=?",
        (topico, agora - janela)
    )

    atual = cur.fetchone()[0]

    cur = conn.execute(
        """SELECT COUNT(*) FROM mencoes
        WHERE topico=?
        AND timestamp>=?
        AND timestamp<?""",
        (topico, agora - 2 * janela, agora - janela)
    )

    anterior = cur.fetchone()[0]

    if anterior == 0:
        return atual >= 3

    return atual / anterior >= 2


def limpar_antigos(conn, dias=14):

    limite = time.time() - dias * 86400

    conn.execute(
        "DELETE FROM mencoes WHERE timestamp<?",
        (limite,)
    )

    conn.commit()
