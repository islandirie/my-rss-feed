# 📋 RULES.md — Coding Standards & the Ponytail Policy

> **The Ponytail Policy (a.k.a. Lazy Senior Dev Rules)**
>
> A lazy senior dev isn't actually lazy — they're *efficient*.
> They've learned that most complexity is self-inflicted,
> and that the best code is the code that doesn't exist yet.
> Write less. Ship more. Sleep well.

---

## The Core Principle

> *"Make it work, make it right, make it fast — in that order, and stop when it's good enough."*

This is a personal curation tool. It doesn't need to scale to a million users.
It needs to run once a day, not crash, and surface 10 good links.
**Optimise for that.**

---

## The Ponytail Policy Rules

### 1. Ship the boring solution
If a dict and a loop solve the problem, use a dict and a loop.
Don't reach for a graph database, an event bus, or a neural net
when the boring option works fine. Boring code is easier to debug at 11pm.

### 2. Prefer deletion over addition
Before adding a feature, ask: *can I solve this by removing something?*
The best refactor is often just `git rm`.

### 3. If it ain't broke, don't touch it
A working 50-line script beats a "clean" 200-line abstraction.
Resist the urge to refactor code you didn't write and don't understand yet.
Read first. Touch second. Rewrite last (and only with a very good reason).

### 4. One thing at a time
Each script does one job. `collect.py` fetches. `rank.py` scores. `render.py` renders.
Don't merge responsibilities to save a file. Separation makes each piece testable and replaceable.

### 5. Config over code
If something might change (feed URLs, keyword weights, category caps), it lives in YAML or JSON.
Not in a constant. Not hardcoded. The pipeline reads config at runtime — no deploy needed to tune it.

### 6. Fail loudly, recover gracefully
A broken feed should **log a warning** and continue — not crash the whole pipeline.
A missing file should return a sensible default — not a stack trace in GitHub Actions.
But when something *shouldn't* fail (e.g. the config file is missing), fail loudly and early.

### 7. No magic, no secrets in code
- All secrets live in GitHub Secrets / environment variables. Never in files.
- Avoid decorator magic, metaclass tricks, or "clever" dynamic dispatch.
  Future you at 11pm should be able to understand the code in under 5 minutes.

### 8. Write for the reader, not the clever reviewer
- Clear names beat short names: `bookmark_similarity` not `bm_sim`
- Inline comments for *why*, not *what* (the code already shows what)
- A short docstring on every script and non-trivial function

### 9. The 10-minute rule
If you can't explain what a piece of code does in 10 minutes to someone else,
it's too complex. Simplify until you can.

### 10. Leave it better than you found it — but not *much* better
Fix the bug you came to fix. Clean up the immediate mess if it takes < 5 minutes.
Don't refactor half the codebase while fixing a typo. Scope creep is how side projects die.

---

## Code Style

| Rule | Detail |
|------|--------|
| Language | Python 3.12+ |
| Formatter | `black` style (but don't add it as a hard dependency unless needed) |
| Line length | 100 chars max |
| Imports | stdlib → third-party → local; alphabetical within groups |
| Types | Use type hints on function signatures; skip for trivial local vars |
| Logging | Use `logging` module; not `print` |
| Exceptions | Catch specific exceptions; don't `except Exception:` unless you log it |
| Strings | f-strings preferred; no `%` formatting |
| File I/O | Use `pathlib.Path`; never `os.path` string concatenation |
| Datetime | Always UTC, always timezone-aware |

---

## Git Conventions

```
type: short description (50 chars max)

Types: feat | fix | digest | docs | chore | refactor
```

Examples:
- `feat: add reddit RSS source support`
- `fix: handle missing published date in feedparser`
- `digest: daily top-10 for 2025-07-28`
- `chore: bump feedparser to 6.0.11`
- `docs: update VIBE_CODING with LLM hook instructions`

---

## What requires a PR / review vs. just commit

| Change type | Process |
|-------------|---------|
| New feed in `feeds.yaml` | Commit directly to main |
| Tuning `interests.yaml` | Commit directly to main |
| Bug fix in a script | Commit directly to main |
| New script or feature | PR preferred — brief description of why |
| Changes to `daily.yml` workflow | PR — Actions changes can break things silently |
| Changes to `render.py` output format | PR — affects the public-facing site |

---

## AI Assistant Rules (for Copilot, Cursor, Claude, etc.)

When using an AI assistant on this project:

1. **Read `VIBE_CODING.md` first** — it has the full architecture and common tasks
2. **Prefer editing existing files** over creating new ones
3. **Don't add dependencies** without a clear reason — the dep list is intentionally tiny
4. **Don't add tests** unless explicitly asked — this is a V1 personal tool
5. **Don't add a web server, database, or message queue** — it's a static site
6. **Don't rewrite working code** to match a different style — boring consistency > clever inconsistency
7. **When in doubt, do less** — ask for clarification rather than guessing scope
8. **Always output a diff-style explanation** of what changed and why before applying
9. **One task per session** — don't bundle unrelated changes
10. **Respect the daily cap: 10 items** — the whole point is signal over noise; this applies to code changes too

---

## The Anti-Patterns (never do these)

- ❌ Adding a new framework or ORM when a dict will do
- ❌ Abstracting code that's only used once
- ❌ "Just in case" parameters and flags that nothing uses
- ❌ Logging everything at INFO level (use DEBUG for verbose, INFO for meaningful events)
- ❌ Commenting out code instead of deleting it (that's what git is for)
- ❌ Hardcoding URLs, keys or file paths in scripts
- ❌ Committing `data/candidates.json` or `data/top10.json` (transient files)
- ❌ Touching `docs/` by hand (it's generated — always regenerate, never hand-edit)
- ❌ Adding a `.env` file with real secrets to the repo
- ❌ Ignoring a flaky feed error — log it, don't swallow it silently
