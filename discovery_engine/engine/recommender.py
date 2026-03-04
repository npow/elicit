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
                supporting_interview_count=len(interviews),
                rationale=item.rationale,
                risks=item.risks,
                next_steps=item.next_steps,
            )
            self.db.add(rec)
            self.db.flush()

            # Build evidence chains from related extractions
            evidence = self._build_evidence_chains(rec, interview_ids)
            recommendations.append(rec)

        self.db.commit()
        return recommendations

    def _build_evidence_chains(
        self, recommendation: Recommendation, interview_ids: list[str]
    ) -> list[EvidenceChain]:
        """Link a recommendation back to supporting evidence from interviews."""
        chains = []

        # Find supporting jobs
        jobs = (
            self.db.query(Job)
            .filter(Job.interview_id.in_(interview_ids))
            .all()
        )
        for job in jobs:
            # Simple keyword matching for evidence linking
            if _text_overlap(recommendation.title + " " + recommendation.description, job.statement):
                chain = EvidenceChain(
                    recommendation_id=recommendation.id,
                    interview_id=job.interview_id,
                    evidence_type="job",
                    source_id=job.id,
                    quote=job.supporting_quote,
                    relevance_score=0.7,
                )
                self.db.add(chain)
                chains.append(chain)

        # Find supporting pain points
        pains = (
            self.db.query(PainPoint)
            .filter(PainPoint.interview_id.in_(interview_ids))
            .all()
        )
        for pain in pains:
            if _text_overlap(recommendation.title + " " + recommendation.description, pain.description):
                chain = EvidenceChain(
                    recommendation_id=recommendation.id,
                    interview_id=pain.interview_id,
                    evidence_type="pain",
                    source_id=pain.id,
                    quote=pain.supporting_quote,
                    relevance_score=0.7,
                )
                self.db.add(chain)
                chains.append(chain)

        return chains


def _text_overlap(text_a: str, text_b: str, threshold: int = 3) -> bool:
    """Check if two texts share enough significant words to be related."""
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "in", "on", "and", "or", "with", "that", "this", "it", "not", "be", "have", "has", "do", "does", "from", "they", "their", "i", "we", "you", "my", "our"}
    words_a = {w.lower() for w in text_a.split() if len(w) > 2 and w.lower() not in stop_words}
    words_b = {w.lower() for w in text_b.split() if len(w) > 2 and w.lower() not in stop_words}
    overlap = words_a & words_b
    return len(overlap) >= threshold
