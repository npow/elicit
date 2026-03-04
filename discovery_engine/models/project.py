"""Project model — groups interviews and analysis."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from discovery_engine.models.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    target_customer: Mapped[str] = mapped_column(Text, default="")

    # Relationships
    interviews = relationship("Interview", back_populates="project", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="project", cascade="all, delete-orphan")
    patterns = relationship("CrossInterviewPattern", back_populates="project", cascade="all, delete-orphan")
    guides = relationship("InterviewGuide", back_populates="project", cascade="all, delete-orphan")
    personas = relationship("SyntheticPersona", back_populates="project", cascade="all, delete-orphan")
    calibration_records = relationship("CalibrationRecord", back_populates="project", cascade="all, delete-orphan")
