#!/usr/bin/env python3
"""
summarize.py — generate "why this matters" bullets for each top-10 item.

Reads  data/top10.json + interests.yaml
Writes data/top10.json  (in-place, adds "why_matters" field to each item)

Strategy (no LLM required — keyword-driven rule system):
  1. Detect primary topics in the item
  2. Map topics → "why it matters" template sentences
  3. Compose a 1-2 sentence summary bullet

For V2, swap in an LLM call here (e.g. OPENAI_API_KEY in GitHub Secrets)
and this script's interface stays identical.

Usage:
    python scripts/summarize.py
"""
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TOP10_FILE = DATA_DIR / "top10.json"
INTERESTS_FILE = ROOT / "interests.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [summarize] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── "why it matters" rule templates ───────────────────────────────────────
# Each entry: (keyword_pattern, template)
# Templates may use {title} as a placeholder.

RULES: list[tuple[str, str]] = [
    # AI / LLM
    (r"\b(coding model|code gen|swe-bench|codegen)\b",
     "Directly impacts your AI-assisted coding workflow — new benchmarks or capabilities in code generation models are immediately actionable."),
    (r"\b(agentic|ai agent|autonomous|multi.agent)\b",
     "Agentic tools are changing how software gets built — worth knowing what's newly available and battle-tested."),
    (r"\b(llm|language model|grok|claude|gemini|mistral|llama|gpt)\b",
     "New or updated LLM releases affect tool choices across your entire stack — from IDE copilots to pipeline automation."),
    (r"\b(mcp|model context protocol|function calling|tool use)\b",
     "Expanding what LLMs can interact with — relevant if you're building or using agentic pipelines."),
    (r"\b(benchmark|leaderboard|arena|eval)\b",
     "Benchmarks cut through the hype — useful for choosing which model or tool to actually rely on."),
    # DevOps / SRE
    (r"\b(kubernetes|k8s|helm|argocd)\b",
     "Kubernetes ecosystem changes can surface new operational patterns or affect your existing clusters."),
    (r"\b(ebpf)\b",
     "eBPF is reshaping observability and security at the kernel level — worth tracking for production relevance."),
    (r"\b(ci.?cd|github.actions|gitops|terraform|iac)\b",
     "Automation and IaC improvements that could directly reduce toil in your delivery pipeline."),
    (r"\b(observability|otel|opentelemetry|tracing|metrics)\b",
     "Better visibility into your systems — new tooling or standards that reduce MTTR."),
    (r"\b(platform.engineer|idp|internal.developer.platform)\b",
     "Platform engineering patterns that improve developer experience and reduce cognitive load."),
    # Security
    (r"\b(zero.?day|cve|exploit|vulnerability|rce|ransomware)\b",
     "Active threat or newly disclosed vulnerability — assess whether it affects your environment."),
    (r"\b(supply.chain|dependency|sbom)\b",
     "Supply chain risks are often overlooked until it's too late — track these proactively."),
    (r"\b(devsecops|secret.management|zero.trust)\b",
     "Integrating security earlier in the lifecycle; useful practices worth adopting."),
    # SWE
    (r"\b(rust|wasm|webassembly)\b",
     "Rust/WASM continue to gain production adoption — worth knowing what's newly ergonomic."),
    (r"\b(architecture|system.design|distributed)\b",
     "Design patterns and lessons from production systems — high-leverage reading for senior engineers."),
    (r"\b(open.source|released|launches|v[0-9]+\.[0-9]+)\b",
     "New release or open-sourced project — quick scan to see if it belongs in your toolkit."),
    # Podcast
    (r"\b(podcast|episode|interview)\b",
     "Curated audio for your commute — scan the episode summary to decide if it earns queue time."),
    # HN / news fallback
    (r"\b(hacker.news|show.hn)\b",
     "Community-vetted signal from Hacker News — high upvote-to-age ratio means the engineering community found it worth reading."),
]

FALLBACK = "Flagged as relevant to your interests — read the summary to decide if it's worth your time."


def text_of(item: dict) -> str:
    return f"{item.get('title', '')} {item.get('summary', '')}".lower()


def why_matters(item: dict) -> str:
    text = text_of(item)
    for pattern, template in RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return template
    return FALLBACK


def load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data: Any) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def main() -> None:
    items = load_json(TOP10_FILE, [])
    if not items:
        log.warning("No top10 items to summarize.")
        return

    log.info("Summarizing %d items …", len(items))
    for item in items:
        item["why_matters"] = why_matters(item)
        log.info("  ✓ %s", item["title"][:70])

    save_json(TOP10_FILE, items)
    log.info("Updated %s with why_matters bullets", TOP10_FILE)


if __name__ == "__main__":
    main()
