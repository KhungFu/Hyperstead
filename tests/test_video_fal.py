"""Videoerzeugung über fal.ai: Warteschlange, Schlüssel, Download ohne Schlüssel."""
import pytest
import agent_tools as T


class R:
    def __init__(self, body, status=200):
        self.status_code, self._b, self.text = status, body, str(body)

    def json(self):
        return self._b


def test_fal_braucht_schluessel(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(T.ToolError, match="FAL_KEY"):
        T.video_generate(tmp_path, {"prompt": "eine Katze"})


def test_fal_standardmodell_ist_der_guenstigste(monkeypatch):
    monkeypatch.delenv("VIDEO_MODEL", raising=False)
    assert T.FAL_VIDEO_MODEL == "minimax/h3-max/text-to-video"


def test_fal_ablauf_und_download_ohne_schluessel(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.setenv("FAL_KEY", "geheim")
    monkeypatch.setenv("VIDEO_MODEL", "fal-ai/kling-video/v2.5-turbo/pro/text-to-video")
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    posted, gets, dl = [], [], {}

    def fake_post(url, headers=None, json=None, timeout=None):
        posted.append((url, headers, json))
        return R({"status_url": "https://queue.fal.run/fal-ai/kling-video/requests/1/status",
                  "response_url": "https://queue.fal.run/fal-ai/kling-video/requests/1"})

    states = iter([{"status": "IN_QUEUE"}, {"status": "COMPLETED"}])

    def fake_get(url, headers=None, timeout=None, **kw):
        gets.append((url, headers))
        if url.endswith("/status"):
            return R(next(states))
        return R({"video": {"url": "https://cdn.example/clip.mp4"}})

    def fake_download(url, key, dst):
        dl.update(url=url, key=key)
        dst.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    monkeypatch.setattr(T.requests, "post", fake_post)
    monkeypatch.setattr(T.requests, "get", fake_get)
    monkeypatch.setattr(T, "_download_video", fake_download)
    out = T.video_generate(tmp_path, {"prompt": "eine Katze", "aspect": "9:16"})

    url, headers, body = posted[0]
    assert url == "https://queue.fal.run/fal-ai/kling-video/v2.5-turbo/pro/text-to-video"
    assert headers == {"Authorization": "Key geheim"}
    assert body == {"prompt": "eine Katze", "aspect_ratio": "9:16"}
    assert all(h == {"Authorization": "Key geheim"} for _, h in gets)
    # Der fal-Schlüssel darf nicht an den Download-Server gehen
    assert dl == {"url": "https://cdn.example/clip.mp4", "key": ""}
    assert "Video erzeugt" in out


def test_fal_bild_zu_video_wird_abgelehnt(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PROVIDER", "fal")
    monkeypatch.setenv("FAL_KEY", "geheim")
    with pytest.raises(T.ToolError, match="Text-zu-Video"):
        T.video_generate(tmp_path, {"prompt": "x", "image": "assets/a.png"})
