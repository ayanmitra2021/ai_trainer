"""Skill Profiler Agent — Step 2.4.

Turns quiz-attempt skill_profile_events into SkillProfilerOutput.
Callers persist skill_profile_snapshots to DB.

Phase 9.4: the profiler now reads quiz_attempt events ONLY. Self-assessment,
certification, and project-history signals are no longer passed to this agent
or reflected in the Skill Radar. The workflow (generate_learning_path.py)
filters events to source='quiz_attempt' before building the profiler input.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.learning_paths import SkillProfilerInput, SkillProfilerOutput


class SkillProfilerAgent(Agent[SkillProfilerInput, SkillProfilerOutput]):
    """Synthesises quiz-attempt evidence into per-skill mastery estimates."""

    name = "skill_profiler"
    model = "claude-sonnet-5"
    output_model = SkillProfilerOutput

    def _build_messages(self, input: SkillProfilerInput) -> list[dict[str, Any]]:
        events_json = json.dumps(input.events, indent=2, default=str)

        return [
            {
                "role": "user",
                "content": (
                    f"## Quiz attempt events for practitioner `{input.practitioner_id}`\n\n"
                    f"```json\n{events_json}\n```\n\n"
                    "Please synthesise these quiz results into skill mastery estimates."
                ),
            }
        ]
