"""Pydantic schemas for extraction results — used for both LLM output parsing and API responses."""

from pydantic import BaseModel, Field


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


class PainPointExtracted(BaseModel):
    """A pain point extracted from an interview transcript."""

    description: str
    severity: str = ""
    frequency: str = ""
    emotional_intensity: str = ""
    supporting_quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class WorkaroundExtracted(BaseModel):
    """A workaround extracted from an interview transcript."""

    description: str
    tools_used: str = ""
    effort_level: str = ""
    satisfaction_with_workaround: str = ""
    supporting_quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class OpportunityExtracted(BaseModel):
    """An opportunity scored via an Opportunity Solution Tree approach."""

    description: str
    opportunity_score: float = Field(default=0.0, ge=0.0)
    importance_score: float = Field(default=0.0, ge=0.0)
    satisfaction_score: float = Field(default=0.0, ge=0.0)
    market_size_indicator: str = ""
    level: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


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
