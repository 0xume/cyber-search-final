from __future__ import annotations

import hashlib
import os
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "CyberSearchBot/0.1 (+https://team-cyber-fiber.github.io/cyber-search; "
    "educational metadata indexer; contact via GitHub issues)"
)

CACHE_DIR = Path(os.environ.get("CYBER_SEARCH_CACHE", ".cache"))

class FetchError(RuntimeError):
    pass

class PoliteFetcher:
    def __init__(self, *, cache_dir: Path = CACHE_DIR, offline: bool = False,
                 default_delay: float = 2.0, timeout: float = 20.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.default_delay = default_delay
        self.timeout = timeout
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    @staticmethod
    def _is_local(url: str) -> bool:
        scheme = urlparse(url).scheme
        return scheme in ("", "file") or os.path.exists(url)

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:20]
        return self.cache_dir / f"{digest}.cache"

    def _respect_delay(self, host: str, delay: float) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self._last_hit[host] = time.monotonic()

    def _robots_allows(self, url: str) -> bool:
        parts = urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None
            self._robots[base] = rp
        if rp is None:
            return False
        return rp.can_fetch(USER_AGENT, url)

    def fetch(self, url: str, *, delay: float | None = None) -> str:
        if self._is_local(url):
            path = Path(urlparse(url).path) if url.startswith("file:") else Path(url)
            return path.read_text(encoding="utf-8", errors="replace")

        cache_file = self._cache_path(url)

        if self.offline:
            if cache_file.exists():
                return cache_file.read_text(encoding="utf-8", errors="replace")
            raise FetchError(f"offline and no cache for {url}")

        if not self._robots_allows(url):
            raise FetchError(f"robots.txt disallows fetching {url}")

        host = urlparse(url).netloc
        self._respect_delay(host, delay if delay is not None else self.default_delay)

        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            if cache_file.exists():
                return cache_file.read_text(encoding="utf-8", errors="replace")
            raise FetchError(f"failed to fetch {url}: {exc}") from exc

        cache_file.write_text(resp.text, encoding="utf-8")
        return resp.text
