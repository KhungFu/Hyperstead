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
import queue
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
MAX_DEPTH = int(os.environ.get("PCL_MAX_DEPTH", "8"))
ALLOW_CLI = os.environ.get("PCL_ALLOW_CLI", "0") == "1"
# Shell-Ausfuehrung ist standardmaessig AUS (auch nach Freigabe). Nur bewusst aktivieren.
ALLOW_SHELL = os.environ.get("PCL_ALLOW_SHELL", "0") == "1"
# 1 = hinter Cloudflare Tunnel / Tailscale Funnel / Reverse-Proxy (Client-IP aus Headern, Cookie "Secure")
TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
SESSION_DAYS = 7

# Telegram (optional): Post vom Chef aufs Handy, Antworten = neuer Auftrag / Ueberarbeiten / Erledigt.
# Die App ruft Telegram nur nach aussen ab (Long-Polling) - kein offener Port, geht auch hinter CGNAT.
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHATS = {c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()}
TG_API = os.environ.get("TELEGRAM_API", "https://api.telegram.org").rstrip("/")  # nur fuer Tests aendern

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

# delegate  = darf Aufgaben an direkte Mitarbeiter verteilen (Chefs lesen danach IMMER deren Berichte)
# judge     = darf Ergebnisse beurteilen und zur Ueberarbeitung zurueckgeben
# auto_run  = verteilte Aufgaben starten sofort (wie in einer Firma: Auftrag erteilt = es geht los)
DEFAULT_PERMS = {"delegate": False, "judge": False, "auto_run": True, "write_files": False, "shell": False}

MAX_REVISIONS = int(os.environ.get("PCL_MAX_REVISIONS", "2"))   # wie oft ein Chef dieselbe Aufgabe zurueckgeben darf
MAX_REVIEW_PASSES = int(os.environ.get("PCL_MAX_REVIEW_PASSES", "4"))  # Pruefrunden pro Chef-Aufgabe
MAX_CONTEXT_CHARS = int(os.environ.get("PCL_MAX_CONTEXT", "24000"))   # Platz fuer Mitarbeiterberichte im Prompt
FINISHED = ("done", "failed", "blocked")

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
  status TEXT DEFAULT 'todo', result TEXT DEFAULT '', created REAL, updated REAL,
  feedback TEXT DEFAULT '', prev_result TEXT DEFAULT '', rounds INTEGER DEFAULT 0, passes INTEGER DEFAULT 0,
  inbox TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS tg_msgs(
  chat TEXT, message_id INTEGER, task_id INTEGER, ts REAL, PRIMARY KEY(chat, message_id));
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
        # Migration alter Datenbanken (Spalten nachruesten)
        have = {r["name"] for r in c.execute("PRAGMA table_info(tasks)")}
        for col, ddl in (("feedback", "TEXT DEFAULT ''"), ("prev_result", "TEXT DEFAULT ''"),
                         ("rounds", "INTEGER DEFAULT 0"), ("passes", "INTEGER DEFAULT 0"),
                         ("inbox", "TEXT DEFAULT ''")):
            if col not in have:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
        c.execute(
            "UPDATE tasks SET status='failed', result=result||'\n\n(Abgebrochen: Neustart)' "
            "WHERE status='running'"
        )
        # Chefs, die auf ihr Team warten, nach einem Neustart pruefen: ist das Team schon fertig?
        for t in c.execute("SELECT id FROM tasks WHERE status='waiting_subtasks'").fetchall():
            open_kids = c.execute("SELECT COUNT(*) FROM tasks WHERE parent_task_id=? AND status NOT IN "
                                  "('done','failed','blocked')", (t["id"],)).fetchone()[0]
            if open_kids == 0:
                c.execute("UPDATE tasks SET status='queued' WHERE id=?", (t["id"],))
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
    return {k: (bool(p[k]) if k in p else d) for k, d in DEFAULT_PERMS.items()}


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


REVIEW_MARKER = "BERICHTE DEINER MITARBEITER"
STATUS_DE = {"done": "fertig", "failed": "FEHLGESCHLAGEN", "blocked": "BLOCKIERT (Agent pausiert)",
             "todo": "noch nicht gestartet", "queued": "wartet", "running": "laeuft",
             "waiting_subtasks": "wartet auf Team", "waiting_approval": "wartet auf Freigabe"}


