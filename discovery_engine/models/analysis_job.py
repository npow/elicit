"""Persistent async analysis job records."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from discovery_engine.models.base import Base, TimestampMixin


class AnalysisJob(TimestampMixin, Base):
    """Tracks queued/running/completed analysis work."""

    __tablename__ = "analysis_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued, running, completed, failed
    project_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("projects.id"), nullable=True)
    interview_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=True)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
