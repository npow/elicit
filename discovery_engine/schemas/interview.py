"""Pydantic schemas for interviews."""

from pydantic import BaseModel


class InterviewCreate(BaseModel):
    title: str = ""
    interviewee_name: str = ""
    interviewee_role: str = ""
    transcript: str = ""


class InterviewResponse(BaseModel):
    id: str
    project_id: str
    title: str
    interviewee_name: str
    interviewee_role: str
    transcript: str
    source_type: str
    status: str
    duration_minutes: float
    created_at: str

    model_config = {"from_attributes": True}
