"""mcp-learning-portal — Local stdio MCP adapter for Learning Portal exports.

Exposes three tools: get_certifications, get_course_completions, get_self_assessment.
Reads flat JSON files from the directory set by LEARNING_PORTAL_DATA_DIR
(default: backend/data/learning_portal/). Each file is a JSON object keyed by
practitioner_id; unknown keys return an empty list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "learning_portal"


def _data_dir() -> Path:
    env = os.environ.get("LEARNING_PORTAL_DATA_DIR")
    return Path(env) if env else _DEFAULT_DATA_DIR


def _load_file(filename: str) -> dict:
    """Load a JSON export file, returning {} if the file doesn't exist yet."""
    path = _data_dir() / filename
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


mcp = FastMCP("mcp-learning-portal")


@mcp.tool()
def get_certifications(practitioner_id: str) -> dict:
    """Return completed certifications for a practitioner."""
    records = _load_file("certifications.json").get(practitioner_id, [])
    return {"practitioner_id": practitioner_id, "certifications": records}


@mcp.tool()
def get_course_completions(practitioner_id: str) -> dict:
    """Return course completions for a practitioner."""
    records = _load_file("course_completions.json").get(practitioner_id, [])
    return {"practitioner_id": practitioner_id, "completions": records}


@mcp.tool()
def get_self_assessment(practitioner_id: str) -> dict:
    """Return self-assessed skill levels for a practitioner."""
    records = _load_file("self_assessments.json").get(practitioner_id, [])
    return {"practitioner_id": practitioner_id, "assessments": records}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
