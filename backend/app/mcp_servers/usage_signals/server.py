"""mcp-usage-signals — Local stdio MCP adapter for usage signal exports.

Exposes two tools: get_claude_code_sessions, get_commit_activity.
Reads flat JSON files from the directory set by USAGE_SIGNALS_DATA_DIR
(default: backend/data/usage_signals/). Each file is a JSON object keyed by
practitioner_id; unknown keys return an empty list.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mapping rule
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Goal: infer which skill node a session or commit most likely represents evidence
of *applying*, so the Adoption Pulse can compare it against the practitioner's
training record for that skill.

For SESSIONS the text signals examined (in priority order) are:
  1. project_type  (if present — explicit project tag; highest confidence)
  2. description   (free text; lower confidence)

For COMMITS the text signals examined (in priority order) are:
  1. repo name            (explicit; highest confidence)
  2. commit message       (lower confidence)
  3. changed file paths   (lowest confidence; matched together as a blob)

Keyword → skill_id table
  ┌────────────────────────────────────────┬──────────────────────────┐
  │ Keywords (case-insensitive, substring) │ skill_id                 │
  ├────────────────────────────────────────┼──────────────────────────┤
  │ rag, retrieval-augmented,              │ rag_fundamentals         │
  │ retrieval augmented, embedding,        │                          │
  │ vector search, semantic search         │                          │
  ├────────────────────────────────────────┼──────────────────────────┤
  │ prompt engineering, chain of thought,  │ prompt_engineering       │
  │ chain-of-thought, few-shot, zero-shot, │                          │
  │ system prompt, prompt template         │                          │
  ├────────────────────────────────────────┼──────────────────────────┤
  │ claude api, messages api,              │ claude_api_usage         │
  │ anthropic sdk, streaming response,     │                          │
  │ vision api                             │                          │
  ├────────────────────────────────────────┼──────────────────────────┤
  │ agentic, tool use, function calling,   │ agent_building           │
  │ mcp server, multi-agent                │                          │
  ├────────────────────────────────────────┼──────────────────────────┤
  │ fine-tuning, fine tuning, finetuning,  │ model_fine_tuning        │
  │ training data, model training, rlhf    │                          │
  └────────────────────────────────────────┴──────────────────────────┘

Confidence
  "high"  — a keyword was found in the primary signal (project_type / repo name)
  "low"   — a keyword was found only in secondary/tertiary signals
  null    — unmapped

Disambiguation policy
  A session or commit is mapped ONLY when EXACTLY ONE skill group matches the
  combined text. Ambiguous items (multiple skills matched) are returned with
  skill_id: null and confidence: null — they are NOT guessed.

  Rationale: false negatives (missed adoption) are less harmful than false
  positives (wrongly crediting adoption of a skill the practitioner didn't
  actually apply). The Correlation Agent is the ethically load-bearing step;
  feeding it clean, conservative data is the right call here.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "usage_signals"


def _data_dir() -> Path:
    env = os.environ.get("USAGE_SIGNALS_DATA_DIR")
    return Path(env) if env else _DEFAULT_DATA_DIR


def _load_file(filename: str) -> dict:
    """Load a JSON export file, returning {} if the file doesn't exist yet."""
    path = _data_dir() / filename
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


_SKILL_KEYWORDS: dict[str, list[str]] = {
    "rag_fundamentals": [
        "rag",
        "retrieval-augmented",
        "retrieval augmented",
        "embedding",
        "vector search",
        "semantic search",
    ],
    "prompt_engineering": [
        "prompt engineering",
        "chain of thought",
        "chain-of-thought",
        "few-shot",
        "zero-shot",
        "system prompt",
        "prompt template",
    ],
    "claude_api_usage": [
        "claude api",
        "messages api",
        "anthropic sdk",
        "streaming response",
        "vision api",
    ],
    "agent_building": [
        "agentic",
        "tool use",
        "function calling",
        "mcp server",
        "multi-agent",
    ],
    "model_fine_tuning": [
        "fine-tuning",
        "fine tuning",
        "finetuning",
        "training data",
        "model training",
        "rlhf",
    ],
}


def _infer_skill_id(
    primary_signal: str,
    secondary_signals: list[str],
) -> tuple[str | None, str | None]:
    """Return (skill_id, confidence), both None when unmapped or ambiguous."""
    combined = " ".join([primary_signal] + secondary_signals).lower()
    matched = [
        skill_id
        for skill_id, keywords in _SKILL_KEYWORDS.items()
        if any(kw.lower() in combined for kw in keywords)
    ]

    if len(matched) != 1:
        return None, None

    skill_id = matched[0]
    confidence = (
        "high"
        if any(kw.lower() in primary_signal.lower() for kw in _SKILL_KEYWORDS[skill_id])
        else "low"
    )
    return skill_id, confidence


def _map_session(session: dict) -> dict:
    """Return the session dict extended with skill_id and confidence."""
    skill_id, confidence = _infer_skill_id(
        session.get("project_type") or "",
        [session.get("description") or ""],
    )
    return {**session, "skill_id": skill_id, "confidence": confidence}


def _map_commit(commit: dict) -> dict:
    """Return the commit dict extended with skill_id and confidence."""
    skill_id, confidence = _infer_skill_id(
        commit.get("repo") or "",
        [
            commit.get("message") or "",
            " ".join(commit.get("files_changed") or []),
        ],
    )
    return {**commit, "skill_id": skill_id, "confidence": confidence}


mcp = FastMCP("mcp-usage-signals")


@mcp.tool()
def get_claude_code_sessions(practitioner_id: str) -> dict:
    """Return Claude Code sessions for a practitioner with inferred skill mappings.

    Each session includes skill_id and confidence (see module docstring for the rule).
    """
    raw = _load_file("sessions.json").get(practitioner_id, [])
    return {"practitioner_id": practitioner_id, "sessions": [_map_session(s) for s in raw]}


@mcp.tool()
def get_commit_activity(practitioner_id: str) -> dict:
    """Return git commit activity for a practitioner with inferred skill mappings.

    Each commit includes skill_id and confidence (see module docstring for the rule).
    """
    raw = _load_file("commits.json").get(practitioner_id, [])
    return {"practitioner_id": practitioner_id, "commits": [_map_commit(c) for c in raw]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
