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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    # WAL: permite leitura (site) e escrita (coletores) acontecendo ao
    # mesmo tempo sem travar uma a outra — resolve "database is locked"
    #
    # Retry: quando várias threads sobem ao mesmo tempo (boot do
    # servidor), a troca pra modo WAL e criação de tabela podem colidir
    # momentaneamente — tenta de novo em vez de matar a thread inteira.
    ultimo_erro = None
    for tentativa in range(5):
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=15000")
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails_cadastrados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inscricoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()
            return conn
        except sqlite3.OperationalError as e:
            ultimo_erro = e
            time.sleep(0.3 * (tentativa + 1))
    raise ultimo_erro


def registrar_email(conn, email):
    try:
        conn.execute(
            "INSERT INTO emails_cadastrados (email, timestamp) VALUES (?, ?)",
            (email.strip().lower(), time.time()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return True  # já cadastrado, tudo bem, não é erro
    except Exception as e:
        print(f"[erro registrar_email] {e}")
        return False


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


def calcular_aceleracao(conn, topico, janela_min=30):
    """
    Detecção real de aceleração — não é o Delt-IEt completo, mas é
    inspirado na mesma ideia: compara a TAXA de menções da janela
    atual com a taxa da janela anterior (a "derivada", não só o volume).
    Retorna True se a taxa mais que dobrou entre as duas janelas.
    """
    agora = time.time()
    janela_seg = janela_min * 60

    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ?",
        (topico, agora - janela_seg),
    )
    atual = cur.fetchone()[0]

    cur = conn.execute(
        "SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ? AND timestamp < ?",
        (topico, agora - 2 * janela_seg, agora - janela_seg),
    )
    anterior = cur.fetchone()[0]

    if anterior == 0:
        return atual >= 3  # sem base de comparação: só marca se já tem volume mínimo
    return (atual / anterior) >= 2.0


def limpar_antigos(conn, dias=14):
    """Remove menções mais velhas que N dias, pra não crescer pra sempre."""
    limite = time.time() - dias * 86400
    conn.execute("DELETE FROM mencoes WHERE timestamp < ?", (limite,))
    conn.commit()
