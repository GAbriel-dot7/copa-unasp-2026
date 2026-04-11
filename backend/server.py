#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║       COPA UNASP 2026 — Backend do Sistema de Leilão     ║
║       Python 3 + SQLite (stdlib apenas)                  ║
║       Inicie com: python3 server.py                      ║
╚══════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
import os
import secrets
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ── Configuração ─────────────────────────────────────────────
PORT        = int(os.environ.get("PORT", 3000))
DB_PATH     = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "database.db"))
FRONTEND    = os.path.join(os.path.dirname(__file__), "..", "frontend")
SALDO_INICIAL = 100_000
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "neorobson")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "")  # e.g. https://your-app.up.railway.app
MAX_FIELD_LEN = 100
ALLOWED_POSITIONS = {"Goleiro", "Fixo", "Ala", "Pivô"}
leilao_iniciado = False     # estado global do leilão
leilao_finalizado = False   # estado global do leilão

# ── Session tokens (in-memory) ───────────────────────────────
active_sessions = {}        # token -> expiry timestamp
SESSION_TTL = 86400         # 24 hours
session_lock = threading.Lock()

# ── Dados iniciais dos craques ────────────────────────────────
CRAQUES_INICIAIS = [
    #        nome           seleção      brasão                  cor-primária  cor-secundária
    (1, "Neo Lucca",    "Argentina",  "img/argentina.png",  "#74ACDF", "#FFFFFF"),
    (2, "Fernando",     "França",     "img/franca.png",     "#002395", "#ED2939"),
    (3, "Luis Gustavo", "Alemanha",   "img/alemanha.png",   "#1F1F1F", "#DD0000"),
    (4, "Tiago",        "Espanha",    "img/espanha.png",    "#AA151B", "#F1BF00"),
    (5, "Miguel",       "Inglaterra", "img/inglaterra.png", "#CC0000", "#FFFFFF"),
    (6, "Ricardo",      "Holanda",    "img/holanda.png",    "#FF6600", "#FFFFFF"),
    (7, "Gustavo",      "Uruguai",    "img/uruguai.png",    "#75AADB", "#FFFFFF"),
]

# ── Banco de dados ────────────────────────────────────────────
db_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS craques (
            id       INTEGER PRIMARY KEY,
            nome     TEXT NOT NULL,
            selecao  TEXT NOT NULL,
            bandeira TEXT NOT NULL,
            cor      TEXT NOT NULL DEFAULT '#0033A0',
            cor_sec  TEXT NOT NULL DEFAULT '#FFD100',
            saldo    INTEGER NOT NULL DEFAULT 100000
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            craque_id INTEGER NOT NULL REFERENCES craques(id),
            jogador   TEXT NOT NULL,
            posicao   TEXT NOT NULL,
            valor     INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Inserir craques iniciais se tabela estiver vazia
    existing = c.execute("SELECT COUNT(*) FROM craques").fetchone()[0]
    if existing == 0:
        c.executemany(
            "INSERT INTO craques (id, nome, selecao, bandeira, cor, cor_sec, saldo) VALUES (?,?,?,?,?,?,?)",
            [(r[0], r[1], r[2], r[3], r[4], r[5], SALDO_INICIAL) for r in CRAQUES_INICIAIS]
        )
        print(f"  ✅ {len(CRAQUES_INICIAIS)} craques inseridos no banco")

    conn.commit()
    conn.close()
    print(f"  ✅ Banco de dados pronto: {DB_PATH}")

# ── Session helpers ───────────────────────────────────────────
def create_session():
    """Create a new session token."""
    token = secrets.token_hex(32)
    with session_lock:
        active_sessions[token] = time.time() + SESSION_TTL
    return token

def validate_session(token):
    """Check if a session token is valid and not expired."""
    with session_lock:
        expiry = active_sessions.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del active_sessions[token]
            return False
        return True

def cleanup_sessions():
    """Remove expired sessions."""
    now = time.time()
    with session_lock:
        expired = [k for k, v in active_sessions.items() if now > v]
        for k in expired:
            del active_sessions[k]

# ── Helpers ───────────────────────────────────────────────────
def cors_origin():
    """Return the allowed CORS origin."""
    return ALLOWED_ORIGIN if ALLOWED_ORIGIN else "*"

def add_security_headers(handler):
    """Add standard security headers to all responses."""
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "SAMEORIGIN")
    handler.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
    handler.send_header("Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'")

def json_response(handler, status, data):
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type",  "application/json; charset=utf-8")
    handler.send_header("Content-Length", len(body))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin",  cors_origin())
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Credentials", "true")
    add_security_headers(handler)
    handler.end_headers()
    handler.wfile.write(body)

