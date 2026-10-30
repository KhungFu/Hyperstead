# PaperclipLite

Ein Agenten-Team als Knoten-Editor, selbst gehostet, leicht genug für den Raspberry Pi.
Projekt anlegen, Agenten per Drag & Drop auf die Fläche ziehen, verbinden (Chef → Mitarbeiter),
pro Knoten KI-Anbieter, Arbeitsanweisung und Rechte einstellen und Aufgaben zuweisen.

## Installation

PaperclipLite ist ein Python-Programm (Flask + SQLite) und läuft auf mehreren Systemen. Mehrere Installationen
können parallel laufen, jede hat ihre eigenen Firmen und Daten.

| System | Stand | Anleitung |
| --- | --- | --- |
| Raspberry Pi / Linux (Debian, Ubuntu) | Hauptsystem, voller Funktionsumfang | unten |
| Windows 10/11 | läuft, ohne `run_code`, manches braucht Zusatzprogramme | [docs/windows.md](docs/windows.md) |
| macOS | ungetestet, Grundfunktionen sollten laufen | unten (von Hand) |
| Eigener Bildrechner (z. B. alter Laptop ohne Grafikkarte) | gratis Bilder mit Referenzbildern für PaperclipLite | [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md) |

Umzug von einem Rechner auf einen anderen: PaperclipLite beenden und `data.db`, den Ordner `workspace/` und `.env`
kopieren ([Beispiel Pi → Windows](docs/windows.md)).

### Raspberry Pi / Linux

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
./install.sh --service     # venv, Abhängigkeiten, .env mit Zufallspasswort, systemd-Dienst
nano .env                  # API-Keys eintragen, danach: sudo systemctl restart paperclip-lite
```

Ohne Dienst: `./install.sh` und dann `./venv/bin/python app.py` → http://127.0.0.1:8787.
Das Login-Passwort steht in `.env` (`APP_TOKEN`). Update später: `git pull && sudo systemctl restart paperclip-lite`.
Mehr Funktionen (Video, OCR, Compiler, Browser): `./install.sh --all`.

### Windows

PowerShell im PaperclipLite-Ordner:

```powershell
git clone https://github.com/KhungFu/paperclip-lite; cd paperclip-lite
powershell -ExecutionPolicy Bypass -File install.ps1
notepad .env
deploy\windows\paperclip-start.bat
```

Was unter Windows fehlt, Autostart und Parallelbetrieb mit dem Pi: [docs/windows.md](docs/windows.md).
Update später: `git pull`, dann neu starten.

### macOS (ungetestet)

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env       # APP_TOKEN=<langes Passwort> eintragen, API-Keys ergänzen
./venv/bin/python app.py   # http://127.0.0.1:8787
```

`install.sh` ist für Debian/Ubuntu gebaut (apt), unter macOS daher von Hand wie oben. Zusatzprogramme per Homebrew
(`brew install ffmpeg tesseract poppler`). `run_code` gibt es nur unter Linux.

### Bilder auf einem eigenen Rechner

Ein Rechner im Heimnetz (auch ohne Grafikkarte, mind. 8 GB RAM) kann für PaperclipLite gratis Bilder mit
Referenzbildern erzeugen. In `.env` genau diese zwei Zeilen aktiv lassen (nur eine `IMAGE_PROVIDER=`-Zeile ohne `#`):

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://<IP des Bildrechners>:1234    # auf dem Bildrechner selbst: http://127.0.0.1:1234
```

Einrichtung: [docs/laptop-bildrechner.md](docs/laptop-bildrechner.md).

## Zugriff aus dem Internet

Die App lauscht absichtlich nur auf `127.0.0.1`. Statt einen Port zu öffnen, nutzt du einen Tunnel.
Das ist auch nötig, wenn dein Mobilfunk-Router keine eingehenden Verbindungen erlaubt (CGNAT).

### Option A (empfohlen): Tailscale, privat nur für deine Geräte

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                    # Login-Link im Browser öffnen
sudo tailscale serve --bg 8787       # HTTPS-Adresse nur im eigenen Tailnet
```

Tailscale auch auf Handy/Laptop installieren, dann die angezeigte `https://dexter….ts.net`-Adresse öffnen.
In `.env` ergänzen: `TRUST_PROXY=1`, danach Dienst neu starten.
**Nicht** `tailscale funnel` benutzen, das würde die App öffentlich ins Netz stellen.

### Option B: Cloudflare Tunnel, öffentliche Adresse mit eigener Domain

```bash
# cloudflared installieren (siehe developers.cloudflare.com/cloudflare-one/connections/connect-networks)
cloudflared tunnel login
cloudflared tunnel create paperclip
cloudflared tunnel route dns paperclip agents.deine-domain.de
# ~/.cloudflared/config.yml:  ingress: - hostname: agents.deine-domain.de  service: http://127.0.0.1:8787
cloudflared tunnel run paperclip
```

