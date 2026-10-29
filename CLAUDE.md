# PaperclipLite – Projektnotizen für die Weiterarbeit

Selbst gehosteter Knoten-Editor für ein Team aus KI-Agenten (Idee: paperclip.ing), läuft auf einem Raspberry Pi 4
(Hostname `dexter`). Sprache der Oberfläche und Doku: Deutsch.

## Aufbau
- `app.py`: komplettes Backend (Flask + SQLite, `PCL_WORKERS` Worker-Threads). Abschnitte: Konfiguration/.env, Datenbank,
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
- Rechte: delegate, judge, auto_run, write_files, shell, recruit.
- Modus `recruit`: Agent mit Recht `recruit`, ohne Mitarbeiter, oberste Aufgabe → `recruit_team` legt Agenten mit `provider=''` an (Rechte nur aus `RECRUIT_PERMS`, max. `RECRUIT_MAX`). Plan-Modus bricht ab, solange Kinder ohne KI existieren. Zuweisung über `/api/models/replace` (provider `''`, optional `project_id`), `model_health` meldet sie als `unassigned`.
- Zeitplan: Tabelle `schedules` (`at` = HH:MM | `open` | `close`, `days` Mo=0), Öffnungszeiten in `settings` (`hours:<pid>`). `schedule_tick` (Worker, alle 20 s) startet fällige Zeitpläne (`tasks.schedule_id`, Nachholfenster 6 h, kein Doppelstart) und nimmt bei Arbeitsbeginn liegengebliebene Aufgaben wieder auf (`resume_open_tasks`, `tasks.resumed` ≤ `PCL_MAX_RESUMES`). `gate_all` hält Queue außerhalb der Öffnungszeiten an. API: `/api/projects/<id>/hours|schedules`, `/api/schedules/<id>[/run]`. Zeitzone `PCL_TZ`. Kontrollgang: `schedules.kind='inspect'` → `fire_schedule` hängt `inspection_report(pid)` (Fakten aus tasks/audit/schedules) + `INSPECT_TASK` an die Beschreibung; `/api/projects/<id>/report`. Geplante Aufgaben lösen nie den Modus `recruit` aus.
- Projektordner: `projects.folder` (Slug des Namens), `proj_dir(pid)` überall statt `WORKSPACE/<id>`; `assign_folder` bei Neuanlage, `migrate_folders` benennt alte Nummernordner um. Löschen eines Projekts lässt den Ordner stehen, ein gleichnamiges neues Projekt übernimmt ihn.
- Veröffentlichen: `site_start/site_stop` starten je Projekt einen `ThreadingHTTPServer` (`PCL_SITE_HOST`, Ports ab `PCL_SITE_PORT_BASE`), liefert `site_root(pid)` = `www/` im Projektordner (existiert er nicht: Rückfall auf den Projektordner ohne `input/`), nie Dotfiles/Symlinks nach außen; Einstellung `site:<pid>`, Start in `start_sites()`. Recht `publish` → Aktion `publish` erzeugt Freigabe (`approvals.kind='publish'`), Klick startet die Seite. API `/api/projects/<id>/site`.

