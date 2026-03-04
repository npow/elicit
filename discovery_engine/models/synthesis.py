"""Synthesis model — cross-interview pattern detection."""

from sqlalchemy import String, Text, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class CrossInterviewPattern(TimestampMixin, Base):
    __tablename__ = "cross_interview_patterns"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(100), default="")  # recurring_job, shared_pain, common_workaround, emerging_theme
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency_count: Mapped[int] = mapped_column(Integer, default=0)  # how many interviews mention this
    interview_ids: Mapped[list] = mapped_column(JSON, default=list)  # list of interview IDs
    source_ids: Mapped[list] = mapped_column(JSON, default=list)  # list of extraction IDs
    strength: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1 pattern strength
    supporting_quotes: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    project = relationship("Project", back_populates="patterns")
