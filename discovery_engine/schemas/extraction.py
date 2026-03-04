"""Pydantic schemas for extraction results — used for both LLM output parsing and API responses."""

from pydantic import BaseModel, Field, field_validator

from discovery_engine.schemas.normalization import (
    map_importance,
    map_satisfaction,
    map_severity,
    to_score_0_1,
    to_text,
)


# ---------------------------------------------------------------------------
# LLM output-parsing schemas
# ---------------------------------------------------------------------------


class JobExtracted(BaseModel):
    """A job-to-be-done extracted from an interview transcript."""

    statement: str
    context: str = ""
    frequency: str = ""
    importance: str = ""
    satisfaction: str = ""
    supporting_quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("statement", "context", "frequency", "supporting_quote", mode="before")
    @classmethod
    def _to_text_fields(cls, v):
        return to_text(v)

    @field_validator("importance", mode="before")
    @classmethod
    def _normalize_importance(cls, v):
        return map_importance(v)

    @field_validator("satisfaction", mode="before")
    @classmethod
    def _normalize_satisfaction(cls, v):
        return map_satisfaction(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v):
        return to_score_0_1(v)


class PainPointExtracted(BaseModel):
    """A pain point extracted from an interview transcript."""

    description: str
    severity: str = ""
    frequency: str = ""
    emotional_intensity: str = ""
    supporting_quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("description", "frequency", "emotional_intensity", "supporting_quote", mode="before")
    @classmethod
    def _to_text_fields(cls, v):
        return to_text(v)

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v):
        return map_severity(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v):
        return to_score_0_1(v)


class WorkaroundExtracted(BaseModel):
    """A workaround extracted from an interview transcript."""

    description: str
    tools_used: str = ""
    effort_level: str = ""
    satisfaction_with_workaround: str = ""
    supporting_quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("description", "effort_level", "satisfaction_with_workaround", "supporting_quote", mode="before")
    @classmethod
    def _to_text_fields(cls, v):
        return to_text(v)

    @field_validator("tools_used", mode="before")
    @classmethod
    def _normalize_tools_used(cls, v):
        if isinstance(v, list):
            return ", ".join(str(item).strip() for item in v if item)
        return to_text(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v):
        return to_score_0_1(v)


_LEVEL_MAP = {"strategic": 0, "tactical": 1, "quick_win": 2}


class OpportunityExtracted(BaseModel):
    """An opportunity scored via an Opportunity Solution Tree approach."""

    description: str
    opportunity_score: float = Field(default=0.0, ge=0.0, le=20.0)
    importance_score: float = Field(default=0.0, ge=0.0, le=10.0)
    satisfaction_score: float = Field(default=0.0, ge=0.0, le=10.0)
    market_size_indicator: str = ""
    level: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    related_job_statement: str = ""

    @field_validator("description", "market_size_indicator", "related_job_statement", mode="before")
    @classmethod
    def _to_text_fields(cls, v):
        return to_text(v)

    @field_validator("opportunity_score", mode="before")
    @classmethod
    def _to_opp_score(cls, v):
        if v is None or v == "":
            return 0.0
        try:
            return min(20.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("importance_score", "satisfaction_score", mode="before")
    @classmethod
    def _to_subscores(cls, v):
        if v is None or v == "":
            return 0.0
        try:
            return min(10.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("level", mode="before")
    @classmethod
    def _to_level(cls, v):
        if isinstance(v, str):
            return _LEVEL_MAP.get(v.lower().strip(), 0)
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v):
        return to_score_0_1(v)


class ExtractionResult(BaseModel):
    """Aggregated extraction output returned by the LLM."""

    jobs: list[JobExtracted] = []
    pain_points: list[PainPointExtracted] = []
    workarounds: list[WorkaroundExtracted] = []
    opportunities: list[OpportunityExtracted] = []


# ---------------------------------------------------------------------------
# API response schemas (include persistence metadata)
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    id: str
    interview_id: str
    statement: str
    context: str
    frequency: str
    importance: str
    satisfaction: str
    supporting_quote: str
    confidence: float
    created_at: str

    model_config = {"from_attributes": True}


class PainPointResponse(BaseModel):
    id: str
    interview_id: str
    description: str
    severity: str
    frequency: str
    emotional_intensity: str
    supporting_quote: str
    confidence: float
    created_at: str

    model_config = {"from_attributes": True}


class WorkaroundResponse(BaseModel):
    id: str
    interview_id: str
    description: str
    tools_used: str
    effort_level: str
    satisfaction_with_workaround: str
    supporting_quote: str
    confidence: float
    created_at: str

    model_config = {"from_attributes": True}


class OpportunityResponse(BaseModel):
    id: str
    interview_id: str
    description: str
    opportunity_score: float
    importance_score: float
    satisfaction_score: float
    market_size_indicator: str
    level: int
    confidence: float
    created_at: str

    model_config = {"from_attributes": True}
