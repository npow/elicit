"""Persona models — synthetic interviews."""

from sqlalchemy import String, Text, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class SyntheticPersona(TimestampMixin, Base):
    """AI-generated persona for synthetic interviews."""
    __tablename__ = "synthetic_personas"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="")
    company_type: Mapped[str] = mapped_column(String(255), default="")
    background: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[list] = mapped_column(JSON, default=list)
    frustrations: Mapped[list] = mapped_column(JSON, default=list)
    current_tools: Mapped[list] = mapped_column(JSON, default=list)
    behavioral_traits: Mapped[list] = mapped_column(JSON, default=list)
    is_adversarial: Mapped[bool] = mapped_column(Boolean, default=False)
    adversarial_traits: Mapped[list] = mapped_column(JSON, default=list)
    model_used: Mapped[str] = mapped_column(String(100), default="")

    project = relationship("Project", back_populates="personas")
    sessions = relationship("SyntheticSession", back_populates="persona", cascade="all, delete-orphan")


class SyntheticSession(TimestampMixin, Base):
    """A single synthetic interview session."""
    __tablename__ = "synthetic_sessions"

    persona_id: Mapped[str] = mapped_column(String(32), ForeignKey("synthetic_personas.id"), nullable=False)
    messages: Mapped[list] = mapped_column(JSON, default=list)  # [{role, content}, ...]
    mom_test_violations: Mapped[list] = mapped_column(JSON, default=list)
    insights_extracted: Mapped[list] = mapped_column(JSON, default=list)
    session_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed

    persona = relationship("SyntheticPersona", back_populates="sessions")
