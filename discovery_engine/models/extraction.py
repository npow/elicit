"""Extraction models — Job, PainPoint, Workaround, Opportunity."""

from sqlalchemy import String, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class Job(TimestampMixin, Base):
    """Jobs-to-be-Done extracted from an interview."""
    __tablename__ = "jobs"

    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(String(50), default="")  # daily, weekly, monthly, rarely
    importance: Mapped[str] = mapped_column(String(50), default="")  # critical, high, medium, low
    satisfaction: Mapped[str] = mapped_column(String(50), default="")  # very_unsatisfied..very_satisfied
    supporting_quote: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    interview = relationship("Interview", back_populates="jobs")


class PainPoint(TimestampMixin, Base):
    """Pain points extracted from an interview."""
    __tablename__ = "pain_points"

    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="")  # critical, high, medium, low
    frequency: Mapped[str] = mapped_column(String(50), default="")
    emotional_intensity: Mapped[str] = mapped_column(String(50), default="")  # extreme, high, moderate, low
    supporting_quote: Mapped[str] = mapped_column(Text, default="")
    related_job_id: Mapped[str] = mapped_column(String(32), ForeignKey("jobs.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    interview = relationship("Interview", back_populates="pain_points")
    related_job = relationship("Job", foreign_keys=[related_job_id])


class Workaround(TimestampMixin, Base):
    """Workarounds/hacks people use today."""
    __tablename__ = "workarounds"

    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tools_used: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    effort_level: Mapped[str] = mapped_column(String(50), default="")  # extreme, high, moderate, low
    satisfaction_with_workaround: Mapped[str] = mapped_column(String(50), default="")
    supporting_quote: Mapped[str] = mapped_column(Text, default="")
    related_pain_id: Mapped[str] = mapped_column(String(32), ForeignKey("pain_points.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    interview = relationship("Interview", back_populates="workarounds")
    related_pain = relationship("PainPoint", foreign_keys=[related_pain_id])


class Opportunity(TimestampMixin, Base):
    """Opportunities mapped from jobs + pains + workarounds."""
    __tablename__ = "opportunities"

    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)  # importance + satisfaction gap
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    satisfaction_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_size_indicator: Mapped[str] = mapped_column(String(50), default="")
    related_job_id: Mapped[str] = mapped_column(String(32), ForeignKey("jobs.id"), nullable=True)
    parent_opportunity_id: Mapped[str] = mapped_column(String(32), ForeignKey("opportunities.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0=root, 1=branch, 2=leaf
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    interview = relationship("Interview", back_populates="opportunities")
    related_job = relationship("Job", foreign_keys=[related_job_id])
    parent = relationship("Opportunity", remote_side="Opportunity.id", foreign_keys=[parent_opportunity_id])
