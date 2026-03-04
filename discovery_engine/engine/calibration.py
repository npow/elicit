"""Calibration engine — compare synthetic predictions vs real interview outcomes."""

import json

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, render_prompt
from discovery_engine.llm.parsers import parse_llm_output
from discovery_engine.models.interview import Interview
from discovery_engine.models.extraction import Job, PainPoint, Workaround
from discovery_engine.models.persona import SyntheticPersona, SyntheticSession
from discovery_engine.models.calibration import CalibrationRecord
from discovery_engine.schemas.calibration import CalibrationExtracted


class CalibrationEngine:
    """Compare synthetic interview predictions against real interview data."""

    def __init__(self, db: Session):
        self.db = db

    async def calibrate(
        self,
        project_id: str,
        persona_id: str,
        interview_id: str,
    ) -> CalibrationRecord:
        """Compare a synthetic persona's predictions with a real interview's findings."""
        persona = self.db.query(SyntheticPersona).filter(SyntheticPersona.id == persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        # Get synthetic predictions (from persona's sessions)
        sessions = (
            self.db.query(SyntheticSession)
            .filter(SyntheticSession.persona_id == persona_id, SyntheticSession.status == "completed")
            .all()
        )
        predicted = self._extract_predictions_from_sessions(persona, sessions)

        # Get real interview extractions
        actual_jobs = self.db.query(Job).filter(Job.interview_id == interview_id).all()
        actual_pains = self.db.query(PainPoint).filter(PainPoint.interview_id == interview_id).all()
        actual_was = self.db.query(Workaround).filter(Workaround.interview_id == interview_id).all()

        actual = {
            "jobs": [j.statement for j in actual_jobs],
            "pains": [p.description for p in actual_pains],
            "workarounds": [w.description for w in actual_was],
        }

        # Use LLM to compare semantically
        prompt = render_prompt(
            "calibration_comparison.txt",
            predicted=json.dumps(predicted, indent=2),
            actual=json.dumps(actual, indent=2),
        )
        raw = await complete(prompt, tier="primary", task_type="calibration")
        parsed = parse_llm_output(raw, CalibrationExtracted)

        record = CalibrationRecord(
            project_id=project_id,
            persona_id=persona_id,
            interview_id=interview_id,
            predicted_jobs=predicted.get("jobs", []),
            predicted_pains=predicted.get("pains", []),
            predicted_workarounds=predicted.get("workarounds", []),
            actual_jobs=actual["jobs"],
            actual_pains=actual["pains"],
            actual_workarounds=actual["workarounds"],
            job_overlap_score=parsed.job_overlap_score,
            pain_overlap_score=parsed.pain_overlap_score,
            workaround_overlap_score=parsed.workaround_overlap_score,
            overall_accuracy=parsed.overall_accuracy,
            notes=parsed.analysis if hasattr(parsed, "analysis") else "",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_accuracy_over_time(self, project_id: str) -> list[dict]:
        """Get calibration accuracy trend for a project."""
        records = (
            self.db.query(CalibrationRecord)
            .filter(CalibrationRecord.project_id == project_id)
            .order_by(CalibrationRecord.created_at)
            .all()
        )
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "overall_accuracy": r.overall_accuracy,
                "job_overlap_score": r.job_overlap_score,
                "pain_overlap_score": r.pain_overlap_score,
                "workaround_overlap_score": r.workaround_overlap_score,
            }
            for r in records
        ]

    def _extract_predictions_from_sessions(
        self,
        persona: SyntheticPersona,
        sessions: list[SyntheticSession],
    ) -> dict:
        """Extract predicted JTBD/pains/workarounds from persona + sessions."""
        # Use persona's defined attributes as baseline predictions
        predicted_jobs = persona.goals if isinstance(persona.goals, list) else []
        predicted_pains = persona.frustrations if isinstance(persona.frustrations, list) else []
        predicted_workarounds = persona.current_tools if isinstance(persona.current_tools, list) else []

        # Add any insights extracted during sessions
        for session in sessions:
            for insight in (session.insights_extracted or []):
                if isinstance(insight, dict):
                    itype = insight.get("type", "")
                    desc = insight.get("description", "")
                    if itype == "job" and desc:
                        predicted_jobs.append(desc)
                    elif itype == "pain" and desc:
                        predicted_pains.append(desc)
                    elif itype == "workaround" and desc:
                        predicted_workarounds.append(desc)

        return {
            "jobs": predicted_jobs,
            "pains": predicted_pains,
            "workarounds": predicted_workarounds,
        }
