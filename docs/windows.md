# PaperclipLite unter Windows 10/11

PaperclipLite läuft auch unter Windows. Oberfläche, Agenten, alle API-Anbieter, Telegram, Suche, Bilder,
PDF/Word, Zeitpläne und Verbindungen funktionieren wie auf dem Pi. Ein paar Linux-Werkzeuge fehlen
(Liste unten). Getestet ist die Windows-Variante bisher nur in der Entwicklungsumgebung (Linux), noch nicht auf
einem echten Windows-Rechner.

## Ablauf: erst parallel, dann Umzug auf den Laptop

**Phase 1 – beide laufen (Laptop zum Ausprobieren):**

- Der Pi bleibt das Hauptsystem mit Telegram und den echten Firmen.
- Auf dem Laptop PaperclipLite neu installieren (Schritte 1–4) und mit einer Testfirma ausprobieren.
- In der `.env` des Laptops `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` **leer** lassen. Telegram erlaubt nur
  einen Abholer je Bot, sonst gehen Nachrichten verloren.
- Die API-Keys aus der `.env` des Pi dürfen auf beiden stehen.
- Der Bildrechner läuft auf dem Laptop. Der Pi nutzt ihn mit `SDCPP_URL=http://<IP des Laptops>:1234`, der Laptop
  selbst mit `SDCPP_URL=http://127.0.0.1:1234` (dann muss `bildrechner-start.bat` auf `0.0.0.0` lauschen, wie
  ausgeliefert).

**Phase 2 – Umzug, der Laptop ersetzt den Pi:**

1. Auf dem Laptop PaperclipLite beenden (Fenster schließen). Die Testdaten werden gleich überschrieben:
   bei Bedarf `data.db` und `workspace` vorher umbenennen.
2. Auf dem Pi: `sudo systemctl stop paperclip-lite`
3. Vom Pi in den PaperclipLite-Ordner des Laptops kopieren: `data.db`, den ganzen Ordner `workspace/` und `.env`.
   Am einfachsten in PowerShell auf dem Laptop (Benutzer und Pfad auf dem Pi anpassen):

   ```powershell
   cd $HOME\paperclip-lite
   scp pi@dexter:~/paperclip-lite/data.db .
   scp pi@dexter:~/paperclip-lite/.env .
   scp -r pi@dexter:~/paperclip-lite/workspace .
   ```

4. In der kopierten `.env` prüfen:
   - `HOST=0.0.0.0` und `APP_TOKEN` bleiben, wenn du vom Handy zugreifst.
   - `OLLAMA_URL` zeigt auf den Pi. Ohne Ollama auf dem Laptop die Ollama-Agenten auf einen anderen Anbieter
     stellen (Menü „⚠ Modelle“).
   - `SDCPP_URL=http://127.0.0.1:1234`.
   - `PCL_ALLOW_SHELL`: Freigegebene Befehle laufen jetzt in `cmd.exe`, Linux-Befehle gehen dort nicht.
5. Laptop starten (`deploy\windows\paperclip-start.bat`) und prüfen: Firmen, Aufträge, Post und Telegram da?
6. Erst dann auf dem Pi abschalten: `sudo systemctl disable paperclip-lite`. Die Daten auf dem Pi bleiben als
   Sicherung liegen.
7. Wer von außen über die alte Adresse (DDNS/Router-Weiterleitung) kam: im Router die Weiterleitung von Port 8787
   auf die IP des Laptops umstellen.

Agenten mit Claude/Codex über CLI brauchen auf dem Laptop eigene Installationen von `claude` bzw. `codex`
mit Anmeldung, sonst die Agenten auf einen API-Anbieter umstellen.

## 1. Herunterladen

Mit Git (PowerShell):

```powershell
cd $HOME
git clone https://github.com/KhungFu/paperclip-lite
cd paperclip-lite
```

Ohne Git: auf GitHub (angemeldet) **Code → Download ZIP**, entpacken, z. B. nach `C:\paperclip-lite`.

## 2. Installieren

