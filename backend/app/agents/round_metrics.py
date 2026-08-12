"""Round-based scoring utility — Step 10.7.

Computes per-round accuracy and the progressive mastery ceiling for a
practitioner × skill (or per certification domain).

Ceiling formula:   ceiling(N) = 1 - (0.5)^N
Weighted accuracy: Σ(accuracy[i] × 2^(i-1)) / Σ(2^(i-1))  (rounds 1-indexed)
Mastery score:     ceiling(N) × weighted_accuracy
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attempt, Item

if TYPE_CHECKING:
    pass

# Threshold for trend indicators — changes within ±1% are "stable"
TREND_DELTA_THRESHOLD = 0.01


@dataclass
class RoundMetrics:
    rounds_completed: int
    per_round_accuracy: list[float]
    mastery_ceiling: float
    weighted_accuracy: float
    current_mastery_score: float
    previous_mastery_score: float | None  # from previous skill_profile_snapshots row


def compute_ceiling(rounds_completed: int) -> float:
    """ceiling(N) = 1 - (0.5)^N. Returns 0.0 for 0 rounds."""
    if rounds_completed == 0:
        return 0.0
    return 1.0 - (0.5 ** rounds_completed)


def compute_weighted_accuracy(per_round_accuracy: list[float]) -> float:
    """Recency-weighted accuracy. Round i (1-indexed) has weight 2^(i-1)."""
    if not per_round_accuracy:
        return 0.0
    weights = [2 ** i for i in range(len(per_round_accuracy))]
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(acc * w for acc, w in zip(per_round_accuracy, weights))
    return weighted_sum / total_weight


async def compute_round_metrics(
    practitioner_id: str,
    skill_id: str,
    db: AsyncSession,
    previous_mastery_score: float | None = None,
) -> RoundMetrics:
    """Compute round-based mastery metrics for a practitioner × skill pair.

    Queries attempts joined to items to determine which generations are fully
    completed (all items in that generation attempted at least once) and computes
    the recency-weighted accuracy across completed rounds.
    """
    # Fetch all items for this skill, grouped by generation
    items_result = await db.execute(
        select(Item.id, Item.generation)
        .where(Item.skill_id == skill_id)
    )
    items_rows = items_result.all()

    if not items_rows:
        return RoundMetrics(
            rounds_completed=0,
            per_round_accuracy=[],
            mastery_ceiling=0.0,
            weighted_accuracy=0.0,
            current_mastery_score=0.0,
            previous_mastery_score=previous_mastery_score,
        )

    # Group item IDs by generation
    items_by_generation: dict[int, list[str]] = defaultdict(list)
    for item_id, generation in items_rows:
        items_by_generation[generation].append(item_id)

    # Fetch all attempts for this practitioner on these items
    all_item_ids = [row[0] for row in items_rows]
    attempts_result = await db.execute(
        select(Attempt.item_id, Attempt.score)
        .where(
            Attempt.practitioner_id == practitioner_id,
            Attempt.item_id.in_(all_item_ids),
        )
    )
    attempt_rows = attempts_result.all()

    # Build a map: item_id -> list of scores (could be multiple attempts)
    attempts_by_item: dict[str, list[float]] = defaultdict(list)
    for item_id, score in attempt_rows:
        attempts_by_item[item_id].append(float(score))

    # Determine completed rounds (all items in generation have ≥1 attempt)
    per_round_accuracy: list[float] = []
    for gen in sorted(items_by_generation.keys()):
        gen_items = items_by_generation[gen]
        all_attempted = all(item_id in attempts_by_item for item_id in gen_items)
        if not all_attempted:
            break  # stop at first incomplete generation
        # Accuracy for this round = mean of the most recent score per item
        gen_scores = [attempts_by_item[item_id][-1] for item_id in gen_items]
        gen_accuracy = sum(gen_scores) / len(gen_scores)
        per_round_accuracy.append(gen_accuracy)

    rounds_completed = len(per_round_accuracy)
    mastery_ceiling = compute_ceiling(rounds_completed)
    weighted_accuracy = compute_weighted_accuracy(per_round_accuracy)
    current_mastery_score = mastery_ceiling * weighted_accuracy

    return RoundMetrics(
        rounds_completed=rounds_completed,
        per_round_accuracy=per_round_accuracy,
        mastery_ceiling=mastery_ceiling,
        weighted_accuracy=weighted_accuracy,
        current_mastery_score=current_mastery_score,
        previous_mastery_score=previous_mastery_score,
    )


async def compute_domain_scores(
    practitioner_id: str,
    certification_id: str,
    db: AsyncSession,
) -> list[dict]:
    """Compute per-domain readiness scores from cert-evaluated quiz answers.

    Queries attempts joined to items where is_cert_evaluated=True and the item's
    certification_domain belongs to the given cert. Groups by domain, applies
    recency-weighted accuracy formula, and upserts certification_domain_scores.

    Returns list of {domain_id, mastery_score, source} dicts.
    """
    from app.db.models import CertificationDomain, CertificationDomainScore

    # Get all cert-evaluated items for this certification's domains
    domains_result = await db.execute(
        select(CertificationDomain.id).where(
            CertificationDomain.certification_id == certification_id
        )
    )
    domain_ids = [row[0] for row in domains_result.all()]
    if not domain_ids:
        return []

    # Get cert-evaluated items in those domains
    items_result = await db.execute(
        select(Item.id, Item.certification_domain_id, Item.generation)
        .where(
            Item.certification_domain_id.in_(domain_ids),
            Item.is_cert_evaluated == True,  # noqa: E712
        )
    )
    items_rows = items_result.all()
    if not items_rows:
        return []

    # Fetch attempts for these items by this practitioner
    item_ids = [row[0] for row in items_rows]
    attempts_result = await db.execute(
        select(Attempt.item_id, Attempt.score, Attempt.attempted_at)
        .where(
            Attempt.practitioner_id == practitioner_id,
            Attempt.item_id.in_(item_ids),
        )
        .order_by(Attempt.attempted_at.asc())
    )
    attempt_rows = attempts_result.all()

    # Build item -> domain mapping and item -> generation mapping
    item_domain: dict[str, str] = {}
    item_generation: dict[str, int] = {}
    for item_id, domain_id, generation in items_rows:
        item_domain[item_id] = domain_id
        item_generation[item_id] = generation

    # Build domain -> {generation -> [scores]} mapping
    domain_gen_scores: dict[str, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item_id, score, _ in attempt_rows:
        domain_id = item_domain.get(item_id)
        generation = item_generation.get(item_id, 1)
        if domain_id:
            domain_gen_scores[domain_id][generation].append(float(score))

    results = []
    now = datetime.now(UTC)

    for domain_id in domain_ids:
        if domain_id not in domain_gen_scores:
            continue  # no cert-evaluated attempts for this domain

        gen_scores = domain_gen_scores[domain_id]
        # Compute per-round accuracy (only completed rounds)
        per_round_accuracy = []
        for gen in sorted(gen_scores.keys()):
            scores = gen_scores[gen]
            if scores:
                per_round_accuracy.append(sum(scores) / len(scores))

        if not per_round_accuracy:
            continue

        rounds_completed = len(per_round_accuracy)
        ceiling = compute_ceiling(rounds_completed)
        weighted_acc = compute_weighted_accuracy(per_round_accuracy)
        mastery_score = ceiling * weighted_acc

        # Upsert certification_domain_scores — never overwrite quiz_derived with estimate
        existing_result = await db.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner_id,
                CertificationDomainScore.certification_domain_id == domain_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            # Save current score as previous before updating
            existing.previous_mastery_score = float(existing.mastery_score)
            existing.mastery_score = mastery_score
            existing.confidence = min(0.9, weighted_acc)  # quiz-derived can go high
            existing.source = "quiz_derived"
            existing.last_computed_at = now
        else:
            new_score = CertificationDomainScore(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner_id,
                certification_domain_id=domain_id,
                mastery_score=mastery_score,
                confidence=min(0.9, weighted_acc),
                source="quiz_derived",
                last_computed_at=now,
            )
            db.add(new_score)

        results.append({
            "domain_id": domain_id,
            "mastery_score": mastery_score,
            "source": "quiz_derived",
        })

    await db.flush()
    return results
