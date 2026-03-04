"""Calibration endpoints — compare synthetic vs real."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.engine.calibration import CalibrationEngine
from discovery_engine.schemas.calibration import CalibrationRequest

router = APIRouter()


@router.post("/{project_id}")
async def run_calibration(
    project_id: str,
    payload: CalibrationRequest,
    db: Session = Depends(get_db),
):
    """Compare a synthetic persona's predictions against a real interview."""
    engine = CalibrationEngine(db)
    try:
        record = await engine.calibrate(
            project_id=project_id,
            persona_id=payload.persona_id,
            interview_id=payload.interview_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "id": record.id,
        "project_id": record.project_id,
        "persona_id": record.persona_id,
        "interview_id": record.interview_id,
        "overall_accuracy": record.overall_accuracy,
        "job_overlap_score": record.job_overlap_score,
        "pain_overlap_score": record.pain_overlap_score,
        "workaround_overlap_score": record.workaround_overlap_score,
        "notes": record.notes,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


@router.get("/accuracy/{project_id}")
def get_accuracy_trend(project_id: str, db: Session = Depends(get_db)):
    """Get calibration accuracy trend."""
    engine = CalibrationEngine(db)
    return engine.get_accuracy_over_time(project_id)
