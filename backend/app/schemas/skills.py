"""Pydantic schemas for the skills API."""

from pydantic import BaseModel


class SkillRead(BaseModel):
    id: str
    name: str
    category: str
    parent_skill_id: str | None
    description: str | None

    model_config = {"from_attributes": True}


class SkillTreeNode(BaseModel):
    """Skill with its direct children, for hierarchical views."""

    id: str
    name: str
    category: str
    parent_skill_id: str | None
    description: str | None
    children: list["SkillTreeNode"] = []

    model_config = {"from_attributes": True}
