"""Curriculum Planner Agent — Step 2.5.

Turns a skill profile snapshot into an ordered learning path. Callers persist
learning_paths and learning_path_items to DB.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.learning_paths import CurriculumPlannerInput, CurriculumPlannerOutput


class CurriculumPlannerAgent(Agent[CurriculumPlannerInput, CurriculumPlannerOutput]):
    """Orders the skills a practitioner should work on next."""

    name = "curriculum_planner"
    model = "claude-sonnet-5"
    output_model = CurriculumPlannerOutput

    def _build_messages(self, input: CurriculumPlannerInput) -> list[dict[str, Any]]:
        scores_json = json.dumps(
            [s.model_dump() for s in input.skill_scores], indent=2
        )
        goal_section = ""
        if input.certification_goal is not None:
            goal_json = json.dumps(input.certification_goal.model_dump(), indent=2)
            goal_section = (
                f"\n\n## Active certification goal\n\n```json\n{goal_json}\n```"
            )

        return [
            {
                "role": "user",
                "content": (
                    f"## Skill scores for practitioner `{input.practitioner_id}`\n\n"
                    f"```json\n{scores_json}\n```"
                    f"{goal_section}\n\n"
                    "Please produce an ordered learning path for this practitioner."
                ),
            }
        ]
