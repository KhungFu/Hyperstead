#!/usr/bin/env python3
"""
PaperclipLite - Agenten-Team als Knoten-Editor (Self-hosted, Raspberry-Pi-tauglich)

Start:  python3 app.py        ->  http://127.0.0.1:8787
Keys:   in .env (siehe .env.example), mehrere Keys pro Anbieter mit Komma = Rotation
"""
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

import requests
from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory

BASE = Path(__file__).resolve().parent


# ----------------------------------------------------------------- .env laden
def load_env():
    f = BASE / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()

DB_PATH = os.environ.get("PCL_DB", str(BASE / "data.db"))
WORKSPACE = Path(os.environ.get("PCL_WORKSPACE", str(BASE / "workspace"))).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get("APP_TOKEN", "")  # = Passwort fuer die Login-Seite
MAX_DEPTH = int(os.environ.get("PCL_MAX_DEPTH", "4"))
ALLOW_CLI = os.environ.get("PCL_ALLOW_CLI", "0") == "1"
# Shell-Ausfuehrung ist standardmaessig AUS (auch nach Freigabe). Nur bewusst aktivieren.
ALLOW_SHELL = os.environ.get("PCL_ALLOW_SHELL", "0") == "1"
# 1 = hinter Cloudflare Tunnel / Tailscale Funnel / Reverse-Proxy (Client-IP aus Headern, Cookie "Secure")
TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
SESSION_DAYS = 7

# Alle Anbieter sprechen das OpenAI-kompatible Chat-Format.
# Modellnamen aendern sich oft -> im Agenten-Panel frei editierbar.
PROVIDERS = {
    "groq": {
        "label": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "label": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
    },
    "deepseek": {
        "label": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
    "qwen": {
        "label": "Qwen (DashScope)",
        "url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key_env": "QWEN_API_KEY",
        "model": "qwen-plus",
    },
    "ollama": {
        "label": "Ollama (lokal)",
        "url": os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions"),
        "key_env": None,
        "model": os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
    },
    "cli": {
        "label": "CLI-Agent (z.B. claude -p)",
        "url": None,
        "key_env": None,
        "model": "",
    },
    "mock": {"label": "Mock (Test, kostenlos)", "url": None, "key_env": None, "model": "mock"},
}

DEFAULT_PERMS = {"delegate": False, "auto_run": False, "write_files": False, "shell": False}

# ------------------------------------------------------------------ Datenbank
SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, goal TEXT DEFAULT '', created REAL);
CREATE TABLE IF NOT EXISTS agents(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, name TEXT NOT NULL,
  role TEXT DEFAULT '', parent_id INTEGER, x REAL DEFAULT 0, y REAL DEFAULT 0,
  provider TEXT DEFAULT 'mock', model TEXT DEFAULT '', system_prompt TEXT DEFAULT '',
  perms TEXT DEFAULT '{}', budget_tokens INTEGER DEFAULT 0, cli_command TEXT DEFAULT '',
  paused INTEGER DEFAULT 0, created REAL);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, agent_id INTEGER NOT NULL,
  parent_task_id INTEGER, title TEXT NOT NULL, description TEXT DEFAULT '',
  status TEXT DEFAULT 'todo', result TEXT DEFAULT '', created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, task_id INTEGER, agent_id INTEGER,
  kind TEXT, payload TEXT, status TEXT DEFAULT 'pending', output TEXT DEFAULT '', created REAL);
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id INTEGER, ts REAL, tokens INTEGER);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, project_id INTEGER, agent_id INTEGER,
  task_id INTEGER, event TEXT, detail TEXT);