def mock_llm(agent, messages):
    """Offline-Test ohne Key: Chefs delegieren an alle Mitarbeiter, pruefen danach und melden hoch."""
    user = messages[-1]["content"]
    p = perms_of(agent)
    kids = q("SELECT name FROM agents WHERE parent_id=?", (agent["id"],))
    title = user.split("\n")[0].replace("Aufgabe: ", "")
    redo = "ÜBERARBEITUNGSAUFTRAG" in user
    pre = "Ueberarbeitet: " if redo else ""
    if user.startswith(REVIEW_MARKER):
        out = {"result": f"[Mock {agent['name']}] {pre}Gesamtbericht nach Pruefung der Mitarbeiterberichte."}
        if p["judge"] and "REVISE" in user and "Ueberarbeitet" not in user:
            ids = re.findall(r"\[Aufgabe #(\d+)\]", user)
            if ids:
                out["review"] = [{"task_id": int(ids[0]), "verdict": "revise", "feedback": "Bitte praezisieren."}]
        return json.dumps(out, ensure_ascii=False), 50
    out = {"result": f"[Mock {agent['name']}] {pre}Auftrag bearbeitet: {title[:100]}"}
    if p["delegate"] and kids:
        out["result"] = f"[Mock {agent['name']}] Plan: Aufgabe an Team verteilt."
        out["delegate"] = [{"to": k["name"], "title": title[:80],
                            "description": "Bitte uebernehmen: " + user[:200]} for k in kids]
    if p["write_files"]:
        out["write_file"] = [{"path": f"{agent['name'].lower()}_notiz.txt", "content": "Mock-Datei\n" + user[:200]}]
    return json.dumps(out, ensure_ascii=False), 50


# ---------------------------------------------------------------- Prompt bauen
def team_of(agent):
    return q("SELECT id, name, role FROM agents WHERE parent_id=? ORDER BY id", (agent["id"],))


def build_system(agent, project, mode, final_only=False):
    """mode: 'work' = selbst erledigen, 'plan' = Chef plant/verteilt, 'review' = Chef liest Berichte und beurteilt."""
    perms = perms_of(agent)
    parent = q1("SELECT name, role FROM agents WHERE id=?", (agent["parent_id"],)) if agent["parent_id"] else None
    kids = team_of(agent)
    s = [f"Du bist '{agent['name']}' (Rolle: {agent['role'] or 'Agent'}) in einem KI-Unternehmen, das wie eine echte Firma arbeitet.",
         f"Projekt: {project['name']}", f"Projektziel: {project['goal'] or '(nicht gesetzt)'}"]
    if parent:
        s.append(f"Dein Vorgesetzter: {parent['name']} ({parent['role']}). Er prueft dein Ergebnis und kann es zur Ueberarbeitung zurueckgeben.")
    if kids:
        s.append("Dein Team (direkte Mitarbeiter): " + ", ".join(f"{k['name']} ({k['role']})" for k in kids))
    if agent["system_prompt"].strip():
        s.append("\nArbeitsanweisung:\n" + agent["system_prompt"].strip())

    fields = ['"result": "Text"']
    rules = []
    if mode == "plan":
        fields[0] = '"result": "dein kurzer Plan ODER, wenn du ohne Team arbeitest, das vollstaendige Ergebnis"'
        fields.append('"delegate": [{"to": "Name des Mitarbeiters", "title": "...", "description": "..."}]')
        rules.append("Du bist Fuehrungskraft: Entweder verteilst du Teilaufgaben an dein Team (delegate) oder du erledigst die Aufgabe selbst "
                     "(dann kein delegate). Mitarbeiter kennen NUR ihre Aufgabe, nicht deine: gib in description alles mit, was sie brauchen "
                     "(Ziel, Umfang, gewuenschtes Format, Qualitaetskriterien). Delegiere nur an exakt benannte Mitarbeiter.")
    elif mode == "review":
        fields[0] = '"result": "konsolidiertes Gesamtergebnis, das an deinen Vorgesetzten bzw. als Endergebnis geht"'
        rules.append("Du hast die Berichte deines Teams gelesen. Pruefe sie kritisch gegen die urspruengliche Aufgabe, fasse zusammen und entscheide.")
        if final_only:
            rules.append("Das ist deine LETZTE Pruefrunde: gib jetzt das Gesamtergebnis ab, ohne weitere Aufgaben oder Rueckgaben.")
        else:
            if perms["judge"]:
                fields.append('"review": [{"task_id": 12, "verdict": "approve oder revise", "feedback": "konkret, was besser werden muss"}]')
                rules.append("Mit review gibst du unzureichende Arbeit mit konkretem Feedback zurueck (verdict revise). Was ausreicht, laesst du weg "
                             "oder markierst approve. Gibst du nichts zurueck, ist deine Aufgabe mit dem Gesamtergebnis abgeschlossen.")
            if perms["delegate"] and kids:
                fields.append('"delegate": [{"to": "Name", "title": "...", "description": "..."}]')
                rules.append("delegate ist hier optional und nur fuer Folgeaufgaben gedacht.")
    if mode in ("work", "review"):
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


def clip(text, n):
    text = text or ""
    return text if len(text) <= n else text[:n] + f"\n[... gekuerzt, {len(text) - n} Zeichen weggelassen]"


def work_prompt(t):
    parts = [f"Aufgabe: {t['title']}\n\n{t['description']}".strip()]
    if t.get("parent_task_id"):
        pt = q1("SELECT t.title, a.name, a.role FROM tasks t LEFT JOIN agents a ON a.id=t.agent_id WHERE t.id=?",
                (t["parent_task_id"],))
        if pt:
            parts.append(f"Auftraggeber: {pt['name']} ({pt['role']}). Dessen uebergeordnete Aufgabe: {pt['title']}")
    if t.get("feedback"):
        parts.append("ÜBERARBEITUNGSAUFTRAG deines Vorgesetzten:\n" + t["feedback"]
                     + "\n\nDein bisheriges Ergebnis (verbessere es gezielt):\n" + clip(t.get("prev_result", ""), 6000))
    return "\n\n".join(parts)


