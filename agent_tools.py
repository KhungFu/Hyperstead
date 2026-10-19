"""
Werkzeuge der Agenten: Websuche, Webseiten lesen, Bilder suchen/laden/erzeugen, Projektdateien lesen.

Eigenstaendiges Modul (keine Imports aus app.py). Alle Funktionen werfen nie nach aussen:
run_tool() liefert immer Text, Fehler beginnen mit "FEHLER:", damit das Modell sie lesen und reagieren kann.
Konfiguration nur ueber Umgebungsvariablen (zur Laufzeit gelesen), siehe .env.example.

Sicherheit:
- fetch_url/image_save duerfen nur oeffentliche Adressen laden (keine localhost-, LAN-, Tailscale-, Metadaten-IPs),
  Weiterleitungen werden Schritt fuer Schritt neu geprueft. (Restrisiko: DNS-Rebinding zwischen Pruefung und Abruf.)
- Alles Geladene ist UNVERTRAUENSWUERDIGE Daten. Die Rechte der Agenten bleiben serverseitig in app.py geprueft.
- Dateien nur innerhalb des Projektordners workspace/<projekt-id>/.
"""
import base64
import ipaddress
import json
import os
import re
import socket
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests

UA = "Mozilla/5.0 (compatible; PaperclipLite/1.0; self-hosted agent team)"
MAX_PAGE_BYTES = 2_000_000
MAX_IMAGE_BYTES = 8_000_000
PAGE_CHARS = 7000        # Text pro Seite, der ans Modell geht
READ_CHARS = 12000       # Text pro gelesener Projektdatei


class ToolError(Exception):
    pass


def _env(k, d=""):
    return os.environ.get(k, d).strip()


def enabled():
    """Globaler Schalter (PCL_ALLOW_WEB=0 sperrt alle Internet-Werkzeuge)."""
    return _env("PCL_ALLOW_WEB", "1") != "0"


# --------------------------------------------------------------------- Beschreibung fuers Modell
TOOLS = {
    "web_search": ("web", '{"tool": "web_search", "query": "Suchbegriff"}  Websuche: aktuelle Infos, Gesetze, Preise, Wettbewerb, Quellen'),
    "fetch_url": ("web", '{"tool": "fetch_url", "url": "https://..."}  Webseite als Text lesen (z.B. Treffer der Suche genauer ansehen)'),
    "image_search": ("images", '{"tool": "image_search", "query": "mountain lake sunrise"}  frei nutzbare Fotos suchen (Lizenz/Urheber werden mitgeliefert)'),
    "image_save": ("images", '{"tool": "image_save", "url": "https://...jpg", "name": "hero"}  Bild in assets/ des Projekts speichern'),
    "image_generate": ("images", '{"tool": "image_generate", "prompt": "detaillierte Bildbeschreibung", "name": "logo"}  Bild per KI erzeugen und in assets/ speichern'),
    "list_files": ("read_files", '{"tool": "list_files", "path": ""}  Dateien im Projektordner auflisten'),
    "read_file": ("read_files", '{"tool": "read_file", "path": "index.html"}  Textdatei aus dem Projektordner lesen'),
}


def available(perms):
    """Namen der Werkzeuge, die dieser Agent nutzen darf."""
    if not enabled():
        return []
    return [n for n, (right, _) in TOOLS.items() if perms.get(right)]


def describe(names):
    return "\n".join("  " + TOOLS[n][1] for n in names)


