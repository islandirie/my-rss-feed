#!/usr/bin/env python3
"""
rank.py — score, filter, and select the daily top-10.

Reads  data/candidates.json + interests.yaml + bookmarks.json
Writes data/top10.json  (the day's selected items, scored and tagged)
       data/seen.json   (updated with today's selections)

Scoring formula:
    FinalScore = (Relevance * CategoryWeight)
               + Freshness
               + SourceQuality
               + BookmarkSimilarity
               - RedundancyPenalty
               - HypePenalty

Usage:
    python scripts/rank.py
"""
import json
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INTERESTS_FILE = ROOT / "interests.yaml"
BOOKMARKS_FILE = ROOT / "bookmarks.json"
CANDIDATES_FILE = DATA_DIR / "candidates.json"
TOP10_FILE = DATA_DIR / "top10.json"
SEEN_FILE = DATA_DIR / "seen.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [rank]    %(levelname)s %(message)s",
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


def tokenise(text: str) -> list[str]:
    """Lowercase word tokens, no punctuation."""
    return re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", text.lower())


def ngrams(tokens: list[str], n: int = 2) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def text_of(item: dict) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')}"


# ── scoring components ─────────────────────────────────────────────────────

def relevance_score(item: dict, keywords: dict, boost_phrases: list[str]) -> float:
    """Keyword + phrase matching against title + summary."""
    text = text_of(item).lower()
    score = 0.0

    for kw, weight in keywords.items():
        if kw.lower() in text:
            score += weight

    for phrase in boost_phrases:
        if phrase.lower() in text:
            score += 5.0  # flat bonus per matching boost phrase

    return score


def freshness_score(item: dict) -> float:
    """Items published in last 12h → max bonus; decays over 48h."""
    try:
        pub = datetime.fromisoformat(item["published"])
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        # exponential decay: half-life ≈ 24h
        return max(0.0, 10.0 * math.exp(-age_hours / 24))
    except Exception:
        return 0.0


def source_quality_score(item: dict) -> float:
    """Map source quality (1-5) to a bonus (0-10)."""
    quality = item.get("source_quality", 3)
    return (quality / 5.0) * 10.0


def bookmark_similarity(item: dict, bookmark_tokens: Counter) -> float:
    """Boost items similar to bookmarked content."""
    if not bookmark_tokens:
        return 0.0

    tokens = tokenise(text_of(item))
    bigrams = ngrams(tokens)
    all_tokens = tokens + bigrams
    if not all_tokens:
        return 0.0

    overlap = sum(bookmark_tokens.get(t, 0) for t in all_tokens)
    # Normalise to max ~15 to keep it bounded
    return min(15.0, overlap * 0.5)


def hype_penalty(item: dict, hype_terms: list[str]) -> float:
    text = text_of(item).lower()
    penalty = 0.0
    for term in hype_terms:
        if term.lower() in text:
            penalty += 8.0
    return penalty


# ── bookmark keyword extraction ────────────────────────────────────────────

def build_bookmark_tokens(bookmarks: dict) -> Counter:
    """Build a weighted token counter from bookmarks."""
    counter: Counter = Counter()
    items = bookmarks.get("items", [])
    for bm in items:
        text = f"{bm.get('title', '')} {' '.join(bm.get('tags', []))}"
        tokens = tokenise(text)
        counter.update(tokens)
        counter.update(ngrams(tokens))
    return counter


# ── diversity / category cap enforcement ───────────────────────────────────

def enforce_caps(ranked: list[dict], categories: dict, daily_cap: int) -> list[dict]:
    """
    Select top-N items respecting per-category caps and global daily_cap.
    Uses a greedy pass over the ranked list.
    """
    cat_counts: dict[str, int] = defaultdict(int)
    selected = []

    for item in ranked:
        if len(selected) >= daily_cap:
            break
        cat = item.get("category", "news")
        cap = categories.get(cat, {}).get("cap", 99)
        if cat_counts[cat] >= cap:
            continue
        selected.append(item)
        cat_counts[cat] += 1

    return selected


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    interests = load_yaml(INTERESTS_FILE)
    bookmarks = load_json(BOOKMARKS_FILE, {"items": []})
    candidates = load_json(CANDIDATES_FILE, [])
    seen = load_json(SEEN_FILE, {"seen_urls": [], "seen_titles": [], "last_updated": None})

    if not candidates:
        log.warning("No candidates found – nothing to rank.")
        save_json(TOP10_FILE, [])
        return

    log.info("Ranking %d candidates …", len(candidates))

    keywords = interests.get("keywords", {})
    boost_phrases = interests.get("boost_phrases", [])
    hype_terms = interests.get("hype_penalties", [])
    categories = interests.get("categories", {})
    daily_cap = interests.get("daily_cap", 10)

    bookmark_tokens = build_bookmark_tokens(bookmarks)

    for item in candidates:
        cat = item.get("category", "news")
        cat_weight = categories.get(cat, {}).get("weight", 1.0)

        r = relevance_score(item, keywords, boost_phrases)
        f = freshness_score(item)
        q = source_quality_score(item)
        b = bookmark_similarity(item, bookmark_tokens)
        hp = hype_penalty(item, hype_terms)

        raw = (r * cat_weight) + f + q + b - hp
        item["score"] = round(raw, 2)
        item["score_breakdown"] = {
            "relevance": round(r, 2),
            "freshness": round(f, 2),
            "source_quality": round(q, 2),
            "bookmark_sim": round(b, 2),
            "hype_penalty": round(-hp, 2),
            "category_weight": cat_weight,
        }

        # Auto-tag based on keyword hits
        tags = set(item.get("tags", []))
        for kw in ["llm", "ai agent", "kubernetes", "security", "devops", "agentic",
                   "benchmark", "coding model", "mcp", "ebpf", "sre", "iac"]:
            if kw.lower() in text_of(item).lower():
                tags.add(kw.replace(" ", "-"))
        item["tags"] = sorted(tags)

    # Sort descending by score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Apply minimum quality threshold (drop anything with score < 5)
    qualified = [i for i in candidates if i["score"] >= 5.0]
    log.info("Qualified (score ≥ 5): %d", len(qualified))

    # Enforce per-category caps + global daily cap
    top10 = enforce_caps(qualified, categories, daily_cap)
    log.info("Selected %d items for today's digest", len(top10))

    for idx, item in enumerate(top10, 1):
        log.info(
            "  #%02d [%6.1f] [%s] %s",
            idx,
            item["score"],
            item["category"],
            item["title"][:70],
        )

    save_json(TOP10_FILE, top10)

    # Update seen.json with today's selections
    seen_urls = set(seen.get("seen_urls", []))
    seen_titles = set(seen.get("seen_titles", []))
    for item in top10:
        seen_urls.add(item["url"].strip().rstrip("/"))
        seen_titles.add(item["title"].lower().strip())

    seen["seen_urls"] = list(seen_urls)
    seen["seen_titles"] = list(seen_titles)
    seen["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_json(SEEN_FILE, seen)
    log.info("Updated seen.json with %d entries", len(seen_urls))


if __name__ == "__main__":
    main()
