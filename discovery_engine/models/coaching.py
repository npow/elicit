"""Coaching models — interview guides and quality scoring."""

from sqlalchemy import String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class InterviewGuide(TimestampMixin, Base):
    """Pre-interview guide based on Mom Test methodology."""
    __tablename__ = "interview_guides"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    target_persona: Mapped[str] = mapped_column(Text, default="")
    opening_questions: Mapped[list] = mapped_column(JSON, default=list)
    deep_dive_questions: Mapped[list] = mapped_column(JSON, default=list)
    validation_questions: Mapped[list] = mapped_column(JSON, default=list)
    anti_patterns_to_avoid: Mapped[list] = mapped_column(JSON, default=list)  # leading questions, etc.
    success_criteria: Mapped[str] = mapped_column(Text, default="")

    project = relationship("Project", back_populates="guides")


class InterviewQualityScore(TimestampMixin, Base):
    """Post-interview quality analysis."""
    __tablename__ = "interview_quality_scores"

    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    mom_test_compliance: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    question_quality: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    insight_depth: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    bias_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100 (lower is better)
    leading_questions_found: Mapped[list] = mapped_column(JSON, default=list)
    missed_opportunities: Mapped[list] = mapped_column(JSON, default=list)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)

    interview = relationship("Interview", back_populates="quality_scores")