Zusätzlich dringend empfohlen: **Cloudflare Access** (E-Mail-Login) davor schalten.
In `.env`: `TRUST_PROXY=1`. Die Befehle können sich ändern, im Zweifel gilt die offizielle Anleitung.

Mit `TRUST_PROXY=1` startet die App nur, wenn `APP_TOKEN` mindestens 12 Zeichen hat.

## Bedienung

| Aktion | So geht's |
|---|---|
| Agent anlegen | Eintrag aus der Palette auf die Fläche ziehen (oder anklicken) |
| Verbinden | unteren Punkt eines Knotens auf einen anderen Knoten ziehen (= Chef → Mitarbeiter) |
| Trennen | Verbindungslinie anklicken |
| Verschieben | Knoten ziehen; Hintergrund ziehen = Ansicht verschieben; Mausrad = Zoom |
| Einstellen | Knoten anklicken → Panel rechts |
| Aufgabe zuweisen | Panel → Tab „Aufgaben" |
| Freigeben | Sidebar „Freigaben" |

## Wie das Unternehmen arbeitet

Ein Chef bekommt eine Aufgabe und **plant** (verteilt Teilaufgaben) oder erledigt sie selbst. Sobald alle
Mitarbeiter fertig sind, wacht er wieder auf, **liest ihre Berichte**, gibt Mängel mit Feedback zurück oder
fasst alles zusammen und berichtet an seinen Chef. So wandert das Ergebnis über beliebig viele Ebenen nach oben.
Status „Wartet auf Team“ heißt: der Chef wartet auf seine Leute. Im Aufgaben-Tab siehst du den ganzen Baum.

## Fähigkeiten der Agenten (Internet, Bilder, Dateien)

Agenten arbeiten in Runden: Sie fordern Werkzeuge an, der Server führt sie aus und gibt die Ergebnisse zurück, bis sie
fertig sind (max. `PCL_MAX_TOOL_STEPS`). Rechte pro Agent: **Internet recherchieren**, **Bilder**, **Projektdateien lesen**
(plus wie bisher Dateien schreiben).

| Werkzeug | Was es tut | Ohne Key |
|---|---|---|
| `web_search` | Websuche (Gesetze, Preise, Wettbewerb …) | DuckDuckGo; besser: `SEARXNG_URL`, `BRAVE_API_KEY` oder `TAVILY_API_KEY` |
| `fetch_url` | Webseite als Text lesen | ja |
| `browse_page` | Seite in einem echten Browser öffnen (JavaScript läuft), optional mit Screenshot, den der Agent als Bild sieht | ja, braucht `./install.sh --browser` |
| `image_search` / `image_save` | frei lizenzierte Fotos suchen und in `assets/` speichern, mit Urheber und Lizenz | Openverse; optional `PEXELS_API_KEY` |
| `image_generate` | KI-Bild als PNG erzeugen, optional mit bis zu 4 Referenzbildern aus dem Projekt (gleiche Figuren und gleicher Stil über eine Serie), Format quadrat/hoch/quer und Zielpfad in `assets/`, `output/` oder `karten/`. Recht **Bilder** oder **Medien** | Pollinations (ohne Key: ohne Referenzbilder; mit `POLLINATIONS_API_KEY` und Pollen-Guthaben: Modell per `POLLINATIONS_MODEL`, mit Referenzbildern); `IMAGE_STYLE` legt einen festen Zeichenstil fest; weitere: `nvidia` (FLUX über build.nvidia.com), `cloudflare` (Workers AI, FLUX.2 klein mit Referenzbildern), `hf` (Hugging Face), Modell jeweils per `IMAGE_MODEL`; gratis mit Referenzbildern auf eigenem Rechner: `IMAGE_PROVIDER=sdcpp` ([Anleitung](docs/laptop-bildrechner.md)); besser `IMAGE_PROVIDER=openai` mit `OPENAI_API_KEY`, `gemini` oder `openrouter` mit `OPENROUTER_API_KEY` |
| `list_files` / `read_file` | Dateien im Projektordner lesen (z. B. Texte der Kollegen) | ja |

Alles Erzeugte liegt unter `workspace/<projekt-id>/`. In der Sidebar zeigt **📁 Dateien** die Dateien, öffnet `index.html`
als Webseite (isolierte Sandbox) und lädt alles als ZIP. Der Link enthält einen geheimen Schlüssel.

**Firmenvorlagen** (🏢 neben „Projekte“): *Webagentur*, *Buchhaltung/Steuerkanzlei*, *Import/Export-Handel* legen Projekt,
Organigramm, Arbeitsanweisungen und Rechte komplett an. Eigene Firmen: Projektziel schreiben („ihr seid eine …“, Land,
Branche), Agenten und Rechte setzen. Die Agenten bekommen Datum und Projektziel mit und sollen Veränderliches (Gesetze,
Preise) erst recherchieren und Quellen nennen.

