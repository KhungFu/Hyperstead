# 🛠 Werkstatt: Agenten arbeiten wie an einem echten Rechner

Mit der Werkstatt arbeitet ein Agent so, als würdest du selbst vor Claude Code oder einem Terminal sitzen. Er führt Befehle
im Projektordner aus, testet, rendert und rüstet fehlende Programme nach, zum Beispiel Remotion, Python-Pakete oder ein
Programm per winget. Das gilt für **alle KIs** und **alle Firmen**, nicht nur für das Animationsstudio.

Jede Installation läuft über einen **Nachrüst-Antrag**: Der Mitarbeiter fragt den CEO, der CEO prüft und legt dir den Antrag vor,
du bestätigst per **Telegram-Knopf** oder im **Web unter ✋ Freigaben**. Danach installiert der Server genau diesen Befehl, der CEO
meldet das Ergebnis zurück und der Mitarbeiter macht mit seiner Aufgabe weiter.

## Einschalten

1. In der `.env` eintragen und Hyperstead neu starten:
   ```
   PCL_ALLOW_WERKSTATT=1
   ```
2. Im Agenten-Fenster beim gewünschten Agenten **„Werkstatt: arbeitet wie an einem echten Rechner“** anhaken, Stufe wählen, speichern.
   Das Recht kann nur der Besitzer vergeben. Ein CEO kann es neuen Mitarbeitern nicht mitgeben.
3. Für Telegram-Knöpfe muss Telegram eingerichtet sein (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). Ohne Telegram geht alles über das Web.

## Wie jede KI arbeitet

| KI im Agenten | So arbeitet sie in der Werkstatt |
|---|---|
| Claude (Abo-CLI `claude`) | Echte Claude-Code-Werkzeuge im Projektordner: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch. Installationsbefehle (npm install, pip install, winget, apt, sudo …), `rm -rf`, `git push` und die `.env` sind ihm gesperrt; er beantragt sie mit `nachruesten`. |
| ChatGPT (Abo-CLI `codex`) | Codex mit eigener Abschottung im Projektordner (Stufe 1 nur lesen, Stufe 2 schreiben im Projekt ohne Netz). Netz und Installationen beantragt er. |
| Alle API-KIs (Gemini, Groq, ChatGPT-API, Qwen, DeepSeek, Mistral, OpenRouter …) und Ollama | Server-Werkzeug `befehl`: führt einen Befehl im Projektordner aus (Windows: PowerShell, Linux: bash) und gibt die Ausgabe zurück. |

Alle Agenten mit Werkstatt haben außerdem `befehl` und `nachruesten`.

## Die drei Stufen

| | Stufe 1 vorsichtig | Stufe 2 normal (Standard) | Stufe 3 frei |
|---|---|---|---|
| Befehle im Projektordner (rendern, testen, Dateien bauen) | Antrag | sofort | sofort |
| Installationen (npm, pip, winget, apt, sudo, curl … \| sh) | Antrag | Antrag | sofort, du bekommst eine Meldung |
| Löschen, Eingriffe ins System, `git push` | Antrag | Antrag | sofort, du bekommst eine Meldung |
| Pfade außerhalb des Projektordners | Antrag | Antrag | sofort |
| Zugangsdaten (`.env`, `tokens/`, Umgebungsvariablen mit Keys) | gesperrt | gesperrt | gesperrt |

Stufe 3 gibt es nur mit `PCL_WERKSTATT_FREI=1` in der `.env`. Ohne den Schalter gilt Stufe 3 wie Stufe 2.

**Wichtig:** Die Einteilung in Stufe 2 erkennt die üblichen Befehle an ihrer Form. Sie ist eine Vorsortierung, keine Abschottung.
Ein Agent könnte sie mit Tricks umgehen (z. B. eine Installation in einem selbst geschriebenen Skript verstecken). Gib die Werkstatt
deshalb nur Agenten, denen du vertraust, und lies bei Anträgen den Befehl.

## Ablauf eines Nachrüst-Antrags

1. Der Mitarbeiter merkt, dass ihm etwas fehlt, und ruft `nachruesten` auf (oder ein `befehl` ist eine Installation). Er nennt den
   genauen Befehl, wofür er ihn braucht und die ungefähre Größe.
2. Der **CEO** (oberster Chef des Projekts) bekommt den Antrag und prüft ihn kurz. Offensichtlich Unnötiges lehnt er ab
   (Begründung geht an den Mitarbeiter). Sonst schreibt er seine Empfehlung dazu und leitet ihn an dich weiter.
   Stellt der CEO selbst den Antrag, geht er direkt an dich.