"""


def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with closing(conn()) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        c.execute(
            "UPDATE tasks SET status='failed', result=result||'\n\n(Abgebrochen: Neustart)' "
            "WHERE status='running'"
        )
        c.commit()


def q(sql, args=()):
    with closing(conn()) as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def q1(sql, args=()):
    r = q(sql, args)
    return r[0] if r else None


def ex(sql, args=()):
    with closing(conn()) as c:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid


def log(event, detail="", project_id=None, agent_id=None, task_id=None):
    ex(
        "INSERT INTO audit(ts,project_id,agent_id,task_id,event,detail) VALUES(?,?,?,?,?,?)",
        (time.time(), project_id, agent_id, task_id, event, str(detail)[:4000]),
    )


def perms_of(agent):
    try:
        p = json.loads(agent.get("perms") or "{}")
    except Exception:
        p = {}
    out = dict(DEFAULT_PERMS)
    out.update({k: bool(p.get(k)) for k in DEFAULT_PERMS})
    return out


def month_start():
    t = time.gmtime()
    return time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0)) - time.timezone


def used_tokens(agent_id):
    r = q1("SELECT COALESCE(SUM(tokens),0) AS s FROM usage WHERE agent_id=? AND ts>=?",
           (agent_id, month_start()))
    return int(r["s"])


# ----------------------------------------------------------------- LLM-Anbieter
_key_idx = {}


def provider_keys(pid):
    env = PROVIDERS[pid]["key_env"]
    if not env:
        return [None]
    return [k.strip() for k in os.environ.get(env, "").split(",") if k.strip()]


_ollama_cache = {"t": 0, "ok": False}


def ollama_reachable():
    """Kurzer TCP-Check (10 s gecacht), damit Ollama nur als verfuegbar gilt, wenn es laeuft."""
    import socket
    from urllib.parse import urlparse
    if time.time() - _ollama_cache["t"] < 10:
        return _ollama_cache["ok"]
    u = urlparse(PROVIDERS["ollama"]["url"])
    try:
        with socket.create_connection((u.hostname, u.port or 80), timeout=0.4):
            ok = True
    except OSError:
        ok = False
    _ollama_cache.update(t=time.time(), ok=ok)
    return ok


def provider_configured(pid):
    if pid == "mock":
        return True
    if pid == "cli":
        return ALLOW_CLI
    if pid == "ollama":
        return ollama_reachable()
    return bool(provider_keys(pid))


def call_llm(agent, messages):
    """Gibt (text, tokens) zurueck. Rotiert Keys bei 429/5xx."""
    pid = agent["provider"]
    if pid not in PROVIDERS:
        raise RuntimeError(f"Unbekannter Anbieter: {pid}")

    if pid == "mock":
        return mock_llm(agent, messages)

    if pid == "cli":
        if not ALLOW_CLI:
            raise RuntimeError("CLI-Agenten sind aus. In .env PCL_ALLOW_CLI=1 setzen.")
        cmd = (agent.get("cli_command") or "").strip()
        if not cmd:
            raise RuntimeError("Kein CLI-Befehl eingetragen.")
        prompt = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
        try:
            r = subprocess.run(shlex.split(cmd), input=prompt, capture_output=True,
                               text=True, timeout=300, cwd=str(WORKSPACE))
        except subprocess.TimeoutExpired:
            raise RuntimeError("CLI-Agent: Zeitlimit (300 s)")
        if r.returncode != 0:
            raise RuntimeError(f"CLI-Fehler: {(r.stderr or r.stdout)[-500:]}")
        out = r.stdout.strip()
        return out, max(1, (len(prompt) + len(out)) // 4)

    cfg = PROVIDERS[pid]
    keys = provider_keys(pid)
    if not keys:
        raise RuntimeError(f"Kein API-Key fuer {cfg['label']} ({cfg['key_env']}) in .env")
    model = agent.get("model") or cfg["model"]
    start = _key_idx.get(pid, 0)
    last = None
    for i in range(len(keys)):
        idx = (start + i) % len(keys)
        headers = {"Content-Type": "application/json"}
        if keys[idx]:
            headers["Authorization"] = f"Bearer {keys[idx]}"
        try:
            r = requests.post(cfg["url"], headers=headers, timeout=120,
                              json={"model": model, "messages": messages, "temperature": 0.4})
        except requests.RequestException as e:
            last = f"Netzwerk: {e}"
            continue
        if r.status_code == 200:
            _key_idx[pid] = idx
            d = r.json()
            text = d["choices"][0]["message"]["content"] or ""
            tok = (d.get("usage") or {}).get("total_tokens") or max(
                1, (sum(len(m["content"]) for m in messages) + len(text)) // 4)
            return text, int(tok)
        last = f"HTTP {r.status_code}: {r.text[:300]}"
        if r.status_code in (429, 500, 502, 503, 504):
            continue  # naechster Key
        break
    raise RuntimeError(last or "Unbekannter Fehler")


def mock_llm(agent, messages):
    """Offline-Test: delegiert an alle direkten Mitarbeiter, wenn erlaubt."""
    user = messages[-1]["content"]
    out = {"result": f"[Mock {agent['name']}] Auftrag bearbeitet: {user[:120]}"}
    kids = q("SELECT name FROM agents WHERE parent_id=?", (agent["id"],))
    if perms_of(agent)["delegate"] and kids and "[Teilaufgabe]" not in user:
        out["delegate"] = [
            {"to": k["name"], "title": "[Teilaufgabe] " + user.split("\n")[0][:60],
             "description": "Bitte uebernehmen: " + user[:200]} for k in kids]
    if perms_of(agent)["write_files"]:
        out["write_file"] = [{"path": f"{agent['name'].lower()}_notiz.txt",
                              "content": "Mock-Datei\n" + user[:200]}]
    return json.dumps(out, ensure_ascii=False), 50


# ---------------------------------------------------------------- Prompt bauen
def build_system(agent, project):
    perms = perms_of(agent)
    parent = q1("SELECT name, role FROM agents WHERE id=?", (agent["parent_id"],)) if agent["parent_id"] else None
    kids = q("SELECT name, role FROM agents WHERE parent_id=?", (agent["id"],))
    s = [f"Du bist '{agent['name']}' (Rolle: {agent['role'] or 'Agent'}) in einem KI-Team.",
         f"Projekt: {project['name']}", f"Projektziel: {project['goal'] or '(nicht gesetzt)'}"]
    if parent:
        s.append(f"Dein Vorgesetzter: {parent['name']} ({parent['role']}).")
    if kids:
        s.append("Deine direkten Mitarbeiter: " + ", ".join(f"{k['name']} ({k['role']})" for k in kids))
    if agent["system_prompt"].strip():
        s.append("\nArbeitsanweisung:\n" + agent["system_prompt"].strip())

    fields = ['"result": "dein Ergebnis / Bericht als Text"']
    rules = []
    if perms["delegate"] and kids:
        fields.append('"delegate": [{"to": "Name des Mitarbeiters", "title": "...", "description": "..."}]')
        rules.append("delegate nur an deine direkten Mitarbeiter (exakter Name).")
    if perms["write_files"]:
        fields.append('"write_file": [{"path": "relativer/pfad.txt", "content": "..."}]')
        rules.append("write_file schreibt nur in dein Projekt-Arbeitsverzeichnis.")
    if perms["shell"]:
        fields.append('"shell": ["befehl"]')
        rules.append("shell-Befehle werden erst nach menschlicher Freigabe ausgefuehrt.")
    s.append("\nAntworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Text davor oder danach:\n{"
             + ", ".join(fields) + "}\nNur 'result' ist Pflicht. " + " ".join(rules)
             + " Alles ausser den hier genannten Aktionen ist dir nicht erlaubt.")
    return "\n".join(s)


def parse_output(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        try:
            d = json.loads(t[a:b + 1])
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {"result": text}


def task_depth(task):
    d, cur = 0, task
    while cur and cur.get("parent_task_id") and d < 50:
        cur = q1("SELECT * FROM tasks WHERE id=?", (cur["parent_task_id"],))
        d += 1
    return d


# -------------------------------------------------------------- Task ausfuehren
def set_task(tid, status=None, result=None):
    sets, args = ["updated=?"], [time.time()]
    if status is not None:
        sets.append("status=?")
        args.append(status)
    if result is not None:
        sets.append("result=?")
        args.append(result)
    args.append(tid)
    ex(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?", args)


def report_up(task):
    pt = task.get("parent_task_id")
    if not pt:
        return
    parent = q1("SELECT * FROM tasks WHERE id=?", (pt,))
    ag = q1("SELECT name FROM agents WHERE id=?", (task["agent_id"],))
    cur = q1("SELECT result FROM tasks WHERE id=?", (task["id"],))
    if parent and ag and cur:
        add = f"\n\n--- Bericht von {ag['name']}: {task['title']} ---\n{cur['result'][:2000]}"
        set_task(pt, result=(parent["result"] + add)[:20000])


def execute_task(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t:
        return
    a = q1("SELECT * FROM agents WHERE id=?", (t["agent_id"],))
    p = q1("SELECT * FROM projects WHERE id=?", (t["project_id"],))
    if not a or not p:
        set_task(tid, "failed", "Agent oder Projekt existiert nicht mehr.")
        return
    pid, aid = p["id"], a["id"]
    if a["paused"]:
        set_task(tid, "blocked", "Agent ist pausiert.")
        log("blocked", "Agent pausiert", pid, aid, tid)
        return
    used = used_tokens(aid)
    if a["budget_tokens"] > 0 and used >= a["budget_tokens"]:
        set_task(tid, "blocked", "Monatsbudget erreicht. Budget erhoehen oder naechsten Monat abwarten.")
        log("budget_stop", f"{used}/{a['budget_tokens']}", pid, aid, tid)
        return

    set_task(tid, "running", "")
    log("task_start", t["title"], pid, aid, tid)
    perms = perms_of(a)
    user = f"Aufgabe: {t['title']}\n\n{t['description']}".strip()
    messages = [{"role": "system", "content": build_system(a, p)},
                {"role": "user", "content": user}]
    try:
        text, tokens = call_llm(a, messages)
    except Exception as e:
        set_task(tid, "failed", f"Fehler: {e}")
        log("task_failed", e, pid, aid, tid)
        return

    ex("INSERT INTO usage(agent_id,ts,tokens) VALUES(?,?,?)", (aid, time.time(), tokens))
    if a["budget_tokens"] > 0 and used < 0.8 * a["budget_tokens"] <= used + tokens:
        log("budget_warn", f"80% erreicht ({used + tokens}/{a['budget_tokens']})", pid, aid, tid)

    data = parse_output(text)
    result = str(data.get("result") or text).strip()
    notes = []

    # --- delegieren
    dele = data.get("delegate")
    if dele:
        if not perms["delegate"]:
            notes.append("Delegieren nicht erlaubt - ignoriert.")
            log("denied", "delegate", pid, aid, tid)
        elif task_depth(t) >= MAX_DEPTH:
            notes.append(f"Max. Delegationstiefe ({MAX_DEPTH}) erreicht - ignoriert.")
        else:
            kids = {k["name"].lower(): k for k in q("SELECT id,name FROM agents WHERE parent_id=?", (aid,))}
            for item in (dele if isinstance(dele, list) else [])[:5]:
                kid = kids.get(str(item.get("to", "")).lower())
                if not kid:
                    notes.append(f"Unbekannter Mitarbeiter '{item.get('to')}' - ignoriert.")
                    continue
                st = "queued" if perms["auto_run"] else "todo"
                nid = ex(
                    "INSERT INTO tasks(project_id,agent_id,parent_task_id,title,description,status,created,updated)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (pid, kid["id"], tid, str(item.get("title", "Aufgabe"))[:200],
                     str(item.get("description", ""))[:4000], st, time.time(), time.time()))
                log("delegated", f"an {kid['name']}: {item.get('title')}", pid, aid, nid)
                notes.append(f"Delegiert an {kid['name']}: {item.get('title')} ({'startet automatisch' if st == 'queued' else 'wartet auf Start'})")

    # --- Dateien schreiben
    wf = data.get("write_file")
    if wf:
        if not perms["write_files"]:
            notes.append("Dateien schreiben nicht erlaubt - ignoriert.")
            log("denied", "write_file", pid, aid, tid)
        else:
            root = (WORKSPACE / str(pid)).resolve()
            root.mkdir(parents=True, exist_ok=True)
            for f in (wf if isinstance(wf, list) else [])[:5]:
                try:
                    target = (root / str(f.get("path", ""))).resolve()
                    target.relative_to(root)  # Pfad muss im Projektordner bleiben
                    content = str(f.get("content", ""))[:200_000]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                    notes.append(f"Datei geschrieben: {target.relative_to(root)}")
                    log("file_written", str(target.relative_to(root)), pid, aid, tid)
                except Exception as e:
                    notes.append(f"Datei abgelehnt ({f.get('path')}): {e}")
                    log("denied", f"write_file {f.get('path')}: {e}", pid, aid, tid)

    # --- Shell -> immer Freigabe
    pending = 0
    sh = data.get("shell")
    if sh:
        if not perms["shell"]:
            notes.append("Shell nicht erlaubt - ignoriert.")
            log("denied", "shell", pid, aid, tid)
        elif not ALLOW_SHELL:
            notes.append("Shell ist auf dem Server deaktiviert (PCL_ALLOW_SHELL=1 in .env) - ignoriert.")
            log("denied", "shell serverseitig aus", pid, aid, tid)
        else:
            for cmd in (sh if isinstance(sh, list) else [sh])[:3]:
                ex("INSERT INTO approvals(project_id,task_id,agent_id,kind,payload,created) VALUES(?,?,?,?,?,?)",
                   (pid, tid, aid, "shell", str(cmd)[:2000], time.time()))
                log("approval_requested", cmd, pid, aid, tid)
                notes.append(f"Wartet auf Freigabe: $ {cmd}")
                pending += 1

    final = result + ("\n\n" + "\n".join(notes) if notes else "")
    if pending:
        set_task(tid, "waiting_approval", final)
    else:
        set_task(tid, "done", final)
        report_up(q1("SELECT * FROM tasks WHERE id=?", (tid,)))
        log("task_done", t["title"], pid, aid, tid)


# ----------------------------------------------------------------- Worker
def worker():
    while True:
        try:
            nxt = q1("SELECT id FROM tasks WHERE status='queued' ORDER BY id LIMIT 1")
            if nxt:
                execute_task(nxt["id"])
            else:
                time.sleep(1)
        except Exception as e:  # Worker darf nie sterben
            print("Worker-Fehler:", e)
            time.sleep(2)


def start_worker():
    threading.Thread(target=worker, daemon=True).start()


# -------------------------------------------------------------------- Web-API
app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="/static")


# ------------------------------------------------------------- Login / Sitzung
def _secret():
    """Zufaelliger Signatur-Schluessel, einmalig erzeugt. Passwortwechsel macht alte Sitzungen ungueltig."""
    f = BASE / ".session_secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        try:
            f.chmod(0o600)
        except OSError:
            pass
    return (f.read_text().strip() + "|" + TOKEN).encode()


def _sign(exp):
    return hmac.new(_secret(), f"pcl|{exp}".encode(), hashlib.sha256).hexdigest()


def make_cookie():
    exp = int(time.time()) + SESSION_DAYS * 86400
    return f"{exp}.{_sign(exp)}"


def verify_cookie(v):
    try:
        exp, sig = (v or "").split(".", 1)
        return int(exp) > time.time() and hmac.compare_digest(sig, _sign(exp))
    except Exception:
        return False


def client_ip():
    if TRUST_PROXY:
        ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", "")
        ip = ip.split(",")[0].strip()
        if ip:
            return ip
    return request.remote_addr or "?"


def is_https():
    return request.is_secure or (TRUST_PROXY and request.headers.get("X-Forwarded-Proto") == "https")


_fails = {}  # ip -> [fehlversuche, fensterstart, gesperrt_bis]

LOGIN_HTML = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PaperclipLite – Login</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0b0c;color:#e8e8ea;
font:15px system-ui,sans-serif}form{background:#111113;border:1px solid #27272b;border-radius:14px;padding:28px;width:min(340px,90vw)}
.logo{width:34px;height:34px;border-radius:10px;background:#f97316;display:grid;place-items:center;font-weight:700;color:#fff;margin-bottom:14px}
input{width:100%;box-sizing:border-box;margin:10px 0;padding:10px;border-radius:8px;border:1px solid #27272b;background:#0b0b0c;color:inherit;font:inherit}
button{width:100%;padding:10px;border:0;border-radius:8px;background:#f97316;color:#fff;font:inherit;cursor:pointer}
.err{color:#ff8a8a;font-size:13px;min-height:18px}</style></head><body>
<form method="post" action="/login"><div class="logo">P</div><b>PaperclipLite</b>
<input type="password" name="password" placeholder="Passwort" autofocus autocomplete="current-password">
<div class="err">__MSG__</div><button>Anmelden</button></form></body></html>"""


