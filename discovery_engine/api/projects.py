"""CRUD endpoints for projects."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview
from discovery_engine.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name,
        description=payload.description,
        hypothesis=payload.hypothesis,
        target_customer=payload.target_customer,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    count = db.query(Interview).filter(Interview.project_id == project.id).count()
    return _to_response(project, count)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    if not projects:
        return []
    # Batch fetch counts to avoid N+1.
    project_ids = [p.id for p in projects]
    count_rows = (
        db.query(Interview.project_id, func.count(Interview.id).label("cnt"))
        .filter(Interview.project_id.in_(project_ids))
        .group_by(Interview.project_id)
        .all()
    )
    counts = {row.project_id: row.cnt for row in count_rows}
    return [_to_response(p, counts.get(p.id, 0)) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    count = db.query(Interview).filter(Interview.project_id == project_id).count()
    return _to_response(project, count)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    count = db.query(Interview).filter(Interview.project_id == project_id).count()
    return _to_response(project, count)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}


def _to_response(project: Project, interview_count: int = 0) -> dict:
    count = interview_count
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "hypothesis": project.hypothesis,
        "target_customer": project.target_customer,
        "created_at": project.created_at.isoformat() if project.created_at else "",
        "interview_count": count,
    }
