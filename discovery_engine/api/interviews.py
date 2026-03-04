"""Interview upload, transcription, and retrieval endpoints."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview
from discovery_engine.schemas.interview import InterviewCreate, InterviewResponse

router = APIRouter()


@router.post("/{project_id}/text", response_model=InterviewResponse)
def upload_text_interview(
    project_id: str,
    payload: InterviewCreate,
    db: Session = Depends(get_db),
):
    """Upload an interview as text transcript."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=422, detail="Transcript cannot be empty")

    interview = Interview(
        project_id=project_id,
        title=payload.title,
        interviewee_name=payload.interviewee_name,
        interviewee_role=payload.interviewee_role,
        transcript=payload.transcript,
        source_type="text",
        status="uploaded",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _to_response(interview)


@router.post("/{project_id}/audio", response_model=InterviewResponse)
async def upload_audio_interview(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Form(""),
    interviewee_name: str = Form(""),
    interviewee_role: str = Form(""),
    db: Session = Depends(get_db),
):
    """Upload an audio file — transcribes with Whisper."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save audio to temp file
    suffix = Path(file.filename).suffix if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Transcribe — always clean up temp file regardless of success/failure
    try:
        transcript = await _transcribe(tmp_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    interview = Interview(
        project_id=project_id,
        title=title or file.filename or "Audio Interview",
        interviewee_name=interviewee_name,
        interviewee_role=interviewee_role,
        transcript=transcript,
        source_type="audio",
        audio_path=tmp_path,
        status="transcribed",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _to_response(interview)


@router.get("/{project_id}", response_model=list[InterviewResponse])
def list_interviews(project_id: str, db: Session = Depends(get_db)):
    interviews = (
        db.query(Interview)
        .filter(Interview.project_id == project_id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [_to_response(i) for i in interviews]


@router.get("/detail/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return _to_response(interview)


@router.delete("/detail/{interview_id}")
def delete_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    audio_path = interview.audio_path if interview.source_type == "audio" else None
    db.delete(interview)
    db.commit()
    if audio_path:
        try:
            os.unlink(audio_path)
        except OSError:
            pass
    return {"deleted": True}


async def _transcribe(audio_path: str) -> str:
    """Transcribe audio using Whisper."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result["text"]
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Whisper not installed. Install with: pip install openai-whisper",
        )


def _to_response(interview: Interview) -> dict:
    return {
        "id": interview.id,
        "project_id": interview.project_id,
        "title": interview.title,
        "interviewee_name": interview.interviewee_name,
        "interviewee_role": interview.interviewee_role,
        "transcript": interview.transcript,
        "source_type": interview.source_type,
        "status": interview.status,
        "duration_minutes": interview.duration_minutes,
        "created_at": interview.created_at.isoformat() if interview.created_at else "",
    }
