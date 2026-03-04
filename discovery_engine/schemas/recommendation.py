"""Pydantic schemas for recommendations and their evidence chains."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# LLM output-parsing schema
# ---------------------------------------------------------------------------


class RecommendationExtracted(BaseModel):
    """A strategic recommendation extracted by the LLM from aggregated insights."""

    title: str
    description: str = ""
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    category: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""
    risks: str = ""
    next_steps: str = ""


# ---------------------------------------------------------------------------
# API response schemas
# ---------------------------------------------------------------------------


class EvidenceChainResponse(BaseModel):
    """A single piece of evidence linking a recommendation back to an interview."""

    id: str
    recommendation_id: str
    interview_id: str
    evidence_type: str
    source_id: str
    quote: str
    relevance_score: float

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    """Full recommendation with its supporting evidence chains."""

    id: str
    project_id: str
    title: str
    description: str
    priority_score: float
    category: str
    confidence: float
    rationale: str
    risks: str
    next_steps: str
    created_at: str
    evidence_chains: list[EvidenceChainResponse] = []

    model_config = {"from_attributes": True}
