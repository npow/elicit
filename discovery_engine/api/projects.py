"""CRUD endpoints for projects."""

from fastapi import APIRouter, Depends, HTTPException
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
    return _to_response(project, db)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [_to_response(p, db) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _to_response(project, db)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}


def _to_response(project: Project, db: Session) -> dict:
    count = db.query(Interview).filter(Interview.project_id == project.id).count()
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "hypothesis": project.hypothesis,
        "target_customer": project.target_customer,
        "created_at": project.created_at.isoformat() if project.created_at else "",
        "interview_count": count,
    }