def login_page(msg="", status=200):
    return Response(LOGIN_HTML.replace("__MSG__", html.escape(msg)), status=status, mimetype="text/html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not TOKEN:
        return redirect("/")
    if request.method == "GET":
        return login_page()
    ip, now = client_ip(), time.time()
    f = _fails.get(ip, [0, now, 0])
    if f[2] > now:
        return login_page(f"Zu viele Versuche. Bitte {int(f[2] - now) // 60 + 1} Min. warten.", 429)
    if hmac.compare_digest(request.form.get("password", "").encode(), TOKEN.encode()):
        _fails.pop(ip, None)
        log("login_ok", ip)
        resp = redirect("/")
        resp.set_cookie("pcl", make_cookie(), httponly=True, samesite="Strict",
                        secure=is_https(), max_age=SESSION_DAYS * 86400)
        return resp
    time.sleep(0.7)  # bremst automatisches Raten
    if now - f[1] > 600:
        f = [0, now, 0]
    f[0] += 1
    if f[0] >= 5:
        f = [0, now, now + 600]  # 10 Min. Sperre pro IP
    _fails[ip] = f
    log("login_failed", ip)
    return login_page("Falsches Passwort.", 401)


@app.route("/logout")
def logout():
    resp = redirect("/login" if TOKEN else "/")
    resp.delete_cookie("pcl")
    return resp


@app.before_request
def guard():
    if request.path == "/login":
        return
    if TOKEN and not verify_cookie(request.cookies.get("pcl")):
        if request.path.startswith("/api/"):
            abort(401)
        return redirect("/login")
    # CSRF: schreibende API-Aufrufe brauchen einen eigenen Header (loest Browser-Preflight aus)
    if request.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("X-PCL") != "1":
            abort(403)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'")
    if is_https():
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    return resp


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/info")
def api_info():
    return jsonify({"auth": bool(TOKEN), "allow_shell": ALLOW_SHELL, "allow_cli": ALLOW_CLI})


@app.get("/api/providers")
def api_providers():
    return jsonify([{"id": k, "label": v["label"], "configured": provider_configured(k),
                     "model": v["model"]} for k, v in PROVIDERS.items()])


@app.get("/api/projects")
def api_projects():
    return jsonify(q("SELECT * FROM projects ORDER BY id"))


@app.post("/api/projects")
def api_project_new():
    d = request.get_json(force=True)
    pid = ex("INSERT INTO projects(name,goal,created) VALUES(?,?,?)",
             (str(d.get("name") or "Neues Projekt")[:100], str(d.get("goal", ""))[:2000], time.time()))
    log("project_created", d.get("name"), pid)
    return jsonify({"id": pid})


@app.put("/api/projects/<int:pid>")
def api_project_put(pid):
    d = request.get_json(force=True)
    for k in ("name", "goal"):
        if k in d:
            ex(f"UPDATE projects SET {k}=? WHERE id=?", (str(d[k])[:2000], pid))
    return jsonify({"ok": True})


@app.delete("/api/projects/<int:pid>")
def api_project_del(pid):
    ex("DELETE FROM tasks WHERE project_id=?", (pid,))
    ex("DELETE FROM approvals WHERE project_id=?", (pid,))
    ex("DELETE FROM agents WHERE project_id=?", (pid,))
    ex("DELETE FROM projects WHERE id=?", (pid,))
    log("project_deleted", pid, pid)  # Audit bleibt erhalten
    return jsonify({"ok": True})


@app.get("/api/projects/<int:pid>/graph")
def api_graph(pid):
    proj = q1("SELECT * FROM projects WHERE id=?", (pid,))
    if not proj:
        abort(404)
    agents = q("SELECT * FROM agents WHERE project_id=? ORDER BY id", (pid,))
    counts = {}
    for r in q("SELECT agent_id, status, COUNT(*) c FROM tasks WHERE project_id=? GROUP BY agent_id, status", (pid,)):
        counts.setdefault(r["agent_id"], {})[r["status"]] = r["c"]
    for a in agents:
        a["perms"] = perms_of(a)
        a["used_tokens"] = used_tokens(a["id"])
        a["counts"] = counts.get(a["id"], {})
    pend = q1("SELECT COUNT(*) c FROM approvals WHERE status='pending'")["c"]
    return jsonify({"project": proj, "agents": agents, "pending_approvals": pend})


def has_cycle(agent_id, new_parent):
    cur, n = new_parent, 0
    while cur and n < 100:
        if cur == agent_id:
            return True
        r = q1("SELECT parent_id FROM agents WHERE id=?", (cur,))
        cur = r["parent_id"] if r else None
        n += 1
    return False


@app.post("/api/projects/<int:pid>/agents")
def api_agent_new(pid):
    d = request.get_json(force=True)
    perms = dict(DEFAULT_PERMS)
    perms.update({k: bool(v) for k, v in (d.get("perms") or {}).items() if k in DEFAULT_PERMS})
    prov = d.get("provider") if d.get("provider") in PROVIDERS else "mock"
    aid = ex(
        "INSERT INTO agents(project_id,name,role,x,y,provider,model,system_prompt,perms,budget_tokens,created)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (pid, str(d.get("name") or "Agent")[:60], str(d.get("role", ""))[:100],
         float(d.get("x", 0)), float(d.get("y", 0)), prov, str(d.get("model", ""))[:100],
         str(d.get("system_prompt", ""))[:8000], json.dumps(perms),
         int(d.get("budget_tokens") or 0), time.time()))
    log("agent_created", d.get("name"), pid, aid)
    return jsonify({"id": aid})


