# 📡 my-rss-feed

> **Daily top-10 digest** of the most signal-rich content across AI/LLM, DevOps, Security and Software Engineering — curated, scored and published automatically to GitHub Pages every day.

[![Daily Digest](https://github.com/islandirie/my-rss-feed/actions/workflows/daily.yml/badge.svg)](https://github.com/islandirie/my-rss-feed/actions/workflows/daily.yml)

**Live site:** [islandirie.github.io/my-rss-feed](https://islandirie.github.io/my-rss-feed)

---

## What it does

Runs a `curate → score → summarize → publish` pipeline once a day via GitHub Actions:

1. **Collect** — fetches the last 48h of content from ~25 high-signal RSS feeds (HN, AI lab blogs, DevOps, security researchers, podcasts)
2. **Rank** — scores each item on relevance, freshness, source quality and similarity to your bookmarks; enforces a hard daily cap of **10 items** with per-category limits
3. **Summarize** — adds a "why it matters" bullet for each item so you can triage at a glance
4. **Publish** — writes a daily Markdown digest to `docs/daily/YYYY-MM-DD.md`, updates the index and Atom feed, and deploys to GitHub Pages

---

## Repo layout

```
feeds.yaml          ← add/remove/toggle RSS sources here
interests.yaml      ← tune keyword weights, category caps, hype penalties
bookmarks.json      ← items you've found valuable (used to personalise scoring)
data/
  seen.json         ← deduplication memory (auto-managed)
  candidates.json   ← raw fetched items (transient, not committed)
  top10.json        ← today's scored/summarised selections (transient)
scripts/
  collect.py        ← fetch + normalise items from all feeds
  rank.py           ← relevance scoring, diversity enforcement, top-10 selection
  summarize.py      ← rule-based "why it matters" bullets (LLM-ready hook)
  render.py         ← generate Markdown digest + index + Atom feed
docs/               ← GitHub Pages output (auto-generated, do not hand-edit)
  index.md
  daily/YYYY-MM-DD.md
  feed.xml
.github/workflows/
  daily.yml         ← scheduled GitHub Actions workflow (07:00 UTC daily)
```

---

## Quick start

### 1. Fork and enable GitHub Pages

1. Fork this repo
2. Go to **Settings → Pages → Source** and set it to `Deploy from branch: main / docs`
3. Go to **Settings → Actions → General** and ensure workflows can write to the repo

### 2. Tune your sources

Edit [`feeds.yaml`](feeds.yaml) — add, remove or disable feeds:

```yaml
- name: "My Favourite Blog"
  url: "https://example.com/feed.xml"
  type: rss
  category: swe       # ai | swe | devops | security | podcast | news
  quality: 4          # 1-5 (higher = more trusted)
  enabled: true
```

### 3. Tune your interests

Edit [`interests.yaml`](interests.yaml) to boost keywords you care about, raise/lower per-category caps, or add hype-penalty terms to suppress low-signal posts.

### 4. Add bookmarks for personalisation

Edit [`bookmarks.json`](bookmarks.json) — paste in titles and tags of articles/tools you've found valuable. The scorer extracts keywords and gives a similarity boost to incoming items that match.

### 5. Run manually

```bash
pip install -r requirements.txt

# Full pipeline
python scripts/collect.py
python scripts/rank.py
python scripts/summarize.py
python scripts/render.py
```

Or trigger the workflow via **Actions → Daily Digest → Run workflow**.

---

## Scoring formula

```
FinalScore = (Relevance × CategoryWeight)
           + Freshness
           + SourceQuality
           + BookmarkSimilarity
           − HypePenalty
```

| Component | Max | Description |
|-----------|-----|-------------|
| Relevance | ~60 | Keyword + phrase match against title + summary |
| Freshness | 10  | Exponential decay (half-life 24h) |
| SourceQuality | 10 | Based on per-feed `quality` rating |
| BookmarkSimilarity | 15 | Token overlap with your saved bookmarks |
| HypePenalty | −8 per term | Suppresses low-signal hype words |

Category caps (configurable in `interests.yaml`):
- 🤖 AI/LLM — max **3/day**
- 💻 SWE — max **3/day**
- ⚙️ DevOps — max **2/day**
- 🔒 Security — max **2/day**
- 🎙️ Podcast — max **2/day**
- 📰 News — max **3/day**

---

## Personalisation (V2 roadmap)

- **70 % personalized / 30 % discovery** budget (to keep you finding new things)
- Bookmark tagging auto-extracts entities to reweight future scoring
- Optional LLM summarisation hook in `summarize.py` — swap in your `OPENAI_API_KEY` GitHub secret for richer "why it matters" bullets

---

## Atom feed

Subscribe to the daily digest at:

```
https://islandirie.github.io/my-rss-feed/feed.xml
```

---

## Contributing / AI-assisted development

See [`VIBE_CODING.md`](VIBE_CODING.md) for the AI-assisted dev guide.

For rules and coding standards see [`RULES.md`](RULES.md).

---

## License

MIT — do what you want, just don't flood the internet with garbage feeds.
