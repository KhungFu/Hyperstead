import io
import json

import app as A
from conftest import drain, make_agent, make_project, make_task, task


def team():
    pid = make_project()
    ceo = make_agent(pid, "CEO", delegate=True, judge=True)
    kids = [make_agent(pid, f"M{i}", parent=ceo) for i in range(2)]
    return pid, ceo, kids


# ------------------------------------------------------------ Workflow
def test_plan_work_review_bis_fertig():
    pid, ceo, kids = team()
    tid = make_task(pid, ceo, "Webseite bauen")
    drain()
    top = task(tid)
    assert top["status"] == "done"
    assert "Gesamtbericht" in top["result"]
    sub = A.q("SELECT * FROM tasks WHERE parent_task_id=?", (tid,))
    assert {s["agent_id"] for s in sub} == set(kids)
    assert all(s["status"] == "done" for s in sub)
    assert A.q1("SELECT COUNT(*) c FROM audit WHERE event='review_wakeup'")["c"] == 1


def test_zyklus_wird_abgelehnt(client):
    pid, ceo, kids = team()
    r = client.put(f"/api/agents/{ceo}", json={"parent_id": kids[0]})
    assert r.status_code == 400


# ------------------------------------------------------------ Parallele Worker
def test_claim_nie_zwei_aufgaben_je_agent_und_eine_ollama():
    pid = make_project()
    a = make_agent(pid, "A")
    o1, o2 = make_agent(pid, "O1", provider="ollama"), make_agent(pid, "O2", provider="ollama")
    ids = [make_task(pid, x) for x in (a, a, o1, o2)]
    got = [A.claim_next() for _ in range(4)]
    assert got == [ids[0], ids[2], None, None]


def test_claim_respektiert_workerzahl():
    pid = make_project()
    ags = [make_agent(pid, f"A{i}") for i in range(5)]
    for x in ags:
        make_task(pid, x)
    got = [A.claim_next() for _ in range(5)]
    assert len([g for g in got if g]) == A.WORKERS


# ------------------------------------------------------------ Gedaechtnis + Firmenwissen
def test_gedaechtnis_dedupliziert_und_kuerzt(monkeypatch):
    pid = make_project()
    a = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "A"),))
    assert A.save_memory(a, ["Besitzer mag kurze Berichte", "besitzer mag kurze berichte"]) == 1
    assert A.save_memory(a, "Besitzer mag kurze Berichte") == 0
    monkeypatch.setattr(A, "MEMORY_CHARS", 120)
    for i in range(10):
        A.save_memory(a, [f"Fakt Nummer {i}"])
    mem = A.q1("SELECT memory FROM agents WHERE id=?", (a["id"],))["memory"]
    assert len(mem) <= 120 and "Fakt Nummer 9" in mem and "Fakt Nummer 0" not in mem


def test_firmenwissen_im_prompt(client):
    pid = make_project()
    a = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "A"),))
    assert client.put(f"/api/projects/{pid}/knowledge", json={"text": "Wir sind eine Webagentur in Wien."}).status_code == 200
    r = client.post(f"/api/projects/{pid}/upload?dir=wissen", data={"file": (io.BytesIO(b"Preis 100 EUR"), "preise.txt")},
                    content_type="multipart/form-data")
    assert r.json["path"] == "wissen/preise.txt"
    p = A.q1("SELECT * FROM projects WHERE id=?", (pid,))
    sysm = A.build_system(a, p, "work")
    assert "Webagentur in Wien" in sysm and "Preis 100 EUR" in sysm and '"remember"' in sysm


def test_upload_nur_input_oder_wissen(client):
    pid = make_project()
    r = client.post(f"/api/projects/{pid}/upload?dir=../etc", data={"file": (io.BytesIO(b"x"), "a.txt")},
                    content_type="multipart/form-data")
    assert r.json["path"] == "input/a.txt"


def test_datei_loeschen_ausserhalb_abgelehnt(client):
    pid = make_project()
    assert client.delete(f"/api/projects/{pid}/files?path=../../etc/passwd").status_code == 400


# ------------------------------------------------------------ Ziele
def test_ziele_fortschritt_und_vererbung(client):
    pid, ceo, kids = team()
    g = client.post(f"/api/projects/{pid}/goals", json={"title": "Webseite online"}).json["id"]
    sub = client.post(f"/api/projects/{pid}/goals", json={"title": "Texte", "parent_id": g}).json["id"]
    tid = client.post(f"/api/agents/{ceo}/tasks", json={"title": "Texte schreiben", "run": True, "goal_id": sub}).json["id"]
    assert "Webseite online > Texte" in A.work_prompt(task(tid))
    drain()
    assert all(t["goal_id"] == sub for t in A.q("SELECT goal_id FROM tasks"))
    tree = {x["id"]: x for x in client.get(f"/api/projects/{pid}/goals").json}
    assert tree[g]["tasks"] == 3 and tree[g]["tasks_done"] == 3 and tree[sub]["depth"] == 1
    client.delete(f"/api/goals/{sub}")
    assert all(t["goal_id"] == g for t in A.q("SELECT goal_id FROM tasks"))


