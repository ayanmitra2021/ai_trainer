"""Skill Profiler Agent — Step 2.4.

Turns skill_profile_events (plus optional MCP data from mcp-learning-portal)
into SkillProfilerOutput. Callers persist skill_profile_snapshots to DB.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.learning_paths import SkillProfilerInput, SkillProfilerOutput


class SkillProfilerAgent(Agent[SkillProfilerInput, SkillProfilerOutput]):
    """Synthesises raw evidence into per-skill mastery estimates."""

    name = "skill_profiler"
    model = "claude-sonnet-5"
    output_model = SkillProfilerOutput

    def _build_messages(self, input: SkillProfilerInput) -> list[dict[str, Any]]:
        events_json = json.dumps(input.events, indent=2, default=str)
        portal_data: dict[str, Any] = {}
        if input.portal_certifications:
            portal_data["certifications"] = input.portal_certifications
        if input.portal_completions:
            portal_data["course_completions"] = input.portal_completions
        if input.portal_self_assessments:
            portal_data["self_assessments"] = input.portal_self_assessments

        portal_section = ""
        if portal_data:
            portal_json = json.dumps(portal_data, indent=2, default=str)
            portal_section = (
                f"\n\n## Learning portal data\n\n```json\n{portal_json}\n```"
            )

        return [
            {
                "role": "user",
                "content": (
                    f"## Skill profile events for practitioner `{input.practitioner_id}`\n\n"
                    f"```json\n{events_json}\n```"
                    f"{portal_section}\n\n"
                    "Please synthesise these signals into skill mastery estimates."
                ),
            }
        ]
