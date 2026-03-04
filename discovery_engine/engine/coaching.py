"""Interview coaching engine — guide generation and quality scoring."""

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, render_prompt
from discovery_engine.llm.parsers import parse_llm_output
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview
from discovery_engine.models.coaching import InterviewGuide, InterviewQualityScore
from discovery_engine.schemas.coaching import InterviewGuideExtracted, QualityScoreExtracted


class CoachingEngine:
    """Generate interview guides and score interview quality."""

    def __init__(self, db: Session):
        self.db = db

    async def generate_guide(
        self,
        project_id: str,
        hypothesis: str,
        target_persona: str,
        existing_insights: str = "",
    ) -> InterviewGuide:
        """Generate a Mom Test interview guide."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        prompt = render_prompt(
            "interview_guide_generation.txt",
            hypothesis=hypothesis,
            target_persona=target_persona,
            existing_insights=existing_insights,
        )
        raw = await complete(prompt, tier="primary", task_type="coaching")
        parsed = parse_llm_output(raw, InterviewGuideExtracted)

        guide = InterviewGuide(
            project_id=project_id,
            title=parsed.title,
            hypothesis=hypothesis,
            target_persona=target_persona,
            opening_questions=parsed.opening_questions,
            deep_dive_questions=parsed.deep_dive_questions,
            validation_questions=parsed.validation_questions,
            anti_patterns_to_avoid=parsed.anti_patterns_to_avoid,
            success_criteria=parsed.success_criteria,
        )
        self.db.add(guide)
        self.db.commit()
        self.db.refresh(guide)
        return guide

    async def score_interview(self, interview_id: str) -> InterviewQualityScore:
        """Analyze interview quality post-interview."""
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        if not interview.transcript:
            raise ValueError("Interview has no transcript")

        prompt = render_prompt(
            "interview_quality_scoring.txt",
            transcript=interview.transcript,
        )
        raw = await complete(prompt, tier="primary", task_type="coaching")
        parsed = parse_llm_output(raw, QualityScoreExtracted)

        score = InterviewQualityScore(
            interview_id=interview_id,
            overall_score=parsed.overall_score,
            mom_test_compliance=parsed.mom_test_compliance,
            question_quality=parsed.question_quality,
            insight_depth=parsed.insight_depth,
            bias_score=parsed.bias_score,
            leading_questions_found=parsed.leading_questions_found,
            missed_opportunities=parsed.missed_opportunities,
            strengths=parsed.strengths,
            suggestions=parsed.suggestions,
        )
        self.db.add(score)
        self.db.commit()
        self.db.refresh(score)
        return score