## Werkzeuge der Agenten
- `run_with_tools` (app.py): Modell antwortet mit `{"tools":[...]}` → Server führt `agent_tools.run_tool` aus → nächste Runde, max. `MAX_TOOL_STEPS`, danach erzwungene Endantwort. Ältere Ergebnisse werden gekürzt (kleine Kontextfenster).
- `copy_files` (Recht `write_files`): kopiert/verschiebt Datei oder Ordner im Projektordner (z. B. `site/`→`www/`), nie nach `input/`/Dotordner, Limits 500 Dateien/100 MB. Das Teamlisting im Prompt (`build_system`) nennt die Rechte jedes Mitarbeiters; `publish` per Agent verlangt `www/index.html`. CLI-Anbieter haben keine eigenen Werkzeuge (Arbeitsordner `workspace/.cli-run/`), Dateien entstehen über die Server-Werkzeuge.
- Programmieren (Recht `code`, Standard aus): `write_code` schreibt Quelltext jeder Sprache (nicht `input/`/Dotdateien, max. 500 KB), `check_code` prüft ohne Ausführung: Python per `compile()`, JSON intern, sonst `CODE_CHECKERS` (node --check, rustc --emit=metadata, javac -proc:none, gcc/g++ -fsyntax-only, gofmt -e, bash -n, ruby -c, php -l, luac -p, tsc, kotlinc, mcs, swiftc) mit minimaler Umgebung (keine Keys) und `PCL_CODE_TIMEOUT`. Fehlt der Compiler, meldet es das. `perl -c`/ghc bewusst nicht (führen Code aus).
- Ausführen (Recht `run_code`, Standard aus, nur mit `bwrap`, `PCL_ALLOW_RUN=0` sperrt): `tools.run_code` startet `RUNNERS` (py/js/sh/rb/php/lua)
  per `_sandbox_cmd` (bubblewrap: `--unshare-all` = kein Netz, nur `/usr` + Teile von `/etc`, Projekt ro unter `/projekt`, Temp-Arbeitsordner
  `/arbeit`, `--clearenv`) mit rlimits (`PCL_RUN_MEM_MB`, CPU, Dateigröße) und `PCL_RUN_TIMEOUT` (killpg). Neue Dateien → `output/run/<zeit>/`.
- Echter Browser: `browse_page` (Recht `web`, nur wenn Playwright importierbar und `PCL_BROWSER`≠0): Chromium je Aufruf, `_browser_lock` (1 Instanz),
  `ctx.route` + `route_web_socket` prüfen JEDE Anfrage mit `check_public` (Restrisiko DNS-Rebinding), WebRTC/Downloads/Service Worker aus.
  Screenshot fängt `run_with_tools` ab wie `view_image` (geht in `seen`). `install.sh --browser|--run`, `selftest.py browser|run`.
- Rechte `web`, `images`, `read_files` (Standard an) + `PCL_ALLOW_WEB=0` global. Webinhalte sind Daten, nie Anweisungen.
- Dateien: `/files/<pid>/<token>/<pfad>` (Link-Token per HMAC, ohne Cookie, weil Sandbox-Seiten Bilder nachladen), immer mit CSP `sandbox`.
- Medien-Werkzeuge (`video_edit` per ffmpeg-Argumentlisten ohne Shell, `speak`, `make_document`, `download_file`, PDF/DOCX/EPUB lesen) liegen ebenfalls in `agent_tools.py`, Recht `media`. Pfade immer per `_inside` auf den Projektordner begrenzt, Temp-Ordner `.tmp-*` sind versteckt.
- `video_generate` (Recht `media`, nur sichtbar mit `VIDEO_PROVIDER=gemini`): Standardmodell `gemini-omni-1.1-flash` über die Interactions-API
  (`/v1beta/interactions`, Video base64 in `steps[].content`, `continue_id` = `previous_interaction_id`); `VIDEO_MODEL=veo-*` nutzt
  `:predictLongRunning` + Operation abfragen + Download. Veo-3.1-Preview-Modelle wurden am 2026-10-22 abgeschaltet. Ergebnis in `output/`.
- `image_generate` (Recht `images` ODER `media`): `IMAGE_PROVIDER` pollinations (Std.; ohne Key alter Gratis-Endpunkt `image.pollinations.ai` ohne Referenzen, mit `POLLINATIONS_API_KEY`
  `gen.pollinations.ai/v1/images/generations`, `image` als LISTE von data-URLs, Std.-Modell `POLLINATIONS_MODEL` = `black-forest-labs/flux.2-klein-4b`; seit 2026-07 kein laufendes Gratis-Guthaben mehr) | openai (`/images/edits` mit `image[]` bei `refs`) |
  gemini (`generateContent`, Text + `inline_data`, `imageConfig.aspectRatio`/`IMAGE_SIZE`, Std.-Modell `GEMINI_IMAGE_MODEL` = `gemini-2.5-flash-image`; Modellnamen per `_model_env` bereinigt, leer = Standard) | openrouter (`/api/v1/images`, `input_references` als data-URL, Std. `google/gemini-2.5-flash-image`). `IMAGE_FALLBACK=pollinations` (Std. aus): Anbieterfehler -> Ersatzbild ohne refs (mit Pollinations-Key mit refs), Hinweis im Ergebnis. `IMAGE_STYLE` wird jedem Prompt vorangestellt. sdcpp = eigener Rechner mit stable-diffusion.cpp `sd-server` (`SDCPP_URL`, `POST /sdapi/v1/txt2img`, refs als `extra_images`, `_sdcpp_size` laengste Seite `SDCPP_SIZE`, `_sdcpp_lock` = ein Bild gleichzeitig, Zeitlimit `SDCPP_TIMEOUT` 1800 s; Anleitung `docs/laptop-bildrechner.md`). `refs` max. 4,
  `format` quadrat/hoch/quer, `path` nur in assets/output/karten (ueberschreibt). Eingabefehler vor dem API-Aufruf. Nur mit Mocks getestet.
