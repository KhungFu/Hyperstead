"""Weitere OpenAI-kompatible Anbieter: Konfiguration, Modelllisten, Kosten."""
import app as A


class R:
    def __init__(self, body, status=200):
        self.status_code, self._b, self.text = status, body, str(body)

    def json(self):
        return self._b


def test_neue_anbieter_vorhanden():
    for pid in ("mistral", "nvidia", "together", "perplexity", "huggingface", "cloudflare"):
        cfg = A.PROVIDERS[pid]
        assert cfg["url"].startswith("https://") and cfg["key_env"] and cfg["model"]


def test_cloudflare_braucht_konto_id(monkeypatch):
    monkeypatch.setenv("CF_API_TOKEN", "t")
    monkeypatch.delenv("CF_ACCOUNT_ID", raising=False)
    assert not A.provider_configured("cloudflare")
    monkeypatch.setenv("CF_ACCOUNT_ID", "abc")
    assert A.provider_configured("cloudflare")


def test_feste_modellliste_ohne_api():
    res = A.list_models("perplexity", force=True)
    assert "sonar-pro" in res["models"] and not res["live"]


def test_together_liste_als_array(monkeypatch):
    monkeypatch.setenv("TOGETHER_API_KEY", "k")
    monkeypatch.setattr(A.requests, "get", lambda url, **kw: R([{"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo"}, {"id": "x/y"}]))
    res = A.list_models("together", force=True)
    assert res["live"] and "x/y" in res["models"]


def test_gratis_modelle_kosten_nichts():
    assert A.est_cost("openrouter", "google/gemma-4-31b-it:free", 1_000_000) == 0.0
    assert A.est_cost("openrouter", "openai/gpt-4o-mini", 1_000_000) == 0.3


def test_abgeschaltetes_standardmodell_wird_ersetzt(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setitem(A.PROVIDERS["groq"], "model", "llama-3.3-70b-versatile")
    monkeypatch.setattr(A.requests, "get", lambda url, **kw: R({"data": [{"id": "openai/gpt-oss-120b"},
                                                                           {"id": "qwen/qwen3-32b"}]}))
    A._models_cache.pop("groq", None)
    assert A.default_model("groq") == "openai/gpt-oss-120b"
    A._models_cache.pop("groq", None)


def test_standardmodell_bleibt_wenn_gelistet(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(A.requests, "get", lambda url, **kw: R({"data": [{"id": "models/gemini-3.1-flash-lite"}]}))
    A._models_cache.pop("gemini", None)
    assert A.default_model("gemini") == "gemini-3.1-flash-lite"
    A._models_cache.pop("gemini", None)


def test_openrouter_bezahlmodell_bekommt_max_tokens(monkeypatch):
    sent = {}
    monkeypatch.setattr(A, "MAX_OUTPUT", 0)
    monkeypatch.setattr(A.requests, "post", lambda url, **kw: sent.update(kw["json"]) or R({}))
    A._post_openai(A.PROVIDERS["openrouter"], "k", "openai/gpt-4o-mini", [])
    assert sent["max_tokens"] == 8192
    sent.clear()
    A._post_openai(A.PROVIDERS["openrouter"], "k", "openrouter/free", [])
    assert "max_tokens" not in sent