def review_prompt(t, child_tasks):
    parts = [f"{REVIEW_MARKER} (du hast alle Berichte gelesen, sie stehen unten).",
             f"Urspruengliche Aufgabe: {t['title']}\n{t['description']}".strip()]
    if t.get("feedback"):
        parts.append("ÜBERARBEITUNGSAUFTRAG deines Vorgesetzten an dich:\n" + t["feedback"]
                     + "\n\nDein bisheriges Gesamtergebnis (verbessere es gezielt, Mitarbeiter darfst du bei Bedarf erneut einbeziehen):\n"
                     + clip(t.get("prev_result", ""), 6000))
    per = min(6000, max(800, MAX_CONTEXT_CHARS // max(1, len(child_tasks))))
    for c in child_tasks:
        ag = q1("SELECT name, role FROM agents WHERE id=?", (c["agent_id"],)) or {"name": "?", "role": ""}
        parts.append(f"--- [Aufgabe #{c['id']}] {c['title']} | Mitarbeiter: {ag['name']} ({ag['role']}) | "
                     f"Status: {STATUS_DE.get(c['status'], c['status'])} | Rueckgaben: {c['rounds']}/{MAX_REVISIONS}\n"
                     + clip(c["result"], per))
    return "\n\n".join(parts)


# -------------------------------------------------------------- Task ausfuehren
def set_task(tid, status=None, result=None, **extra):
    sets, args = ["updated=?"], [time.time()]
    if status is not None:
        sets.append("status=?")
        args.append(status)
    if result is not None:
        sets.append("result=?")
        args.append(result)
    for k, v in extra.items():
        sets.append(f"{k}=?")
        args.append(v)
    args.append(tid)
    ex(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?", args)


def wake_parent(t):
    """Wenn alle Mitarbeiter-Aufgaben fertig sind, kommt der Chef wieder dran (Pruefen + Bericht)."""
    pt = (t or {}).get("parent_task_id")
    if not pt:
        return
    parent = q1("SELECT * FROM tasks WHERE id=?", (pt,))
    if not parent or parent["status"] != "waiting_subtasks":
        return
    open_kids = q1("SELECT COUNT(*) c FROM tasks WHERE parent_task_id=? AND status NOT IN ('done','failed','blocked')",
                   (pt,))["c"]
    if open_kids == 0:
        set_task(pt, "queued")
        log("review_wakeup", "Alle Mitarbeiter fertig - Chef prueft die Berichte", parent["project_id"], parent["agent_id"], pt)


def finish(tid, status, result=None):
    set_task(tid, status, result)
    if status in FINISHED:
        set_task(tid, feedback="", prev_result="")
        t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
        wake_parent(t)
        if t and not t["parent_task_id"]:
            inbox_arrived(t)  # oberste Aufgabe fertig = Post fuer den Besitzer


def execute_task(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t:
        return
    a = q1("SELECT * FROM agents WHERE id=?", (t["agent_id"],))
    p = q1("SELECT * FROM projects WHERE id=?", (t["project_id"],))
    if not a or not p:
        finish(tid, "failed", "Agent oder Projekt existiert nicht mehr.")
        return
    pid, aid = p["id"], a["id"]
    if a["paused"]:
        finish(tid, "blocked", "Agent ist pausiert.")
        log("blocked", "Agent pausiert", pid, aid, tid)
        return

    perms = perms_of(a)
    kids = team_of(a)
    manager = perms["delegate"] and bool(kids)
    child_tasks = q("SELECT * FROM tasks WHERE parent_task_id=? ORDER BY id", (tid,))
    depth = task_depth(t)
    can_delegate = manager and depth < MAX_DEPTH
    if child_tasks:
        mode = "review"
    elif can_delegate:
        mode = "plan"
    else:
        mode = "work"
    final_only = mode == "review" and t["passes"] >= MAX_REVIEW_PASSES

    set_task(tid, "running")
    log("task_start", f"{t['title']} [{mode}]", pid, aid, tid)
    user = review_prompt(t, child_tasks) if mode == "review" else work_prompt(t)
    messages = [{"role": "system", "content": build_system(a, p, mode, final_only)},
                {"role": "user", "content": user}]
    try:
        text, tokens = call_llm(a, messages)
    except Exception as e:
        finish(tid, "failed", f"Fehler: {e}")
        log("task_failed", e, pid, aid, tid)
        return
    ex("INSERT INTO usage(agent_id,ts,tokens) VALUES(?,?,?)", (aid, time.time(), tokens))

    data = parse_output(text)
    result = str(data.get("result") or text).strip()
    notes = []
    revised = created = 0

    # --- Urteil: Arbeit zur Ueberarbeitung zurueckgeben (nur mit Recht 'judge')
    rv = data.get("review")
    if rv:
        if mode != "review" or final_only:
            notes.append("Rueckgabe nur in einer Pruefrunde moeglich - ignoriert.")
        elif not perms["judge"]:
            notes.append("Beurteilen/Zurueckgeben nicht erlaubt - ignoriert.")
            log("denied", "review", pid, aid, tid)
        else:
            by_id = {c["id"]: c for c in child_tasks}
            for item in (rv if isinstance(rv, list) else [])[:20]:
                try:
                    ct = by_id.get(int(item.get("task_id")))
                except (TypeError, ValueError):
                    ct = None
                if not ct or str(item.get("verdict", "")).lower() != "revise":
                    continue
                feedback = str(item.get("feedback") or "Bitte ueberarbeiten.")[:3000]
                cag = q1("SELECT name FROM agents WHERE id=?", (ct["agent_id"],)) or {"name": "?"}
                if ct["rounds"] >= MAX_REVISIONS:
                    notes.append(f"{cag['name']}: maximale Rueckgaben ({MAX_REVISIONS}) erreicht - Ergebnis uebernommen.")
                    continue
                set_task(ct["id"], "queued", feedback=feedback, prev_result=ct["result"], rounds=ct["rounds"] + 1)
                log("revision_requested", f"an {cag['name']}: {feedback}", pid, aid, ct["id"])
                notes.append(f"Zur Ueberarbeitung zurueckgegeben an {cag['name']}: {feedback[:120]}")
                revised += 1

    # --- Delegieren
    dele = data.get("delegate")
    if dele:
        if not perms["delegate"]:
            notes.append("Delegieren nicht erlaubt - ignoriert.")
            log("denied", "delegate", pid, aid, tid)
        elif final_only:
            notes.append("Letzte Pruefrunde: keine neuen Aufgaben - ignoriert.")
        elif not can_delegate:
            notes.append(f"Keine Mitarbeiter bzw. max. Delegationstiefe ({MAX_DEPTH}) erreicht - ignoriert.")
        else:
            by_name = {k["name"].lower(): k for k in kids}
            for item in (dele if isinstance(dele, list) else [])[:8]:
                kid = by_name.get(str(item.get("to", "")).lower())
                if not kid:
                    notes.append(f"Unbekannter Mitarbeiter '{item.get('to')}' - ignoriert.")
                    continue
                st = "queued" if perms["auto_run"] else "todo"
                nid = ex(
                    "INSERT INTO tasks(project_id,agent_id,parent_task_id,title,description,status,created,updated)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (pid, kid["id"], tid, str(item.get("title", "Aufgabe"))[:200],
                     str(item.get("description", ""))[:6000], st, time.time(), time.time()))
                log("delegated", f"an {kid['name']}: {item.get('title')}", pid, aid, nid)
                notes.append(f"Delegiert an {kid['name']}: {item.get('title')}"
                             + ("" if st == "queued" else " (wartet auf manuellen Start)"))
                created += 1

    # --- Team arbeitet (wieder): Chef wartet, bis alle fertig sind
    if revised or created:
        if data.get("write_file") or data.get("shell"):
            notes.append("Dateien/Shell werden erst im Abschluss ausgefuehrt - jetzt ignoriert.")
        set_task(tid, "waiting_subtasks", result + "\n\n" + "\n".join(notes),
                 passes=t["passes"] + (1 if mode == "review" else 0))
        log("waiting_team", f"{created} neue, {revised} zurueckgegebene Aufgaben", pid, aid, tid)
        return

    # --- Abschluss: Dateien schreiben
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
                tg_notify(f"🖐 Freigabe nötig · {a['name']} ({p['name']})\nAuftrag #{tid}: {t['title']}\n$ {str(cmd)[:500]}\n\n"
                          "Bitte im Web unter „Freigaben“ entscheiden.")

    final = result + ("\n\n" + "\n".join(notes) if notes else "")
    if pending:
        set_task(tid, "waiting_approval", final)
    else:
        finish(tid, "done", final)
        log("task_done", f"{t['title']} [{mode}]", pid, aid, tid)


def delete_subtree(tid):
    for c in q("SELECT id FROM tasks WHERE parent_task_id=?", (tid,)):
        delete_subtree(c["id"])
    ex("DELETE FROM approvals WHERE task_id=?", (tid,))
    ex("DELETE FROM tasks WHERE id=?", (tid,))


def task_tree(tid, depth=0):
    rows = q("SELECT t.id, t.title, t.status, t.result, t.rounds, t.agent_id, a.name AS agent_name, a.role AS agent_role "
             "FROM tasks t LEFT JOIN agents a ON a.id=t.agent_id WHERE t.parent_task_id=? ORDER BY t.id", (tid,))
    for r in rows:
        r["result"] = clip(r["result"], 4000)
        r["children"] = task_tree(r["id"], depth + 1) if depth < 10 else []
    return rows


# ------------------------------------------------------- Post (Eingang des Besitzers)
# "Post" = eine oberste Aufgabe (ohne Auftraggeber) ist fertig/fehlgeschlagen/blockiert.
# inbox: '' = (noch) keine Post, 'new' = ungelesen/offen, 'closed' = vom Besitzer als erledigt markiert.
KIND_DE = {"done": ("✅", "Ergebnis fertig"), "failed": ("❌", "Fehlgeschlagen"), "blocked": ("⛔", "Blockiert")}
OK_WORDS = {"ok", "erledigt", "fertig", "beendet", "abgeschlossen", "passt", "✅", "👍"}


def team_stats(tid):
    n = rev = 0
    for c in q("SELECT id, rounds FROM tasks WHERE parent_task_id=?", (tid,)):
        a, b = team_stats(c["id"])
        n += 1 + a
        rev += c["rounds"] + b
    return n, rev


def get_setting(k, default=None):
    r = q1("SELECT v FROM settings WHERE k=?", (k,))
    return r["v"] if r else default


def set_setting(k, v):
    ex("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (k, str(v)))


def inbox_arrived(t):
    ex("UPDATE tasks SET inbox='new' WHERE id=?", (t["id"],))
    log("inbox_new", f"{t['title']} [{t['status']}]", t["project_id"], t["agent_id"], t["id"])
    tg_notify_post(t["id"])


def inbox_close(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t or t["parent_task_id"]:
        return False, f"Auftrag #{tid} gibt es nicht (oder er ist nur eine Teilaufgabe)."
    if t["status"] not in FINISHED:
        return False, f"Auftrag #{tid} ist noch nicht fertig (Status: {STATUS_DE.get(t['status'], t['status'])})."
    ex("UPDATE tasks SET inbox='closed' WHERE id=?", (tid,))
    log("inbox_closed", t["title"], t["project_id"], t["agent_id"], tid)
    return True, f"✅ Auftrag #{tid} „{t['title']}“ ist als erledigt markiert."


def inbox_rework(tid, feedback):
    feedback = (feedback or "").strip()
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t or t["parent_task_id"]:
        return False, f"Auftrag #{tid} gibt es nicht (oder er ist nur eine Teilaufgabe)."
    if not feedback:
        return False, "Bitte schreib dazu, was geändert werden soll."
    if t["status"] not in FINISHED:
        return False, (f"Auftrag #{tid} ist gerade in Arbeit ({STATUS_DE.get(t['status'], t['status'])}). "
                       "Ich melde mich, sobald Post da ist.")
    ag = q1("SELECT name FROM agents WHERE id=?", (t["agent_id"],)) or {"name": "?"}
    set_task(tid, "queued", feedback=feedback[:3000], prev_result=t["result"], rounds=t["rounds"] + 1,
             passes=0, inbox="")
    log("inbox_rework", feedback[:500], t["project_id"], t["agent_id"], tid)
    return True, f"🔁 Auftrag #{tid} „{t['title']}“ geht zur Überarbeitung zurück an {ag['name']}."


def top_agent(pid, name=None):
    ags = q("SELECT * FROM agents WHERE project_id=? ORDER BY id", (pid,))
    if name:
        for a in ags:
            if a["name"].lower() == name.lower():
                return a
        return None
    roots = [a for a in ags if not a["parent_id"]]
    for a in roots:
        if perms_of(a)["delegate"]:
            return a
    return (roots or ags or [None])[0]


def inbox_new_order(pid, text, agent_name=None):
    text = text.strip()
    a = top_agent(pid, agent_name)
    if not a:
        return None, None
    title = text.splitlines()[0][:80] or "Auftrag"
    tid = ex("INSERT INTO tasks(project_id,agent_id,title,description,status,created,updated) VALUES(?,?,?,?,?,?,?)",
             (pid, a["id"], title, text[:8000], "queued", time.time(), time.time()))
    log("task_created", f"per Post/Telegram: {title}", pid, a["id"], tid)
    return tid, a


def active_project():
    pid = get_setting("tg_project")
    if pid and q1("SELECT 1 FROM projects WHERE id=?", (int(pid),)):
        return q1("SELECT * FROM projects WHERE id=?", (int(pid),))
    r = q1("SELECT p.* FROM tasks t JOIN projects p ON p.id=t.project_id ORDER BY t.updated DESC LIMIT 1")
    return r or q1("SELECT * FROM projects ORDER BY id LIMIT 1")


# ------------------------------------------------------------------------ Telegram
_tg_out = queue.Queue()
_tg_denied = {}


def _safe(e):
    s = str(e)
    return s.replace(TG_TOKEN, "***") if TG_TOKEN else s


def tg(method, **params):
    r = requests.post(f"{TG_API}/bot{TG_TOKEN}/{method}", json=params, timeout=(5, params.get("timeout", 0) + 15))
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(d.get("description", "Telegram-Fehler"))
    return d["result"]


def tg_send_now(chat, text, task_id=None, buttons=None, force_reply=False):
    p = {"chat_id": chat, "text": text[:4000]}
    if buttons:
        p["reply_markup"] = {"inline_keyboard": buttons}
    elif force_reply:
        p["reply_markup"] = {"force_reply": True, "selective": True}
    m = tg("sendMessage", **p)
    if task_id:
        ex("INSERT OR REPLACE INTO tg_msgs(chat,message_id,task_id,ts) VALUES(?,?,?,?)",
           (str(chat), m["message_id"], task_id, time.time()))
    return m


def tg_notify(text, task_id=None, buttons=None, chats=None):
    """Aus beliebigen Threads aufrufen (Worker, Web): stellt nur in die Warteschlange."""
    if not (TG_TOKEN and TG_CHATS):
        return
    for c in (chats or TG_CHATS):
        _tg_out.put((c, text, task_id, buttons))


def tg_sender():
    while True:
        chat, text, task_id, buttons = _tg_out.get()
        try:
            tg_send_now(chat, text, task_id, buttons)
        except Exception as e:
            print("Telegram-Senden:", _safe(e))
            log("telegram_error", "Senden: " + _safe(e))


def tg_notify_post(tid, chats=None):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if not t:
        return
    a = q1("SELECT name FROM agents WHERE id=?", (t["agent_id"],)) or {"name": "?"}
    p = q1("SELECT name FROM projects WHERE id=?", (t["project_id"],)) or {"name": "?"}
    icon, label = KIND_DE.get(t["status"], ("📬", t["status"]))
    n, rev = team_stats(tid)
    head = f"📬 Post von {a['name']} ({p['name']})\n{icon} {label} · Auftrag #{tid}\n„{t['title']}“"
    if n:
        head += f"\nTeam: {n} Aufgaben, {rev} Rückgaben"
    res = t["result"] or "(kein Text)"
    text = head + "\n\n" + clip(res, 2800) + "\n\n↩️ Antworte auf diese Nachricht = Auftrag neu bearbeiten."
    buttons = [[{"text": "✅ Erledigt", "callback_data": f"ok:{tid}"},
                {"text": "🔁 Überarbeiten", "callback_data": f"rw:{tid}"}]]
    if len(res) > 2800:
        buttons.append([{"text": "📄 Ganzes Ergebnis", "callback_data": f"more:{tid}"}])
    tg_notify(text, tid, buttons, chats)


HELP_DE = ("PaperclipLite – so geht's:\n"
           "• Einfach schreiben = neuer Auftrag an den Chef (mit „@Name text“ an einen bestimmten Agenten)\n"
           "• Auf eine Post-Nachricht antworten = Auftrag neu bearbeiten (dein Text ist die Anweisung)\n"
           "• Antwort „ok“ oder Button ✅ = als erledigt markieren\n"
           "/post – offene Post anzeigen\n/status – was läuft gerade\n/ok <Nr> – Auftrag erledigt\n"
           "/neu <Text> – neuer Auftrag\n/projekt [Nr] – Projekt anzeigen/wechseln")


def tg_unbutton(cb):
    try:
        m = cb["message"]
        tg("editMessageReplyMarkup", chat_id=m["chat"]["id"], message_id=m["message_id"], reply_markup={"inline_keyboard": []})
    except Exception:
        pass


def tg_callback(cb):
    chat = str(cb["message"]["chat"]["id"])
    if chat not in TG_CHATS:
        return
    action, _, arg = (cb.get("data") or "").partition(":")
    try:
        tid = int(arg)
    except ValueError:
        return
    if action == "ok":
        ok, msg = inbox_close(tid)
        tg("answerCallbackQuery", callback_query_id=cb["id"], text=msg[:190])
        if ok:
            tg_unbutton(cb)
    elif action == "rw":
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        tg_send_now(chat, f"Was soll bei Auftrag #{tid} geändert werden? Schreib es als Antwort auf diese Nachricht.",
                    task_id=tid, force_reply=True)
    elif action == "more":
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        t = q1("SELECT result FROM tasks WHERE id=?", (tid,))
        txt = (t or {}).get("result") or "(leer)"
        for i in range(0, min(len(txt), 20000), 3800):
            tg_send_now(chat, txt[i:i + 3800])


def tg_list_open(chat):
    rows = q("SELECT id FROM tasks WHERE parent_task_id IS NULL AND inbox='new' ORDER BY updated DESC LIMIT 5")
    if not rows:
        tg_send_now(chat, "📭 Keine offene Post.")
    for r in rows:
        tg_notify_post(r["id"], chats=[chat])


def tg_status(chat):
    rows = q("SELECT t.id, t.title, t.status, a.name FROM tasks t LEFT JOIN agents a ON a.id=t.agent_id "
             "WHERE t.status IN ('queued','running','waiting_subtasks','waiting_approval') ORDER BY t.id DESC LIMIT 15")
    open_post = q1("SELECT COUNT(*) c FROM tasks WHERE parent_task_id IS NULL AND inbox='new'")["c"]
    lines = [f"📬 Offene Post: {open_post}", ""]
    lines += [f"#{r['id']} {r['name']}: {r['title'][:50]} – {STATUS_DE.get(r['status'], r['status'])}" for r in rows] \
        or ["Gerade läuft nichts."]
    tg_send_now(chat, "\n".join(lines))


def tg_new_order(chat, text):
    pr = active_project()
    if not pr:
        tg_send_now(chat, "Es gibt noch kein Projekt. Lege zuerst im Web eins an.")
        return
    name = None
    m = re.match(r"^@(\S+)\s+(.+)$", text, re.S)
    if m:
        name, text = m.group(1), m.group(2)
    tid, a = inbox_new_order(pr["id"], text, name)
    if not tid:
        tg_send_now(chat, f"Agent „{name}“ gibt es im Projekt {pr['name']} nicht." if name else
                    f"Im Projekt {pr['name']} gibt es noch keinen Agenten.")
        return
    tg_send_now(chat, f"📝 Auftrag #{tid} an {a['name']} übergeben (Projekt {pr['name']}). "
                      "Ich melde mich, sobald Post da ist.", task_id=tid)


def tg_handle(u):
    if u.get("callback_query"):
        return tg_callback(u["callback_query"])
    m = u.get("message")
    if not m or not m.get("text"):
        return
    chat, text = str(m["chat"]["id"]), m["text"].strip()
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    rest = text[len(text.split()[0]):].strip() if cmd else text
    if chat not in TG_CHATS:
        if cmd == "/start":
            tg_send_now(chat, f"Deine Chat-ID ist {chat}.\nTrage sie in .env ein: TELEGRAM_CHAT_ID={chat}\n"
                              "Danach PaperclipLite neu starten.")
        elif _tg_denied.get(chat, 0) < 5:
            _tg_denied[chat] = _tg_denied.get(chat, 0) + 1
            log("telegram_denied", f"unbekannter Chat {chat}")
        return
    if cmd in ("/start", "/hilfe", "/help"):
        return tg_send_now(chat, HELP_DE)
    if cmd == "/post":
        return tg_list_open(chat)
    if cmd == "/status":
        return tg_status(chat)
    if cmd == "/projekt":
        projs = q("SELECT * FROM projects ORDER BY id")
        if rest.isdigit() and any(p["id"] == int(rest) for p in projs):
            set_setting("tg_project", rest)
        cur = active_project()
        return tg_send_now(chat, "Projekte (Nr – Name):\n" + "\n".join(
            f"{'👉 ' if cur and p['id'] == cur['id'] else '   '}{p['id']} – {p['name']}" for p in projs)
            + "\n\nWechseln: /projekt <Nr>. Neue Aufträge gehen ins gewählte Projekt.")
    if cmd == "/ok":
        if rest.lstrip("#").isdigit():
            return tg_send_now(chat, inbox_close(int(rest.lstrip("#")))[1])
        rows = q("SELECT id FROM tasks WHERE parent_task_id IS NULL AND inbox='new'")
        if len(rows) == 1:
            return tg_send_now(chat, inbox_close(rows[0]["id"])[1])
        return tg_send_now(chat, "Welcher Auftrag? /ok <Nr> (offene Post: /post)")
    if cmd == "/neu":
        return tg_new_order(chat, rest) if rest else tg_send_now(chat, "Wie lautet der Auftrag? /neu <Text>")
    if cmd:
        return tg_send_now(chat, HELP_DE)
    # Antwort auf eine Nachricht des Bots -> betrifft genau diesen Auftrag
    rt = (m.get("reply_to_message") or {}).get("message_id")
    mapped = q1("SELECT task_id FROM tg_msgs WHERE chat=? AND message_id=?", (chat, rt)) if rt else None
    if mapped:
        if text.lower().strip(" .!") in OK_WORDS:
            return tg_send_now(chat, inbox_close(mapped["task_id"])[1])
        ok, msg = inbox_rework(mapped["task_id"], text)
        return tg_send_now(chat, msg, task_id=mapped["task_id"] if ok else None)
    tg_new_order(chat, text)


def tg_poll():
    try:
        tg("deleteWebhook")
    except Exception as e:
        print("Telegram deleteWebhook:", _safe(e))
    offset = None
    while True:
        try:
            params = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
            if offset is not None:
                params["offset"] = offset
            for u in tg("getUpdates", **params):
                offset = u["update_id"] + 1
                try:
                    tg_handle(u)
                except Exception as e:
                    print("Telegram-Handler:", _safe(e))
                    log("telegram_error", "Handler: " + _safe(e))
        except Exception as e:
            print("Telegram-Abruf:", _safe(e))
            time.sleep(10)


def start_telegram():
    if not TG_TOKEN:
        return
    threading.Thread(target=tg_sender, daemon=True).start()
    threading.Thread(target=tg_poll, daemon=True).start()
    if not TG_CHATS:
        print("Telegram: Bot-Token gesetzt, aber TELEGRAM_CHAT_ID fehlt. Schreib dem Bot /start, er nennt dir die ID.")


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
    return jsonify({"auth": bool(TOKEN), "allow_shell": ALLOW_SHELL, "allow_cli": ALLOW_CLI,
                    "telegram": bool(TG_TOKEN and TG_CHATS)})


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
    inbox_new = q1("SELECT COUNT(*) c FROM tasks WHERE parent_task_id IS NULL AND inbox='new'")["c"]
    return jsonify({"project": proj, "agents": agents, "pending_approvals": pend, "inbox_new": inbox_new})


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
        "INSERT INTO agents(project_id,name,role,x,y,provider,model,system_prompt,perms,created)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (pid, str(d.get("name") or "Agent")[:60], str(d.get("role", ""))[:100],
         float(d.get("x", 0)), float(d.get("y", 0)), prov, str(d.get("model", ""))[:100],
         str(d.get("system_prompt", ""))[:8000], json.dumps(perms), time.time()))
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
    rows = q("SELECT * FROM tasks WHERE agent_id=? ORDER BY id DESC LIMIT 100", (aid,))
    for r in rows:
        r["children"] = task_tree(r["id"])  # Team-Arbeit unter dieser Aufgabe (rekursiv ueber alle Ebenen)
    return jsonify(rows)


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
    if t["status"] in ("running", "queued", "waiting_approval", "waiting_subtasks"):
        abort(400, "Aufgabe laeuft bereits bzw. wartet auf Freigabe oder das Team.")
    # Neustart einer Chef-Aufgabe = von vorn planen: alte Team-Aufgaben werden verworfen
    for c in q("SELECT id FROM tasks WHERE parent_task_id=?", (tid,)):
        delete_subtree(c["id"])
    set_task(tid, "queued", feedback="", prev_result="", rounds=0, passes=0, inbox="")
    log("task_restarted", t["title"], t["project_id"], t["agent_id"], tid)
    return jsonify({"ok": True})


@app.delete("/api/tasks/<int:tid>")
def api_task_del(tid):
    t = q1("SELECT * FROM tasks WHERE id=?", (tid,))
    if t:
        delete_subtree(tid)
        log("task_deleted", t["title"], t["project_id"], t["agent_id"], tid)
        # War das die letzte offene Aufgabe eines wartenden Chefs? Dann darf er weitermachen.
        pt = t.get("parent_task_id")
        if pt and not q1("SELECT 1 FROM tasks WHERE parent_task_id=?", (pt,)):
            parent = q1("SELECT * FROM tasks WHERE id=?", (pt,))
            if parent and parent["status"] == "waiting_subtasks":
                set_task(pt, "queued")
        elif pt:
            wake_parent({"parent_task_id": pt})
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
            finish(t["id"], "done")  # meldet das Ergebnis weiter: weckt den Chef, falls er wartet
    return jsonify({"ok": True})


@app.get("/api/inbox")
def api_inbox():
    rows = q("""SELECT t.id, t.title, t.status, t.result, t.inbox, t.updated, t.rounds, a.name AS agent_name,
                       p.name AS project_name, t.project_id, t.agent_id
                FROM tasks t LEFT JOIN agents a ON a.id=t.agent_id LEFT JOIN projects p ON p.id=t.project_id
                WHERE t.parent_task_id IS NULL AND t.inbox IN ('new','closed')
                ORDER BY (t.inbox='new') DESC, t.updated DESC LIMIT 40""")
    for r in rows:
        r["result"] = clip(r["result"], 20000)
        r["team"], r["revisions"] = team_stats(r["id"])
    return jsonify(rows)


@app.post("/api/inbox/<int:tid>/close")
def api_inbox_close(tid):
    ok, msg = inbox_close(tid)
    if not ok:
        abort(400, msg)
    return jsonify({"ok": True})


@app.post("/api/inbox/<int:tid>/rework")
def api_inbox_rework(tid):
    ok, msg = inbox_rework(tid, str(request.get_json(force=True).get("feedback", "")))
    if not ok:
        abort(400, msg)
    return jsonify({"ok": True})


@app.post("/api/telegram/test")
def api_telegram_test():
    if not (TG_TOKEN and TG_CHATS):
        abort(400, "Telegram ist nicht eingerichtet (TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID in .env).")
    tg_notify("✅ PaperclipLite ist verbunden. Schreib mir einen Auftrag oder /hilfe.")
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
    start_telegram()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8787"))
    exposed = host not in ("127.0.0.1", "localhost", "::1") or TRUST_PROXY
    if exposed and len(TOKEN) < 12:
        sys.exit("ABBRUCH: Die App ist von aussen erreichbar (HOST/TRUST_PROXY), aber APP_TOKEN fehlt "
                 "oder ist kuerzer als 12 Zeichen. Setze ein langes Passwort in .env.")
    if exposed and ALLOW_SHELL:
        print("WARNUNG: PCL_ALLOW_SHELL=1 bei erreichbarer App - wer das Passwort hat, kann Befehle freigeben.")
    print(f"PaperclipLite laeuft auf http://{host}:{port}  (Login: {'an' if TOKEN else 'aus'}, "
          f"Shell: {'an' if ALLOW_SHELL else 'aus'}, Telegram: {'an' if TG_TOKEN and TG_CHATS else 'aus'})")
    app.run(host=host, port=port, threaded=True)