def require_admin(handler):
    auth = handler.headers.get("Authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not validate_session(token):
        json_response(handler, 401, {"erro": "Não autorizado"})
        return False
    return True

def sanitize_str(value, max_len=MAX_FIELD_LEN):
    """Sanitize a string input: strip and truncate."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if len(value) > max_len:
        value = value[:max_len]
    return value

def serve_file(handler, filepath):
    ext_map = {
        ".html": "text/html; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".svg":  "image/svg+xml",
        ".ico":  "image/x-icon",
    }
    ext  = os.path.splitext(filepath)[1].lower()
    mime = ext_map.get(ext, "application/octet-stream")
    try:
        with open(filepath, "rb") as f:
            body = f.read()
        handler.send_response(200)
        handler.send_header("Content-Type",   mime)
        handler.send_header("Content-Length", len(body))
        # HTML must be revalidated; static assets can be cached aggressively.
        if ext == ".html":
            handler.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        else:
            handler.send_header("Cache-Control", "public, max-age=604800, immutable")
        add_security_headers(handler)
        handler.end_headers()
        handler.wfile.write(body)
    except FileNotFoundError:
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"404 Not Found")

# ── Handlers da API ───────────────────────────────────────────
def handle_get_craques(handler):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, nome, selecao, bandeira, cor, cor_sec, saldo FROM craques ORDER BY id"
    ).fetchall()
    conn.close()
    json_response(handler, 200, [dict(r) for r in rows])

def handle_get_compras(handler):
    conn = get_db()
    rows = conn.execute("""
        SELECT
            c.id,
            c.craque_id,
            cr.nome  AS craque,
            cr.selecao,
            cr.bandeira,
            c.jogador,
            c.posicao,
            c.valor,
            c.timestamp
        FROM compras c
        JOIN craques cr ON cr.id = c.craque_id
        ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    json_response(handler, 200, [dict(r) for r in rows])

def handle_login(handler):
    """Authenticate with password and return a session token."""
    length = int(handler.headers.get("Content-Length", 0))
    body   = handler.rfile.read(length)

    try:
        data = json.loads(body)
    except Exception:
        json_response(handler, 400, {"erro": "JSON inválido"})
        return

    password = data.get("senha", "")
    if not isinstance(password, str) or password != ADMIN_PASSWORD:
        json_response(handler, 401, {"erro": "Senha incorreta"})
        return

    cleanup_sessions()
    token = create_session()
    json_response(handler, 200, {"ok": True, "token": token})

def handle_post_compra(handler):
    length = int(handler.headers.get("Content-Length", 0))
    body   = handler.rfile.read(length)

    try:
        data = json.loads(body)
    except Exception:
        json_response(handler, 400, {"erro": "JSON inválido"})
        return

    craque_id   = data.get("craque_id")
    jogador     = sanitize_str(data.get("jogador") or "")
    posicao     = sanitize_str(data.get("posicao") or "")
    valor       = data.get("valor")

    # Validação de campos
    if not craque_id or not jogador or not posicao or not valor:
        json_response(handler, 400, {"erro": "Campos obrigatórios: craque_id, jogador, posicao, valor"})
        return

    if posicao not in ALLOWED_POSITIONS:
        json_response(handler, 400, {"erro": f"Posição inválida. Use: {', '.join(sorted(ALLOWED_POSITIONS))}"})
        return

    try:
        craque_id = int(craque_id)
    except (ValueError, TypeError):
        json_response(handler, 400, {"erro": "craque_id deve ser um número inteiro"})
        return

    try:
        valor = int(valor)
        if valor <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        json_response(handler, 400, {"erro": "Valor deve ser um número inteiro positivo"})
        return

    # Transação atômica
    with db_lock:
        conn = get_db()
        try:
            conn.execute("BEGIN EXCLUSIVE")
            craque = conn.execute(
                "SELECT id, nome, saldo FROM craques WHERE id = ?", (craque_id,)
            ).fetchone()

            if not craque:
                conn.rollback()
                conn.close()
                json_response(handler, 404, {"erro": "Craque não encontrado"})
                return

            if craque["saldo"] < valor:
                conn.rollback()
                conn.close()
                json_response(handler, 400, {
                    "erro": f"Saldo insuficiente. {craque['nome']} tem apenas {craque['saldo']:,} créditos"
                })
                return

            conn.execute(
                "UPDATE craques SET saldo = saldo - ? WHERE id = ?",
                (valor, craque_id)
            )
            conn.execute(
                "INSERT INTO compras (craque_id, jogador, posicao, valor) VALUES (?,?,?,?)",
                (craque_id, jogador, posicao, valor)
            )
            conn.execute("COMMIT")

            novo_saldo = conn.execute(
                "SELECT saldo FROM craques WHERE id = ?", (craque_id,)
            ).fetchone()["saldo"]
            conn.close()

            json_response(handler, 201, {
                "ok": True,
                "mensagem": f"{jogador} comprado com sucesso!",
                "novo_saldo": novo_saldo
            })

        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"  ❌ Erro interno em POST /api/compras: {e}")
            json_response(handler, 500, {"erro": "Erro interno do servidor"})

def handle_get_status(handler):
    json_response(handler, 200, {"iniciado": leilao_iniciado, "finalizado": leilao_finalizado})

