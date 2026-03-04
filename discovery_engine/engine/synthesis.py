"""Cross-interview pattern detection engine."""

import json

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, render_prompt
from discovery_engine.llm.parsers import parse_llm_list
from discovery_engine.models.interview import Interview
from discovery_engine.models.extraction import Job, PainPoint, Workaround
from discovery_engine.models.synthesis import CrossInterviewPattern


class SynthesisEngine:
    """Detect patterns across multiple interviews in a project."""

    def __init__(self, db: Session):
        self.db = db

    async def synthesize(self, project_id: str) -> list[CrossInterviewPattern]:
        """Run cross-interview synthesis for a project.

        Requires at least 2 analyzed interviews.
        """
        interviews = (
            self.db.query(Interview)
            .filter(Interview.project_id == project_id, Interview.status == "analyzed")
            .all()
        )

        if len(interviews) < 2:
            return []

        # Build data payload for each interview
        interviews_data = []
        for interview in interviews:
            jobs = self.db.query(Job).filter(Job.interview_id == interview.id).all()
            pains = self.db.query(PainPoint).filter(PainPoint.interview_id == interview.id).all()
            workarounds = self.db.query(Workaround).filter(Workaround.interview_id == interview.id).all()

            interviews_data.append({
                "interview_id": interview.id,
                "title": interview.title,
                "interviewee_role": interview.interviewee_role,
                "jobs": [{"id": j.id, "statement": j.statement, "importance": j.importance} for j in jobs],
                "pain_points": [{"id": p.id, "description": p.description, "severity": p.severity} for p in pains],
                "workarounds": [{"id": w.id, "description": w.description, "effort_level": w.effort_level} for w in workarounds],
            })

        prompt = render_prompt(
            "cross_interview_synthesis.txt",
            interviews_data=json.dumps(interviews_data, indent=2),
        )
        raw = await complete(prompt, tier="primary", task_type="synthesis")

        # Parse into a lightweight schema for validation
        from pydantic import BaseModel

        class PatternParsed(BaseModel):
            pattern_type: str = ""
            description: str
            frequency_count: int = 0
            interview_ids: list[str] = []
            strength: float = 0.0
            supporting_quotes: list[str] = []
            confidence: float = 0.0

        parsed = parse_llm_list(raw, PatternParsed)

        # Delete old patterns for this project and replace
        self.db.query(CrossInterviewPattern).filter(
            CrossInterviewPattern.project_id == project_id
        ).delete()

        patterns = []
        for item in parsed:
            pattern = CrossInterviewPattern(
                project_id=project_id,
                pattern_type=item.pattern_type,
                description=item.description,
                frequency_count=item.frequency_count,
                interview_ids=item.interview_ids,
                strength=item.strength,
                supporting_quotes=item.supporting_quotes,
                confidence=item.confidence,
            )
            self.db.add(pattern)
            patterns.append(pattern)

        self.db.commit()
        return patterns
