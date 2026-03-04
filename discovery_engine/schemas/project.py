"""Pydantic schemas for projects."""

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    hypothesis: str = ""
    target_customer: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    hypothesis: str | None = None
    target_customer: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    hypothesis: str
    target_customer: str
    created_at: str
    interview_count: int = 0

    model_config = {"from_attributes": True}
