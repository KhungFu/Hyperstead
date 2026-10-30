# PaperclipLite unter Windows 10/11

PaperclipLite läuft auch unter Windows. Oberfläche, Agenten, alle API-Anbieter, Telegram, Suche, Bilder,
PDF/Word, Zeitpläne und Verbindungen funktionieren wie auf dem Pi. Ein paar Linux-Werkzeuge fehlen
(Liste unten). Getestet ist die Windows-Variante bisher nur in der Entwicklungsumgebung (Linux), noch nicht auf
einem echten Windows-Rechner.

## Pi und Laptop: beides oder umziehen?

- **Beides parallel:** zwei getrennte Installationen mit eigenen Firmen, Aufträgen und Daten. Den
  `TELEGRAM_BOT_TOKEN` nur auf **einer** Maschine eintragen, sonst stören sich die beiden Bots (Telegram erlaubt
  nur einen Abholer je Bot).
- **Umziehen:** auf dem Pi `sudo systemctl stop paperclip-lite`, dann `data.db`, den Ordner `workspace/` und
  `.env` auf den Laptop in den PaperclipLite-Ordner kopieren (z. B. per `scp` oder USB-Stick). Danach den Dienst
  auf dem Pi abschalten: `sudo systemctl disable paperclip-lite`.

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

Autostart: Win+R, `shell:startup`, Verknüpfung zu `deploy\windows\paperclip-start.bat` hineinlegen.

## 5. Bildrechner auf demselben Laptop

Wenn der Bildrechner ([Anleitung](laptop-bildrechner.md)) auf demselben Laptop läuft, in `.env`:

```
IMAGE_PROVIDER=sdcpp
SDCPP_URL=http://127.0.0.1:1234
```

Dann reicht in `bildrechner-start.bat` `--listen-ip 127.0.0.1` und die Firewall-Regel für Port 1234 entfällt.
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
