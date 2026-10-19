# PaperclipLite

Ein Agenten-Team als Knoten-Editor, selbst gehostet, leicht genug für den Raspberry Pi.
Projekt anlegen, Agenten per Drag & Drop auf die Fläche ziehen, verbinden (Chef → Mitarbeiter),
pro Knoten KI-Anbieter, Arbeitsanweisung und Rechte einstellen und Aufgaben zuweisen.

## Installation (Pi / Linux)

```bash
git clone https://github.com/KhungFu/paperclip-lite && cd paperclip-lite
./install.sh --service     # venv, Abhängigkeiten, .env mit Zufallspasswort, systemd-Dienst
nano .env                  # API-Keys eintragen, danach: sudo systemctl restart paperclip-lite
```

Ohne Dienst: `./install.sh` und dann `./venv/bin/python app.py` → http://127.0.0.1:8787.
Das Login-Passwort steht in `.env` (`APP_TOKEN`). Update später: `git pull && sudo systemctl restart paperclip-lite`.

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
| `image_search` / `image_save` | frei lizenzierte Fotos suchen und in `assets/` speichern, mit Urheber und Lizenz | Openverse; optional `PEXELS_API_KEY` |
| `image_generate` | KI-Bild erzeugen | Pollinations; besser `IMAGE_PROVIDER=gemini` oder `openai` |
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
| `make_document` | aus Markdown-Kapiteln **PDF, DOCX, EPUB oder HTML** (A4/A5, Cover, Bilder, Umlaute und türkische Zeichen) |
| `media_info` | Dauer, Auflösung, Codecs |
| `download_file` | PDFs, EPUB, Office, Audio, Video, ZIP aus dem Netz in `downloads/` laden |
| `read_file` | liest Text, Markdown, HTML, **PDF, DOCX, EPUB**, auch lange Dateien in Abschnitten |

**Eigene Dateien** (Videos zum Bearbeiten, PDFs, Bilder, Texte) lädst du in „📁 Dateien dieses Projekts“ hoch, sie landen in
`input/`; fertige Ergebnisse liegen in `output/`, Bilder in `assets/`. Ehrliche Grenzen: Es gibt **keine KI-Videogenerierung**
(Text-zu-Video). „Animation“ heißt hier: Szenenbilder per Bild-KI + Zoom/Schwenk + Sprecher + Schnitt. Auf dem Raspberry Pi
rechnet ffmpeg langsam (eine Minute 720p-Video kann mehrere Minuten dauern), Zeitlimit `PCL_FFMPEG_TIMEOUT`.

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
| Ollama | – | lokale Modelle auf dem Pi |
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

## Grenzen dieser Version

- Ein Worker, Aufgaben laufen nacheinander.
- Kein automatischer Heartbeat nach Zeitplan (Aufgaben starten manuell oder per Delegation).
- Keine Text-zu-Video-KI, keine Scan-/Bild-PDFs (OCR), keine eigene Anstellung neuer Agenten durch den CEO (Organigramm legst du an).
- Kein echter Browser: Seiten werden als Text gelesen, JavaScript-lastige Seiten liefern oft wenig. Die DuckDuckGo-Suche ohne Key kann begrenzt oder geändert werden.
- Kein Budget: Tokens werden nur gezählt. Die Rundenlimits (Überarbeitungen, Prüfdurchgänge, Tiefe) verhindern Endlosschleifen.
- Sitzungen sind einfache signierte Cookies, ein einzelnes Gerät lässt sich nicht gezielt abmelden
  (Passwort ändern macht alle Sitzungen ungültig).