# ------------------------------------------------------------------------- Sicherer Abruf
def check_public(host):
    """Wirft ToolError, wenn der Host nicht auf eine oeffentliche Adresse zeigt."""
    if not host:
        raise ToolError("Ungueltige Adresse")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise ToolError(f"Host '{host}' nicht auffindbar")
    for i in infos:
        ip = ipaddress.ip_address(i[4][0].split("%")[0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise ToolError("Zugriff auf lokale/private Adressen ist gesperrt")


def safe_get(url, max_bytes, hops=5):
    """GET mit Pruefung jeder Weiterleitung. Gibt (response, bytes, abgeschnitten) zurueck."""
    for _ in range(hops):
        u = urlparse(url)
        if u.scheme not in ("http", "https"):
            raise ToolError("Nur http(s)-Adressen sind erlaubt")
        check_public(u.hostname)
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=(6, 20),
                         stream=True, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            url = urljoin(url, r.headers["Location"])
            r.close()
            continue
        buf, cut = bytearray(), False
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > max_bytes:
                cut = True
                break
        r.close()
        if r.status_code >= 400:
            raise ToolError(f"HTTP {r.status_code} von {urlparse(url).netloc}")
        return r, bytes(buf[:max_bytes]), cut
    raise ToolError("Zu viele Weiterleitungen")


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "template"}
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.title, self._in_title = [], 0, "", False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BREAK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in self.BREAK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self.out.append(data)


def html_to_text(html):
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        pass
    text = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return p.title.strip(), text


def _clip(text, n):
    return text if len(text) <= n else text[:n] + f"\n[... gekuerzt, {len(text) - n} Zeichen weggelassen]"


# ------------------------------------------------------------------------------ Werkzeuge
def web_search(query, n=6):
    query = str(query or "").strip()[:300]
    if not query:
        raise ToolError("query fehlt")
    n = min(max(int(n or 6), 1), 10)
    rows = []  # (titel, url, text)
    if _env("SEARXNG_URL"):
        r = requests.get(_env("SEARXNG_URL").rstrip("/") + "/search", params={"q": query, "format": "json"},
                         headers={"User-Agent": UA}, timeout=15)
        rows = [(x.get("title", ""), x.get("url", ""), x.get("content", "")) for x in r.json().get("results", [])]
    elif _env("TAVILY_API_KEY"):
        r = requests.post("https://api.tavily.com/search", json={"query": query, "max_results": n},
                          headers={"Authorization": "Bearer " + _env("TAVILY_API_KEY")}, timeout=20)
        rows = [(x.get("title", ""), x.get("url", ""), x.get("content", "")) for x in r.json().get("results", [])]
    elif _env("BRAVE_API_KEY"):
        r = requests.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": n},
                         headers={"X-Subscription-Token": _env("BRAVE_API_KEY"), "Accept": "application/json"}, timeout=15)
        rows = [(x.get("title", ""), x.get("url", ""), re.sub(r"<[^>]+>", "", x.get("description", "")))
                for x in r.json().get("web", {}).get("results", [])]
    else:  # ohne Key: DuckDuckGo-HTML (kann sich aendern oder Anfragen begrenzen)
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers={"User-Agent": UA}, timeout=15)
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)',
                             r.text, re.S):
            href = m.group(1)
            if "uddg=" in href:
                href = unquote(parse_qs(urlparse(href if href.startswith("http") else "https:" + href).query).get("uddg", [href])[0])
            sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', m.group(3), re.S)
            clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
            rows.append((clean(m.group(2)), href, clean(sn.group(1)) if sn else ""))
    rows = [r for r in rows if r[1]][:n]
    if not rows:
        return "Keine Treffer (oder die Suche ist gerade nicht erreichbar). Formuliere die Suche anders."
    return "\n".join(f"{i}. {t}\n   {u}\n   {_clip(s, 300)}" for i, (t, u, s) in enumerate(rows, 1))


def fetch_url(url):
    r, data, cut = safe_get(str(url or "").strip(), MAX_PAGE_BYTES)
    ctype = r.headers.get("Content-Type", "").lower()
    if any(x in ctype for x in ("image/", "video/", "audio/", "zip", "octet-stream", "pdf")):
        raise ToolError(f"Kein Text-Inhalt ({ctype.split(';')[0]}). Fuer Bilder image_save nutzen.")
    text = data.decode(r.encoding or "utf-8", errors="replace")
    if "html" in ctype or text.lstrip()[:1] == "<":
        title, body = html_to_text(text)
    else:
        title, body = "", text
    head = f"Quelle: {url}" + (f"\nTitel: {title}" if title else "") + ("\n(Seite war sehr gross, nur der Anfang wurde gelesen)" if cut else "")
    return head + "\n\n" + _clip(body, PAGE_CHARS)


