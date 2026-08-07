"""Nudge Campaign Composer Agent — Step 7.3.

Composes a campaign nudge message from category context. Never sees individual
practitioner names or emails — only the category description, tone hint, and
recipient count.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent
from app.schemas.nudge_campaign import NudgeCampaignComposerInput, NudgeCampaignComposerOutput


class NudgeCampaignComposerAgent(Agent[NudgeCampaignComposerInput, NudgeCampaignComposerOutput]):
    """Drafts campaign nudge subject + body from category context."""

    name = "nudge_campaign_composer"
    model = "claude-sonnet-4-5"
    output_model = NudgeCampaignComposerOutput

    def _build_messages(self, input: NudgeCampaignComposerInput) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": (
                    f"## Nudge campaign brief\n\n"
                    f"**Target group:** {input.category_description}\n"
                    f"**Recipient count:** {input.recipient_count}\n"
                    f"**Tone guidance:** {input.tone_hint}\n\n"
                    "Please draft an email subject line and body for this nudge campaign."
                ),
            }
        ]