def handle_iniciar(handler):
    global leilao_iniciado
    leilao_iniciado = True
    json_response(handler, 200, {"ok": True, "mensagem": "Leilão iniciado!"})

def handle_finalizar(handler):
    global leilao_finalizado
    leilao_finalizado = True
    json_response(handler, 200, {"ok": True, "mensagem": "Leilão finalizado!"})

def handle_reabrir(handler):
    global leilao_iniciado, leilao_finalizado
    leilao_iniciado = False
    leilao_finalizado = False
    json_response(handler, 200, {"ok": True, "mensagem": "Leilão reaberto!"})

def handle_reset(handler):
    """Endpoint de reset para testes — redefine todos os saldos e apaga compras"""
    global leilao_iniciado, leilao_finalizado
    leilao_iniciado = False
    leilao_finalizado = False
    with db_lock:
        conn = get_db()
        conn.execute("DELETE FROM compras")
        conn.execute("UPDATE craques SET saldo = ?", (SALDO_INICIAL,))
        conn.commit()
        conn.close()
    json_response(handler, 200, {"ok": True, "mensagem": "Sistema resetado com sucesso"})

def handle_delete_compra(handler, compra_id):
    """Desfaz uma compra — devolve o saldo ao craque"""
    with db_lock:
        conn = get_db()
        try:
            conn.execute("BEGIN EXCLUSIVE")
            compra = conn.execute(
                "SELECT id, craque_id, jogador, valor FROM compras WHERE id = ?", (compra_id,)
            ).fetchone()
            if not compra:
                conn.rollback()
                conn.close()
                json_response(handler, 404, {"erro": "Compra não encontrada"})
                return
            conn.execute("UPDATE craques SET saldo = saldo + ? WHERE id = ?",
                         (compra["valor"], compra["craque_id"]))
            conn.execute("DELETE FROM compras WHERE id = ?", (compra_id,))
            conn.execute("COMMIT")
            conn.close()
            json_response(handler, 200, {
                "ok": True,
                "mensagem": f"Compra de {compra['jogador']} desfeita com sucesso!"
            })
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"  ❌ Erro interno em DELETE /api/compras: {e}")
            json_response(handler, 500, {"erro": "Erro interno do servidor"})

# ── Request Handler principal ─────────────────────────────────
class LeilaoHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Log limpo e colorido
        status = args[1] if len(args) > 1 else "???"
        color  = "\033[32m" if str(status).startswith("2") else "\033[31m"
        reset  = "\033[0m"
        print(f"  {color}{args[1]}{reset}  {self.command:4} {args[0].split()[0]}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"

        # ── API routes ────────────────────────────────────────
        if path == "/api/craques":
            handle_get_craques(self)
            return
        if path == "/api/status":
            handle_get_status(self)
            return
        if path == "/api/compras":
            handle_get_compras(self)
            return

        # ── Static files ──────────────────────────────────────
        # Rotas amigáveis
        route_map = {
            "/":              "admin.html",
            "/admin":         "admin.html",
            "/telao":         "telao.html",
            "/manifest.json": "manifest.json",
            "/sw.js":         "sw.js",
        }
        if path in route_map:
            serve_file(self, os.path.join(FRONTEND, route_map[path]))
            return

        # Arquivos estáticos (css, js, img)
        safe_path = path.lstrip("/")
        full_path = os.path.realpath(os.path.join(FRONTEND, safe_path))
        frontend_real = os.path.realpath(FRONTEND)

        if full_path.startswith(frontend_real) and os.path.isfile(full_path):
            serve_file(self, full_path)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        import re
        m = re.match(r"/api/compras/(\d+)$", path)
        if m:
            if not require_admin(self):
                return
            handle_delete_compra(self, int(m.group(1)))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        if path == "/api/login":
            handle_login(self)
            return
        if path == "/api/compras":
            if not require_admin(self):
                return
            handle_post_compra(self)
            return
        if path == "/api/reset":
            if not require_admin(self):
                return
            handle_reset(self)
            return
        if path == "/api/iniciar":
            if not require_admin(self):
                return
            handle_iniciar(self)
            return
        if path == "/api/finalizar":
            if not require_admin(self):
                return
            handle_finalizar(self)
            return
        if path == "/api/reabrir":
            if not require_admin(self):
                return
            handle_reabrir(self)
            return

        self.send_response(404)
        self.end_headers()

# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║     ⚽  COPA UNASP 2026 — Servidor de Leilão     ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  Inicializando banco de dados...")
    init_db()
    print()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), LeilaoHandler)

    print(f"  🌐 Servidor rodando em http://localhost:{PORT}")
    print(f"  📋 Admin  →  http://localhost:{PORT}/admin")
    print(f"  📺 Telão  →  http://localhost:{PORT}/telao")
    print(f"  🗃️  Banco  →  {DB_PATH}")
    print()
    print("  Pressione Ctrl+C para encerrar.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  ⛔ Servidor encerrado.")
