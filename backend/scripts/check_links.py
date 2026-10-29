"""Check that every learning-link URL in data/skills_seed.json works (Section 10.4).

Sends a GET request to every URL, prints any that do not end in HTTP 200, and exits with code 1 if any fail.
YouTube links are checked through YouTube's oEmbed endpoint, because youtube.com returns 200 even for
videos that do not exist.

Run from backend/ before every release:  python scripts/check_links.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_seed.json"
USER_AGENT = "Mozilla/5.0 (compatible; ResumeFitAnalyzer-LinkChecker/1.0)"


@dataclass
class LinkResult:
    url: str
    status: int | None  # final HTTP status, or None if the request failed
    final_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200


def _target(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith("youtube.com") or host == "youtu.be":
        return f"https://www.youtube.com/oembed?format=json&url={quote(url, safe='')}"
    return url


def check_url(url: str, timeout: float = 20, retries: int = 2) -> LinkResult:
    """Request one URL (following redirects) and report the final status.

    Network errors, 429 and 5xx are retried (they are often temporary); other statuses fail at once.
    """
    for attempt in range(retries + 1):
        result = _request(url, timeout)
        temporary = result.status is None or result.status == 429 or result.status >= 500
        if result.ok or not temporary or attempt == retries:
            return result
        time.sleep(1 + attempt)
    return result


def _request(url: str, timeout: float) -> LinkResult:
    request = Request(_target(url), headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json,*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return LinkResult(url, response.status, response.geturl())
    except HTTPError as exc:
        return LinkResult(url, exc.code, error=f"HTTP {exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return LinkResult(url, None, error=str(reason))


def collect_urls(entries: list[dict]) -> dict[str, list[str]]:
    """Map each URL to the skills that use it."""
    urls: dict[str, list[str]] = {}
    for entry in entries:
        for link in entry.get("links", []):
            urls.setdefault(link["url"], []).append(entry["name"])
    return urls


def run(seed_path: Path, timeout: float, workers: int) -> int:
    entries = json.loads(seed_path.read_text(encoding="utf-8"))
    urls = collect_urls(entries)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda u: check_url(u, timeout), urls))

    failures = [r for r in results if not r.ok]
    redirects = [r for r in results if r.ok and r.final_url and r.final_url.rstrip("/") != _target(r.url).rstrip("/")]
    for result in failures:
        print(f"FAIL  {result.error or result.status}  {result.url}  (skills: {', '.join(urls[result.url])})")
    for result in redirects:
        print(f"note  redirects to {result.final_url}  from {result.url}")
    print(f"\nChecked {len(results)} URLs for {len(entries)} skills: {len(results) - len(failures)} OK, "
          f"{len(failures)} failed, {len(redirects)} redirected.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=Path, default=SEED_PATH, help="path to skills_seed.json")
    parser.add_argument("--timeout", type=float, default=20, help="seconds per request")
    parser.add_argument("--workers", type=int, default=12, help="parallel requests")
    args = parser.parse_args(argv)
    return run(args.seed, args.timeout, args.workers)


if __name__ == "__main__":
    sys.exit(main())