- Anbieter: `PROVIDERS` mit `kind` (openai/anthropic) und `models_url`; `list_models` (Cache 10 min), `/api/providers/<id>/models`, `/api/providers/test`.
- Chat: Tabelle `chats`, `/api/agents/<id>/chat` (+`/order`). Uploads: `/api/projects/<id>/upload` → `input/` über `save_input`
  (Name bereinigt, nie überschreiben, `renamed` in der Antwort). Chat-POST nimmt `files` (nur Pfade in `input/`, dazu automatisch Dateien aus `input/`, deren Name in der Nachricht steht), stellt `files_note` vor die Nachricht
  und hängt den INHALT an (`chat_attachment_block`: Text/PDF/DOCX über `tools.read_file`, Bilder als Bild über `call_llm(..., images=)`:
  API als image_url/image-Block, `claude_cli` per `--input-format stream-json`, `codex_cli` per `-i`; lehnt das Modell Bilder ab, Text-Retry mit Hinweis).
  `chats.files` merkt die Anhänge, ältere Nachrichten bekommen den Text gekürzt. `chat_system` listet die Dateien in `input/`.
- Bilder in Aufgaben: Werkzeug `view_image` (Recht `read_files`, Bilder und Seiten gescannter PDFs über `tools.pdf_page_images`:
  pdftoppm, sonst eingebettete Scanbilder per pypdf). `run_with_tools` fängt es ab und schickt alle Bilder des Laufs (`seen`, max.
  `PCL_RUN_MAX_IMAGES`) in jeder Runde mit; `task_images` hängt im Auftrag genannte Bilder/Scans aus `input/` gleich an. `call_llm_img` = mit Text-Rückfall.
  `read_file` liest PDFs bis `PCL_MAX_READ_MB` (200). UI: Ergebnisse mit 📋 Kopieren (`resHtml`/`copyText`, Fallback ohne HTTPS),
  `loadTasks` zeichnet nur bei Änderungen neu und nie während einer Markierung.
- Selbstkontrolle: `run_with_tools` rendert neue PDFs aus `made` (`tools.pdf_overview` = alle Seiten auf einem Bild + Seite 1) und erzwingt eine
  Runde „SELBSTKONTROLLE“ (`PCL_SELF_CHECKS`, Standard 1). `build_system` hat den Absatz ARBEITSWEISE (max. 2 Rückfragen, sonst ANNAHME, nachrechnen).
- Dateien in Aufgaben: Werkzeug `write_file` (Recht `write_files`, intern `write_code`, nicht `input/`/Dotpfade) schreibt SOFORT im Werkzeug-Schritt,
  damit `make_document` im selben Lauf daraus bauen kann (die Aktion `write_file` im End-JSON greift erst nach dem Lauf). `make_document` gibt es mit
  `media` ODER `write_files`. Teamlisting zeigt auch die Rechte des Teams darunter (`descendants`). Keine Hinweise mehr „CLI liefert nur Text“:
  CLI-Agenten erzeugen Dateien genauso über die Server-Werkzeuge (der Hinweis hatte Chefs zum Blockieren gebracht).
