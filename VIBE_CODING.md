# 🤖 VIBE_CODING.md — AI-Assisted Development Guide

> This file tells any AI coding assistant (Copilot, Cursor, Claude, etc.)
> how this project works, what conventions to follow, and where to focus effort.
> Keep this file up to date as the project evolves.

---

## Project summary

`my-rss-feed` is a **curate → score → summarize → publish** pipeline that:
- Fetches RSS/podcast/HN content daily
- Scores items for relevance to a tech-focused persona (AI/LLM, DevOps, Security, SWE)
- Publishes a capped top-10 digest to GitHub Pages via GitHub Actions

**Do not over-engineer.** This is a personal utility — prefer working simple code
over clever abstractions. See [`RULES.md`](RULES.md).

---

## Architecture

```
feeds.yaml          ← source config
interests.yaml      ← keyword weights, category caps, hype penalties
bookmarks.json      ← personalisation seed
data/seen.json      ← dedup memory (persisted in git)
scripts/collect.py  ← fetch + normalise
scripts/rank.py     ← score + select top-10
scripts/summarize.py← "why it matters" bullets
scripts/render.py   ← generate docs/ output
.github/workflows/daily.yml ← orchestration
docs/               ← GitHub Pages output
```

---

## How each script works

### `scripts/collect.py`
- Reads `feeds.yaml`, fetches each enabled feed with `feedparser`
- Normalises fields: title, url, source, category, source_quality, summary, published
- Deduplicates against `data/seen.json` (url + title match)
- Writes `data/candidates.json` (list of dicts)
- CLI: `python scripts/collect.py [--lookback-hours 48]`

### `scripts/rank.py`
- Reads `data/candidates.json`, `interests.yaml`, `bookmarks.json`
- Scores each item: Relevance × CategoryWeight + Freshness + SourceQuality + BookmarkSimilarity − HypePenalty
- Enforces per-category caps and global `daily_cap: 10`
- Updates `data/seen.json` with today's picks to prevent repeats
- Writes `data/top10.json`

### `scripts/summarize.py`
- Reads `data/top10.json`
- Adds `why_matters` string to each item using a regex rule table
- **LLM hook:** Replace the `why_matters()` function body with an LLM call if you add `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` to GitHub Secrets. The interface (one string per item) stays identical.
- Writes updated `data/top10.json` in place

### `scripts/render.py`
- Reads `data/top10.json`
- Writes `docs/daily/YYYY-MM-DD.md`, updates `docs/index.md` and `docs/feed.xml`
- CLI: `python scripts/render.py [--date YYYY-MM-DD]`

---

## Common tasks for AI assistants

### Add a new RSS feed
1. Open `feeds.yaml`
2. Add an entry under `sources:` with name, url, type, category, quality, enabled
3. Run `python scripts/collect.py` to verify it fetches correctly

### Add a new keyword or interest
1. Open `interests.yaml`
2. Add to `keywords:` dict with a weight (1-10) or `boost_phrases:` list
3. No code changes needed

### Add a new category
1. Add to `categories:` in `interests.yaml` with cap and weight
2. Add to `CATEGORY_EMOJI` and `CATEGORY_LABEL` in `scripts/render.py`
3. That's it

### Enable LLM summarisation
1. Add your API key as a GitHub Secret (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`)
2. In `scripts/summarize.py`, replace the `why_matters()` function with an LLM call
3. Add the SDK to `requirements.txt` (`openai` or `anthropic`)
4. Update `.github/workflows/daily.yml` to pass the secret as an env var

### Add personalisation from new bookmarks
1. Open `bookmarks.json`
2. Add items to the `items` array with title and tags
3. The scorer will automatically pick up new bookmark tokens next run

### Debug scoring
```bash
python scripts/collect.py
python scripts/rank.py
# Check data/top10.json — each item has a score_breakdown field
cat data/top10.json | python -m json.tool | grep -A8 score_breakdown
```

---

## Conventions

| Concern | Convention |
|---------|------------|
| Python version | 3.12+ |
| Dependencies | `requirements.txt`, minimal (feedparser, PyYAML, requests) |
| Data files | JSON with `_comment` field for docs |
| Config files | YAML with inline comments |
| Logging | `logging` module, `[script_name]` prefix |
| Paths | Always use `pathlib.Path`, `ROOT` relative |
| Error handling | Log and continue — a broken feed should never crash the pipeline |
| Date/time | Always UTC, timezone-aware `datetime` objects |
| Markdown output | Pure Markdown, no HTML (GitHub Pages renders it) |

---

## What NOT to do

- ❌ Don't add a database (SQLite, Postgres, etc.) — JSON files are sufficient
- ❌ Don't add a web framework (Flask, FastAPI) — this is a static site
- ❌ Don't add a JS build step — pure Markdown + Jekyll (GitHub Pages default)
- ❌ Don't pin dependency versions unnecessarily — `requirements.txt` is minimal
- ❌ Don't add ML/vector search in V1 — keyword scoring is fast and debuggable
- ❌ Don't commit `data/candidates.json` or `data/top10.json` — they're transient

---

## Running locally

```bash
# Install deps
pip install -r requirements.txt

# Full pipeline
python scripts/collect.py
python scripts/rank.py
python scripts/summarize.py
python scripts/render.py

# Check output
open docs/daily/$(date +%Y-%m-%d).md
```

---

## Testing

No formal test suite yet (V1 is intentionally minimal). To manually validate:

```bash
# Check collect works (should print items per feed)
python scripts/collect.py --lookback-hours 168  # 7 days for first run

# Check rank works (should print scored items)
python scripts/rank.py

# Check render produces output
python scripts/render.py
ls docs/daily/
```

---

## GitHub Actions workflow

The workflow (`daily.yml`) runs at 07:00 UTC daily:
1. Checkout → Install Python deps → collect → rank → summarize → render
2. Commits `docs/` and `data/seen.json` back to main
3. Deploys to GitHub Pages

Manual trigger available via **Actions → Daily Digest → Run workflow** with optional `lookback_hours` override.

---

## Future ideas (V2+)

- [ ] LLM-powered "why it matters" summaries (hook already in `summarize.py`)
- [ ] Bookmark auto-sync from browser extension or Pocket/Raindrop API
- [ ] Weekly "best of week" digest from the 7 daily digests
- [ ] "Muted topics" list — suppress patterns for N days
- [ ] Per-category RSS feeds for feed-reader users
- [ ] Simple web UI for thumbs-up/down on items (writes back to `bookmarks.json`)
