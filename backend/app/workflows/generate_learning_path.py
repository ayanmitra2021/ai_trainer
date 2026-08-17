"""generate_learning_path workflow — Phase 12.1 / Phase 17.

Orchestrates: Skill Profiler → Domain Score computation → Curriculum Planner.

Phase 17: Quiz questions ARE now generated as part of path generation — see
POST /learning-paths/generate route which calls _run_quiz_batch_for_path after
this workflow completes.  This workflow returns the path; the route layer
handles exhaustion detection and quiz generation.

One workflow_runs row is written at the start; its status is updated to
completed or failed at the end.  Each agent writes its own agent_runs row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.base import ModelClient
from app.agents.curriculum_planner import CurriculumPlannerAgent
from app.agents.model_client import create_model_client
from app.agents.skill_profiler import SkillProfilerAgent
from app.agents.round_metrics import compute_domain_scores, compute_round_metrics
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationSkill,
    LearningPath,
    LearningPathItem,
    MasteryHistory,
    Practitioner,
    PractitionerCertificationGoal,
    PractitionerProfile,
    ProfileSkillAssessment,
    Skill,
    SkillProfileEvent,
    SkillProfileSnapshot,
    Item,
    WorkflowRun,
)
from app.schemas.learning_paths import (
    CertGoalContext,
    CurriculumPlannerInput,
    GenerateLearningPathResponse,
    RoundMetricsPerSkill,
    SkillProfilerInput,
    SkillScoreContext,
)


async def run_generate_learning_path(
    practitioner_id: str,
    db: AsyncSession,
    claude_client: ModelClient | None = None,
) -> GenerateLearningPathResponse:
    """Run the generate_learning_path workflow.

    Sequence:
      1. Write workflow_runs row (status=running)
      2. Skill Profiler — compute / refresh skill snapshots
      3. Curriculum Planner — order the learning path
      4. Persist learning_path + learning_path_items
      5. Compute certification domain scores from cert-evaluated quiz answers
      6. Mark workflow_runs completed (or failed on any exception)

    Phase 17: Quiz questions ARE now generated as part of path generation.
    The POST /learning-paths/generate route calls _run_quiz_batch_for_path
    after this workflow returns, handling exhaustion detection and difficulty
    adjustment automatically.
    """
    if claude_client is None:
        claude_client = create_model_client()
    workflow_run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # ── 1. Open workflow run ───────────────────────────────────────────────
    workflow_run = WorkflowRun(
        id=workflow_run_id,
        workflow_name="generate_learning_path",
        triggered_by=practitioner_id,
        status="running",
        started_at=now,
    )
    db.add(workflow_run)
    await db.commit()

    practitioner = await db.get(Practitioner, practitioner_id)
    if practitioner is None:
        workflow_run.status = "failed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        raise ValueError(f"Practitioner {practitioner_id} not found")

    try:
        result = await _run_steps(
            practitioner_id=practitioner_id,
            workflow_run_id=workflow_run_id,
            db=db,
            claude_client=claude_client,
        )
        workflow_run.status = "completed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        return result

    except Exception:
        workflow_run.status = "failed"
        workflow_run.completed_at = datetime.now(UTC)
        await db.commit()
        raise


async def _run_steps(
    practitioner_id: str,
    workflow_run_id: str,
    db: AsyncSession,
    claude_client: ModelClient,
) -> GenerateLearningPathResponse:
    # ── 2. Skill Profiler ─────────────────────────────────────────────────
    # Phase 9.4: fetch ONLY quiz_attempt events. Self-assessment, certification,
    # and project-history signals are no longer used to compute the radar —
    # mastery is driven exclusively by demonstrated quiz performance.
    # Self-assessment ratings stored in profile_skill_assessments are preserved
    # in the DB as part of the locked profile record but are not passed here.
    events_result = await db.execute(
        select(SkillProfileEvent)
        .where(
            SkillProfileEvent.practitioner_id == practitioner_id,
            SkillProfileEvent.source == "quiz_attempt",
        )
        .order_by(SkillProfileEvent.occurred_at.desc())
    )
    events = events_result.scalars().all()
    events_data = [
        {
            "skill_id": e.skill_id,
            "source": e.source,
            "signal_strength": float(e.signal_strength),
            "occurred_at": e.occurred_at.isoformat(),
            "metadata": e.metadata_,
        }
        for e in events
    ]

    # Phase 10.3: compute round metrics for all skills that have items
    # These are passed to the Skill Profiler as primary mastery signals.
    all_items_skills_result = await db.execute(
        select(Item.skill_id).distinct()
        .where(Item.skill_id != None)  # noqa: E711
    )
    skills_with_items = [row[0] for row in all_items_skills_result.all()]

    quiz_round_metrics: list[RoundMetricsPerSkill] = []
    for skill_id_with_items in skills_with_items:
        round_m = await compute_round_metrics(
            practitioner_id=practitioner_id,
            skill_id=skill_id_with_items,
            db=db,
        )
        if round_m.rounds_completed > 0:
            quiz_round_metrics.append(
                RoundMetricsPerSkill(
                    skill_id=skill_id_with_items,
                    rounds_completed=round_m.rounds_completed,
                    mastery_ceiling=round_m.mastery_ceiling,
                    weighted_accuracy=round_m.weighted_accuracy,
                    current_mastery_score=round_m.current_mastery_score,
                )
            )

    profiler_input = SkillProfilerInput(
        practitioner_id=practitioner_id,
        events=events_data,
        quiz_round_metrics=quiz_round_metrics,
    )
    profiler = SkillProfilerAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    profiler_output = await profiler.run(profiler_input)

    # Override profiler scores with round-metrics scores where available
    round_metrics_map = {rm.skill_id: rm for rm in quiz_round_metrics}
    for scored in profiler_output.skill_scores:
        if scored.skill_id in round_metrics_map:
            rm = round_metrics_map[scored.skill_id]
            scored.mastery_score = rm.current_mastery_score

    # ── 2b. Self-assessment initial seed ─────────────────────────────────────
    # For skills that have NO quiz rounds yet, seed mastery from the locked
    # profile's self-assessment ratings so the Skill Radar is not all-zero on
    # first load.  Scale factor 0.35 keeps initial estimates well below the
    # 50 % first-quiz ceiling, leaving clear room for quiz performance to drive
    # real change.  Skills that already have quiz data are never touched here.
    _SELF_ASSESSMENT_INITIAL_SCALE = 0.35

    # Load self-assessment ratings for the active profile (one DB round-trip).
    _sa_result = await db.execute(
        select(ProfileSkillAssessment)
        .join(PractitionerProfile, ProfileSkillAssessment.profile_id == PractitionerProfile.id)
        .where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    _assessment_map: dict[str, float] = {
        row.skill_id: float(row.signal_strength)
        for row in _sa_result.scalars().all()
    }

    # ── 3. Curriculum Planner ──────────────────────────────────────────────
    # Build skill score context from ALL skills in the catalog.
    # Skills the profiler scored get their real scores; everything else
    # defaults to mastery=0 / confidence=0 so the planner always has real
    # skill IDs to choose from and never has to invent them.
    all_skills_result = await db.execute(select(Skill))
    all_skills: list[Skill] = list(all_skills_result.scalars().all())
    valid_skill_ids: set[str] = {s.id for s in all_skills}

    profiler_score_map = {s.skill_id: s for s in profiler_output.skill_scores}

    skill_scores_context: list[SkillScoreContext] = []
    for skill in all_skills:
        if skill.id in profiler_score_map:
            scored = profiler_score_map[skill.id]
            skill_scores_context.append(
                SkillScoreContext(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    mastery_score=scored.mastery_score,
                    confidence=scored.confidence,
                )
            )
        else:
            # No profiler data yet — treat as completely unscored
            skill_scores_context.append(
                SkillScoreContext(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    mastery_score=0.0,
                    confidence=0.0,
                )
            )

    # Seed initial mastery from self-assessment for skills with no quiz data.
    # A skill is "quiz-naive" when it has no entry in round_metrics_map, meaning
    # the practitioner has never completed a full round of questions for it.
    # We never overwrite a skill that already has quiz-derived mastery.
    for skill_ctx in skill_scores_context:
        if (
            skill_ctx.skill_id not in round_metrics_map
            and skill_ctx.skill_id in _assessment_map
        ):
            skill_ctx.mastery_score = round(
                _assessment_map[skill_ctx.skill_id] * _SELF_ASSESSMENT_INITIAL_SCALE, 3
            )
            # Low confidence — self-reported, not yet quiz-verified
            if skill_ctx.confidence == 0.0:
                skill_ctx.confidence = 0.25

    # Upsert snapshots for ALL skills in the catalog (not just profiler-scored
    # ones). This ensures the Skill Radar always has data to display, even for
    # brand-new practitioners who have no skill_profile_events yet.
    now = datetime.now(UTC)
    for skill_ctx in skill_scores_context:
        existing = await db.get(
            SkillProfileSnapshot, (practitioner_id, skill_ctx.skill_id)
        )
        if existing is not None:
            existing.mastery_score = skill_ctx.mastery_score
            existing.confidence = skill_ctx.confidence
            existing.last_computed_at = now
        else:
            db.add(SkillProfileSnapshot(
                practitioner_id=practitioner_id,
                skill_id=skill_ctx.skill_id,
                mastery_score=skill_ctx.mastery_score,
                confidence=skill_ctx.confidence,
                last_computed_at=now,
            ))
    await db.flush()

    # Append mastery history rows for skills the Skill Profiler actually scored
    # (mastery_score > 0 means the profiler had real signal, not just a zero-pad).
    # These rows feed the ProgressTrendChart and the AdoptionTrendChart baseline.
    for skill_ctx in skill_scores_context:
        if skill_ctx.mastery_score > 0.0:
            db.add(MasteryHistory(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                skill_id=skill_ctx.skill_id,
                mastery_score=skill_ctx.mastery_score,
                recorded_at=now,
            ))
    await db.flush()

    # Fetch active profile once here — used for cert context and domain scoring below.
    active_profile_result = await db.execute(
        select(PractitionerProfile).where(
            PractitionerProfile.practitioner_id == practitioner_id,
            PractitionerProfile.is_active == True,  # noqa: E712
        )
    )
    active_profile = active_profile_result.scalar_one_or_none()

    # Resolve certification context — two sources in priority order:
    #
    # 1. Active profile's certification_id (locked at profile creation time).
    #    This is the authoritative source — it's the exam the practitioner has
    #    committed to and is always set for any locked profile.
    # 2. PractitionerCertificationGoal (any status) — fallback for practitioners
    #    who have a goal but no locked profile yet.
    #
    # The old filter `status == "selected"` was too strict: the Certification
    # Advisor sets status = "recommended", never "selected", so the cert context
    # was always None and the planner picked skills based on gap alone rather
    # than exam relevance.
    cert_goal_context: CertGoalContext | None = None

    # Source 1: active profile cert (preferred)
    cert_from_profile: Certification | None = None
    if active_profile is not None and active_profile.certification_id is not None:
        cert_from_profile = await db.get(
            Certification,
            active_profile.certification_id,
            options=[selectinload(Certification.certification_skills)],
        )

    if cert_from_profile is not None:
        # Phase 13.3: prefer agent_discovered skills; fall back to seed if none.
        _discovered_result = await db.execute(
            select(CertificationSkill).where(
                CertificationSkill.certification_id == cert_from_profile.id,
                CertificationSkill.source == "agent_discovered",
            )
        )
        _discovered = _discovered_result.scalars().all()
        _cert_skills_to_use = _discovered if _discovered else cert_from_profile.certification_skills

        skill_weights = {
            cs.skill_id: float(cs.weight)
            for cs in _cert_skills_to_use
        }
        cert_goal_context = CertGoalContext(
            certification_code=cert_from_profile.code,
            certification_name=cert_from_profile.name,
            status="selected",
            skill_weights=skill_weights,
        )
    else:
        # Source 2: any goal row (fallback)
        goal_result = await db.execute(
            select(PractitionerCertificationGoal)
            .options(
                selectinload(PractitionerCertificationGoal.certification).selectinload(
                    Certification.certification_skills
                )
            )
            .where(
                PractitionerCertificationGoal.practitioner_id == practitioner_id,
                PractitionerCertificationGoal.status.in_(["selected", "recommended"]),
            )
            .order_by(PractitionerCertificationGoal.selected_at.desc())
            .limit(1)
        )
        active_goal = goal_result.scalar_one_or_none()
        if active_goal is not None:
            cert = active_goal.certification
            skill_weights = {
                cs.skill_id: float(cs.weight)
                for cs in cert.certification_skills
            }
            cert_goal_context = CertGoalContext(
                certification_code=cert.code,
                certification_name=cert.name,
                status=active_goal.status,
                skill_weights=skill_weights,
            )

    planner_input = CurriculumPlannerInput(
        practitioner_id=practitioner_id,
        skill_scores=skill_scores_context,
        certification_goal=cert_goal_context,
    )
    planner = CurriculumPlannerAgent(
        client=claude_client, db_session=db, workflow_run_id=workflow_run_id
    )
    planner_output = await planner.run(planner_input)

    # Safety guard: drop any path items whose skill_id isn't in the DB.
    # This prevents FK violations if the model ignores the "don't invent IDs" rule.
    valid_path_items = [
        item for item in planner_output.path_items
        if item.skill_id in valid_skill_ids
    ]
    if len(valid_path_items) < len(planner_output.path_items):
        invalid_ids = [
            item.skill_id for item in planner_output.path_items
            if item.skill_id not in valid_skill_ids
        ]
        import logging
        logging.getLogger(__name__).warning(
            "Curriculum Planner returned %d invalid skill IDs (dropped): %s",
            len(invalid_ids), invalid_ids,
        )
        planner_output.path_items = valid_path_items

    # ── 4. Persist learning path ───────────────────────────────────────────
    # Mark any previously active paths as completed so there is exactly one
    # active path at a time.
    prev_paths_result = await db.execute(
        select(LearningPath).where(
            LearningPath.practitioner_id == practitioner_id,
            LearningPath.status == "active",
        )
    )
    for prev in prev_paths_result.scalars().all():
        prev.status = "completed"

    learning_path_id = str(uuid.uuid4())
    learning_path = LearningPath(
        id=learning_path_id,
        practitioner_id=practitioner_id,
        generated_at=datetime.now(UTC),
        status="active",
        workflow_run_id=workflow_run_id,
    )
    db.add(learning_path)
    await db.flush()

    for seq_order, path_item_spec in enumerate(planner_output.path_items):
        lp_item = LearningPathItem(
            id=str(uuid.uuid4()),
            learning_path_id=learning_path_id,
            skill_id=path_item_spec.skill_id,
            sequence_order=seq_order,
            resource_type=path_item_spec.resource_type,
            status="pending",
            rationale=path_item_spec.rationale,
        )
        db.add(lp_item)

    await db.flush()

    # ── 5. Compute domain scores from cert-evaluated quiz answers ──────────
    # Phase 10.3: after persisting the learning path, update domain scores
    # from any cert-evaluated quiz answers the practitioner has submitted.
    # active_profile was already fetched above (before cert context resolution).
    if active_profile is not None and active_profile.certification_id is not None:
        await compute_domain_scores(
            practitioner_id=practitioner_id,
            certification_id=active_profile.certification_id,
            db=db,
        )

    return GenerateLearningPathResponse(
        workflow_run_id=workflow_run_id,
        learning_path_id=learning_path_id,
        status="completed",
    )
