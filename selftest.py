#!/usr/bin/env python3
"""PaperclipLite Selbsttest: prueft auf dem echten Rechner (Pi), ob alles funktioniert, was die Agenten brauchen.

    ./venv/bin/python selftest.py            # alles pruefen
    ./venv/bin/python selftest.py web        # nur Gruppe: web | browser | run | llm | telegram | media | ocr | code

Jede Zeile: OK / FEHLT (optional) / FEHLER, bei Problemen mit konkretem Hinweis. Es werden keine Keys ausgegeben.
Die LLM-Tests senden je Anbieter eine winzige Anfrage (kostet praktisch nichts). Bilder werden nur im Temp-Ordner erzeugt.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import requests  # noqa: E402

import agent_tools as T  # noqa: E402
import app as A  # noqa: E402  (laedt .env)

RES = {"ok": 0, "warn": 0, "fail": 0}


def line(state, name, detail=""):
    sym = {"ok": "\033[32mOK     \033[0m", "warn": "\033[33mFEHLT  \033[0m", "fail": "\033[31mFEHLER \033[0m"}[state]
    RES[state] += 1
    print(f"  {sym} {name:<34} {detail}")


def check(name, fn, optional=False, hint=""):
    t0 = time.time()
    try:
        out = fn()
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:220].replace("\n", " ")
        line("warn" if optional else "fail", name, msg + (f"  -> {hint}" if hint else ""))
        return None
    line("ok", name, f"{(out or '')}  ({time.time() - t0:.1f} s)".strip())
    return out


WIN = os.name == "nt"
if WIN:
    os.system("")  # schaltet Farbcodes in cmd.exe ein (sonst erscheint "←[32m")
# Installationshinweis je System: (Linux/Pi, Windows)
WIN_HINTS = {
    "ffmpeg": "winget install Gyan.FFmpeg (danach neues Fenster)",
    "tesseract-ocr tesseract-ocr-deu": "winget install UB-Mannheim.TesseractOCR (Deutsch bei der Installation anhaken), Ordner in den PATH",
    "poppler-utils": "Poppler fuer Windows (github.com/oschwartz10612/poppler-windows), Ordner Library\\bin in den PATH",
}


def fix(linux, windows):
    return windows if WIN else linux


def need(prog, apt):
    if not shutil.which(prog):
        raise RuntimeError(f"'{prog}' nicht installiert: " + fix(f"sudo apt install {apt}", WIN_HINTS.get(apt, f"{prog} installieren und in den PATH")))
    return shutil.which(prog)


def group_web():
    print("\nInternet-Werkzeuge")
    check("Websuche", lambda: (lambda r: r.splitlines()[0][:80] if r.startswith("1.") else (_ for _ in ()).throw(RuntimeError(r)))(
        T.web_search("Raspberry Pi 4 Datenblatt", 3)),
        hint="DuckDuckGo (ohne Key) wird manchmal begrenzt: SEARXNG_URL, TAVILY_API_KEY oder BRAVE_API_KEY in .env setzen")
    check("Seite lesen", lambda: T.fetch_url("https://example.com")[:60].replace("\n", " "))
    check("Bildsuche", lambda: (lambda r: r.splitlines()[0][:80] if r.strip() and "Keine" not in r[:10] else (_ for _ in ()).throw(RuntimeError(r[:100])))(
        T.image_search("mountain lake", 3)))
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)
        prov = T._env("IMAGE_PROVIDER", "pollinations").lower()  # noqa: SLF001
        if prov in ("gemini", "openai", "openrouter"):
            def imodel():
                if prov == "openrouter":
                    model = T._model_env("IMAGE_MODEL", T.OPENROUTER_IMAGE_MODEL)  # noqa: SLF001
                    r = requests.get("https://openrouter.ai/api/v1/images/models", timeout=20,
                                     headers={"Authorization": "Bearer " + T._env("OPENROUTER_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                    if r.status_code < 400:
                        ids = {m.get("id") for m in (r.json().get("data") or [])}
                        if model not in ids:
                            raise RuntimeError(f"Modell '{model}' nicht in der Bildmodell-Liste von OpenRouter. Z. B.: "
                                               + ", ".join(sorted(i for i in ids if i)[:8]))
                elif prov == "gemini":
                    model = T._model_env("IMAGE_MODEL", T.GEMINI_IMAGE_MODEL)  # noqa: SLF001
                    r = requests.get(f"{T.GEMINI_BASE}/models/{model}", timeout=20,
                                     headers={"x-goog-api-key": T._env("GEMINI_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                else:
                    model = T._model_env("IMAGE_MODEL", "gpt-image-1")  # noqa: SLF001
                    base = T._env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")  # noqa: SLF001
                    r = requests.get(f"{base}/models/{model}", timeout=20,
                                     headers={"Authorization": "Bearer " + T._env("OPENAI_API_KEY").split(",")[0].strip()})  # noqa: SLF001
                if r.status_code >= 400:
                    raise RuntimeError(f"Modell '{model}' nicht verfuegbar (HTTP {r.status_code}): {r.text[:150]}")
                return f"{model} verfuegbar"
            check(f"Bild-Modell ({prov})", imodel, hint="IMAGE_MODEL in .env leer lassen (Standard) oder einen Namen aus der Modellliste eintragen, ohne models/ und Anfuehrungszeichen")
        if prov == "sdcpp":
            check("Bildrechner erreichbar", lambda: f"HTTP {requests.get(T._env('SDCPP_URL').rstrip('/') + '/', timeout=10).status_code}",  # noqa: SLF001
                  hint="Laptop an? sd-server gestartet? SDCPP_URL in .env = http://<IP des Laptops>:1234, Windows-Firewall fuer privates Netz erlauben")
        check(f"Bild erzeugen ({prov})", lambda: T.image_generate(root, {"prompt": "a red apple, simple illustration", "name": "test",
                                                                          "quality": "low" if prov == "openai" else ""})[:80],
              hint="Bildrechner gestartet?" if prov == "sdcpp" else "anderen IMAGE_PROVIDER mit Key waehlen, wenn dieser nicht erreichbar ist")
        ref = next(iter(sorted((root / "assets").glob("test.*"))), None) if (root / "assets").exists() else None
        pkey = prov == "pollinations" and T._env("POLLINATIONS_API_KEY").strip()  # noqa: SLF001
        if (prov in ("openai", "gemini", "openrouter", "sdcpp", "cloudflare") or pkey) and ref:
            check("Bild mit Referenzbild", lambda: T.image_generate(root, {
                "prompt": "the same apple, now cut in half, same drawing style", "refs": [f"assets/{ref.name}"],
                "path": "karten/test-ref.png", "quality": "low" if prov == "openai" else ""})[:80],
                  hint="Referenzbilder brauchen ein Bildmodell mit Bearbeiten-Funktion (gpt-image-1, gemini-2.5-flash-image, "
                       "bei Pollinations z. B. black-forest-labs/flux.2-klein-4b)")
    if T.video_enabled() and T._env("VIDEO_PROVIDER").lower() == "fal":  # noqa: SLF001
        def vkey():
            T._fal_key()  # noqa: SLF001
            return "FAL_KEY gesetzt (kein Clip erzeugt, das kostet Geld)"
        check("Video-Anbieter (fal.ai)", vkey, optional=True, hint="FAL_KEY in .env eintragen, VIDEO_PROVIDER=fal")
    elif T.video_enabled():
        def vmodel():
            key, model = T._gemini_key(), T._model_env("VIDEO_MODEL", "gemini-omni-1.1-flash")  # noqa: SLF001
            r = requests.get(f"{T.GEMINI_BASE}/models/{model}", headers={"x-goog-api-key": key}, timeout=20)
            if r.status_code >= 400:
                raise RuntimeError(f"Modell '{model}' nicht verfuegbar (HTTP {r.status_code})")
            return f"{model} verfuegbar (kein Clip erzeugt, das kostet Geld)"
        check("Video-Modell (Gemini)", vmodel, optional=True, hint="GEMINI_API_KEY mit Abrechnung? VIDEO_MODEL pruefen")
    else:
        line("warn", "Videoerzeugung", "aus (optional: VIDEO_PROVIDER=gemini oder fal in .env)")
    check("SSRF-Schutz blockt lokale Adressen", lambda: "ok" if _blocked() else (_ for _ in ()).throw(RuntimeError("nicht blockiert!")))


def _blocked():
    try:
        T.fetch_url("http://127.0.0.1:8787/")
    except T.ToolError:
        return True
    return False


def group_llm():
    print("\nKI-Anbieter (je eine Mini-Anfrage)")
    any_real = False
    for pid, cfg in A.PROVIDERS.items():
        if pid in ("mock", "cli"):
            continue
        if not A.provider_configured(pid):
            if cfg.get("kind") == "cli":
                why = "PCL_ALLOW_CLI=1 in .env fehlt" if not A.ALLOW_CLI else f"'{cfg['bin']}' nicht installiert (siehe README: CLI-Anbieter)"
            else:
                why = "kein Key" if pid != "ollama" else f"nicht erreichbar ({cfg['url']}) - laeuft 'ollama serve'?"
            line("warn", cfg["label"], why)
            continue
        any_real = True

        def run(pid=pid):
            txt, tok = A.call_llm({"provider": pid, "model": "", "name": "Selbsttest", "id": 0, "perms": "{}"},
                                  [{"role": "user", "content": "Antworte nur mit dem Wort: bereit"}])
            return f"Antwort: {txt.strip()[:40]!r}"
        check(f"{cfg['label']} ({cfg['model'] or 'Standard'})", run,
              hint="CLI-Programm angemeldet? Einmal von Hand testen: echo hallo | " + (cfg.get("cmd") or "") if cfg.get("kind") == "cli" else "")
        if pid == "ollama":
            def olist():
                r = A.list_models("ollama", force=True)
                if r.get("error"):
                    raise RuntimeError(r["error"])
                return f"{len(r['models'])} Modelle: " + ", ".join(r["models"][:4])
            check("Ollama: Modellliste", olist, hint="Modell laden: ollama pull qwen2.5:3b")
    if not any_real:
        line("fail", "kein echter KI-Anbieter", "in .env mindestens einen Key setzen oder Ollama starten")


def group_telegram():
    print("\nTelegram")
    if not A.TG_TOKEN:
        line("warn", "Bot-Token", "TELEGRAM_BOT_TOKEN nicht gesetzt (optional)")
        return

    def me():
        r = requests.get(f"{A.TG_API}/bot{A.TG_TOKEN}/getMe", timeout=15).json()
        if not r.get("ok"):
            raise RuntimeError("Token ungueltig (@BotFather pruefen)")
        return "Bot @" + r["result"].get("username", "?")
    check("Bot erreichbar", me)
    if not A.TG_CHATS:
        line("warn", "Chat-ID", "TELEGRAM_CHAT_ID fehlt: dem Bot /start schreiben, er nennt sie")
        return
    cid = sorted(A.TG_CHATS)[0]

    def send():
        r = requests.post(f"{A.TG_API}/bot{A.TG_TOKEN}/sendMessage", json={"chat_id": cid, "text": "PaperclipLite Selbsttest: Telegram funktioniert."}, timeout=15).json()
        if not r.get("ok"):
            raise RuntimeError(r.get("description", "Senden fehlgeschlagen"))
        return "Testnachricht gesendet"
    check("Nachricht an deine Chat-ID", send)


def group_media():
    print("\nVideo, Sprache, Dokumente")
    check("ffmpeg", lambda: need("ffmpeg", "ffmpeg") and "ok", optional=WIN)
    check("ffprobe", lambda: need("ffprobe", "ffmpeg") and "ok", optional=WIN)
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)

        def tts():
            out = T.speak(root, "Hallo, das ist ein Test der Sprachausgabe.", "de", "t")
            eng = "Piper" if T._piper()[0] else "espeak-ng"  # noqa: SLF001
            return f"{eng}: {out[:60]}"
        check("Sprachausgabe", tts, optional=WIN, hint=fix("sudo apt install espeak-ng; besser: ./install.sh --piper",
                                             "venv\\Scripts\\pip install edge-tts und TTS_ENGINE=edge in .env (Online-Stimme)"))
        check("Piper (gute Stimme)", lambda: (lambda x: "Modell " + Path(x[1]).name if x[0] else (_ for _ in ()).throw(RuntimeError("nicht eingerichtet")))(T._piper()),  # noqa: SLF001
              optional=True, hint=fix("./install.sh --piper", "optional, unter Windows von Hand (siehe docs/windows.md)"))

        def doc():
            r = T.make_document(root, {"title": "Test", "format": "pdf", "content": "# Kapitel\n\nUmlaute: äöüß. Türkisch: ğışçö."})
            if "WARNUNG" in r:
                raise RuntimeError(r[r.index("WARNUNG"):][:160])
            return r[:70]
        check("PDF erzeugen (Umlaute, Tuerkisch)", doc, hint=fix("sudo apt install fonts-dejavu-core", "Schrift Arial/Georgia in C:\\Windows\\Fonts fehlt?"))


def group_ocr():
    print("\nOCR (gescannte PDFs und Bilder)")
    check("tesseract", lambda: need("tesseract", "tesseract-ocr tesseract-ocr-deu") and "Sprachen: " + (T._tess_lang() or "keine"),  # noqa: SLF001
          optional=WIN)
    check("pdftoppm", lambda: need("pdftoppm", "poppler-utils") and "ok", optional=WIN)
    if shutil.which("tesseract") and "deu" not in T._tess_lang():  # noqa: SLF001
        line("warn", "Deutsch fuer OCR", fix("sudo apt install tesseract-ocr-deu", "Tesseract neu installieren und Deutsch anhaken")
             + " (Umlaute werden sonst schlechter erkannt)")


CODE_SAMPLES = {  # Datei -> fehlerfreies Mini-Programm (wird nur geprueft, nicht ausgefuehrt)
    "t.py": "print('ok')\n", "t.js": "console.log('ok');\n", "t.ts": "const x: number = 1;\n",
    "Main.java": "public class Main { public static void main(String[] a) { System.out.println(1); } }\n",
    "t.rs": "fn main() { println!(\"ok\"); }\n", "t.go": "package main\n\nfunc main() {}\n",
    "t.c": "int main(void) { return 0; }\n", "t.cpp": "int main() { return 0; }\n", "t.sh": "echo ok\n",
    "t.rb": "puts 1\n", "t.php": "<?php echo 1;\n", "t.lua": "print(1)\n",
}


def group_code():
    print("\nProgrammieren (Recht 'Programmieren': Code pruefen/kompilieren)")
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        for fn, src in CODE_SAMPLES.items():
            (Path(td) / fn).write_text(src, encoding="utf-8")
            def run(fn=fn):
                r = T.check_code(td, fn)
                if "nicht installiert" in r:
                    raise RuntimeError(r.split(".")[0] + fix("  -> ./install.sh --code", "  -> optional, Compiler installieren und in den PATH"))
                if "FEHLER" in r:
                    raise RuntimeError(r[:200])
                return "ok"
            ext = Path(fn).suffix.lower()
            lang = "Python" if ext == ".py" else T.CODE_CHECKERS[ext][0]
            check(f"{lang} ({fn})", run, optional=True)


def group_browser():
    print("\nEchter Browser (browse_page)")
    if not T.browser_enabled():
        line("warn", "Browser", "aus (optional: " + fix("./install.sh --browser", "venv\\Scripts\\pip install playwright; venv\\Scripts\\python -m playwright install chromium") + ")")
        return
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        check("Seite im Browser oeffnen", lambda: (lambda r: f"{len(r[1])} Screenshot, " + r[0].splitlines()[1][:50])(
            T.browse_page(td, "https://example.com", screenshot=True)),
            hint="Chromium fehlt? ./venv/bin/python -m playwright install chromium (oder PCL_BROWSER_PATH)")

    def blocked():
        try:
            T.browse_page(td, "http://127.0.0.1:8787/")
        except T.ToolError:
            return "ok"
        raise RuntimeError("nicht blockiert!")
    check("Browser blockt lokale Adressen", blocked)


def group_run():
    print("\nCode ausfuehren (Recht 'Code ausfuehren', abgeschottet)")
    if not T.run_enabled():
        line("warn", "Code ausfuehren", fix("aus (bubblewrap fehlt: ./install.sh --run, oder PCL_ALLOW_RUN=0)",
                                            "gibt es unter Windows nicht (braucht Linux), PCL_ALLOW_RUN=0 blendet es aus"))
        return
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        def py():
            r = T.run_code(td, code="print(6*7)", lang="python")
            if "Exit-Code 0" not in r or "42" not in r:
                raise RuntimeError(r[:200] + "  -> Unprivilegierte User-Namespaces aktiv? (sysctl kernel.unprivileged_userns_clone=1)")
            return "ok"
        check("Python in der Sandbox", py)

        def nonet():
            r = T.run_code(td, code="import socket\ntry:\n socket.create_connection(('1.1.1.1',53),3); print('NETZ')\n"
                                    "except OSError: print('zu')", lang="python")
            if "zu" not in r:
                raise RuntimeError("Sandbox hat Internet! " + r[:120])
            return "kein Internet in der Sandbox"
        check("Sandbox ohne Netz", nonet)


GROUPS = {"web": group_web, "browser": group_browser, "run": group_run, "llm": group_llm, "telegram": group_telegram, "media": group_media, "ocr": group_ocr, "code": group_code}

if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in GROUPS] or list(GROUPS)
    print("PaperclipLite Selbsttest")
    for g in wanted:
        GROUPS[g]()
    print(f"\nErgebnis: {RES['ok']} OK, {RES['warn']} fehlt/optional, {RES['fail']} Fehler")
    sys.exit(1 if RES["fail"] else 0)
