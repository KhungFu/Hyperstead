"""image_generate gegen simulierte Bild-APIs (kein echter Key, kein Internet)."""
import base64
import json

import pytest

import agent_tools as T

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class Resp:
    def __init__(self, body, status=200):
        self.status_code, self._body = status, body
        self.text = json.dumps(body)

    def json(self):
        return self._body


@pytest.fixture
def openai(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("IMAGE_QUALITY", raising=False)
    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    return calls


def test_openai_ohne_referenz(openai, tmp_path):
    out = T.image_generate(tmp_path, {"prompt": "Kind malt mit Buntstift", "name": "Karte 1", "format": "hoch"})
    assert "assets/karte-1.png" in out and (tmp_path / "assets/karte-1.png").read_bytes() == PNG
    url, kw = openai[0]
    assert url.endswith("/images/generations")
    assert kw["json"]["size"] == "1024x1536" and kw["headers"]["Authorization"] == "Bearer sk-test"


def test_openai_mit_referenzbildern_und_zielpfad(openai, tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input/figuren.png").write_bytes(PNG)
    (tmp_path / "input/stil.jpg").write_bytes(JPG)
    out = T.image_generate(tmp_path, {"prompt": "K1 und K6 spielen", "refs": ["input/figuren.png", "input/stil.jpg"],
                                      "path": "karten/bilder/k01.png", "quality": "high"})
    assert "mit 2 Referenzbild" in out and (tmp_path / "karten/bilder/k01.png").exists()
    url, kw = openai[0]
    assert url.endswith("/images/edits")
    assert [f[0] for f in kw["files"]] == ["image[]", "image[]"]
    assert kw["files"][1][1][2] == "image/jpeg"
    assert kw["data"]["quality"] == "high" and kw["data"]["size"] == "1024x1024"
    # gleicher Pfad nochmal: wird ersetzt statt k01-1.png
    T.image_generate(tmp_path, {"prompt": "neu", "path": "karten/bilder/k01.png"})
    assert sorted(p.name for p in (tmp_path / "karten/bilder").iterdir()) == ["k01.png"]


@pytest.mark.parametrize("call, msg", [
    ({"prompt": "x", "path": "../weg.png"}, "ausserhalb"),
    ({"prompt": "x", "path": "input/x.png"}, "path muss in"),
    ({"prompt": "x", "path": "karten.png"}, "path muss in"),
    ({"prompt": "x", "refs": ["input/fehlt.png"]}, "nicht gefunden"),
    ({"prompt": "x", "refs": ["../../etc/passwd"]}, "nicht gefunden"),
    ({"prompt": "x", "refs": ["a.png"] * 5}, "Hoechstens"),
    ({"prompt": "x", "format": "rund"}, "format"),
    ({"prompt": "x", "quality": "ultra"}, "quality"),
    ({"prompt": ""}, "prompt fehlt"),
])
def test_ungueltige_eingaben_kosten_nichts(openai, tmp_path, call, msg):
    with pytest.raises(T.ToolError, match=msg):
        T.image_generate(tmp_path, call)
    assert not openai  # Fehler fallen VOR dem kostenpflichtigen Aufruf auf


def test_referenz_muss_bild_sein(openai, tmp_path):
    (tmp_path / "notiz.txt").write_text("kein Bild")
    with pytest.raises(T.ToolError, match="PNG, JPG oder WEBP"):
        T.image_generate(tmp_path, {"prompt": "x", "refs": "notiz.txt"})


def test_openai_fehler_wird_gemeldet(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Incorrect API key"}}, 401))
    with pytest.raises(T.ToolError, match="HTTP 401 Incorrect API key"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_openai_ohne_key(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(T.ToolError, match="OPENAI_API_KEY fehlt"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_gemini_mit_referenz(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(PNG).decode()}}]}}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"], "format": "quer", "path": "output/a.png"})
    assert "output/a.png" in out
    parts = seen["json"]["contents"][0]["parts"]
    assert parts[0] == {"text": "x"} and parts[1]["inline_data"]["mime_type"] == "image/png"
    assert "/models/gemini-2.5-flash-image:generateContent" in seen["url"]
    assert seen["json"]["generationConfig"]["imageConfig"] == {"aspectRatio": "3:2"}


def test_gemini_bildgroesse_und_abrechnungshinweis(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("IMAGE_SIZE", "2k")
    seen = {}

    def post(url, **kw):
        seen.update(kw)
        return Resp({"error": {"code": 429, "message": "quota exceeded, limit: 0"}}, 429)
    monkeypatch.setattr(T.requests, "post", post)
    with pytest.raises(T.ToolError, match="HTTP 429.*Abrechnung"):
        T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["json"]["generationConfig"]["imageConfig"]["imageSize"] == "2K"


def test_pollinations_lehnt_referenzen_ab(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    (tmp_path / "ref.png").write_bytes(PNG)
    with pytest.raises(T.ToolError, match="nur mit IMAGE_PROVIDER=openai, gemini oder openrouter"):
        T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"]})


def test_recht_bilder_oder_medien(openai, tmp_path):
    assert "image_generate" in T.available({"images": 1})
    assert "image_generate" in T.available({"media": 1})
    assert "image_generate" not in T.available({"web": 1})
    text, made = T.run_tool({"tool": "image_generate", "prompt": "x", "path": "karten/k02.png"}, tmp_path, {"media": 1})
    assert made == "karten/k02.png", text
    text, _ = T.run_tool({"tool": "image_generate", "prompt": "x"}, tmp_path, {"web": 1})
    assert "nicht erlaubt" in text


@pytest.mark.parametrize("value, expected", [
    ("", "gemini-2.5-flash-image"), ("  ", "gemini-2.5-flash-image"), ('"gemini-nano-banana-2.1"', "gemini-nano-banana-2.1"),
    ("models/gemini-3-pro-image", "gemini-3-pro-image"), ("gemini-2.5-flash-image\r", "gemini-2.5-flash-image"),
])
def test_gemini_modellname_gehaertet(monkeypatch, tmp_path, value, expected):
    monkeypatch.setenv("IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("IMAGE_MODEL", value)
    seen = {}

    def post(url, **kw):
        seen["url"] = url
        return Resp({"error": {"code": 400, "message": "bad"}}, 400)
    monkeypatch.setattr(T.requests, "post", post)
    with pytest.raises(T.ToolError, match=f"Gemini \\({expected}\\).*HTTP 400"):
        T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"].endswith(f"/models/{expected}:generateContent")


def test_openrouter_mit_referenz(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.delenv("IMAGE_MODEL", raising=False)
    monkeypatch.delenv("IMAGE_SIZE", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/png"}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.jpg").write_bytes(JPG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.jpg"], "format": "hoch", "path": "karten/k1.png"})
    assert "karten/k1.png" in out and (tmp_path / "karten/k1.png").read_bytes() == PNG
    assert seen["url"] == "https://openrouter.ai/api/v1/images"
    assert seen["headers"]["Authorization"] == "Bearer or-test"
    body = seen["json"]
    assert body["model"] == "google/gemini-2.5-flash-image" and body["aspect_ratio"] == "2:3"
    assert body["input_references"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_openrouter_fehler_und_key(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(T.ToolError, match="OPENROUTER_API_KEY fehlt"):
        T.image_generate(tmp_path, {"prompt": "x"})
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Insufficient credits"}}, 402))
    with pytest.raises(T.ToolError, match="HTTP 402 .*Guthaben.*Insufficient credits"):
        T.image_generate(tmp_path, {"prompt": "x"})


class Raw:
    status_code, content = 200, PNG


def test_rueckfall_auf_pollinations(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "Insufficient credits"}}, 402))
    got = []
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: got.append(url) or Raw())
    (tmp_path / "ref.png").write_bytes(PNG)
    call = {"prompt": "x", "refs": ["ref.png"], "path": "karten/k1.png"}
    monkeypatch.delenv("IMAGE_FALLBACK", raising=False)
    with pytest.raises(T.ToolError, match="402"):  # Standard: kein Rueckfall
        T.image_generate(tmp_path, call)
    assert not got
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    out = T.image_generate(tmp_path, call)
    assert "pollinations" in got[0] and (tmp_path / "karten/k1.png").exists()
    assert out.startswith("HINWEIS: Auf Pollinations umgestiegen") and "bei openrouter" in out and "HTTP 402" in out[:150]
    assert "OHNE Referenzbilder" in out and "mit 1 Referenzbild" not in out
    text, made = T.run_tool({"tool": "image_generate", **call}, tmp_path, {"media": 1})
    assert made == "karten/k1.png", text


def test_pollinations_mit_key_modell_und_referenzen(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    monkeypatch.setenv("IMAGE_STYLE", "Buntstift auf Pastell")
    monkeypatch.delenv("POLLINATIONS_MODEL", raising=False)
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "K1 winkt", "refs": ["ref.png"], "format": "hoch", "path": "karten/k1.png"})
    assert "mit 1 Referenzbild" in out and (tmp_path / "karten/k1.png").read_bytes() == PNG
    body = seen["json"]
    assert seen["url"] == "https://gen.pollinations.ai/v1/images/generations"
    assert seen["headers"]["Authorization"] == "Bearer sk_test"
    assert body["model"] == T.POLLINATIONS_MODEL and body["size"] == "1024x1536"
    assert isinstance(body["image"], list) and body["image"][0].startswith("data:image/png;base64,")
    assert body["prompt"].startswith("Stil: Buntstift auf Pastell") and "K1 winkt" in body["prompt"]


def test_pollinations_guthaben_leer(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    monkeypatch.setenv("POLLINATIONS_MODEL", "google/gemini-2.5-flash-image")
    monkeypatch.setattr(T.requests, "post", lambda url, **kw: Resp({"error": {"message": "budget exhausted"}}, 402))
    with pytest.raises(T.ToolError, match="gemini-2.5-flash-image.*HTTP 402.*Pollen-Guthaben"):
        T.image_generate(tmp_path, {"prompt": "x"})


def test_pollinations_ohne_key_mit_modell(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "pollinations")
    monkeypatch.delenv("POLLINATIONS_API_KEY", raising=False)
    monkeypatch.setenv("POLLINATIONS_MODEL", "flux")
    seen = {}
    monkeypatch.setattr(T.requests, "get", lambda url, **kw: seen.update(url=url, **kw) or Raw())
    T.image_generate(tmp_path, {"prompt": "x"})
    assert seen["url"].startswith("https://image.pollinations.ai/prompt/") and seen["params"]["model"] == "flux"


def test_rueckfall_mit_pollinations_key_behaelt_referenzen(monkeypatch, tmp_path):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("IMAGE_FALLBACK", "pollinations")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "sk_test")
    urls = []

    def post(url, **kw):
        urls.append(url)
        if "openrouter" in url:
            return Resp({"error": {"message": "Insufficient credits"}}, 402)
        assert len(kw["json"]["image"]) == 1
        return Resp({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    monkeypatch.setattr(T.requests, "post", post)
    (tmp_path / "ref.png").write_bytes(PNG)
    out = T.image_generate(tmp_path, {"prompt": "x", "refs": ["ref.png"]})
    assert "gen.pollinations.ai" in urls[-1] and "mit 1 Referenzbild" in out and "Referenzbildern erzeugt" in out
