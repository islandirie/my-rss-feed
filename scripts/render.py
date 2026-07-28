#!/usr/bin/env python3
"""
render.py — generate the GitHub Pages output from today's top-10.

Reads  data/top10.json
Writes docs/daily/YYYY-MM-DD.md   (today's digest page)
       docs/index.md              (landing page with recent digests)
       docs/feed.xml              (Atom feed of the last 30 digests)

Usage:
    python scripts/render.py [--date YYYY-MM-DD]
"""
import argparse
import glob
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DAILY_DIR = DOCS_DIR / "daily"
TOP10_FILE = DATA_DIR / "top10.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [render]   %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CATEGORY_EMOJI = {
    "ai": "🤖",
    "swe": "💻",
    "devops": "⚙️",
    "security": "🔒",
    "podcast": "🎙️",
    "news": "📰",
}

CATEGORY_LABEL = {
    "ai": "AI / LLM",
    "swe": "Software Engineering",
    "devops": "DevOps / Platform",
    "security": "Security",
    "podcast": "Podcast",
    "news": "News",
}


def load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def fmt_date_human(date_str: str) -> str:
    """'2025-07-28' → 'Monday, July 28 2025'"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%A, %B %-d %Y")
    except Exception:
        return date_str


def published_relative(iso_str: str) -> str:
    """Return a human-readable relative time string."""
    try:
        pub = datetime.fromisoformat(iso_str)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - pub
        hours = int(delta.total_seconds() // 3600)
        if hours < 1:
            return "just now"
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return ""


# ── daily digest page ─────────────────────────────────────────────────────

def render_daily_page(items: list[dict], date_str: str) -> str:
    """Return the Markdown content for one daily digest page."""
    human_date = fmt_date_human(date_str)
    lines = [
        f"# Daily Digest — {human_date}",
        "",
        f"> **{len(items)} items** curated from tech podcasts, blogs, HN and security feeds.",
        "> Scored by relevance, freshness, source quality and your bookmark history.",
        "",
        "---",
        "",
    ]

    for idx, item in enumerate(items, 1):
        cat = item.get("category", "news")
        emoji = CATEGORY_EMOJI.get(cat, "📌")
        label = CATEGORY_LABEL.get(cat, cat.title())
        tags = item.get("tags", [])
        tag_str = " ".join(f"`{t}`" for t in tags) if tags else ""
        rel_time = published_relative(item.get("published", ""))
        score = item.get("score", 0)

        lines += [
            f"## {idx}. {emoji} {item['title']}",
            "",
            f"**Source:** {item.get('source', '')}  "
            f"**Category:** {label}  "
            f"**Score:** {score:.0f}  "
            + (f"**Published:** {rel_time}" if rel_time else ""),
            "",
        ]

        summary = item.get("summary", "").strip()
        if summary:
            lines += [f"> {summary[:280]}{'…' if len(summary) > 280 else ''}", ""]

        why = item.get("why_matters", "")
        if why:
            lines += [f"**Why it matters:** {why}", ""]

        if tag_str:
            lines += [f"**Tags:** {tag_str}", ""]

        lines += [f"🔗 [Read more]({item.get('url', '#')})", "", "---", ""]

    lines += [
        "",
        "*Generated automatically by [my-rss-feed](https://github.com/islandirie/my-rss-feed)*",
    ]
    return "\n".join(lines)


# ── index page ────────────────────────────────────────────────────────────

def render_index(recent_dates: list[str]) -> str:
    """Return the Markdown content for docs/index.md."""
    lines = [
        "# 📡 my-rss-feed — Daily Tech Digest",
        "",
        "A daily curated top-10 from the tech world: AI/LLM releases, DevOps tools,",
        "security news, SWE insights and podcasts.",
        "",
        "**Signal over noise.** Max 10 items/day, category-capped, scored by relevance.",
        "",
        "---",
        "",
        "## Recent Digests",
        "",
    ]

    for date_str in sorted(recent_dates, reverse=True)[:30]:
        human = fmt_date_human(date_str)
        lines.append(f"- [{human}](daily/{date_str}.md)")

    lines += [
        "",
        "---",
        "",
        "## About",
        "",
        "Built with a `curate → score → summarize → publish` pipeline running daily via GitHub Actions.",
        "",
        "- **Sources:** RSS feeds from HN, AI labs, DevOps blogs, security researchers & podcasts",
        "- **Scoring:** Relevance keywords + freshness decay + source quality + bookmark similarity",
        "- **Caps:** max 3 AI · 2 security · 2 DevOps · 3 SWE · 2 podcasts per day",
        "",
        "→ [How to add sources / tune interests](../feeds.yaml)",
        "→ [Add bookmarks to personalise](../bookmarks.json)",
        "→ [Contributing / AI dev guide](../VIBE_CODING.md)",
        "",
        "*Auto-updated daily by GitHub Actions*",
    ]
    return "\n".join(lines)


# ── Atom feed ─────────────────────────────────────────────────────────────

def render_atom_feed(recent_digests: list[tuple[str, list[dict]]]) -> str:
    """Return an Atom XML feed of recent daily digests."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []

    for date_str, items in recent_digests[:30]:
        titles = "; ".join(i["title"][:50] for i in items[:3])
        content_lines = []
        for item in items:
            content_lines.append(
                f"<p><b>{xml_escape(item['title'])}</b> "
                f"— {xml_escape(item.get('why_matters', ''))} "
                f"<a href=\"{xml_escape(item.get('url',''))}\">Read</a></p>"
            )
        content_html = "\n".join(content_lines)
        entries.append(
            f"""  <entry>
    <id>tag:my-rss-feed,{date_str}:daily-digest</id>
    <title>{xml_escape(f"Daily Digest {date_str}: {titles}")}</title>
    <updated>{date_str}T00:00:00Z</updated>
    <link href="https://islandirie.github.io/my-rss-feed/daily/{date_str}.html"/>
    <content type="html">{xml_escape(content_html)}</content>
  </entry>"""
        )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>my-rss-feed — Daily Tech Digest</title>
  <id>https://islandirie.github.io/my-rss-feed/</id>
  <link href="https://islandirie.github.io/my-rss-feed/"/>
  <link rel="self" href="https://islandirie.github.io/my-rss-feed/feed.xml"/>
  <updated>{now}</updated>
  <author><name>islandirie</name></author>
{chr(10).join(entries)}
</feed>
"""


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Render daily digest pages")
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Date string YYYY-MM-DD (default: today UTC)",
    )
    args = parser.parse_args()
    date_str = args.date

    items = load_json(TOP10_FILE, [])
    if not items:
        log.warning("No top10 items to render — writing empty digest.")

    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # Write today's daily page
    daily_path = DAILY_DIR / f"{date_str}.md"
    daily_content = render_daily_page(items, date_str)
    daily_path.write_text(daily_content, encoding="utf-8")
    log.info("Wrote %s  (%d items)", daily_path, len(items))

    # Collect all existing daily dates
    existing = sorted(
        Path(p).stem
        for p in glob.glob(str(DAILY_DIR / "*.md"))
    )

    # Update index
    index_path = DOCS_DIR / "index.md"
    index_content = render_index(existing)
    index_path.write_text(index_content, encoding="utf-8")
    log.info("Updated %s  (%d digests listed)", index_path, len(existing))

    # Load last 30 digests for Atom feed
    recent_digests = []
    for ds in sorted(existing, reverse=True)[:30]:
        p = DAILY_DIR / f"{ds}.md"
        # We only have markdown; for the feed, reuse today's items for today's date
        if ds == date_str:
            recent_digests.append((ds, items))
        else:
            recent_digests.append((ds, []))

    feed_path = DOCS_DIR / "feed.xml"
    feed_content = render_atom_feed(recent_digests)
    feed_path.write_text(feed_content, encoding="utf-8")
    log.info("Updated %s", feed_path)


if __name__ == "__main__":
    main()
