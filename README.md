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

## KI-Anbieter

Groq, Gemini, DeepSeek, Qwen und Ollama laufen über das OpenAI-kompatible Format mit Key-Rotation.
Modellnamen ändern sich oft, im Agenten-Panel kannst du das Modell frei eintragen.

**ChatGPT / Claude über Web-Login (OAuth)** lassen sich nicht sauber als API nutzen. Das Abgreifen von
Web-Sitzungen verstößt gegen die Nutzungsbedingungen und wird geblockt. Der saubere Weg ist der Anbieter
**„CLI-Agent"**: Du trägst einen Befehl ein, der den Prompt von stdin liest (z. B. `claude -p`), und
meldest dich einmalig mit der offiziellen CLI an. Dafür `PCL_ALLOW_CLI=1` in `.env` setzen.

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
- Agenten haben kein Web-Browsing und kein Dateilesen, nur Schreiben.
- Kein Budget: Tokens werden nur gezählt. Die Rundenlimits (Überarbeitungen, Prüfdurchgänge, Tiefe) verhindern Endlosschleifen.
- Sitzungen sind einfache signierte Cookies, ein einzelnes Gerät lässt sich nicht gezielt abmelden
  (Passwort ändern macht alle Sitzungen ungültig).
