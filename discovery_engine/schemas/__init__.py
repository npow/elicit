"""Pydantic schemas for API and LLM parsing."""

from discovery_engine.schemas.calibration import (
    CalibrationExtracted,
    CalibrationRequest,
    CalibrationResponse,
)
from discovery_engine.schemas.coaching import (
    InterviewGuideExtracted,
    InterviewGuideRequest,
    InterviewGuideResponse,
    QualityScoreExtracted,
    QualityScoreResponse,
)
from discovery_engine.schemas.extraction import (
    ExtractionResult,
    JobExtracted,
    JobResponse,
    OpportunityExtracted,
    OpportunityResponse,
    PainPointExtracted,
    PainPointResponse,
    WorkaroundExtracted,
    WorkaroundResponse,
)
from discovery_engine.schemas.interview import InterviewCreate, InterviewResponse
from discovery_engine.schemas.persona import (
    ChatMessage,
    PersonaExtracted,
    PersonaGenerateRequest,
    PersonaResponse,
    SessionResponse,
)
from discovery_engine.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from discovery_engine.schemas.recommendation import (
    EvidenceChainResponse,
    RecommendationExtracted,
    RecommendationResponse,
)

__all__ = [
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    # Interview
    "InterviewCreate",
    "InterviewResponse",
    # Extraction — LLM parsing
    "JobExtracted",
    "PainPointExtracted",
    "WorkaroundExtracted",
    "OpportunityExtracted",
    "ExtractionResult",
    # Extraction — API responses
    "JobResponse",
    "PainPointResponse",
    "WorkaroundResponse",
    "OpportunityResponse",
    # Recommendation
    "RecommendationExtracted",
    "EvidenceChainResponse",
    "RecommendationResponse",
    # Coaching
    "InterviewGuideRequest",
    "InterviewGuideExtracted",
    "InterviewGuideResponse",
    "QualityScoreExtracted",
    "QualityScoreResponse",
    # Persona
    "PersonaGenerateRequest",
    "PersonaExtracted",
    "PersonaResponse",
    "SessionResponse",
    "ChatMessage",
    # Calibration
    "CalibrationRequest",
    "CalibrationExtracted",
    "CalibrationResponse",
]