def image_search(query, n=6):
    query = str(query or "").strip()[:200]
    if not query:
        raise ToolError("query fehlt")
    n = min(max(int(n or 6), 1), 10)
    items = []
    if _env("PEXELS_API_KEY"):
        r = requests.get("https://api.pexels.com/v1/search", params={"query": query, "per_page": n},
                         headers={"Authorization": _env("PEXELS_API_KEY")}, timeout=15)
        for x in r.json().get("photos", []):
            items.append((x["src"].get("large2x") or x["src"]["large"], x.get("alt") or query,
                          x.get("photographer", "?"), "Pexels-Lizenz (frei nutzbar)", x.get("url", "")))
    else:  # Openverse: Millionen frei lizenzierte Bilder, kein Key noetig
        r = requests.get("https://api.openverse.org/v1/images/",
                         params={"q": query, "page_size": n, "license_type": "commercial"},
                         headers={"User-Agent": UA}, timeout=20)
        for x in r.json().get("results", []):
            lic = f"CC {x.get('license', '?').upper()} {x.get('license_version', '')}".strip()
            items.append((x.get("url", ""), x.get("title") or query, x.get("creator") or "unbekannt", lic,
                          x.get("foreign_landing_url", "")))
    items = [i for i in items if i[0]]
    if not items:
        return "Keine Bilder gefunden. Versuche englische oder allgemeinere Suchbegriffe."
    return "\n".join(f"{i}. {t}\n   Bild-URL: {u}\n   Urheber: {c} | Lizenz: {lic} | Seite: {page}"
                     for i, (u, t, c, lic, page) in enumerate(items, 1)) + \
        "\nHinweis: Bei CC-Lizenzen den Urheber im Impressum/Bildnachweis nennen. Danach mit image_save speichern."


_IMG_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}