@app.put("/api/agents/<int:aid>")
def api_agent_put(aid):
    a = q1("SELECT * FROM agents WHERE id=?", (aid,))
    if not a:
        abort(404)
    d = request.get_json(force=True)
    changed = []
    if "parent_id" in d:
        np = d["parent_id"]
        if np is not None:
            np = int(np)
            pa = q1("SELECT project_id FROM agents WHERE id=?", (np,))
            if not pa or pa["project_id"] != a["project_id"]:
                abort(400, "Ungueltiger Vorgesetzter")
            if has_cycle(aid, np):
                abort(400, "Zyklus: Ein Agent kann nicht sein eigener Vorgesetzter sein.")
        ex("UPDATE agents SET parent_id=? WHERE id=?", (np, aid))
        changed.append("parent")
    for k, cast, mx in (("name", str, 60), ("role", str, 100), ("model", str, 100),
                        ("system_prompt", str, 8000), ("cli_command", str, 500)):
        if k in d:
            ex(f"UPDATE agents SET {k}=? WHERE id=?", (cast(d[k])[:mx], aid))
            changed.append(k)
    for k in ("x", "y"):
        if k in d:
            ex(f"UPDATE agents SET {k}=? WHERE id=?", (float(d[k]), aid))
    if "provider" in d:
        if d["provider"] not in PROVIDERS:
            abort(400, "Unbekannter Anbieter")
        ex("UPDATE agents SET provider=? WHERE id=?", (d["provider"], aid))
        changed.append("provider")
    if "budget_tokens" in d:
        ex("UPDATE agents SET budget_tokens=? WHERE id=?", (max(0, int(d["budget_tokens"] or 0)), aid))
        changed.append("budget")
    if "paused" in d:
        ex("UPDATE agents SET paused=? WHERE id=?", (1 if d["paused"] else 0, aid))
        changed.append("paused" if d["paused"] else "resumed")
    if "perms" in d:
        p = dict(DEFAULT_PERMS)
        p.update({k: bool(v) for k, v in (d["perms"] or {}).items() if k in DEFAULT_PERMS})
        ex("UPDATE agents SET perms=? WHERE id=?", (json.dumps(p), aid))
        changed.append("perms=" + json.dumps(p))
    if changed:
        log("agent_updated", ", ".join(changed), a["project_id"], aid)
    return jsonify({"ok": True})


