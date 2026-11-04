"""Werkstatt: Agenten arbeiten mit echten Befehlen im Projektordner und ruesten Programme nach.

Stufen (je Agent):
  1 vorsichtig: jeder Befehl wird als Antrag gestellt
  2 normal:     Befehle im Projekt laufen sofort; Installationen, Loeschen, Pfade ausserhalb des Projekts -> Antrag
  3 frei:       alles laeuft sofort (nur mit PCL_WERKSTATT_FREI=1, sonst wie Stufe 2)

Antrag = Mitarbeiter -> CEO prueft -> Besitzer bestaetigt (Web oder Telegram) -> Server fuehrt den Befehl aus.
Die Einteilung unten ist eine Vorsortierung nach Mustern, KEINE Abschottung: Stufe 2 faengt die ueblichen
Installations- und Loeschbefehle ab, ein Agent mit boeser Absicht koennte sie umgehen. Deshalb ist die Werkstatt
standardmaessig aus und nur der Besitzer kann sie je Agent einschalten.
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

IS_WIN = os.name == "nt"


def cmd_timeout():      # Befehl eines Agenten (.env wird erst nach dem Import gelesen, deshalb als Funktion)
    return int(os.environ.get("PCL_BEFEHL_TIMEOUT", "600"))


def install_timeout():  # freigegebene Nachruestung
    return int(os.environ.get("PCL_NACHRUEST_TIMEOUT", "1800"))

OUT_CHARS = 6000
_lock = threading.Lock()  # immer nur ein Werkstatt-Befehl gleichzeitig (kleiner Laptop/Pi)


def enabled():
    return os.environ.get("PCL_ALLOW_WERKSTATT", "0") == "1"


def free_allowed():
    return os.environ.get("PCL_WERKSTATT_FREI", "0") == "1"


def level(raw):
    """Stufe aus dem gespeicherten Wert; Stufe 3 nur, wenn der Besitzer sie in der .env erlaubt."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 2
    n = min(3, max(1, n))
    return 2 if n == 3 and not free_allowed() else n


INSTALL = [
    r"\b(npm|pnpm|yarn|bun)\s+(i|install|add|ci|update|upgrade|up|link|dlx|x)\b",
    r"\b(npm|pnpm|yarn)\s+(-g|--global)\b", r"\bnpm\s+exec\b",
    r"\bpip3?\s+(install|download|uninstall)\b", r"-m\s+pip\s+(install|download|uninstall)\b", r"\bpipx\b",
    r"\buv\s+(pip|add|tool|sync|python\s+install)\b", r"\bconda\s+(install|create|update)\b", r"\bpoetry\s+(add|install)\b",
    r"\b(winget|choco|chocolatey|scoop|apt|apt-get|aptitude|dpkg|dnf|yum|zypper|pacman|brew|snap|flatpak|port|pkg|rpm|msiexec)\b",
    r"\bsudo\b", r"\bsu\s", r"\bdoas\b", r"\brunas\b", r"Start-Process[^\n]*-Verb\s+RunAs",
    r"\bcargo\s+(install|binstall)\b", r"\bgo\s+install\b", r"\bgem\s+install\b", r"\bcomposer\s+(require|global)\b",
    r"\b(Install-Module|Install-Package|Install-Script|Add-AppxPackage|Enable-WindowsOptionalFeature)\b",
    r"\b(rustup|nvm|volta|fnm)\b", r"\bnpx\s+(-y|--yes)\b",
    r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|]*\|\s*(sh|bash|zsh|python3?|iex|Invoke-Expression)\b",
    r"\b(iex|Invoke-Expression)\b",
    r"\bplaywright\s+install\b", r"\bremotion\s+browser\s+ensure\b",
]
DANGER = [
    r"(^|[\s;&|(])(rm|rmdir|rd|del|erase|shred|unlink)\s", r"\bRemove-Item\b", r"\b(ri|rmdir)\s+-",
    r"\bformat(\.com)?\s+[a-z]:", r"\b(mkfs|fdisk|diskpart|dd)\b", r"\b(shutdown|reboot|halt|poweroff|Stop-Computer|Restart-Computer)\b",
    r"\breg(\.exe)?\s+(add|delete|import)\b", r"\b(Set-ItemProperty|New-ItemProperty)\b[^\n]*HK(LM|CU)",
    r"\b(schtasks|crontab|systemctl|service|sc(\.exe)?\s+(create|config|delete)|launchctl)\b",
    r"\bgit\s+(push|remote\s+(add|set-url))\b", r"\bchmod\s+[0-7]*[67][0-7]*\s+/", r"\bchown\b",
    r"\b(setx|Set-ExecutionPolicy|netsh|New-NetFirewallRule|icacls|takeown)\b",
    r"\b(Stop-Process|taskkill|kill|pkill|killall)\b",
]
SECRET = [r"(^|[\\/\s\"'=])\.env\b", r"\btokens[\\/]", r"\bAPP_TOKEN\b", r"_API_KEY\b", r"\bpcl\.db\b", r"\.secret\b",
          r"\b(printenv|Get-ChildItem\s+env:|gci\s+env:|ls\s+env:)", r"(^|[\s;&|])(env|set)\s*($|[;&|])",
          r"\$env:\w*(KEY|TOKEN|SECRET|PASSWORD)", r"\.ssh\b", r"\.claude[\\/]", r"\.codex[\\/]", r"\bid_rsa\b"]
