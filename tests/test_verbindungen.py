import json

import app as A
from conftest import drain, make_agent, make_project, make_task, task


def scripted(monkeypatch, replies):
    """Mock-Modell, das nacheinander die gegebenen Antworten liefert (z. B. erst Werkzeugaufruf, dann Ergebnis)."""
    it = iter(replies)
    monkeypatch.setattr(A, "mock_llm", lambda agent, messages: (json.dumps(next(it)), 10))


def conn(client, pid, url, **kw):
    d = {"name": "crm", "url": url, "method": "POST", "description": "Kunde anlegen", "confirm": False, **kw}
    r = client.post(f"/api/projects/{pid}/connections", json=d)
    assert r.status_code == 200, r.data
    return r.json["id"]


def test_agent_ruft_verbindung_direkt(client, echo, monkeypatch):
    monkeypatch.setenv("CRM_TOKEN", "geheim123")
    pid = make_project()
    a = make_agent(pid, "Vertrieb", connect=True)
    conn(client, pid, echo.url, headers={"Authorization": "Bearer ${CRM_TOKEN}"})
    scripted(monkeypatch, [{"tools": [{"tool": "call_connection", "name": "crm", "data": {"name": "Ali"}}]},
                           {"result": "Kunde Ali angelegt"}])
    tid = make_task(pid, a)
    drain()
    assert task(tid)["status"] == "done"
    assert len(echo.hits) == 1 and json.loads(echo.hits[0]["body"]) == {"name": "Ali"}
    assert echo.hits[0]["headers"]["Authorization"] == "Bearer geheim123"
    assert "geheim123" not in json.dumps(A.q("SELECT * FROM audit"))


def test_ohne_recht_kein_aufruf(client, echo, monkeypatch):
    pid = make_project()
    a = make_agent(pid, "Vertrieb")
    conn(client, pid, echo.url)
    p = A.q1("SELECT * FROM projects WHERE id=?", (pid,))
    assert "call_connection" not in A.build_system(A.q1("SELECT * FROM agents WHERE id=?", (a,)), p, "work")
    scripted(monkeypatch, [{"tools": [{"tool": "call_connection", "name": "crm", "data": {}}]}, {"result": "x"}])
    make_task(pid, a)
    drain()
    assert echo.hits == []


def test_verbindung_mit_freigabe(client, echo, monkeypatch):
    pid = make_project()
    a = make_agent(pid, "Vertrieb", connect=True)
    conn(client, pid, echo.url, confirm=True)
    scripted(monkeypatch, [{"tools": [{"tool": "call_connection", "name": "crm", "data": {"name": "Ali"}}]},
                           {"result": "Anfrage gestellt"}])
    tid = make_task(pid, a)
    drain()
    assert task(tid)["status"] == "waiting_approval" and echo.hits == []
    ap = client.get("/api/approvals").json[0]
    assert ap["kind"] == "connect" and "Ali" in ap["payload"]
    client.post(f"/api/approvals/{ap['id']}", json={"decision": "approve"})
    t = task(tid)
    assert t["status"] == "done" and "angelegt" in t["result"] and len(echo.hits) == 1


def test_eingang_erzeugt_auftrag(client):
    pid = make_project()
    ceo = make_agent(pid, "CEO", delegate=True)
    path = client.get(f"/api/projects/{pid}/connections").json["hook"]["path"]
    assert client.post(path, json={"text": "Wochenbericht"}).status_code == 404  # standardmaessig aus
    client.put(f"/api/projects/{pid}/hook", json={"enabled": True})
    r = client.post(path, json={"text": "Wochenbericht bitte"})
    assert r.status_code == 200 and task(r.json["task_id"])["agent_id"] == ceo
    assert client.post(f"/hook/{pid}/falsch", json={"text": "x"}).status_code == 404
    new = client.put(f"/api/projects/{pid}/hook", json={"reset": True}).json["path"]
    assert new != path and client.post(path, json={"text": "x"}).status_code == 404


def test_eingang_braucht_kein_login_aber_api_schon(client, monkeypatch):
    monkeypatch.setattr(A, "TOKEN", "einlangespasswort")
    pid = make_project()
    make_agent(pid, "CEO")
    A.set_setting(f"hook:{pid}", "1")
    assert client.get(f"/api/projects/{pid}/connections").status_code == 401
    assert client.post(f"/hook/{pid}/{A.hook_token(pid)}", json={"text": "x"}).status_code == 200


def test_post_geht_an_verbindung(client, echo):
    pid = make_project()
    a = make_agent(pid, "CEO")
    conn(client, pid, echo.url, on_post=True, confirm=True)
    tid = make_task(pid, a, "Bericht")
    drain()
    import time
    for _ in range(50):
        if echo.hits:
            break
        time.sleep(0.05)
    body = json.loads(echo.hits[0]["body"])
    assert body["event"] == "post" and body["task_id"] == tid and body["status"] == "done"


def test_ungueltige_verbindung_abgelehnt(client):
    pid = make_project()
    assert client.post(f"/api/projects/{pid}/connections", json={"name": "x", "url": "file:///etc/passwd"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/connections", json={"name": "x", "url": "http://a", "headers": "kaputt"}).status_code == 400