3. **Du** bekommst eine Telegram-Nachricht mit ✅ Ja / ❌ Nein und siehst den Antrag unter ✋ Freigaben. Du kannst auch schon
   entscheiden, während der CEO noch prüft.
4. Nach deinem Ja führt der Server den Befehl im Projektordner aus (Zeitlimit `PCL_NACHRUEST_TIMEOUT`, Standard 30 Minuten).
   Das Ergebnis steht in der Freigabe, in Telegram und im Verlauf.
5. Der CEO meldet dem Mitarbeiter das Ergebnis, die Aufgabe geht automatisch weiter.
6. Was installiert wurde, steht in `wissen/werkzeuge.md` im Projekt, damit niemand dasselbe noch einmal beantragt.

Höchstens `PCL_NACHRUEST_MAX` (6) Anträge je Aufgabe.

## Beispiel: Remotion für das Animationsstudio

Ein Agent mit Werkstatt prüft `node --version`. Fehlt Node.js, beantragt er
`winget install --id OpenJS.NodeJS.LTS -e --scope user --accept-package-agreements --accept-source-agreements`.
Danach beantragt er `npm install remotion @remotion/cli` im Projektordner und rendert mit `npx remotion render …` nach `output/`.
Remotion ist laut seiner Lizenz für Einzelpersonen und kleine Firmen (bis 3 Mitarbeiter) kostenlos, größere Firmen brauchen eine Firmenlizenz.

## Gut zu wissen

- **Windows-UAC:** Manche winget-Installationen öffnen das Fenster „Darf diese App Änderungen vornehmen?“. Das muss jemand am Laptop
  bestätigen. Mit `--scope user` klappt es oft ohne.
- **Pi/Linux:** `apt` braucht `sudo`. Läuft Hyperstead ohne Passwort-freies sudo, schlägt die Installation fehl. Dann installierst du
  das Programm selbst und der Mitarbeiter findet es danach.
- **Was installiert ist, gilt für den ganzen Rechner** (bzw. bei npm/pip im Projektordner für dieses Projekt).
- **Abo-Verbrauch:** Claude Code und Codex mit Werkzeugen verbrauchen mehr von deinem Abo als reine Textantworten.
- **Zeitlimits:** `PCL_BEFEHL_TIMEOUT` (600 s je Befehl), `PCL_WERKSTATT_TIMEOUT` (3600 s je Claude-/Codex-Lauf).
- Es läuft immer nur ein Werkstatt-Befehl gleichzeitig.
- Jeder Befehl und jede Entscheidung steht im Verlauf (Audit-Log).
- Noch nicht gebaut: ein Stopp-Knopf, der einen laufenden Befehl abbricht (das Zeitlimit beendet ihn). Ein Live-Protokoll während
  eines Claude-Code-Laufs gibt es auch noch nicht, die Schritte stehen erst danach im Ergebnis.

## Probleme

| Meldung | Was tun |
|---|---|
| „Keine Werkstatt (Recht 'werkstatt' fehlt oder PCL_ALLOW_WERKSTATT ist aus)“ | `PCL_ALLOW_WERKSTATT=1` in `.env`, neu starten, Häkchen beim Agenten setzen. |
| Häkchen ist grau | `PCL_ALLOW_WERKSTATT=1` fehlt oder Hyperstead wurde nicht neu gestartet. |
| Stufe 3 ist grau | `PCL_WERKSTATT_FREI=1` in `.env`. |
| „Zugangsdaten … sind für Agenten gesperrt“ | Gewollt: Agenten dürfen `.env`, Tokens und Keys nie lesen. |
| Antrag hängt bei „Der CEO prüft gerade …“ | Der CEO hat keine KI oder sie antwortet nicht. Du kannst trotzdem entscheiden. |
| Installation „Exit 1“ | Ausgabe in der Freigabe lesen. Oft fehlt sudo (Pi) oder die UAC-Bestätigung (Windows). Der Mitarbeiter bekommt die Ausgabe und kann einen anderen Befehl beantragen. |
| Claude-Code-Fehler „unknown option“ | Claude Code aktualisieren (`npm install -g @anthropic-ai/claude-code`), die Schalter `--tools`/`--allowedTools`/`--disallowedTools` brauchen eine aktuelle Version. |
