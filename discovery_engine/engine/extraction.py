"""Extraction engine — JTBD, pain points, workarounds from a single transcript."""

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, render_prompt
from discovery_engine.llm.parsers import parse_llm_list
from discovery_engine.models.interview import Interview
from discovery_engine.models.extraction import Job, PainPoint, Workaround, Opportunity
from discovery_engine.schemas.extraction import (
    JobExtracted,
    PainPointExtracted,
    WorkaroundExtracted,
    OpportunityExtracted,
)
from discovery_engine.schemas.normalization import text_similarity


class ExtractionEngine:
    """Extract structured insights from a single interview transcript."""

    def __init__(self, db: Session):
        self.db = db

    async def extract_jobs(self, interview: Interview) -> list[Job]:
        """Extract Jobs-to-be-Done from transcript."""
        prompt = render_prompt("jtbd_extraction.txt", transcript=interview.transcript)
        raw = await complete(prompt, tier="primary", task_type="extraction")
        parsed = parse_llm_list(raw, JobExtracted)

        jobs = []
        for item in parsed:
            job = Job(
                interview_id=interview.id,
                statement=item.statement,
                context=item.context,
                frequency=item.frequency,
                importance=item.importance,
                satisfaction=item.satisfaction,
                supporting_quote=item.supporting_quote,
                confidence=_confidence_or_default(item.confidence, default=0.72),
            )
            self.db.add(job)
            jobs.append(job)
        return jobs

    async def extract_pain_points(self, interview: Interview) -> list[PainPoint]:
        """Extract pain points from transcript."""
        prompt = render_prompt("pain_point_extraction.txt", transcript=interview.transcript)
        raw = await complete(prompt, tier="primary", task_type="extraction")
        parsed = parse_llm_list(raw, PainPointExtracted)

        pains = []
        for item in parsed:
            pain = PainPoint(
                interview_id=interview.id,
                description=item.description,
                severity=item.severity,
                frequency=item.frequency,
                emotional_intensity=item.emotional_intensity,
                supporting_quote=item.supporting_quote,
                confidence=_confidence_or_default(item.confidence, default=0.72),
            )
            self.db.add(pain)
            pains.append(pain)
        return pains

    async def extract_workarounds(self, interview: Interview) -> list[Workaround]:
        """Extract workarounds from transcript."""
        prompt = render_prompt("workaround_detection.txt", transcript=interview.transcript)
        raw = await complete(prompt, tier="primary", task_type="extraction")
        parsed = parse_llm_list(raw, WorkaroundExtracted)

        workarounds = []
        for item in parsed:
            wa = Workaround(
                interview_id=interview.id,
                description=item.description,
                tools_used=item.tools_used,
                effort_level=item.effort_level,
                satisfaction_with_workaround=item.satisfaction_with_workaround,
                supporting_quote=item.supporting_quote,
                confidence=_confidence_or_default(item.confidence, default=0.68),
            )
            self.db.add(wa)
            workarounds.append(wa)
        return workarounds

    async def extract_all(self, interview: Interview) -> dict:
        """Run all extraction steps on an interview and persist results."""
        # Replace prior extractions to keep reruns idempotent.
        self.db.query(Opportunity).filter(Opportunity.interview_id == interview.id).delete(synchronize_session=False)
        self.db.query(Workaround).filter(Workaround.interview_id == interview.id).delete(synchronize_session=False)
        self.db.query(PainPoint).filter(PainPoint.interview_id == interview.id).delete(synchronize_session=False)
        self.db.query(Job).filter(Job.interview_id == interview.id).delete(synchronize_session=False)

        try:
            jobs = await self.extract_jobs(interview)
            pains = await self.extract_pain_points(interview)
            workarounds = await self.extract_workarounds(interview)

            # Flush so jobs/pains have DB-assigned IDs before linking.
            self.db.flush()

            # Link pains to their closest job by text similarity.
            _link_pains_to_jobs(pains, jobs)

            # Link workarounds to their closest pain point.
            _link_workarounds_to_pains(workarounds, pains)

            # Map opportunities from the extractions (also links to jobs).
            opportunities = await self._map_opportunities(interview, jobs, pains, workarounds)

            interview.status = "analyzed"
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "jobs": jobs,
            "pain_points": pains,
            "workarounds": workarounds,
            "opportunities": opportunities,
        }

    async def _map_opportunities(
        self,
        interview: Interview,
        jobs: list[Job],
        pains: list[PainPoint],
        workarounds: list[Workaround],
    ) -> list[Opportunity]:
        """Map opportunities from extracted data."""
        jobs_data = [{"statement": j.statement, "importance": j.importance, "satisfaction": j.satisfaction} for j in jobs]
        pains_data = [{"description": p.description, "severity": p.severity} for p in pains]
        wa_data = [{"description": w.description, "effort_level": w.effort_level} for w in workarounds]

        prompt = render_prompt(
            "opportunity_mapping.txt",
            jobs=jobs_data,
            pain_points=pains_data,
            workarounds=wa_data,
        )
        raw = await complete(prompt, tier="primary", task_type="extraction")
        parsed = parse_llm_list(raw, OpportunityExtracted)

        opps = []
        for item in parsed:
            opp = Opportunity(
                interview_id=interview.id,
                description=item.description,
                opportunity_score=item.opportunity_score,
                importance_score=item.importance_score,
                satisfaction_score=item.satisfaction_score,
                market_size_indicator=item.market_size_indicator,
                level=item.level,
                confidence=_confidence_or_default(item.confidence, default=0.65),
            )
            self.db.add(opp)
            opps.append(opp)

        # Flush to get opportunity IDs, then link each to its best-matching job.
        self.db.flush()
        if jobs:
            for opp, item in zip(opps, parsed):
                if item.related_job_statement:
                    best_job, score = _best_match(item.related_job_statement, jobs, lambda j: j.statement)
                    if best_job and score >= 0.05:
                        opp.related_job_id = best_job.id

        return opps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _confidence_or_default(value: float | None, default: float) -> float:
    """Return value if it's a usable float ≥ 0, else return default."""
    if value is None:
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return default if num < 0 else num  # 0.0 is valid (completely uncertain)


def _best_match(query: str, candidates: list, key_fn) -> tuple:
    """Return (candidate, score) with highest text similarity to query."""
    best, best_score = None, 0.0
    for c in candidates:
        score = text_similarity(query, key_fn(c))
        if score > best_score:
            best, best_score = c, score
    return best, best_score


def _link_pains_to_jobs(pains: list[PainPoint], jobs: list[Job]) -> None:
    """Set related_job_id on each pain point using text similarity."""
    if not jobs or not pains:
        return
    for pain in pains:
        best_job, score = _best_match(pain.description, jobs, lambda j: j.statement)
        if best_job and score >= 0.05:
            pain.related_job_id = best_job.id


def _link_workarounds_to_pains(workarounds: list[Workaround], pains: list[PainPoint]) -> None:
    """Set related_pain_id on each workaround using text similarity."""
    if not pains or not workarounds:
        return
    for wa in workarounds:
        best_pain, score = _best_match(wa.description, pains, lambda p: p.description)
        if best_pain and score >= 0.05:
            wa.related_pain_id = best_pain.id
