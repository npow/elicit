"""Recommendation model — "Build this next" with evidence chains."""

from sqlalchemy import String, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_rank: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(100), default="")  # feature, improvement, pivot, experiment
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    supporting_interview_count: Mapped[int] = mapped_column(Integer, default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    risks: Mapped[str] = mapped_column(Text, default="")
    next_steps: Mapped[str] = mapped_column(Text, default="")

    project = relationship("Project", back_populates="recommendations")
    evidence_chains = relationship("EvidenceChain", back_populates="recommendation", cascade="all, delete-orphan")


class EvidenceChain(TimestampMixin, Base):
    """Links a recommendation back to specific extracted data."""
    __tablename__ = "evidence_chains"

    recommendation_id: Mapped[str] = mapped_column(String(32), ForeignKey("recommendations.id"), nullable=False)
    interview_id: Mapped[str] = mapped_column(String(32), ForeignKey("interviews.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), default="")  # job, pain, workaround, opportunity, quote
    source_id: Mapped[str] = mapped_column(String(32), default="")  # FK to the specific extraction
    quote: Mapped[str] = mapped_column(Text, default="")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation = relationship("Recommendation", back_populates="evidence_chains")