**Sicherheit der Werkzeuge:** Seitenabrufe sind auf öffentliche Adressen beschränkt (kein localhost, LAN, Tailscale,
Cloud-Metadaten; Weiterleitungen werden einzeln geprüft). Webinhalte gelten für die Agenten als unvertrauenswürdige Daten,
trotzdem kann eine präparierte Seite ein Modell beeinflussen: gib Agenten mit Internet keine Shell und prüfe Ergebnisse.
Agenten haben bewusst **keine** Werkzeuge für Käufe, Orders, Zahlungen oder E-Mail-Versand, sie liefern Entwürfe und Empfehlungen.
Bildlizenzen (CC) verlangen oft eine Namensnennung, der Bildredakteur schreibt dafür `bildnachweis.md`.

## Medien, Dokumente und eigene Dateien

Mit dem Recht **Medien & Dokumente erstellen** (und `ffmpeg`/Schriften auf dem Pi, siehe `install.sh`):

| Werkzeug | Was es kann |
|---|---|
| `video_edit` | Video schneiden (`trim`), zusammenfügen (`concat`), **Diashow-Animation mit Zoom** aus Bildern (`slideshow`, optional mit Ton), Text/Untertitel/Logo einblenden, Ton ersetzen/mischen, Tempo ändern, in GIF/WebM/MP3 umwandeln, Standbild ziehen |
| `speak` | Text zu Sprecher-Audio (espeak-ng offline; besser: Piper; optional Edge-Stimmen) |
| `write_file` | mit dem Recht **Dateien schreiben**: legt Kapitel, HTML, CSV usw. sofort an, damit im selben Auftrag daraus ein PDF/DOCX/EPUB wird |
| `make_document` | aus Markdown-Kapiteln **PDF, DOCX, EPUB oder HTML** (A4/A5, Cover, Bilder, Umlaute und türkische Zeichen); mit `html` aus **HTML+CSS** ein PDF mit freiem Layout (Vorlagen nachbauen, per WeasyPrint, lädt nur Dateien aus dem Projekt) |
| `video_generate` | **KI-Videoclip** aus Text (optional mit Startbild), ca. 4–10 s, über Googles Gemini-API (Modell hinter Google Flow). Standard aus, einschalten mit `VIDEO_PROVIDER=gemini` + `GEMINI_API_KEY`. **Kostet pro Sekunde Video**, ein Flow-/Google-One-Abo zählt hier nicht |
| `media_info` | Dauer, Auflösung, Codecs |
| `download_file` | PDFs, EPUB, Office, Audio, Video, ZIP aus dem Netz in `downloads/` laden |
| `read_file` | liest Text, Markdown, HTML, **PDF, DOCX, EPUB**, auch lange Dateien in Abschnitten |
| `view_image` | **sieht** Bilder, Screenshots, Karten, Layouts und Seiten gescannter PDFs an (braucht ein Modell mit Bildverständnis, z. B. Claude, GPT-4o, Gemini) |

**Selbstkontrolle:** Erzeugt ein Agent ein PDF, rendert der Server es danach als Bild (Übersicht aller Seiten + Seite 1 groß) und schickt es
ihm mit der Pflicht, jede Anforderung des Auftrags zu prüfen und Fehler zu beheben, bevor er meldet (`PCL_SELF_CHECKS`, Standard 1, 0 = aus).