Python 3.10 oder neuer muss installiert sein (`py --version`). Dann im PaperclipLite-Ordner:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Das legt `venv` an, installiert die Pakete und erzeugt `.env` mit einem zufälligen Login-Passwort (wird angezeigt,
notieren). Keys eintragen: `notepad .env`.

## 3. Starten

Doppelklick auf `deploy\windows\paperclip-start.bat` (oder `venv\Scripts\python.exe app.py`).
Dann im Browser: <http://127.0.0.1:8787>

Prüfen, was geht: `venv\Scripts\python.exe selftest.py`

## 4. Vom Handy oder anderen Rechnern erreichbar

In `.env`: `HOST=0.0.0.0` (APP_TOKEN muss gesetzt sein). Dann einmal als Administrator:

```bat
netsh advfirewall firewall add rule name="PaperclipLite" dir=in action=allow protocol=TCP localport=8787 profile=private
powercfg /change standby-timeout-ac 0
```

Aufruf dann über `http://<IP des Laptops>:8787` (IP mit `ipconfig`). Von unterwegs am sichersten über Tailscale.

Autostart: Win+R, `shell:startup`, Verknüpfungen zu `deploy\windows\paperclip-start.bat` und (falls genutzt)
`C:\bildrechner\bildrechner-start.bat` hineinlegen. Der Laptop muss dafür angemeldet starten: Windows-Anmeldung
ohne Passwort (netplwiz) oder automatische Anmeldung einrichten, sonst startet nach einem Stromausfall nichts.

## 5. Bildrechner auf demselben Laptop

Einrichten mit einem Befehl: `powershell -ExecutionPolicy Bypass -File deploy\windows\bildrechner-einrichten.ps1`
([Anleitung](laptop-bildrechner.md)). Läuft der Bildrechner auf demselben Laptop, in `.env`:

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://127.0.0.1:1234
```

Solange auch der Pi den Bildrechner nutzt, bleibt `--listen-ip 0.0.0.0` samt Firewall-Regel. Nach dem Umzug reicht
`--listen-ip 127.0.0.1`, dann entfällt die Firewall-Regel für Port 1234.
Achtung: Der Bildrechner braucht rund 5,5 GB RAM, Windows 2–3 GB, PaperclipLite etwa 0,2 GB. Mit 8 GB wird
das knapp. Andere Programme (Browser mit vielen Tabs) beim Bildermachen schließen. Ollama zusätzlich auf
dem Laptop passt nicht mehr.

## Was unter Windows fehlt oder Zusatzprogramme braucht

| Funktion | Unter Windows | Was tun |
| --- | --- | --- |
| Code ausführen (`run_code`) | geht nicht | braucht Linux-Sandbox (bubblewrap), das Werkzeug wird automatisch ausgeblendet |
| Code prüfen (`check_code`) | Python und JSON gehen | andere Sprachen nur, wenn der Compiler im PATH ist |
| Shell-Freigaben (`PCL_ALLOW_SHELL`) | laufen in `cmd.exe` | Linux-Befehle (`ls`, `grep`) gehen dort nicht |
| HTML → PDF (`make_document` mit html) | meist nicht | WeasyPrint braucht GTK unter Windows; PDF aus Text/Markdown geht trotzdem |
| OCR für gescannte PDFs | nur mit Zusatz | Tesseract und Poppler für Windows installieren und in den PATH legen |
| Video (`video_edit`) | nur mit Zusatz | `winget install Gyan.FFmpeg` |
| Sprache (`speak`) | nur mit Zusatz | `venv\Scripts\pip install edge-tts` (braucht Internet); Piper/espeak optional |
| Echter Browser (`browse_page`) | optional | `venv\Scripts\pip install playwright` und `venv\Scripts\python -m playwright install chromium` |
| Claude/Codex über CLI | wenn installiert | `claude` bzw. `codex` unter Windows installieren und anmelden, `PCL_ALLOW_CLI=1` |
| Ollama | geht | Ollama für Windows installieren; auf 8 GB RAM nur kleine Modelle |
