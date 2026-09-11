"""Ingestion and source records with provenance.

Deliberately stdlib-only. See README for why.
"""
import hashlib
import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional

USER_AGENT = "rigor-harness/0.1 (pilot; contact: repo owner)"


class _TextExtractor(HTMLParser):
    """Collect visible prose, one block element per line.

    Line breaks come only from block-level tags. Inline tags (code, a, em)
    join into the surrounding sentence, so "set the env var
    <code>OPENAI_AGENTS_DISABLE_TRACING=1</code>" stays one sentence instead
    of being cut at the code span. Code blocks (<pre>) are dropped: they are
    examples, not claims.
    """

    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "pre"}
    BLOCK = {"p", "li", "dt", "dd", "div", "section", "article", "blockquote",
             "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td", "th",
             "ul", "ol", "dl", "br", "hr", "details", "summary", "figcaption"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._lines: List[str] = []
        self._current: List[str] = []

    def _break(self) -> None:
        line = re.sub(r"\s+", " ", "".join(self._current)).strip()
        if line:
            self._lines.append(line)
        self._current = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag in self.BLOCK and not self._skip_depth:
            self._break()

    def handle_startendtag(self, tag, attrs):
        if tag in self.BLOCK and not self._skip_depth:
            self._break()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            if self._skip_depth:
                self._skip_depth -= 1
        elif tag in self.BLOCK and not self._skip_depth:
            self._break()

    def handle_data(self, data):
        if not self._skip_depth:
            self._current.append(data)

    def text(self) -> str:
        self._break()
        return "\n".join(self._lines)


def fetch(url: str, timeout: int = 30) -> Dict:
    """Retrieve a URL and return a raw fetch record.

    Returns the bytes plus everything needed to identify what was fetched and
    when. No parsing decisions are made here.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        status = resp.status
    return {
        "url": url,
        "http_status": status,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "content_length": len(body),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "content_type": headers.get("content-type"),
        "_body": body,
        "fetch_mode": "live_http",
    }


def to_source_record(fetch_record: Dict) -> Dict:
    """Turn a raw fetch into a structured source record with a stable identity.

    source_id is derived from the URL, so re-ingesting the same URL addresses
    the same object. content_sha256 is what changes when the page changes,
    which is how a revision is detected without creating a duplicate source.
    """
    html = fetch_record["_body"].decode("utf-8", errors="replace")
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.text()
    return {
        "source_id": "src_" + hashlib.sha256(fetch_record["url"].encode()).hexdigest()[:16],
        "url": fetch_record["url"],
        "http_status": fetch_record["http_status"],
        "first_seen_at": fetch_record["fetched_at"],
        "last_seen_at": fetch_record["fetched_at"],
        "content_sha256": fetch_record["content_sha256"],
        "content_length": fetch_record["content_length"],
        "etag": fetch_record["etag"],
        "last_modified": fetch_record["last_modified"],
        "content_type": fetch_record["content_type"],
        "fetch_mode": fetch_record.get("fetch_mode", "live_http"),
        "fixture_path": fetch_record.get("fixture_path"),
        "revision_count": 1,
        "text": text,
    }


class SourceStore:
    """Idempotent store keyed on source_id.

    Acceptance test 4: re-running the same source must not create a second
    independent copy. Re-ingesting updates last_seen_at, and bumps
    revision_count only when the content hash actually changed.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._data: Dict[str, Dict] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)

    def upsert(self, record: Dict) -> Dict:
        sid = record["source_id"]
        existing = self._data.get(sid)
        if existing is None:
            self._data[sid] = record
            return {"action": "created", "record": record, "content_changed": False}
        changed = existing["content_sha256"] != record["content_sha256"]
        existing["last_seen_at"] = record["last_seen_at"]
        existing["fetch_mode"] = record.get("fetch_mode")
        existing["fixture_path"] = record.get("fixture_path")
        if changed:
            existing["content_sha256"] = record["content_sha256"]
            existing["content_length"] = record["content_length"]
            existing["text"] = record["text"]
            existing["revision_count"] = existing.get("revision_count", 1) + 1
        return {"action": "updated", "record": existing, "content_changed": changed}

    def count(self) -> int:
        return len(self._data)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        serializable = {
            k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
            for k, v in self._data.items()
        }
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, sort_keys=True)