_ABS = re.compile(r"""(?:^|(?<=[\s"'=(:,;|&<>]))(~[\\/]|~(?=\s|$)|[A-Za-z]:[\\/]|\\\\|/(?!dev/null\b)[A-Za-z_.][\w.\-]+|%\w+%|\$HOME\b|\$\{HOME|\$env:(?!npm_)\w+)""")


def classify(cmd, root):
    """-> (art, grund): art 'frei' | 'antrag' | 'verboten'."""
    c = str(cmd or "")
    if not c.strip():
        return "verboten", "leerer Befehl"
    for p in SECRET:
        if re.search(p, c, re.I):
            return "verboten", "Zugangsdaten (.env, Tokens, Umgebungsvariablen, Anmeldedaten) sind für Agenten gesperrt"
    for p in INSTALL:
        if re.search(p, c, re.I):
            return "antrag", "Installation/Nachrüsten"
    for p in DANGER:
        if re.search(p, c, re.I):
            return "antrag", "Löschen oder Eingriff ins System"
    if re.search(r"(^|[\\/\s\"'=])\.\.([\\/]|$|\s)", c):
        return "antrag", "Pfad außerhalb des Projektordners (..)"
    rs = str(Path(root).resolve())
    for m in _ABS.finditer(c):
        rest = c[m.start():].split()[0].strip("\"'")
        if rest.lower().startswith(rs.lower()):
            continue
        return "antrag", "Pfad außerhalb des Projektordners"
    return "frei", ""


