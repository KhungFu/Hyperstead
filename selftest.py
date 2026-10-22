#!/usr/bin/env python3
"""PaperclipLite Selbsttest: prueft auf dem echten Rechner (Pi), ob alles funktioniert, was die Agenten brauchen.

    ./venv/bin/python selftest.py            # alles pruefen
    ./venv/bin/python selftest.py web        # nur Gruppe: web | llm | telegram | media | ocr | code

Jede Zeile: OK / FEHLT (optional) / FEHLER, bei Problemen mit konkretem Hinweis. Es werden keine Keys ausgegeben.
Die LLM-Tests senden je Anbieter eine winzige Anfrage (kostet praktisch nichts). Bilder werden nur im Temp-Ordner erzeugt.
"""
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


def need(prog, apt):
    if not shutil.which(prog):
        raise RuntimeError(f"'{prog}' nicht installiert: sudo apt install {apt}")
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
        check(f"Bild erzeugen ({T._env('IMAGE_PROVIDER', 'pollinations')})", lambda: T.image_generate(root, "a red apple, simple illustration", "test")[:80],
              hint="IMAGE_PROVIDER=gemini oder openai mit Key waehlen, wenn Pollinations nicht erreichbar ist")
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
    check("ffmpeg", lambda: need("ffmpeg", "ffmpeg") and "ok")
    check("ffprobe", lambda: need("ffprobe", "ffmpeg") and "ok")
    with tempfile.TemporaryDirectory(prefix="pcl-selftest-") as td:
        root = Path(td)

        def tts():
            out = T.speak(root, "Hallo, das ist ein Test der Sprachausgabe.", "de", "t")
            eng = "Piper" if T._piper()[0] else "espeak-ng"  # noqa: SLF001
            return f"{eng}: {out[:60]}"
        check("Sprachausgabe", tts, hint="sudo apt install espeak-ng; besser: ./install.sh --piper")
        check("Piper (gute Stimme)", lambda: (lambda x: "Modell " + Path(x[1]).name if x[0] else (_ for _ in ()).throw(RuntimeError("nicht eingerichtet")))(T._piper()),  # noqa: SLF001
              optional=True, hint="./install.sh --piper")

        def doc():
            r = T.make_document(root, {"title": "Test", "format": "pdf", "content": "# Kapitel\n\nUmlaute: äöüß. Türkisch: ğışçö."})
            if "WARNUNG" in r:
                raise RuntimeError(r[r.index("WARNUNG"):][:160])
            return r[:70]
        check("PDF erzeugen (Umlaute, Tuerkisch)", doc, hint="sudo apt install fonts-dejavu-core")


def group_ocr():
    print("\nOCR (gescannte PDFs und Bilder)")
    check("tesseract", lambda: need("tesseract", "tesseract-ocr tesseract-ocr-deu") and "Sprachen: " + (T._tess_lang() or "keine"))  # noqa: SLF001
    check("pdftoppm", lambda: need("pdftoppm", "poppler-utils") and "ok")
    if shutil.which("tesseract") and "deu" not in T._tess_lang():  # noqa: SLF001
        line("warn", "Deutsch fuer OCR", "sudo apt install tesseract-ocr-deu (Umlaute werden sonst schlechter erkannt)")


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
            (Path(td) / fn).write_text(src)
            def run(fn=fn):
                r = T.check_code(td, fn)
                if "nicht installiert" in r:
                    raise RuntimeError(r.split(".")[0] + "  -> ./install.sh --code")
                if "FEHLER" in r:
                    raise RuntimeError(r[:200])
                return "ok"
            ext = Path(fn).suffix.lower()
            lang = "Python" if ext == ".py" else T.CODE_CHECKERS[ext][0]
            check(f"{lang} ({fn})", run, optional=True)


GROUPS = {"web": group_web, "llm": group_llm, "telegram": group_telegram, "media": group_media, "ocr": group_ocr, "code": group_code}

if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in GROUPS] or list(GROUPS)
    print("PaperclipLite Selbsttest")
    for g in wanted:
        GROUPS[g]()
    print(f"\nErgebnis: {RES['ok']} OK, {RES['warn']} fehlt/optional, {RES['fail']} Fehler")
    sys.exit(1 if RES["fail"] else 0)
