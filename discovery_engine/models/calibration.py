"""Calibration model — synthetic vs real accuracy tracking."""

from sqlalchemy import String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class CalibrationRecord(TimestampMixin, Base):
    __tablename__ = "calibration_records"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    persona_id: Mapped[str] = mapped_column(String(32), ForeignKey("synthetic_personas.id"), nullable=True)
    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=True)

    # What the synthetic interview predicted
    predicted_jobs: Mapped[list] = mapped_column(JSON, default=list)
    predicted_pains: Mapped[list] = mapped_column(JSON, default=list)
    predicted_workarounds: Mapped[list] = mapped_column(JSON, default=list)

    # What the real interview found
    actual_jobs: Mapped[list] = mapped_column(JSON, default=list)
    actual_pains: Mapped[list] = mapped_column(JSON, default=list)
    actual_workarounds: Mapped[list] = mapped_column(JSON, default=list)

    # Overlap scores (0-1)
    job_overlap_score: Mapped[float] = mapped_column(Float, default=0.0)
    pain_overlap_score: Mapped[float] = mapped_column(Float, default=0.0)
    workaround_overlap_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_accuracy: Mapped[float] = mapped_column(Float, default=0.0)

    notes: Mapped[str] = mapped_column(Text, default="")

    project = relationship("Project", back_populates="calibration_records")
