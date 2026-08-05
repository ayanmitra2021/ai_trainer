"""Skills API — skill graph read endpoints.

Step 2.1 scenario:
  - The skill graph endpoint preserves hierarchy — child skills correctly
    reference their parent_skill_id.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Skill
from app.db.session import get_db
from app.schemas.skills import SkillRead, SkillTreeNode

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillRead])
async def list_skills(db: AsyncSession = Depends(get_db)) -> list[SkillRead]:
    """Return all skills as a flat list, preserving parent_skill_id references."""
    result = await db.execute(
        select(Skill).order_by(Skill.category, Skill.name)
    )
    skills = result.scalars().all()
    return [SkillRead.model_validate(s) for s in skills]


@router.get("/tree", response_model=list[SkillTreeNode])
async def skill_tree(db: AsyncSession = Depends(get_db)) -> list[SkillTreeNode]:
    """Return skills as a tree — root nodes (parent_skill_id=None) with children nested."""
    result = await db.execute(
        select(Skill).order_by(Skill.category, Skill.name)
    )
    all_skills = result.scalars().all()

    # Build nodes indexed by id
    node_by_id: dict[str, SkillTreeNode] = {
        s.id: SkillTreeNode(
            id=s.id,
            name=s.name,
            category=s.category,
            parent_skill_id=s.parent_skill_id,
            description=s.description,
        )
        for s in all_skills
    }

    roots: list[SkillTreeNode] = []
    for skill in all_skills:
        node = node_by_id[skill.id]
        if skill.parent_skill_id is None:
            roots.append(node)
        else:
            parent = node_by_id.get(skill.parent_skill_id)
            if parent is not None:
                parent.children.append(node)

    return roots
