"""Gemeinsame Testumgebung: eigene Datenbank und eigener Arbeitsordner, Anbieter 'mock' (ohne Internet, ohne Keys)."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="pcl-test-")
os.environ.update(PCL_DB=f"{_TMP}/test.db", PCL_WORKSPACE=f"{_TMP}/ws", PCL_WORKERS="3", PCL_SELF_CHECKS="0",
                  APP_TOKEN="", TELEGRAM_BOT_TOKEN="", PCL_LLM_RETRIES="0")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as A  # noqa: E402

A.init_db()
TABLES = ("tasks", "agents", "projects", "approvals", "goals", "llm_calls", "usage", "settings", "schedules", "chats", "audit")


@pytest.fixture(autouse=True)
def fresh():
    for t in TABLES:
        A.ex(f"DELETE FROM {t}")
    yield


@pytest.fixture
def client():
    A.app.testing = True
    c = A.app.test_client()
    c.environ_base["HTTP_X_PCL"] = "1"
    return c


def make_project(name="Testfirma"):
    pid = A.ex("INSERT INTO projects(name,goal,created) VALUES(?,?,0)", (name, "Testziel"))
    A.assign_folder(pid, name)
    return pid


def make_agent(pid, name, parent=None, provider="mock", **perms):
    p = dict(A.DEFAULT_PERMS, **perms)
    return A.ex("INSERT INTO agents(project_id,name,role,provider,parent_id,perms,created) VALUES(?,?,?,?,?,?,0)",
                (pid, name, name, provider, parent, json.dumps(p)))


def make_task(pid, aid, title="Auftrag", status="queued", goal_id=0):
    return A.ex("INSERT INTO tasks(project_id,agent_id,title,status,created,updated,goal_id) VALUES(?,?,?,?,0,0,?)",
                (pid, aid, title, status, goal_id))


def drain(limit=60):
    """Arbeitet die Warteschlange synchron ab (wie die Worker, nur ohne Threads)."""
    for _ in range(limit):
        tid = A.claim_next()
        if not tid:
            return
        A.run_claimed(tid)


def task(tid):
    return A.q1("SELECT * FROM tasks WHERE id=?", (tid,))
