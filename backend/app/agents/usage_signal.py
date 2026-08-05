"""Usage-Signal Agent — Step 3.1.

Ingests raw usage evidence from mcp-usage-signals (pre-fetched by the workflow)
and normalizes it into structured NormalizedEvent records. Callers persist
usage_events rows to the database.

Model: Haiku 4.5 — high-volume classification/normalization task.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.pulse import UsageSignalInput, UsageSignalOutput


class UsageSignalAgent(Agent[UsageSignalInput, UsageSignalOutput]):
    """Normalizes raw MCP usage signals into structured usage events."""

    name = "usage_signal"
    model = "claude-haiku-4-5-20251001"
    output_model = UsageSignalOutput

    def _build_messages(self, input: UsageSignalInput) -> list[dict[str, Any]]:
        signals_json = json.dumps(
            [s.model_dump() for s in input.raw_signals], indent=2, default=str
        )
        skills_json = json.dumps(input.known_skills, indent=2)

        return [
            {
                "role": "user",
                "content": (
                    f"## Usage signals for practitioner `{input.practitioner_id}`\n\n"
                    f"```json\n{signals_json}\n```\n\n"
                    f"## Known skills (current skill graph)\n\n"
                    f"```json\n{skills_json}\n```\n\n"
                    "Please normalize these signals into structured usage events."
                ),
            }
        ]