**Eigene Dateien** (Videos zum Bearbeiten, PDFs, Bilder, Layouts, Texte) lädst du in „📁 Dateien dieses Projekts“ hoch oder schickst sie
direkt im **💬 Chat** mit einem Agenten mit (📎-Knopf, hineinziehen oder Bild einfügen, mehrere auf einmal). Sie landen in
`input/` (Name bereinigt, vorhandene Dateien werden nie überschrieben, sondern `name-1.png` …, Grenze `PCL_MAX_UPLOAD_MB`); im Chat
bekommt der Agent den **Inhalt** direkt mit der Nachricht (Texte, PDFs, Word als Text, Bilder als Bild, sofern das Modell Bilder versteht;
sonst Texterkennung). Mit **📂 aus input/** hängst du Dateien an, die schon dort liegen, oder du schreibst einfach den Dateinamen in die Nachricht, und „Als Auftrag erteilen“ gibt ihn ans Team weiter; fertige Ergebnisse liegen in `output/`, Bilder in `assets/`. Ehrliche Grenzen: Ohne `video_generate` gibt es **keine KI-Videogenerierung**
(Text-zu-Video), „Animation“ heißt dann: Szenenbilder per Bild-KI + Zoom/Schwenk + Sprecher + Schnitt. Mit `video_generate` entstehen
kurze Clips, längere Filme setzt `video_edit op=concat` zusammen. MagicLight hat keine API: dort erzeugte Videos lädst du nach `input/` hoch. Auf dem Raspberry Pi
rechnet ffmpeg langsam (eine Minute 720p-Video kann mehrere Minuten dauern), Zeitlimit `PCL_FFMPEG_TIMEOUT` (Standard 1 Stunde je Schritt).

**Gescannte PDFs und Bilder (OCR):** `read_file` liest Scans automatisch per `tesseract` (`sudo apt install tesseract-ocr tesseract-ocr-deu poppler-utils`). Das ist langsam (ca. 5–15 s je Seite auf dem Pi, Limit `PCL_OCR_MAX_PAGES`) und kann Fehler enthalten.

**Gute Sprecherstimme:** `./install.sh --piper` richtet Piper mit deutscher Stimme ein; sie wird danach automatisch für deutsche Texte genutzt (andere Sprachen: espeak-ng).

## Chat und Vorlagen

- **💬 Chat-Tab** (im Agenten-Panel): freies Gespräch mit jedem Agenten, z. B. mit der Leitung der *Gedankenwerkstatt*, zum Philosophieren,
  Ideen entwickeln und Hinterfragen. „📋 Als Auftrag erteilen“ übergibt das Gespräch dem Agenten und seinem Team, das Ergebnis kommt als Post.
  Der Chat läuft ohne Werkzeuge.
- **Firmenvorlagen** (🏢): Webagentur, Buchhaltung/Steuerkanzlei, Import/Export-Handel, **Animationsagentur**, **Buchverlag/Content-Agentur**,
  **Gedankenwerkstatt**, **Recherchebüro** (findet und liest PDFs). Beim Gründen wählst du Modell für Leitung und Mitarbeiter.

## Post und Telegram

Sobald ein **oberster Auftrag** (den du einem Agenten, meist dem CEO, gegeben hast) fertig, fehlgeschlagen oder
blockiert ist, liegt Post für dich bereit: Sidebar „📬 Post“ und, wenn eingerichtet, eine Telegram-Nachricht mit
Art, Auftrag, Team-Kennzahlen und dem Ergebnis. Die Rechte-/Berichtskette darunter läuft wie gehabt.

**Telegram einrichten (ca. 2 Minuten):**
1. In Telegram `@BotFather` → `/newbot` → Token kopieren → `.env`: `TELEGRAM_BOT_TOKEN=…`
2. `sudo systemctl restart paperclip-lite`, dem neuen Bot `/start` schreiben → er nennt deine Chat-ID.
3. `.env`: `TELEGRAM_CHAT_ID=…` eintragen, Dienst neu starten. Im Web unter „Post“ gibt es eine Testnachricht.

**Bedienung in Telegram:**

| Du tust | Ergebnis |
|---|---|
| Einfach Text schreiben | neuer Auftrag an den Chef des gewählten Projekts (`@Name Text` = bestimmter Agent) |
| Auf eine Post-Nachricht **antworten** | Auftrag wird mit deinem Text als Anweisung neu bearbeitet |
| Button ✅ oder Antwort „ok“ | Auftrag als erledigt markiert |
| Datei, Foto, Album, Video oder Sprachnachricht senden | landet in `input/` des gewählten Projekts; die Bildunterschrift wird zum Auftrag (als Antwort auf Post: zur Überarbeitung), ohne Text geht die Datei an deinen nächsten Auftrag. Telegram-Bots dürfen nur Dateien bis 20 MB laden, größere im Web hochladen |
| `/post`, `/status`, `/ok <Nr>`, `/neu <Text>`, `/projekt [Nr]` | Übersicht bzw. Kurzbefehle |

Die App fragt Telegram nur nach außen ab, es wird kein Port geöffnet (geht auch hinter CGNAT). Nur die Chat-ID aus
`.env` darf Befehle geben, nimm einen privaten Chat, keine Gruppe. Freigaben für Shell-Befehle laufen bewusst
**nicht** über Telegram, dort kommt nur ein Hinweis.

## Rechte pro Agent

- **Delegieren**: darf Aufgaben an *direkte* Mitarbeiter verteilen (bis `PCL_MAX_DEPTH` Ebenen, Standard 8).
  Optional starten sie automatisch, sonst startest du sie selbst.
- **Ergebnisse beurteilen**: der Chef darf Arbeit mit Feedback zur Überarbeitung zurückgeben (max. 2 Runden je Mitarbeiter).
- **Lesen**: Chefs sehen immer die Berichte ihrer Mitarbeiter, dafür ist kein eigenes Recht nötig.
- **Dateien schreiben**: nur in `workspace/<projekt-id>/`, Pfade außerhalb werden abgelehnt.
- **Code ausführen** (Standard aus): `run_code` startet Python, JavaScript, Bash, Ruby, PHP oder Lua in einer Sandbox, siehe unten.
- **Shell vorschlagen**: nur wenn der Server `PCL_ALLOW_SHELL=1` hat, und dann immer erst nach Freigabe.
- **Pause**: blockiert alle neuen Aufgaben des Agenten.

Die Rechte werden **serverseitig** geprüft. Schreibt ein Modell eine nicht erlaubte Aktion in seine
Antwort, wird sie ignoriert und im Verlauf protokolliert.

## KI-Anbieter und Modellwahl

Pro Agent wählst du **Anbieter und Modell** (Panel → Einstellungen). Die Modellliste holt die App live vom Anbieter,
mit **▶ Testen** prüfst du Key und Modell sofort. So setzt du das passende Modell pro Rolle: stärkstes für Chefs
(Planen, Prüfen, Denken), gute Text- oder Code-Modelle für Mitarbeiter, schnelle günstige für einfache Arbeit.

| Anbieter | Key in `.env` | Hinweis |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Sonnet, Haiku, Opus … je Agent wählbar |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | ein Key für hunderte Modelle (Claude, GPT, Gemini, DeepSeek, Qwen, Llama …) |
| Groq, Gemini, DeepSeek, Qwen | `GROQ_API_KEY`, `GEMINI_API_KEY`, … | mehrere Keys mit Komma = Rotation bei Limit |
| Mistral, NVIDIA NIM, Together, Perplexity | `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `PERPLEXITY_API_KEY` | Perplexity-Modelle (`sonar`) suchen selbst im Netz |
| Hugging Face, Cloudflare Workers AI | `HF_TOKEN` bzw. `CF_ACCOUNT_ID` + `CF_API_TOKEN` | kleine Gratis-Kontingente |
| Ollama | – | lokale Modelle auf dem Pi |
| Claude (CLI, dein Abo) / ChatGPT (Codex-CLI, dein Abo) | – | fest eingebaut: `claude -p --tools "" --strict-mcp-config --no-session-persistence` (Claude ohne eigene Werkzeuge und ohne Konnektoren, nur Text; die Arbeitsanweisung ersetzt den Claude-Code-Systemprompt) bzw. `codex exec --skip-git-repo-check --ephemeral -` (Codex läuft von sich aus im Nur-Lesen-Sandkasten), Modell im Dropdown (Claude: sonnet/opus/haiku); braucht `PCL_ALLOW_CLI=1` und das angemeldete Programm auf dem Pi |
| CLI-Agent | – | Befehl, der den Prompt von stdin liest, z. B. `claude -p --model sonnet`; braucht `PCL_ALLOW_CLI=1` |

**Wichtig:** Ein Web-Login (OAuth, „Abo“) von ChatGPT oder Claude lässt sich nicht sauber als API nutzen, das Abgreifen von
Web-Sitzungen verstößt gegen die Nutzungsbedingungen. Wege: der **API-Key** des Anbieters (Abrechnung nach Verbrauch, nicht
das Chat-Abo) oder der **CLI-Agent** mit der offiziellen, einmalig angemeldeten CLI. Es gibt kein Budget in der App: bei
bezahlten APIs und vielen Werkzeug-Runden können Kosten entstehen, die Tokens siehst du pro Agent am Knoten.

## Sicherheit

- Login-Seite mit signiertem Cookie (7 Tage, `HttpOnly`, `SameSite=Strict`, `Secure` hinter HTTPS).
- Nach 5 falschen Passwörtern 10 Minuten Sperre pro IP, alle Versuche stehen im Audit-Log.
- Schreibende API-Aufrufe brauchen einen eigenen Header (CSRF-Schutz), dazu CSP und weitere Header.
- Shell und CLI-Agenten sind standardmäßig **aus**. Wer das Passwort kennt und `PCL_ALLOW_SHELL=1` gesetzt hat,
  kann Befehle mit den Rechten des App-Benutzers freigeben. `workspace/` ist das Arbeitsverzeichnis, aber **keine Sandbox**.
- `.env`, Datenbank und Arbeitsordner stehen in `.gitignore`. Keys gehören nie ins Repo.
- Bei Trading-Bots (NEXUS) Agenten nie ohne menschliche Freigabe handeln lassen.

## Firmenwissen und Gedächtnis

- **🧠 Firmenwissen** (Seitenleiste): Was alle Agenten eines Projekts immer wissen sollen (Firma, Kunden, Stil, Preise, Regeln). Steht in
  `wissen/firmenwissen.md` im Projektordner. Alle `.md`/`.txt` in `wissen/` gehen bei jedem Auftrag und im Chat mit (zusammen bis
  `PCL_KNOWLEDGE_CHARS`, Standard 8000 Zeichen); andere Unterlagen (PDF, Word …) dort sehen die Agenten als Liste und lesen sie bei Bedarf.
- **Gedächtnis je Agent**: Ein Agent kann sich am Ende eines Auftrags bis zu 5 dauerhafte Fakten merken (Vorlieben, Entscheidungen, Kunden,
  was funktioniert hat). Sie stehen im Agenten-Panel unter „🧠 Gedächtnis“, du kannst sie ändern oder leeren. Grenze `PCL_MEMORY_CHARS`
  (4000), die ältesten Einträge fallen zuerst heraus. Jede neue Notiz steht im Audit-Log.

## Ziele, Freigaben, Nutzung (wie bei Paperclip)

- **🎯 Ziele**: Ziele und Unterziele je Projekt. Beim Zuweisen einer Aufgabe wählst du optional das Ziel, delegierte Aufgaben erben es.
  Chefs sehen die Ziele mit Fortschritt im Prompt, der CEO-Kontrollgang berichtet ihn. Abhaken = erreicht.
- **Vorher fragen** (Fenster ✋ Freigaben, je Projekt, Standard aus): *Plan des obersten Chefs freigeben* hält einen neuen Auftrag an,
  bis du den Verteilungsplan freigibst; *Neue Mitarbeiter freigeben* hält das Selbst-Einstellen des CEO an. Freigeben/Ablehnen auch per
  Telegram-Knopf. Abgelehnt = der Auftrag landet als ❌ in der Post, deine Antwort darauf lässt den Chef neu planen.
  Shell-Freigaben gehen weiterhin nur im Web.
- **📊 Nutzung & Kosten**: Aufrufe, Tokens und geschätzte Kosten je Projekt, Agent und Modell (heute, 7, 30 Tage). Kein Limit.
  Abo-CLIs und Ollama zählen als 0 $; ab `PCL_ABO_WARN_5H` Abo-Aufrufen in 5 Stunden (Standard 150, 0 = aus) kommt eine Telegram-Warnung.
  Preise sind grobe Schätzungen, eigene per `PCL_PRICES='{"sonnet": 5}'` (US-$ je 1 Mio. Tokens, Teil des Modellnamens).

## Tests

```bash
./venv/bin/pip install pytest && ./venv/bin/python -m pytest -q tests
```
Läuft ohne Internet und ohne Keys (Anbieter `mock`, eigene Datenbank).

## 🔌 Verbindungen (Webhooks)

- **Ausgang:** Im Fenster 🔌 Verbindungen trägst du Adressen ein (n8n, Zapier, Make, eigener Dienst; auch `http://127.0.0.1:…` auf dem Pi),
  mit Beschreibung für die Agenten und optional Kopfzeilen. Geheimnisse gehören in `.env` und werden als `${NAME}` eingesetzt.
  Agenten mit dem Recht **„Darf Verbindungen nutzen“** rufen sie per Werkzeug `call_connection` auf; Adresse und Kopfzeilen kann der Agent
  nicht ändern, er schickt nur Daten. **„Nur nach meiner Freigabe“** (Standard an) legt jeden Aufruf erst unter ✋ Freigaben vor.
  **„Bei Post benachrichtigen“** schickt jedes fertige Ergebnis eines obersten Auftrags als JSON an die Adresse. Zeitlimit `PCL_CONN_TIMEOUT` (30 s).
- **Eingang:** „Aufträge von außen“ einschalten, dann nimmt `POST /hook/<projekt>/<schlüssel>` mit `{"text": "…", "agent": "optional"}`
  einen Auftrag an den Chef an (z. B. aus n8n, iOS-Kurzbefehlen oder DEXTER). Ohne Login, geschützt nur durch den Schlüssel in der Adresse:
  „Neuen Schlüssel“ macht die alte Adresse ungültig. Erreichbar ist sie nur so weit wie PaperclipLite selbst (z. B. nur im Tailnet).

## 🌐 Echter Browser und ▶ Code ausführen

- **Browser** (`./install.sh --browser`, installiert Playwright + Chromium, ca. 400 MB, nur 64-Bit-System): Agenten mit dem Recht
  „Internet recherchieren“ bekommen `browse_page`. Die Seite läuft mit JavaScript, der Agent bekommt den sichtbaren Text, die Links und
  auf Wunsch einen Screenshot (sieht ihn wie bei `view_image`, `save` legt ihn in `assets/screenshots/` ab). Jede Anfrage der Seite
  (Skripte, Frames, XHR, WebSockets) muss an eine öffentliche Adresse gehen, LAN/localhost wird blockiert, WebRTC und Downloads sind aus.
  Immer nur ein Browser gleichzeitig (RAM), Zeitlimit `PCL_BROWSER_TIMEOUT` (30 s). Eigenes Chromium: `PCL_BROWSER_PATH`, aus: `PCL_BROWSER=0`.
- **Code ausführen** (`./install.sh --run`, installiert bubblewrap): Recht „Darf Code ausführen“ (Standard aus) gibt `run_code`.
  Das Skript läuft abgeschottet: **kein Internet**, nur `/usr` und der Projektordner (schreibgeschützt unter `/projekt`) sichtbar,
  keine `.env`, keine Datenbank, kein Home. Was das Skript in sein Arbeitsverzeichnis schreibt, landet in `output/run/<zeit>/`
  (max. 50 Dateien/50 MB). Grenzen: `PCL_RUN_TIMEOUT` (60 s), `PCL_RUN_MEM_MB` (1024). Es läuft das Python/Node des Systems,
  also nur Pakete, die per apt installiert sind (z. B. `sudo apt install python3-pandas python3-matplotlib`). Global aus: `PCL_ALLOW_RUN=0`.
  Prüfen: `./venv/bin/python selftest.py run browser`.

## Parallele Arbeit

Bis zu `PCL_WORKERS` Aufgaben laufen gleichzeitig (Standard 2, höchstens 6), z. B. mehrere Mitarbeiter eines Chefs oder Aufträge
verschiedener Projekte. Ein Agent bearbeitet nie zwei Aufgaben auf einmal, und es läuft höchstens eine Ollama-Aufgabe gleichzeitig
(RAM auf dem Pi). Bei Abo-CLIs (Claude, Codex) zählen parallele Aufrufe schneller gegen das Abo-Limit; dann `PCL_WORKERS=1` setzen.

## Grenzen dieser Version

- Kein automatischer Heartbeat nach Zeitplan (Aufgaben starten manuell oder per Delegation).
- Keine Text-zu-Video-KI, keine Scan-/Bild-PDFs (OCR), keine eigene Anstellung neuer Agenten durch den CEO (Organigramm legst du an).
- Der echte Browser (`browse_page`) liest Seiten, klickt aber nicht und füllt keine Formulare aus (keine Logins, keine Käufe). Die DuckDuckGo-Suche ohne Key kann begrenzt oder geändert werden.
- Kein Budget: Tokens und geschätzte Kosten werden nur angezeigt (📊). Die Rundenlimits (Überarbeitungen, Prüfdurchgänge, Tiefe) verhindern Endlosschleifen.
- Sitzungen sind einfache signierte Cookies, ein einzelnes Gerät lässt sich nicht gezielt abmelden
  (Passwort ändern macht alle Sitzungen ungültig).


## Selbsttest auf dem Pi

Nach Installation und Eintragen der Keys prüft `./venv/bin/python selftest.py` alles Echte, was sich ohne Internet nicht testen ließ:
Websuche, Seiten lesen, Bildsuche und Bildgenerator, SSRF-Schutz, jeder KI-Anbieter mit Mini-Anfrage (inkl. Ollama), Telegram
(Bot-Token und Testnachricht an deine Chat-ID), ffmpeg, Sprachausgabe, PDF mit Umlauten, OCR. Einzelne Gruppen:
`selftest.py web | llm | telegram | media | ocr`. Jede Zeile zeigt OK, FEHLT (optional) oder FEHLER mit konkretem Hinweis.

## Ollama (lokale Modelle)

Anbieter „Ollama (lokal)“: kein Key nötig, die Modellliste kommt direkt von Ollama (`ollama pull qwen2.5:3b`). Im Dialog „Firma aus Vorlage“
gibt es die Knöpfe „Alles lokal“ und „Nur Mitarbeiter lokal“; sonst wählst du Ollama je Agent. Läuft Ollama auf einem anderen Rechner
(z. B. dem Laptop), setze `OLLAMA_URL` auf dessen Adresse. Kleine Modelle (3B) sind auf dem Pi langsam und halten das Werkzeug-Protokoll
oft schlecht ein; für Chefs ein starkes Modell, lokal eher für einfache Mitarbeiter oder den Chat.

## Claude und ChatGPT über dein Abo (CLI statt API-Key)

In `.env`: `PCL_ALLOW_CLI=1`. Die Programme installierst und meldest du einmal selbst auf dem Pi an (Anleitungen der Hersteller:
Claude Code `claude`, OpenAI Codex `codex`; Anmeldung mit deinem Abo). Danach erscheinen „Claude (CLI, dein Abo)“ und „ChatGPT (Codex-CLI, dein Abo)“
in allen Anbieter-Listen. Der Server ruft sie ohne Shell auf, in einem leeren Ordner und **ohne unsere API-Keys in der Umgebung**
(sonst würde `claude` den API-Key statt des Abos abrechnen). Grenzen: langsamer als die API (Programmstart je Antwort), Abo-Limits gelten
(viele Agenten = schnell am Limit), und die CLI-Programme haben eigene Werkzeuge – Befehl bei Bedarf über `PCL_CLI_CLAUDE` / `PCL_CLI_CODEX` anpassen.

## Modell weg? Agenten umstellen
PaperclipLite prüft alle 6 Stunden (`PCL_MODEL_CHECK_HOURS`), ob die Modelle der Agenten beim Anbieter noch existieren, und merkt es auch, wenn ein Aufruf „Modell nicht gefunden“ meldet. Dann kommt eine Telegram-Nachricht, die Aufgabe scheitert mit klarem Hinweis, und im Menü **⚠ Modelle** stellst du alle betroffenen Agenten mit einem Klick auf ein anderes Modell um.

## Große Teams
Ein Vorgesetzter kann beliebig viele Mitarbeiter haben. Im Panel des Vorgesetzten (Einstellungen) wählst du unter **Unterstellte Mitarbeiter** per Häkchen alle aus und speicherst die Zuweisung. Alternativ: unteren Punkt des Vorgesetzten auf einen Mitarbeiter ziehen. Der Knopf **🗂 Ordnen** legt alles als Organigramm an (Gruppen ab 6 Mitarbeitern in Reihen zu je 5).

## CEO stellt sein Team selbst zusammen
Der CEO aus der Palette hat das Recht **„Darf sein Team selbst zusammenstellen“** (`recruit`). Hat er noch keine Mitarbeiter und bekommt einen Auftrag, analysiert er ihn und legt Mitarbeiter mit Rolle, Arbeitsanweisung und Berichtslinien an (bis 20, auch Abteilungsleiter mit eigenem Team). Die Neuen haben **noch keine KI**: Du weist sie im Menü **⚠ Modelle** (alle auf einmal) oder je Agent in den Einstellungen zu und antwortest dann in der **Post** auf den Auftrag (z. B. „Weiter“). Danach verteilt der CEO die Arbeit wie gewohnt. Der CEO kann Neuen nur Web, Bilder, Dateien lesen/schreiben und Medien mitgeben, nie Shell.

## Öffnungszeiten und tägliche Aufgaben
Seitenleiste **🕘 Zeitplan**: Pro Projekt Arbeitsbeginn, Feierabend und Arbeitstage festlegen. Je Mitarbeiter lassen sich **tägliche Aufgaben** anlegen (feste Uhrzeit, bei Arbeitsbeginn oder bei Feierabend, an wählbaren Wochentagen), z. B. „jeden Tag um 15:00 die Website kontrollieren“. Das Ergebnis kommt wie jede Post in die Ansicht „Post“ (und per Telegram). Läuft die letzte Aufgabe eines Zeitplans noch, wird nicht doppelt gestartet; war der Pi zur Uhrzeit aus, wird bis zu 6 Stunden nachgeholt.
Bei Arbeitsbeginn nimmt die Firma liegengebliebene Aufgaben wieder auf (nicht gestartete starten, gescheiterte oberste Aufgaben bis zu `PCL_MAX_RESUMES`=2 mal erneut). Optional ruht die Firma außerhalb der Öffnungszeiten ganz. Die Uhrzeit ist die des Pi; stimmt sie nicht, `PCL_TZ=Europe/Vienna` in `.env` setzen.

## CEO-Kontrollgang
Im Fenster **🕘 Zeitplan** richtet **👑 CEO-Kontrollgang** einen täglichen Kontrollgang des obersten Chefs ein (Standard: bei Feierabend; weitere Zeiten über „Neue tägliche Aufgabe“ + Häkchen *Kontrollgang*). Das System legt ihm einen **Statusbericht** mit Fakten bei: je Mitarbeiter heute gestartet/fertig/fehlgeschlagen/offen, Arbeitsstarts außerhalb der Öffnungszeiten, offene Aufgaben ohne Arbeitsbeginn, Mitarbeiter ohne KI, liegengebliebene Aufträge und ob die täglichen Aufgaben gelaufen sind. Der CEO bewertet das, verteilt bei Bedarf Folgeaufgaben an sein Team und schreibt einen Kontrollbericht in die Post. „📋 Statusbericht ansehen“ zeigt die Fakten ohne CEO.

## Projektordner
Jedes Projekt hat einen **Ordner mit seinem Namen** unter `workspace/` (z. B. `workspace/Buchverlag-Content-Agentur/`, Umlaute werden umschrieben). Er bleibt beim Umbenennen des Projekts gleich und wird beim **Löschen eines Projekts nie gelöscht**. Legst du ein Projekt mit gleichem Namen neu an, übernimmt es den vorhandenen Ordner samt Dateien. Alte Nummernordner (`workspace/1`, `workspace/2` …) werden beim Start automatisch auf den Projektnamen umbenannt.

## Webseite veröffentlichen
Im Fenster **📁 Dateien dieses Projekts** gibt es **🚀 Veröffentlichen**: Veröffentlicht wird **nur der Ordner `www/` im Projektordner** (`www/index.html`, dazu CSS, Bilder … mit relativen Pfaden); alles andere im Projekt (Notizen, `output/`, `input/`, Dotfiles, Symlinks nach außen) bleibt unsichtbar. Gibt es keinen `www/`-Ordner, wird wie bisher die `index.html` des Projektordners (ohne `input/` und versteckte Dateien) ausgeliefert. Die Seite läuft dauerhaft auf einem eigenen Port (ab 8800, `PCL_SITE_PORT_BASE`) ausgeliefert, standardmäßig nur auf dem Pi selbst: `http://127.0.0.1:8800/`. Für Zugriff im Netz `PCL_SITE_HOST=0.0.0.0` in `.env`. Agenten mit dem Recht „Darf die Webseite zur Veröffentlichung vorschlagen“ können auf „veröffentlichen“ eine Freigabe anfordern; erst dein Klick unter **Freigaben** schaltet die Seite online. Änderungen der Agenten sind sofort sichtbar, nach einem Neustart läuft die Seite automatisch wieder. Für das offene Internet gehört ein Reverse-Proxy mit HTTPS davor (z. B. Caddy), nicht der Mini-Server.
