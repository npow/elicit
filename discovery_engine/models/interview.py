"""Interview model — transcript and metadata."""

from sqlalchemy import String, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class Interview(TimestampMixin, Base):
    __tablename__ = "interviews"

    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    interviewee_name: Mapped[str] = mapped_column(String(255), default="")
    interviewee_role: Mapped[str] = mapped_column(String(255), default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(50), default="text")  # text, audio
    audio_path: Mapped[str] = mapped_column(String(500), default="")
    duration_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")  # uploaded, transcribed, analyzed

    # Relationships
    project = relationship("Project", back_populates="interviews")
    jobs = relationship("Job", back_populates="interview", cascade="all, delete-orphan")
    pain_points = relationship("PainPoint", back_populates="interview", cascade="all, delete-orphan")
    workarounds = relationship("Workaround", back_populates="interview", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="interview", cascade="all, delete-orphan")
    quality_scores = relationship("InterviewQualityScore", back_populates="interview", cascade="all, delete-orphan")
