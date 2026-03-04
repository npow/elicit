"""Recommendation engine — "Build this next" with evidence chains."""

import json

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, render_prompt
from discovery_engine.llm.parsers import parse_llm_list
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview
from discovery_engine.models.extraction import Job, PainPoint, Workaround, Opportunity
from discovery_engine.models.synthesis import CrossInterviewPattern
from discovery_engine.models.recommendation import Recommendation, EvidenceChain
from discovery_engine.schemas.recommendation import RecommendationExtracted
from discovery_engine.schemas.normalization import text_similarity

# Minimum Jaccard similarity for an extraction to count as supporting evidence.
_EVIDENCE_THRESHOLD = 0.06
# Maximum total evidence items per recommendation (ranked by relevance).
_MAX_EVIDENCE = 12


class RecommendationEngine:
    """Generate prioritized product recommendations from patterns and opportunities."""

    def __init__(self, db: Session):
        self.db = db

    async def generate(self, project_id: str) -> list[Recommendation]:
        """Generate recommendations for a project based on patterns and opportunities."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        patterns = (
            self.db.query(CrossInterviewPattern)
            .filter(CrossInterviewPattern.project_id == project_id)
            .all()
        )

        interviews = (
            self.db.query(Interview)
            .filter(Interview.project_id == project_id, Interview.status == "analyzed")
            .all()
        )
        interview_ids = [i.id for i in interviews]

        opportunities = (
            self.db.query(Opportunity)
            .filter(Opportunity.interview_id.in_(interview_ids))
            .order_by(Opportunity.opportunity_score.desc())
            .all()
        )

        patterns_data = [
            {
                "pattern_type": p.pattern_type,
                "description": p.description,
                "frequency_count": p.frequency_count,
                "strength": p.strength,
            }
            for p in patterns
        ]

        opps_data = [
            {
                "description": o.description,
                "opportunity_score": o.opportunity_score,
                "importance_score": o.importance_score,
                "satisfaction_score": o.satisfaction_score,
            }
            for o in opportunities[:20]  # Top 20 to keep prompt manageable
        ]

        prompt = render_prompt(
            "recommendation_generation.txt",
            patterns=json.dumps(patterns_data, indent=2),
            opportunities=json.dumps(opps_data, indent=2),
            project_hypothesis=project.hypothesis,
        )
        raw = await complete(prompt, tier="primary", task_type="recommendation")
        parsed = parse_llm_list(raw, RecommendationExtracted)
        if not parsed:
            parsed = self._fallback_recommendations(patterns, opportunities)

        # Delete old recommendations for this project and their evidence chains.
        existing_recommendations = (
            self.db.query(Recommendation.id)
            .filter(Recommendation.project_id == project_id)
            .all()
        )
        recommendation_ids = [rid for (rid,) in existing_recommendations]
        if recommendation_ids:
            self.db.query(EvidenceChain).filter(
                EvidenceChain.recommendation_id.in_(recommendation_ids)
            ).delete(synchronize_session=False)
            self.db.query(Recommendation).filter(
                Recommendation.id.in_(recommendation_ids)
            ).delete(synchronize_session=False)

        recommendations = []
        for rank, item in enumerate(parsed, 1):
            rec = Recommendation(
                project_id=project_id,
                title=item.title,
                description=item.description,
                priority_score=item.priority_score,
                priority_rank=rank,
                category=item.category,
                confidence=item.confidence,
                supporting_interview_count=0,
                rationale=item.rationale,
                risks=item.risks,
                next_steps=item.next_steps,
            )
            self.db.add(rec)
            self.db.flush()

            # Build evidence chains from related extractions
            evidence = self._build_evidence_chains(rec, interview_ids)
            rec.supporting_interview_count = len({c.interview_id for c in evidence})
            recommendations.append(rec)

        self.db.commit()
        return recommendations

    def _fallback_recommendations(
        self,
        patterns: list[CrossInterviewPattern],
        opportunities: list[Opportunity],
    ) -> list[RecommendationExtracted]:
        """Deterministic fallback recommendations when LLM parsing yields no items."""
        recs: list[RecommendationExtracted] = []

        # opportunity_score is 0-20 per the prompt specification.
        for opp in opportunities[:5]:
            raw = opp.opportunity_score or 0.0
            normalized = min(1.0, raw / 20.0)  # opportunity_score is always 0-20
            recs.append(
                RecommendationExtracted(
                    title=f"Address: {opp.description[:90]}",
                    description=(
                        "Prioritize a focused solution for this recurring opportunity and validate it "
                        "with a small experiment tied to measurable outcomes."
                    ),
                    priority_score=max(0.1, float(normalized)),
                    category="build_now",
                    confidence=0.65,
                    rationale="Derived from top opportunity scoring across analyzed interviews.",
                    risks="Risk of overfitting a single segment without follow-up validation.",
                    next_steps="Define MVP hypothesis, ship prototype, and run 5 targeted interviews.",
                )
            )
            if len(recs) >= 3:
                break

        if len(recs) < 3:
            for pattern in sorted(patterns, key=lambda p: p.strength or 0.0, reverse=True):
                recs.append(
                    RecommendationExtracted(
                        title=f"Exploit recurring pattern: {pattern.description[:80]}",
                        description=(
                            "Translate this cross-interview pattern into a concrete product bet with "
                            "clear success metrics."
                        ),
                        priority_score=max(0.1, min(0.9, pattern.strength or 0.0)),
                        category="iterate",
                        confidence=max(0.55, min(0.85, pattern.confidence or 0.6)),
                        rationale="Pattern recurs across multiple interviews.",
                        risks="Pattern may be too broad without segment-specific scoping.",
                        next_steps="Define segment, design experiment, and instrument adoption/failure signals.",
                    )
                )
                if len(recs) >= 3:
                    break

        return recs

    def _build_evidence_chains(
        self, recommendation: Recommendation, interview_ids: list[str]
    ) -> list[EvidenceChain]:
        """Link a recommendation to supporting evidence using text similarity."""
        rec_text = recommendation.title + " " + recommendation.description
        candidates: list[tuple[float, str, str, str, str]] = []
        # (relevance, evidence_type, interview_id, source_id, quote)

        jobs = self.db.query(Job).filter(Job.interview_id.in_(interview_ids)).all()
        for job in jobs:
            score = text_similarity(rec_text, job.statement + " " + (job.supporting_quote or ""))
            if score >= _EVIDENCE_THRESHOLD:
                candidates.append((score, "job", job.interview_id, job.id, job.supporting_quote or job.statement))

        pains = self.db.query(PainPoint).filter(PainPoint.interview_id.in_(interview_ids)).all()
        for pain in pains:
            score = text_similarity(rec_text, pain.description + " " + (pain.supporting_quote or ""))
            if score >= _EVIDENCE_THRESHOLD:
                candidates.append((score, "pain", pain.interview_id, pain.id, pain.supporting_quote or pain.description))

        workarounds = self.db.query(Workaround).filter(Workaround.interview_id.in_(interview_ids)).all()
        for wa in workarounds:
            score = text_similarity(rec_text, wa.description + " " + (wa.supporting_quote or ""))
            if score >= _EVIDENCE_THRESHOLD:
                candidates.append((score, "workaround", wa.interview_id, wa.id, wa.supporting_quote or wa.description))

        opportunities = self.db.query(Opportunity).filter(Opportunity.interview_id.in_(interview_ids)).all()
        for opp in opportunities:
            score = text_similarity(rec_text, opp.description)
            if score >= _EVIDENCE_THRESHOLD:
                candidates.append((score, "opportunity", opp.interview_id, opp.id, opp.description))

        # Keep only the top-N most relevant, sorted by score descending.
        candidates.sort(key=lambda x: x[0], reverse=True)
        chains = []
        for relevance, ev_type, interview_id, source_id, quote in candidates[:_MAX_EVIDENCE]:
            chain = EvidenceChain(
                recommendation_id=recommendation.id,
                interview_id=interview_id,
                evidence_type=ev_type,
                source_id=source_id,
                quote=quote,
                relevance_score=round(relevance, 3),
            )
            self.db.add(chain)
            chains.append(chain)

        return chains
