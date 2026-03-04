"""Coaching endpoints — interview prep and quality review."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.models.coaching import InterviewGuide, InterviewQualityScore
from discovery_engine.engine.coaching import CoachingEngine
from discovery_engine.schemas.coaching import InterviewGuideRequest

router = APIRouter()


@router.post("/guide/{project_id}")
async def generate_guide(
    project_id: str,
    payload: InterviewGuideRequest,
    db: Session = Depends(get_db),
):
    """Generate a Mom Test interview guide."""
    engine = CoachingEngine(db)
    try:
        guide = await engine.generate_guide(
            project_id=project_id,
            hypothesis=payload.hypothesis,
            target_persona=payload.target_persona,
            existing_insights=payload.existing_insights,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _guide_dict(guide)


@router.get("/guides/{project_id}")
def list_guides(project_id: str, db: Session = Depends(get_db)):
    """List all interview guides for a project."""
    guides = (
        db.query(InterviewGuide)
        .filter(InterviewGuide.project_id == project_id)
        .order_by(InterviewGuide.created_at.desc())
        .all()
    )
    return [_guide_dict(g) for g in guides]


@router.post("/score/{interview_id}")
async def score_interview(interview_id: str, db: Session = Depends(get_db)):
    """Score an interview's quality."""
    engine = CoachingEngine(db)
    try:
        score = await engine.score_interview(interview_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail)
    return _score_dict(score)


@router.get("/scores/{interview_id}")
def get_scores(interview_id: str, db: Session = Depends(get_db)):
    """Get quality scores for an interview."""
    scores = (
        db.query(InterviewQualityScore)
        .filter(InterviewQualityScore.interview_id == interview_id)
        .order_by(InterviewQualityScore.created_at.desc())
        .all()
    )
    return [_score_dict(s) for s in scores]


def _guide_dict(g: InterviewGuide) -> dict:
    return {
        "id": g.id,
        "project_id": g.project_id,
        "title": g.title,
        "hypothesis": g.hypothesis,
        "target_persona": g.target_persona,
        "opening_questions": g.opening_questions,
        "deep_dive_questions": g.deep_dive_questions,
        "validation_questions": g.validation_questions,
        "anti_patterns_to_avoid": g.anti_patterns_to_avoid,
        "success_criteria": g.success_criteria,
        "created_at": g.created_at.isoformat() if g.created_at else "",
    }


def _score_dict(s: InterviewQualityScore) -> dict:
    return {
        "id": s.id,
        "interview_id": s.interview_id,
        "overall_score": s.overall_score,
        "mom_test_compliance": s.mom_test_compliance,
        "question_quality": s.question_quality,
        "insight_depth": s.insight_depth,
        "bias_score": s.bias_score,
        "leading_questions_found": s.leading_questions_found,
        "missed_opportunities": s.missed_opportunities,
        "strengths": s.strengths,
        "suggestions": s.suggestions,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }
