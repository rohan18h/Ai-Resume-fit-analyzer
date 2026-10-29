"""check_links.py against a local HTTP server (no internet needed)."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_links  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/ok":
            self.send_response(200)
        elif self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/ok")
        else:
            self.send_response(404)
        self.end_headers()

    def log_message(self, *args: object) -> None:  # keep test output quiet
        pass


@pytest.fixture(scope="module")
def base_url() -> str:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_check_url_statuses(base_url: str) -> None:
    assert check_links.check_url(f"{base_url}/ok").ok
    moved = check_links.check_url(f"{base_url}/moved")
    assert moved.ok and moved.final_url.endswith("/ok")
    missing = check_links.check_url(f"{base_url}/missing")
    assert not missing.ok and missing.status == 404


def test_unreachable_host_fails() -> None:
    result = check_links.check_url("http://127.0.0.1:9/nothing", timeout=2, retries=0)
    assert not result.ok and result.status is None


def test_temporary_errors_are_retried_but_404_is_not(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    replies = {"flaky": [None, 200], "gone": [404, 200]}

    def fake_request(url: str, timeout: float) -> check_links.LinkResult:
        calls.append(url)
        return check_links.LinkResult(url, replies[url].pop(0))

    monkeypatch.setattr(check_links, "_request", fake_request)
    monkeypatch.setattr(check_links.time, "sleep", lambda _: None)
    assert check_links.check_url("flaky").ok
    assert check_links.check_url("gone").status == 404
    assert calls == ["flaky", "flaky", "gone"]


def test_youtube_links_use_oembed() -> None:
    target = check_links._target("https://www.youtube.com/watch?v=abc")
    assert target.startswith("https://www.youtube.com/oembed?format=json&url=")


def test_main_exit_code(base_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def write_seed(urls: list[str]) -> Path:
        path = tmp_path / "seed.json"
        path.write_text(json.dumps([{"name": "x", "links": [{"url": u} for u in urls]}]), encoding="utf-8")
        return path

    assert check_links.main(["--seed", str(write_seed([f"{base_url}/ok"]))]) == 0
    assert check_links.main(["--seed", str(write_seed([f"{base_url}/ok", f"{base_url}/missing"]))]) == 1
    assert f"FAIL  HTTP 404  {base_url}/missing" in capsys.readouterr().out
