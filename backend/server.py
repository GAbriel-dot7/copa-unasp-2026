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
import re
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ── Configuração ─────────────────────────────────────────────
PORT        = int(os.environ.get("PORT", 3000))
DB_PATH     = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "database.db"))
FRONTEND    = os.path.join(os.path.dirname(__file__), "..", "frontend")
SALDO_INICIAL = 100_000
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "neorobson")
leilao_iniciado = False     # estado global do leilão
leilao_finalizado = False   # estado global do leilão

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
            posicao   TEXT DEFAULT '',
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

# ── Helpers ───────────────────────────────────────────────────
def json_response(handler, status, data):
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type",  "application/json; charset=utf-8")
    handler.send_header("Content-Length", len(body))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin",  "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Token")
    handler.end_headers()
    handler.wfile.write(body)

def require_admin(handler):
    token = handler.headers.get("X-Admin-Token", "")
    if token != ADMIN_TOKEN:
        json_response(handler, 401, {"erro": "Não autorizado"})
        return False
    return True

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

def handle_post_compra(handler):
    length = int(handler.headers.get("Content-Length", 0))
    body   = handler.rfile.read(length)

    try:
        data = json.loads(body)
    except Exception:
        json_response(handler, 400, {"erro": "JSON inválido"})
        return

    craque_id   = data.get("craque_id")
    jogador     = (data.get("jogador") or "").strip()
    posicao     = (data.get("posicao") or "").strip()
    valor       = data.get("valor")

    # Validação de campos (posicao é opcional)
    if not craque_id or not jogador or not valor:
        json_response(handler, 400, {"erro": "Campos obrigatórios: craque_id, jogador, valor"})
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
            json_response(handler, 500, {"erro": f"Erro interno: {str(e)}"})

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
        conn.execute(f"UPDATE craques SET saldo = {SALDO_INICIAL}")
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
            json_response(handler, 500, {"erro": str(e)})

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
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Token")
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
