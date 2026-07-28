#!/usr/bin/env python3
"""
collect.py — fetch new items from all enabled RSS/API sources.

Reads feeds.yaml, fetches each feed, normalises fields, deduplicates
against data/seen.json, and writes data/candidates.json for the next step.

Usage:
    python scripts/collect.py [--lookback-hours 48]
"""
import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FEEDS_FILE = ROOT / "feeds.yaml"
SEEN_FILE = DATA_DIR / "seen.json"
CANDIDATES_FILE = DATA_DIR / "candidates.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [collect] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def clean_html(text: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(entry: feedparser.FeedParserDict) -> datetime:
    """Return a timezone-aware datetime for a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def normalise_entry(
    entry: feedparser.FeedParserDict,
    source_name: str,
    source_category: str,
    source_quality: int,
) -> dict:
    """Convert a feedparser entry to a normalised item dict."""
    title = clean_html(entry.get("title", ""))
    link = entry.get("link", "")

    # Summary: prefer content over summary
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = clean_html(entry.content[0].get("value", ""))
    if not content:
        content = clean_html(entry.get("summary", ""))

    # Truncate to ~500 chars to keep memory light
    content = content[:500]

    published = parse_date(entry)

    return {
        "title": title,
        "url": link,
        "source": source_name,
        "category": source_category,
        "source_quality": source_quality,
        "summary": content,
        "published": published.isoformat(),
        "fetched": datetime.now(timezone.utc).isoformat(),
        "score": 0.0,
        "why_matters": "",
        "tags": [],
    }


# ── main fetch loop ────────────────────────────────────────────────────────

def fetch_feed(source: dict, cutoff: datetime) -> list[dict]:
    """Fetch one feed and return normalised items newer than cutoff."""
    url = source["url"]
    name = source["name"]
    category = source["category"]
    quality = source.get("quality", 3)

    log.info("Fetching  %s", name)
    try:
        feed = feedparser.parse(url, agent="my-rss-feed/1.0 (github-pages-digest)")
    except Exception as exc:
        log.warning("  ✗ fetch error for %s: %s", name, exc)
        return []

    if feed.bozo and feed.bozo_exception:
        log.debug("  ⚠ bozo feed %s: %s", name, feed.bozo_exception)

    items = []
    for entry in feed.entries:
        pub = parse_date(entry)
        if pub < cutoff:
            continue
        item = normalise_entry(entry, name, category, quality)
        if item["url"] and item["title"]:
            items.append(item)

    log.info("  → %d new items (since %s)", len(items), cutoff.strftime("%Y-%m-%d %H:%M"))
    return items


def deduplicate(items: list[dict], seen: dict) -> list[dict]:
    """Remove items already present in seen.json."""
    seen_urls = set(seen.get("seen_urls", []))
    seen_titles = set(t.lower() for t in seen.get("seen_titles", []))

    fresh = []
    for item in items:
        url = item["url"].strip().rstrip("/")
        title_key = item["title"].lower().strip()
        if url in seen_urls:
            continue
        if title_key in seen_titles:
            continue
        fresh.append(item)

    return fresh


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect RSS feed items")
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=48,
        help="How many hours back to look for items (default: 48)",
    )
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.lookback_hours)
    log.info("Collecting items since %s UTC", cutoff.strftime("%Y-%m-%d %H:%M"))

    config = load_yaml(FEEDS_FILE)
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    log.info("Loaded %d enabled sources", len(sources))

    seen = load_json(SEEN_FILE, {"seen_urls": [], "seen_titles": [], "last_updated": None})

    all_items: list[dict] = []
    for source in sources:
        items = fetch_feed(source, cutoff)
        all_items.extend(items)
        time.sleep(0.5)  # be polite to servers

    log.info("Total raw items fetched: %d", len(all_items))

    fresh = deduplicate(all_items, seen)
    log.info("After deduplication: %d items", len(fresh))

    # Sort by published date descending before handing off to rank.py
    fresh.sort(key=lambda x: x["published"], reverse=True)

    save_json(CANDIDATES_FILE, fresh)
    log.info("Saved %d candidates → %s", len(fresh), CANDIDATES_FILE)


if __name__ == "__main__":
    main()