- `make_document` mit `html` (Pfad oder HTML-Text → `work/<name>.html`): WeasyPrint (optional, `install.sh` installiert es, braucht libpango),
  eigener URL-Fetcher erlaubt nur `data:` und Dateien im Projektordner ohne Dotpfade (kein Netz, kein SSRF). Chromium-Rückfall bewusst nicht.
- `claude_cli`: läuft mit `--strict-mcp-config` (keine Konnektoren wie Gmail/Drive aus dem Abo) und bekommt die System-Nachricht als
  `--system-prompt` statt des Claude-Code-Prompts. Ohne beides hielt sich das Modell für werkzeuglos und ignorierte die JSON-Werkzeuge.
  Kann ein Modell keine Bilder, sagt `call_llm_img` ihm das (Bericht nennt Agent/Modell). Angeworbene Mitarbeiter haben immer `read_files`.
  Telegram: Datei-Nachrichten (`tg_file_of`) → `tg_save_file` → Bildunterschrift = Auftrag/Überarbeitung, ohne Text in `_tg_pending` für den nächsten Auftrag, Alben über `_tg_groups`/`tg_flush_groups`.
- Oberfläche responsive: unter 820 px Menü ☰ (`#app.side-open`), Panel als Vollbild, Canvas per Pointer-Events (Touch, zwei Finger = Zoom).
- Installer: `install.sh --system` (Medien/OCR per apt), `--code` (Compiler aus `CODE_PKGS`), `--all` (alles inkl. Piper + Dienst). `selftest.py code` prüft alle Sprachen.
- OCR: `ocr_pdf`/`ocr_image` (tesseract + pdftoppm) als Rückfall in `_doc_text`/`read_file`. Piper: `_piper()` sucht im venv und in `models/piper/`. `selftest.py` prüft auf dem Pi alle externen Dienste (Suche, Bilder, LLMs, Telegram, Medien, OCR). Ollama-Zeitlimit `OLLAMA_TIMEOUT`.
- `call_llm`: bei 429/5xx oder leerer Antwort (`EmptyReply` aus `_parse_reply`, z. B. Gemini ohne `content` bei Filter) erst alle Keys, dann `PCL_LLM_RETRIES` (3) weitere Runden mit Pause `PCL_LLM_RETRY_WAIT` (8 s, verdoppelt, Retry-After beachtet). Abgeschnittene leere Antworten (`length`) werden nicht wiederholt.
- Gruppen-Umstellung: Menü „🔀 KI für Gruppe“, `GET /api/agents/all`, `POST /api/models/assign` (`agent_ids`, `provider`, `model`).
- Modell-Überwachung: `model_health` (Agenten-Modell nicht mehr in der Live-Liste oder Aufruf mit 404/„model not found“ → `_bad_models`), Worker prüft alle `PCL_MODEL_CHECK_HOURS` (6) und meldet Änderungen einmalig (Audit + Telegram, Marker `settings.model_alert_sig`). UI: Menü „⚠ Modelle“, `GET /api/model_health`, `POST /api/models/replace` (Sammel-Umstellung).
- Nur gegen simulierte Antworten getestet, in der Entwicklungsumgebung gab es kein Internet: echte Suche/Bildanbieter zuerst auf dem Pi prüfen.

## Gedaechtnis, Firmenwissen, parallele Worker
- `agents.memory`: Agent liefert optional `remember` (max. `REMEMBER_MAX`), `save_memory` haengt datiert an, dedupliziert, kuerzt auf `PCL_MEMORY_CHARS`.
  `memory_block` + `knowledge_block` (Ordner `wissen/`, `.md/.txt` in den Prompt bis `PCL_KNOWLEDGE_CHARS`, Rest als Liste) stehen in `build_system` und `chat_system`.
  API `/api/projects/<id>/knowledge` (GET/PUT `wissen/firmenwissen.md`), Upload mit `?dir=wissen`. Agent-PUT nimmt `memory`.
- Worker: `start_worker` startet `WORKERS` Threads; `claim_next` setzt unter `_claim_lock` atomar `queued`->`running` (nie zwei Aufgaben je Agent,
  max. eine Ollama-Aufgabe). Nur Worker 0 macht `schedule_tick`/Modellpruefung. `wake_parent` weckt per bedingtem UPDATE genau einmal.
  `run_claimed` setzt bei Ausnahme `failed` statt `running` haengen zu lassen.

