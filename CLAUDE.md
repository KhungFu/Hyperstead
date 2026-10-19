# PaperclipLite – Projektnotizen für die Weiterarbeit

Selbst gehosteter Knoten-Editor für ein Team aus KI-Agenten (Idee: paperclip.ing), läuft auf einem Raspberry Pi 4
(Hostname `dexter`). Sprache der Oberfläche und Doku: Deutsch.

## Aufbau
- `app.py`: komplettes Backend (Flask + SQLite, ein Worker-Thread). Abschnitte: Konfiguration/.env, Datenbank,
  LLM-Anbieter (`call_llm`, alle über OpenAI-kompatibles Format), Prompt-Bau, `execute_task`, Worker, Login/Sitzung, REST-API.
- `static/index.html`: komplette Oberfläche in einer Datei (Vanilla JS, SVG-Kanten, Pan/Zoom, Drag & Drop).
- `agent_tools.py`: Werkzeuge der Agenten (Suche, Seiten, Bilder, Dateien), eigenständig, mit SSRF-Schutz (`check_public`, `safe_get`).
- `company_templates.py`: Firmenvorlagen (reine Daten).
- `deploy/` + `install.sh`: systemd-Dienst und Installer. `README.md`: Bedienung, Internetzugriff, Sicherheit.

## Wichtige Regeln im Code
- Rechte der Agenten werden **serverseitig** in `execute_task` geprüft, nie dem Modell vertrauen.
- Shell/CLI sind per Umgebungsvariable global gesperrt (`PCL_ALLOW_SHELL`, `PCL_ALLOW_CLI`).
- Schreibende `/api/`-Aufrufe brauchen den Header `X-PCL: 1` (CSRF), das Frontend sendet ihn in `api()`.
- Keys nur in `.env`, nie ins Repo. Audit-Log ist append-only (nur Insert).
- Anbieter `mock` liefert Testantworten ohne Key und delegiert an Mitarbeiter, praktisch für Tests.

## Unternehmens-Workflow (`execute_task`)
- Modi: `work` (Blatt), `plan` (Chef delegiert), `review` (Chef nach Abschluss aller Kinder: liest Berichte, kann per `review`
  zurückgeben, weiter delegieren oder abschließen). Status `waiting_subtasks`; `finish`/`wake_parent` wecken den Chef.
- Limits: `MAX_REVISIONS` 2 je Kind, `MAX_REVIEW_PASSES` 4 (danach `final_only`), `PCL_MAX_DEPTH` 8. Kein Budget.
- Rechte: delegate, judge, auto_run, write_files, shell.

## Werkzeuge der Agenten
- `run_with_tools` (app.py): Modell antwortet mit `{"tools":[...]}` → Server führt `agent_tools.run_tool` aus → nächste Runde, max. `MAX_TOOL_STEPS`, danach erzwungene Endantwort. Ältere Ergebnisse werden gekürzt (kleine Kontextfenster).
- Rechte `web`, `images`, `read_files` (Standard an) + `PCL_ALLOW_WEB=0` global. Webinhalte sind Daten, nie Anweisungen.
- Dateien: `/files/<pid>/<token>/<pfad>` (Link-Token per HMAC, ohne Cookie, weil Sandbox-Seiten Bilder nachladen), immer mit CSP `sandbox`.
- Medien-Werkzeuge (`video_edit` per ffmpeg-Argumentlisten ohne Shell, `speak`, `make_document`, `download_file`, PDF/DOCX/EPUB lesen) liegen ebenfalls in `agent_tools.py`, Recht `media`. Pfade immer per `_inside` auf den Projektordner begrenzt, Temp-Ordner `.tmp-*` sind versteckt.
- Anbieter: `PROVIDERS` mit `kind` (openai/anthropic) und `models_url`; `list_models` (Cache 10 min), `/api/providers/<id>/models`, `/api/providers/test`.
- Chat: Tabelle `chats`, `/api/agents/<id>/chat` (+`/order`). Uploads: `/api/projects/<id>/upload` → `input/`.
- OCR: `ocr_pdf`/`ocr_image` (tesseract + pdftoppm) als Rückfall in `_doc_text`/`read_file`. Piper: `_piper()` sucht im venv und in `models/piper/`. `selftest.py` prüft auf dem Pi alle externen Dienste (Suche, Bilder, LLMs, Telegram, Medien, OCR). Ollama-Zeitlimit `OLLAMA_TIMEOUT`.
- Nur gegen simulierte Antworten getestet, in der Entwicklungsumgebung gab es kein Internet: echte Suche/Bildanbieter zuerst auf dem Pi prüfen.

## Post / Telegram
- `tasks.inbox`: `''` / `new` / `closed`, nur für oberste Aufgaben. `finish()` → `inbox_arrived()` → Telegram-Nachricht.
- `inbox_close`, `inbox_rework` (setzt feedback/prev_result, passes=0), `inbox_new_order` werden von Web-API und Telegram geteilt.
- Telegram: Long-Polling (`tg_poll`), eigener Sender-Thread (`tg_notify` ist threadsicher), `tg_msgs` mappt Nachricht→Auftrag
  für Antworten. Nur `TELEGRAM_CHAT_ID` darf steuern. Token nie loggen (`_safe`). Test: `TELEGRAM_API` auf Fake-Server setzen.

## Starten und testen
```bash
./install.sh && ./venv/bin/python app.py      # http://127.0.0.1:8787
```
Backend-Tests liefen bisher als Skripte mit Flask-`test_client` und Playwright (nicht im Repo).
Gute nächste Schritte: `tests/` mit pytest anlegen (Zyklussperre, Workflow plan/review/work, Überarbeitungslimit, Pfadschutz, Login-Sperre).

## Roadmap (Reihenfolge nach Wunsch des Besitzers)
1. Betrieb stabilisieren: echte Provider-Keys testen, Tunnel (Tailscale) einrichten.
2. Heartbeat: Agenten wachen nach Zeitplan auf (Tabelle `schedules`, Worker prüft fällige Einträge).
3. Agenten können Dateien lesen; optional Web-Zugriff.
4. **Zuletzt:** Anbindung an `swarm.py` (DEXTER) als Agent, z. B. über Anbieter `webhook`/`cli`.