def clean_env(root=None):
    """Umgebung ohne Zugangsdaten; npx installiert nichts heimlich nach."""
    env = {k: v for k, v in os.environ.items()
           if not (re.search(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", k, re.I) or k in ("TELEGRAM_CHAT_ID",))}
    env["npm_config_yes"] = "false"
    env["PCL_WERKSTATT"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if root:
        nb = Path(root) / "node_modules" / ".bin"
        env["PATH"] = str(nb) + os.pathsep + env.get("PATH", "")
    return env


def shell_argv(cmd, shell=None):
    sh = (shell or "").lower().strip()
    if not sh:
        sh = "powershell" if IS_WIN else "bash"
    if sh in ("powershell", "pwsh", "ps"):
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        return [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd]
    if sh == "cmd":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmd]
    exe = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
    return [exe, "-c", cmd]


def run(cmd, root, shell=None, timeout=None):
    """Fuehrt einen Befehl im Projektordner aus. -> (exitcode, ausgabe)"""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    tmo = timeout or cmd_timeout()
    kw = {}
    if IS_WIN:
        kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kw["start_new_session"] = True
    with _lock:
        t0 = time.time()
        try:
            p = subprocess.Popen(shell_argv(cmd, shell), cwd=str(root), env=clean_env(root), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
        except FileNotFoundError as e:
            return 127, f"Shell nicht gefunden: {e}"
        try:
            out, _ = p.communicate(timeout=tmo)
        except subprocess.TimeoutExpired:
            _kill(p)
            out = (p.communicate()[0] or "") if p.stdout else ""
            return 124, clip(out) + f"\n(Zeitlimit {tmo} s erreicht - abgebrochen)"
        return p.returncode, clip(out) + f"\n(fertig in {time.time() - t0:.0f} s)"


def _kill(p):
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, 9)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def clip(s, n=OUT_CHARS):
    s = s or ""
    return s if len(s) <= n else s[:n // 3] + f"\n... ({len(s) - n} Zeichen gekuerzt) ...\n" + s[-(2 * n // 3):]


def note_installed(root, cmd, wozu, who, code):
    """Firmenwissen: was schon nachgeruestet ist, damit es niemand doppelt beantragt."""
    f = Path(root) / "wissen" / "werkzeuge.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    head = "" if f.exists() else ("# Nachgeruestete Werkzeuge\n\nVom Besitzer freigegeben und installiert. "
                                   "Vor einem neuen Antrag hier nachsehen.\n\n")
    line = (f"- {time.strftime('%d.%m.%Y')}: `{cmd}`" + (f" fuer {wozu}" if wozu else "") + f" (beantragt von {who}, "
            + ("ok" if code == 0 else f"Fehler, Exit {code}") + ")\n")
    with f.open("a", encoding="utf-8") as fh:
        fh.write(head + line)


def platform_hint():
    if IS_WIN:
        return ("Windows: Befehle laufen in PowerShell (oder \"shell\": \"cmd\"). Programme installierst du mit winget "
                "(z. B. winget install --id OpenJS.NodeJS.LTS -e --scope user --accept-package-agreements --accept-source-agreements), "
                "Pakete mit npm/pip.")
    return "Linux: Befehle laufen in bash. Programme ueber apt (braucht sudo), Pakete mit npm/pip (pip am besten in einem venv im Projekt)."


def doc(lvl, native=""):
    lv = {1: "1 (vorsichtig): JEDER Befehl ist ein Antrag",
          2: "2 (normal): Befehle im Projektordner laufen sofort; Installationen, Loeschen und Pfade ausserhalb des Projekts sind Antraege",
          3: "3 (frei): alles laeuft sofort, der Besitzer bekommt nur eine Meldung"}[lvl]
    return ("\nWERKSTATT (du arbeitest wie an einem echten Rechner, Stufe " + lv + "):\n"
            + (native + "\n" if native else "")
            + "- befehl: {\"tool\": \"befehl\", \"befehl\": \"npx remotion render src/index.ts Main output/film.mp4\", \"shell\": \"\"} "
              f"fuehrt einen Befehl im Projektordner aus (Zeitlimit {cmd_timeout()} s) und liefert die Ausgabe. {platform_hint()}\n"
            + "- nachruesten: {\"tool\": \"nachruesten\", \"befehl\": \"npm install remotion @remotion/cli\", \"wozu\": \"Vorspann animieren\", "
              "\"groesse\": \"ca. 300 MB\"} beantragt ein Programm oder Paket, das dir fehlt. Der Antrag geht an den CEO, der CEO legt ihn dem "
              "Besitzer vor, nach dessen Ja installiert der Server genau diesen Befehl und du bekommst die Aufgabe mit dem Ergebnis zurueck. "
              "Beantrage nur, was die Arbeit wirklich besser macht, schau vorher in wissen/werkzeuge.md und pruefe mit befehl (z. B. node --version), "
              "ob es schon da ist. Stell einen Antrag nur einmal, arbeite am Rest weiter und schreib im result, worauf du wartest.\n"
            + "- Zugangsdaten (.env, Tokens, Umgebungsvariablen) sind gesperrt. Was du installierst, gilt fuer alle Projekte auf diesem Rechner.")


def ceo_prompt(req_name, req_role, cmd, wozu, groesse, project):
    return (f"Ein Mitarbeiter deiner Firma '{project}' beantragt, ein Programm/Paket auf dem Rechner nachzuruesten.\n"
            f"Mitarbeiter: {req_name} ({req_role or 'ohne Rolle'})\nBefehl: {cmd}\nWofuer: {wozu or '(nicht angegeben)'}\n"
            f"Groesse: {groesse or '(nicht angegeben)'}\n\nPruefe als Chef: Braucht die Firma das wirklich fuer bessere Arbeit, ist der Befehl "
            "sinnvoll und aus einer serioesen Quelle (offizielle Paketquellen npm/PyPI/winget/apt), gibt es das schon? Du entscheidest NICHT "
            "endgueltig, der Besitzer bestaetigt danach. Lehne nur ab, was offensichtlich unnoetig, doppelt oder gefaehrlich ist.\n"
            "Antworte NUR mit JSON: {\"weiterleiten\": true oder false, \"empfehlung\": \"ein bis zwei Saetze an den Besitzer\"}")