## Ziele, Freigabe-Schranken, Nutzung
- `goals` (parent_id 0 = oberstes), `tasks.goal_id` (vererbt in `create_subtasks`). `goal_tree` (Tiefe + Fortschritt inkl. Unterziele),
  `goals_block` in `build_system` (nur Chefs/oberste) und `inspection_report`, `goal_line` in work/review_prompt. API `/api/projects/<id>/goals`, `/api/goals/<id>`.
- Schranken `settings gates:<pid>` (`plan`, `recruit`, Standard aus): `request_gate` legt `approvals.kind='plan'|'recruit'` mit `data` (JSON) an,
  Aufgabe `waiting_approval`; `decide_gate` (Web + Telegram `ga:`/`gd:` mit Approval-ID, atomar) erzeugt dann die Teilaufgaben bzw. ruft `recruit_team`.
  Ablehnen = `failed` -> Post -> Antwort = neu planen. Nur oberste, nicht geplante Aufgaben im Modus `plan`. Shell nie ueber Telegram.
- `call_llm` = Huelle um `_call_llm`, schreibt jeden Aufruf in `llm_calls` (`record_call`, `est_cost` mit `PRICES`/`PCL_PRICES`, Abo/lokal = 0).
  Abo-Warnung `PCL_ABO_WARN_5H` einmal je 5 h (`settings abo_warn:<anbieter>`). API `/api/usage?days=`.
- Tests: `tests/` (pytest, `conftest.drain()` arbeitet die Queue synchron ab). Neue Funktionen dort mit abdecken.

## Verbindungen (Webhooks)
- Tabelle `connections` (Besitzer legt URL/Methode/Kopfzeilen fest, `${ENV}` in Kopfzeilen aus .env, `confirm`, `on_post`). Recht `connect`
  -> `connections_doc` im Werkzeugblock, `call_connection` in `run_with_tools` (confirm -> `approvals.kind='connect'`, Task endet `waiting_approval`).
  `conn_request` ohne Redirects, max. 200 KB, `PCL_CONN_TIMEOUT`. Private Adressen erlaubt (nur Besitzer setzt sie).
  `notify_connections_post` aus `inbox_arrived` (Thread). Eingang `POST /hook/<pid>/<hook_token>` (guard-Ausnahme, `settings hook:<pid>`,
  Schluessel per `hook_nonce:<pid>` erneuerbar) -> `inbox_new_order`. Generische Freigabe beendet nur Aufgaben in `waiting_approval`.

## Post / Telegram
- `tasks.inbox`: `''` / `new` / `closed`, nur für oberste Aufgaben. `finish()` → `inbox_arrived()` → Telegram-Nachricht.
- `inbox_close`, `inbox_rework` (setzt feedback/prev_result, passes=0), `inbox_new_order` werden von Web-API und Telegram geteilt.
- Telegram: Long-Polling (`tg_poll`), eigener Sender-Thread (`tg_notify` ist threadsicher), `tg_msgs` mappt Nachricht→Auftrag
  für Antworten. Nur `TELEGRAM_CHAT_ID` darf steuern. Token nie loggen (`_safe`). Test: `TELEGRAM_API` auf Fake-Server setzen.

## Starten und testen
```bash
./install.sh && ./venv/bin/python app.py      # http://127.0.0.1:8787
```
Tests: `python -m pytest -q tests` (mock-Anbieter, ohne Internet). UI-Prüfung weiter per Playwright (nicht im Repo).

## Roadmap (Reihenfolge nach Wunsch des Besitzers)
1. Betrieb stabilisieren: echte Provider-Keys testen, Tunnel (Tailscale) einrichten.
2. Heartbeat: Agenten wachen nach Zeitplan auf (Tabelle `schedules`, Worker prüft fällige Einträge).
3. Agenten können Dateien lesen; optional Web-Zugriff.
4. **Zuletzt:** Anbindung an `swarm.py` (DEXTER) als Agent, z. B. über Anbieter `webhook`/`cli`.