def _sniff(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.lstrip()[:5] in (b"<?xml", b"<svg ") or b"<svg" in data[:600]:
        return "svg"
    return None


def _safe_name(name, default):
    n = re.sub(r"[^a-z0-9_-]+", "-", str(name or "").lower()).strip("-")[:50]
    return n or default


def _store_image(root, data, name, default):
    ext = _sniff(data)
    if not ext:
        raise ToolError("Das ist keine gueltige Bilddatei (PNG, JPG, GIF, WEBP oder SVG).")
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    base, i = _safe_name(name, default), 0
    while True:
        target = assets / (f"{base}{'' if not i else '-' + str(i)}.{ext}")
        if not target.exists():
            break
        i += 1
    target.write_bytes(data)
    return f"assets/{target.name}", len(data)


def image_save(root, url, name=""):
    r, data, cut = safe_get(str(url or "").strip(), MAX_IMAGE_BYTES)
    if cut:
        raise ToolError(f"Bild ist groesser als {MAX_IMAGE_BYTES // 1_000_000} MB")
    rel, size = _store_image(root, data, name, "bild")
    return f"Gespeichert: {rel} ({size // 1024} KB). Im HTML so einbinden: <img src=\"{rel}\" alt=\"...\">"


def image_generate(root, prompt, name=""):
    prompt = str(prompt or "").strip()[:800]
    if not prompt:
        raise ToolError("prompt fehlt")
    prov = _env("IMAGE_PROVIDER", "pollinations").lower()
    data = None
    if prov == "gemini":
        key = _env("GEMINI_API_KEY").split(",")[0].strip()
        if not key:
            raise ToolError("IMAGE_PROVIDER=gemini, aber GEMINI_API_KEY fehlt")
        model = _env("IMAGE_MODEL", "gemini-2.5-flash-image")
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                          headers={"x-goog-api-key": key}, timeout=120,
                          json={"contents": [{"parts": [{"text": prompt}]}]})
        for part in (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob:
                data = base64.b64decode(blob["data"])
        if not data:
            raise ToolError("Gemini hat kein Bild geliefert: " + _clip(r.text, 300))
    elif prov == "openai":
        key = _env("OPENAI_API_KEY").split(",")[0].strip()
        if not key:
            raise ToolError("IMAGE_PROVIDER=openai, aber OPENAI_API_KEY fehlt")
        base = _env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        r = requests.post(base + "/images/generations", headers={"Authorization": "Bearer " + key}, timeout=180,
                          json={"model": _env("IMAGE_MODEL", "gpt-image-1"), "prompt": prompt, "size": "1024x1024"})
        d = (r.json().get("data") or [{}])[0]
        if d.get("b64_json"):
            data = base64.b64decode(d["b64_json"])
        elif d.get("url"):
            data = safe_get(d["url"], MAX_IMAGE_BYTES)[1]
        else:
            raise ToolError("Bildanbieter hat kein Bild geliefert: " + _clip(r.text, 300))
    else:  # pollinations: kostenlos, ohne Key
        r = requests.get("https://image.pollinations.ai/prompt/" + quote(prompt),
                         params={"width": 1024, "height": 768, "nologo": "true", "seed": int(time.time()) % 100000},
                         headers={"User-Agent": UA}, timeout=120)
        if r.status_code >= 400:
            raise ToolError(f"Bildgenerator antwortet mit HTTP {r.status_code}")
        data = r.content
    rel, size = _store_image(root, data, name, "generiert")
    return f"Bild erzeugt und gespeichert: {rel} ({size // 1024} KB). Im HTML so einbinden: <img src=\"{rel}\" alt=\"...\">"


def _inside(root, rel):
    target = (root / str(rel or "")).resolve()
    target.relative_to(root.resolve())  # wirft ValueError ausserhalb
    return target


def list_files(root, path=""):
    try:
        d = _inside(root, path)
    except ValueError:
        raise ToolError("Pfad liegt ausserhalb des Projektordners")
    if not d.exists():
        return "(Ordner ist leer oder existiert noch nicht)"
    rows = []
    for f in sorted(d.rglob("*"))[:300]:
        if f.is_file():
            rows.append(f"{f.relative_to(root.resolve())}  ({f.stat().st_size // 1024 or 1} KB)")
    return "\n".join(rows) or "(keine Dateien)"


def read_file(root, path):
    try:
        f = _inside(root, path)
    except ValueError:
        raise ToolError("Pfad liegt ausserhalb des Projektordners")
    if not f.is_file():
        raise ToolError(f"Datei '{path}' gibt es nicht (list_files zeigt den Inhalt)")
    data = f.read_bytes()[:400_000]
    if b"\x00" in data[:2000]:
        return f"{path}: Binaerdatei ({f.stat().st_size // 1024} KB), kann nicht als Text gelesen werden."
    return f"Datei {path}:\n" + _clip(data.decode("utf-8", errors="replace"), READ_CHARS)


# ----------------------------------------------------------------------------- Dispatcher
def run_tool(call, root, perms):
    """call: dict {"tool": ..., ...}. Gibt (text, erzeugte_datei_oder_None) zurueck. Wirft nie."""
    name = str((call or {}).get("tool", ""))
    spec = TOOLS.get(name)
    if not spec:
        return f"FEHLER: Unbekanntes Werkzeug '{name}'. Erlaubt: {', '.join(available(perms)) or 'keine'}.", None
    if name not in available(perms):
        return f"FEHLER: Werkzeug '{name}' ist fuer dich nicht erlaubt.", None
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        if name == "web_search":
            out = web_search(call.get("query"), call.get("count"))
        elif name == "fetch_url":
            out = fetch_url(call.get("url"))
        elif name == "image_search":
            out = image_search(call.get("query"), call.get("count"))
        elif name == "image_save":
            out = image_save(root, call.get("url"), call.get("name"))
        elif name == "image_generate":
            out = image_generate(root, call.get("prompt"), call.get("name"))
        elif name == "list_files":
            out = list_files(root, call.get("path"))
        else:
            out = read_file(root, call.get("path"))
        made = None
        m = re.search(r"(assets/[\w.-]+)", out) if name in ("image_save", "image_generate") else None
        if m:
            made = m.group(1)
        return out, made
    except ToolError as e:
        return f"FEHLER: {e}", None
    except requests.RequestException as e:
        return f"FEHLER: Netzwerk ({type(e).__name__}). Spaeter erneut versuchen oder anders suchen.", None
    except Exception as e:  # Modell soll weiterarbeiten koennen
        return f"FEHLER: {type(e).__name__}: {e}", None