def test_ziel_aus_fremdem_projekt_abgelehnt(client):
    pid, ceo, _ = team()
    other = make_project("Andere")
    g = client.post(f"/api/projects/{other}/goals", json={"title": "fremd"}).json["id"]
    assert client.post(f"/api/agents/{ceo}/tasks", json={"title": "x", "goal_id": g}).status_code == 400


# ------------------------------------------------------------ Freigabe-Schranken
def test_plan_freigabe(client):
    pid, ceo, kids = team()
    client.put(f"/api/projects/{pid}/gates", json={"plan": True})
    tid = make_task(pid, ceo)
    drain()
    assert task(tid)["status"] == "waiting_approval"
    assert A.q1("SELECT COUNT(*) c FROM tasks WHERE parent_task_id=?", (tid,))["c"] == 0
    ap = client.get("/api/approvals").json
    assert len(ap) == 1 and ap[0]["kind"] == "plan" and "M0" in ap[0]["payload"]
    client.post(f"/api/approvals/{ap[0]['id']}", json={"decision": "approve"})
    assert task(tid)["status"] == "waiting_subtasks"
    drain()
    assert task(tid)["status"] == "done"
    r = client.post(f"/api/approvals/{ap[0]['id']}", json={"decision": "approve"})
    assert r.status_code == 404  # nicht zweimal entscheidbar


def test_plan_ablehnen_und_ueberarbeiten(client):
    pid, ceo, kids = team()
    client.put(f"/api/projects/{pid}/gates", json={"plan": True})
    tid = make_task(pid, ceo)
    drain()
    apid = client.get("/api/approvals").json[0]["id"]
    client.post(f"/api/approvals/{apid}", json={"decision": "deny"})
    t = task(tid)
    assert t["status"] == "failed" and "abgelehnt" in t["result"]
    A.inbox_rework(tid, "Weniger Aufgaben bitte")
    drain()
    assert task(tid)["status"] == "waiting_approval"  # neuer Plan, wieder zur Freigabe


def test_ohne_schranke_keine_freigabe():
    pid, ceo, kids = team()
    tid = make_task(pid, ceo)
    drain()
    assert task(tid)["status"] == "done"
    assert A.q1("SELECT COUNT(*) c FROM approvals")["c"] == 0


def test_team_freigabe(client):
    pid = make_project()
    ceo = make_agent(pid, "CEO", delegate=True, recruit=True)
    client.put(f"/api/projects/{pid}/gates", json={"recruit": True})
    tid = make_task(pid, ceo)
    drain()
    assert task(tid)["status"] == "waiting_approval"
    assert A.q1("SELECT COUNT(*) c FROM agents WHERE project_id=?", (pid,))["c"] == 1
    ap = client.get("/api/approvals").json[0]
    assert ap["kind"] == "recruit"
    client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"})
    assert task(tid)["status"] == "done"
    assert A.q1("SELECT COUNT(*) c FROM agents WHERE project_id=? AND provider=''", (pid,))["c"] == 3


def test_telegram_entscheidet_keine_shell_freigabe():
    pid, ceo, _ = team()
    tid = make_task(pid, ceo, status="waiting_approval")
    apid = A.ex("INSERT INTO approvals(project_id,task_id,agent_id,kind,payload,created) VALUES(?,?,?,?,?,0)",
                (pid, tid, ceo, "shell", "rm -rf /"))
    sent = []
    A.TG_CHATS.add("42")
    try:
        orig = A.tg
        A.tg = lambda method, **p: sent.append((method, p)) or {"message_id": 1}
        A.tg_callback({"id": "x", "data": f"ga:{apid}", "message": {"chat": {"id": 42}, "message_id": 5}})
    finally:
        A.tg = orig
        A.TG_CHATS.discard("42")
    assert A.q1("SELECT status FROM approvals WHERE id=?", (apid,))["status"] == "pending"


# ------------------------------------------------------------ Nutzung + Kosten
def test_nutzung_wird_gezaehlt(client):
    pid, ceo, kids = team()
    make_task(pid, ceo)
    drain()
    r = client.get("/api/usage?days=1").json
    assert r["total"]["calls"] == 4  # Plan, 2 Mitarbeiter, Pruefung
    assert r["total"]["tokens"] == 200
    assert {x["name"] for x in r["by_agent"]} == {"CEO", "M0", "M1"}


def test_kostenschaetzung():
    assert A.est_cost("anthropic", "claude-sonnet-4-5", 1_000_000) == 5
    assert A.est_cost("claude_cli", "sonnet", 1_000_000) == 0
    assert A.est_cost("openrouter", "voellig-unbekannt", 1000) is None


def test_abo_warnung_einmal_je_fenster(monkeypatch):
    sent = []
    monkeypatch.setattr(A, "tg_notify", lambda text, *a, **k: sent.append(text))
    monkeypatch.setattr(A, "ABO_WARN_5H", 3)
    pid = make_project()
    a = A.q1("SELECT * FROM agents WHERE id=?", (make_agent(pid, "A", provider="claude_cli"),))
    for _ in range(6):
        A.record_call(a, 100, 1.0)
    assert len(sent) == 1 and "Abo-Kontingent" in sent[0]
