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
        from pydantic import BaseModel, field_validator
        from discovery_engine.schemas.normalization import to_score_0_1

        _STRENGTH_MAP = {"strong": 0.9, "moderate": 0.6, "weak": 0.3, "emerging": 0.45}

        class PatternParsed(BaseModel):
            pattern_type: str = ""
            description: str
            frequency_count: int = 0
            interview_ids: list[str] = []
            strength: float = 0.0
            supporting_quotes: list[str] = []
            confidence: float = 0.0

            @field_validator("strength", mode="before")
            @classmethod
            def _norm_strength(cls, v):
                if isinstance(v, str):
                    return _STRENGTH_MAP.get(v.strip().lower(), 0.5)
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.5

            @field_validator("confidence", mode="before")
            @classmethod
            def _norm_confidence(cls, v):
                return to_score_0_1(v)

            @field_validator("supporting_quotes", mode="before")
            @classmethod
            def _norm_quotes(cls, v):
                if not isinstance(v, list):
                    return []
                result = []
                for item in v:
                    if isinstance(item, dict):
                        result.append(item.get("quote") or str(item))
                    else:
                        result.append(str(item))
                return result

        parsed = parse_llm_list(raw, PatternParsed)
        if not parsed:
            parsed = self._heuristic_patterns(interviews_data)

        # Delete old patterns for this project and replace
        try:
            self.db.query(CrossInterviewPattern).filter(
                CrossInterviewPattern.project_id == project_id
            ).delete(synchronize_session=False)

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
        except Exception:
            self.db.rollback()
            raise
        return patterns

    def _heuristic_patterns(self, interviews_data: list[dict]):
        """Fallback patterns when LLM output is unusable."""
        from pydantic import BaseModel

        class PatternParsed(BaseModel):
            pattern_type: str = ""
            description: str
            frequency_count: int = 0
            interview_ids: list[str] = []
            strength: float = 0.0
            supporting_quotes: list[str] = []
            confidence: float = 0.0

        keyword_buckets = {
            "decision_anxiety": ["uncertain", "unsure", "risk", "trust", "doubt", "confused", "worried", "afraid", "hesitant", "overwhelm"],
            "process_friction": ["complicated", "tedious", "manually", "time-consuming", "difficult", "struggle", "annoying", "frustrat", "hard to", "painful"],
            "comparison_difficulty": ["compare", "evaluate", "alternatives", "options", "tradeoff", "decision", "pick", "choose", "assess", "trade-off"],
            "workaround_necessity": ["workaround", "hack", "instead", "manually", "spreadsheet", "export", "copy", "paste", "multiple tools", "duct tape"],
            "poor_visibility": ["no feedback", "unclear", "confusing", "don't know", "can't tell", "missing", "no way to", "no visibility", "blind"],
        }

        bucket_hits: dict[str, dict] = {
            name: {"interview_ids": set(), "quotes": []} for name in keyword_buckets
        }

        for interview in interviews_data:
            interview_id = interview.get("interview_id", "")
            snippets = []
            snippets.extend([j.get("statement", "") for j in interview.get("jobs", [])])
            snippets.extend([p.get("description", "") for p in interview.get("pain_points", [])])
            snippets.extend([w.get("description", "") for w in interview.get("workarounds", [])])
            snippet_text = " ".join(snippets).lower()

            for bucket, keywords in keyword_buckets.items():
                if any(kw in snippet_text for kw in keywords):
                    bucket_hits[bucket]["interview_ids"].add(interview_id)
                    for s in snippets[:3]:
                        if s:
                            bucket_hits[bucket]["quotes"].append(s)

        bucket_labels = {
            "decision_anxiety": "Users express uncertainty and anxiety at key decision points — trust signals and risk reduction are needed.",
            "process_friction": "Core workflows are perceived as complicated or tedious — there is demand for simplification.",
            "comparison_difficulty": "Users struggle to evaluate and compare options — better guidance or comparison tooling is needed.",
            "workaround_necessity": "Users rely on manual workarounds to accomplish goals the product should handle natively.",
            "poor_visibility": "Users lack feedback and visibility into outcomes — feedback loops are absent or unclear.",
        }

        output: list[PatternParsed] = []
        interview_total = max(1, len(interviews_data))
        for bucket, hit_data in bucket_hits.items():
            ids = sorted(i for i in hit_data["interview_ids"] if i)
            freq = len(ids)
            if freq < 2:
                continue
            strength = min(1.0, freq / interview_total)
            output.append(
                PatternParsed(
                    pattern_type="shared_pain",
                    description=bucket_labels[bucket],
                    frequency_count=freq,
                    interview_ids=ids,
                    strength=strength,
                    supporting_quotes=hit_data["quotes"][:4],
                    confidence=0.6 + (0.1 * min(freq, 3)),
                )
            )
        return output
