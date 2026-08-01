"""
Banco de dados SQLite simples — armazena cada menção capturada,
com timestamp e fonte, pra depois calcular contagem por janela.
"""
import sqlite3
import os
import time
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "sabytu.db")


_inicializado = False
_lock_inicializacao = threading.Lock()


def _inicializar_schema():
    """Cria as tabelas, uma única vez por processo — não a cada conexão.
    Isso é o que estava causando disputa constante pelo banco: antes,
    toda chamada de get_conn() tentava recriar as tabelas de novo."""
    global _inicializado
    with _lock_inicializacao:
        if _inicializado:
            return
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15)
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
                conn.close()
                _inicializado = True
                return
            except sqlite3.OperationalError:
                time.sleep(0.3 * (tentativa + 1))
        conn.close()


def get_conn():
    print("Entrou em get_conn()")

    if not _inicializado:
        print("Inicializando schema...")
        _inicializar_schema()
        print("Schema inicializado.")

    print("Abrindo sqlite...")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    print("SQLite aberto.")

    conn.execute("PRAGMA busy_timeout=15000")
    print("Pragma OK.")

    return conn


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
    try:
        conn.execute(
            "INSERT INTO mencoes (topico, fonte, texto, timestamp) VALUES (?, ?, ?, ?)",
            (topico, fonte, texto[:200], time.time()),
        )
        conn.commit()
        print(f"✅ GRAVOU: {topico} ({fonte})")
    except Exception as e:
        print(f"❌ ERRO AO GRAVAR: {e}")


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


def detectar_convergencia(conn, topico, janela_horas=6):
    """
    O 'Convergência' — não é volume, é DIVERSIDADE de fonte.
    Verifica se o mesmo tema foi confirmado por fontes de natureza
    DIFERENTE na mesma janela: comentário (bluesky/rss) E comportamento
    de compra (mercado livre/amazon) ao mesmo tempo.

    Isso é mais raro e mais forte que só volume alto numa fonte só —
    é a peça que faltava pro Delt-IEt fazer sentido de verdade.
    """
    limite = time.time() - janela_horas * 3600

    FONTES_COMENTARIO = ("bluesky", "rss")
    FONTES_COMPRA = ("fonte_consumo_1", "fonte_consumo_2", "fonte_consumo_3")

    placeholders_comentario = ",".join("?" * len(FONTES_COMENTARIO))
    placeholders_compra = ",".join("?" * len(FONTES_COMPRA))

    cur = conn.execute(
        f"SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ? AND fonte IN ({placeholders_comentario})",
        (topico, limite, *FONTES_COMENTARIO),
    )
    tem_comentario = cur.fetchone()[0] > 0

    cur = conn.execute(
        f"SELECT COUNT(*) FROM mencoes WHERE topico = ? AND timestamp >= ? AND fonte IN ({placeholders_compra})",
        (topico, limite, *FONTES_COMPRA),
    )
    tem_compra = cur.fetchone()[0] > 0

    return tem_comentario and tem_compra


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