@app.delete("/api/agents/<int:aid>")
def api_agent_del(aid):
    a = q1("SELECT * FROM agents WHERE id=?", (aid,))
    if not a:
        abort(404)
    ex("UPDATE agents SET parent_id=NULL WHERE parent_id=?", (aid,))
    ex("DELETE FROM tasks WHERE agent_id=?", (aid,))
    ex("DELETE FROM agents WHERE id=?", (aid,))
    log("agent_deleted", a["name"], a["project_id"], aid)
    return jsonify({"ok": True})


@app.get("/api/agents/<int:aid>/tasks")
def api_tasks(aid):
    return jsonify(q("SELECT * FROM tasks WHERE agent_id=? ORDER BY id DESC LIMIT 100", (aid,)))


@app.post("/api/agents/<int:aid>/tasks")
def api_task_new(aid):
    a = q1("SELECT * FROM agents WHERE id=?", (aid,))
    if not a:
        abort(404)
    d = request.get_json(force=True)
    title = str(d.get("title") or "").strip()
    if not title:
        abort(400, "Titel fehlt")
    st = "queued" if d.get("run") else "todo"
    tid = ex("INSERT INTO tasks(project_id,agent_id,title,description,status,created,updated) VALUES(?,?,?,?,?,?,?)",
             (a["project_id"], aid, title[:200], str(d.get("description", ""))[:8000], st, time.time(), time.time()))
    log("task_created", title, a["project_id"], aid, tid)
    return jsonify({"id": tid})


