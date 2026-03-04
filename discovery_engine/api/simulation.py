"""Simulation endpoints — synthetic personas and interviews."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.models.persona import SyntheticPersona, SyntheticSession
from discovery_engine.engine.simulator import SimulatorEngine
from discovery_engine.schemas.persona import PersonaGenerateRequest, ChatMessage

router = APIRouter()


@router.post("/personas/{project_id}")
async def generate_personas(
    project_id: str,
    payload: PersonaGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate synthetic personas for a project."""
    engine = SimulatorEngine(db)
    try:
        personas = await engine.generate_personas(
            project_id=project_id,
            count=payload.count,
            is_adversarial=payload.is_adversarial,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [_persona_dict(p) for p in personas]


@router.get("/personas/{project_id}")
def list_personas(project_id: str, db: Session = Depends(get_db)):
    """List all personas for a project."""
    personas = (
        db.query(SyntheticPersona)
        .filter(SyntheticPersona.project_id == project_id)
        .order_by(SyntheticPersona.created_at.desc())
        .all()
    )
    return [_persona_dict(p) for p in personas]


@router.post("/sessions/{persona_id}/start")
async def start_session(persona_id: str, db: Session = Depends(get_db)):
    """Start a new synthetic interview session."""
    engine = SimulatorEngine(db)
    try:
        session = await engine.start_session(persona_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _session_dict(session)


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    payload: ChatMessage,
    db: Session = Depends(get_db),
):
    """Send a message in a synthetic interview."""
    engine = SimulatorEngine(db)
    try:
        result = await engine.send_message(session_id, payload.content)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail)
    # Keep both keys for compatibility with existing clients.
    return {
        "response": result.get("response", ""),
        "reply": result.get("response", ""),
        "mom_test_validation": result.get("mom_test_validation", {}),
        "mom_test_feedback": result.get("mom_test_validation", {}),
    }


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, db: Session = Depends(get_db)):
    """End a synthetic interview session."""
    engine = SimulatorEngine(db)
    try:
        session = await engine.end_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _session_dict(session)


@router.get("/sessions/{persona_id}")
def list_sessions(persona_id: str, db: Session = Depends(get_db)):
    """List all sessions for a persona."""
    sessions = (
        db.query(SyntheticSession)
        .filter(SyntheticSession.persona_id == persona_id)
        .order_by(SyntheticSession.created_at.desc())
        .all()
    )
    return [_session_dict(s) for s in sessions]


@router.get("/session/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get a specific session."""
    session = db.query(SyntheticSession).filter(SyntheticSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_dict(session)


def _persona_dict(p: SyntheticPersona) -> dict:
    return {
        "id": p.id,
        "project_id": p.project_id,
        "name": p.name,
        "role": p.role,
        "company_type": p.company_type,
        "background": p.background,
        "goals": p.goals,
        "frustrations": p.frustrations,
        "current_tools": p.current_tools,
        "behavioral_traits": p.behavioral_traits,
        "is_adversarial": p.is_adversarial,
        "model_used": p.model_used,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


def _session_dict(s: SyntheticSession) -> dict:
    return {
        "id": s.id,
        "persona_id": s.persona_id,
        "messages": s.messages,
        "mom_test_violations": s.mom_test_violations,
        "insights_extracted": s.insights_extracted,
        "session_quality_score": s.session_quality_score,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }
