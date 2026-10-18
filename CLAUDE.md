# PaperclipLite – Projektnotizen für die Weiterarbeit

Selbst gehosteter Knoten-Editor für ein Team aus KI-Agenten (Idee: paperclip.ing), läuft auf einem Raspberry Pi 4
(Hostname `dexter`). Sprache der Oberfläche und Doku: Deutsch.

## Aufbau
- `app.py`: komplettes Backend (Flask + SQLite, ein Worker-Thread). Abschnitte: Konfiguration/.env, Datenbank,
  LLM-Anbieter (`call_llm`, alle über OpenAI-kompatibles Format), Prompt-Bau, `execute_task`, Worker, Login/Sitzung, REST-API.
- `static/index.html`: komplette Oberfläche in einer Datei (Vanilla JS, SVG-Kanten, Pan/Zoom, Drag & Drop).
- `deploy/` + `install.sh`: systemd-Dienst und Installer. `README.md`: Bedienung, Internetzugriff, Sicherheit.

## Wichtige Regeln im Code
- Rechte der Agenten werden **serverseitig** in `execute_task` geprüft, nie dem Modell vertrauen.
- Shell/CLI sind per Umgebungsvariable global gesperrt (`PCL_ALLOW_SHELL`, `PCL_ALLOW_CLI`).
- Schreibende `/api/`-Aufrufe brauchen den Header `X-PCL: 1` (CSRF), das Frontend sendet ihn in `api()`.
- Keys nur in `.env`, nie ins Repo. Audit-Log ist append-only (nur Insert).
- Anbieter `mock` liefert Testantworten ohne Key und delegiert an Mitarbeiter, praktisch für Tests.

## Starten und testen
```bash
./install.sh && ./venv/bin/python app.py      # http://127.0.0.1:8787
```
Backend-Tests liefen bisher als Skripte mit Flask-`test_client` und Playwright (nicht im Repo).
Gute nächste Schritte: `tests/` mit pytest anlegen (Zyklussperre, Budget, Pfadschutz, Login-Sperre).

## Roadmap (Reihenfolge nach Wunsch des Besitzers)
1. Betrieb stabilisieren: echte Provider-Keys testen, Tunnel (Tailscale) einrichten.
2. Heartbeat: Agenten wachen nach Zeitplan auf (Tabelle `schedules`, Worker prüft fällige Einträge).
3. Agenten können Dateien lesen; optional Web-Zugriff.
4. **Zuletzt:** Anbindung an `swarm.py` (DEXTER) als Agent, z. B. über Anbieter `webhook`/`cli`.