@app.post("/api/tasks/<int:tid>/run")
def api_task_run(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t:
        abort(404)
    if t["status"] in ("running", "queued", "waiting_approval"):
        abort(400, "Aufgabe laeuft bereits bzw. wartet auf Freigabe.")
    set_task(tid, "queued")
    return jsonify({"ok": True})


@app.delete("/api/tasks/<int:tid>")
def api_task_del(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if t:
        ex("DELETE FROM approvals WHERE task_id=? AND status='pending'", (tid,))
        ex("DELETE FROM tasks WHERE id=?", (tid,))
        log("task_deleted", t["title"], t["project_id"], t["agent_id"], tid)
    return jsonify({"ok": True})


@app.get("/api/approvals")
def api_approvals():
    rows = q("""SELECT ap.*, a.name AS agent_name, t.title AS task_title
                FROM approvals ap LEFT JOIN agents a ON a.id=ap.agent_id
                LEFT JOIN tasks t ON t.id=ap.task_id
                WHERE ap.status='pending' ORDER BY ap.id""")
    return jsonify(rows)


@app.post("/api/approvals/<int:aid>")
def api_approval_decide(aid):
    ap = q1("SELECT * FROM approvals WHERE id=?", (aid,))
    if not ap or ap["status"] != "pending":
        abort(404)
    decision = request.get_json(force=True).get("decision")
    t = q1("SELECT * FROM tasks WHERE id=?", (ap["task_id"],))
    pid = ap["project_id"]
    if decision == "deny":
        ex("UPDATE approvals SET status='denied' WHERE id=?", (aid,))
        log("approval_denied", ap["payload"], pid, ap["agent_id"], ap["task_id"])
        add = f"\n\nAbgelehnt: $ {ap['payload']}"
    elif decision == "approve":
        if not ALLOW_SHELL:
            abort(400, "Shell ist auf dem Server deaktiviert (PCL_ALLOW_SHELL=1 in .env).")
        proj_dir = WORKSPACE / str(pid)
        proj_dir.mkdir(parents=True, exist_ok=True)
        try:
            r = subprocess.run(ap["payload"], shell=True, cwd=str(proj_dir),
                               capture_output=True, text=True, timeout=30)
            out = (r.stdout + r.stderr)[-4000:]
            out = f"(Exit {r.returncode})\n{out}"
        except subprocess.TimeoutExpired:
            out = "Zeitlimit (30 s) - abgebrochen."
        ex("UPDATE approvals SET status='approved', output=? WHERE id=?", (out, aid))
        log("approval_granted", ap["payload"], pid, ap["agent_id"], ap["task_id"])
        add = f"\n\n$ {ap['payload']}\n{out}"
    else:
        abort(400)
    if t:
        set_task(t["id"], result=(t["result"] + add)[:20000])
        left = q1("SELECT COUNT(*) c FROM approvals WHERE task_id=? AND status='pending'", (t["id"],))["c"]
        if left == 0:
            set_task(t["id"], "done")
            report_up(q1("SELECT * FROM tasks WHERE id=?", (t["id"],)))
    return jsonify({"ok": True})


@app.get("/api/audit")
def api_audit():
    pid = request.args.get("project_id")
    aid = request.args.get("agent_id")
    sql, args = "SELECT au.*, a.name AS agent_name FROM audit au LEFT JOIN agents a ON a.id=au.agent_id WHERE 1=1", []
    if pid:
        sql += " AND au.project_id=?"
        args.append(int(pid))
    if aid:
        sql += " AND au.agent_id=?"
        args.append(int(aid))
    sql += " ORDER BY au.id DESC LIMIT ?"
    args.append(min(int(request.args.get("limit", 100)), 500))
    return jsonify(q(sql, args))


@app.errorhandler(400)
def bad(e):
    return (e.description if hasattr(e, "description") else "Fehler"), 400


if __name__ == "__main__":
    init_db()
    start_worker()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8787"))
    exposed = host not in ("127.0.0.1", "localhost", "::1") or TRUST_PROXY
    if exposed and len(TOKEN) < 12:
        sys.exit("ABBRUCH: Die App ist von aussen erreichbar (HOST/TRUST_PROXY), aber APP_TOKEN fehlt "
                 "oder ist kuerzer als 12 Zeichen. Setze ein langes Passwort in .env.")
    if exposed and ALLOW_SHELL:
        print("WARNUNG: PCL_ALLOW_SHELL=1 bei erreichbarer App - wer das Passwort hat, kann Befehle freigeben.")
    print(f"PaperclipLite laeuft auf http://{host}:{port}  (Login: {'an' if TOKEN else 'aus'}, "
          f"Shell: {'an' if ALLOW_SHELL else 'aus'})")
    app.run(host=host, port=port, threaded=True)
