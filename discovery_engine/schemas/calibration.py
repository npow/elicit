"""Pydantic schemas for calibration — comparing simulated vs. real interview data."""

from pydantic import BaseModel, Field, field_validator

from discovery_engine.schemas.normalization import to_score_0_1, to_text


# ---------------------------------------------------------------------------
# Request / LLM output-parsing schemas
# ---------------------------------------------------------------------------


class CalibrationRequest(BaseModel):
    """Input for triggering a calibration comparison."""

    persona_id: str
    interview_id: str


class CalibrationExtracted(BaseModel):
    """Calibration analysis produced by the LLM."""

    job_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    pain_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    workaround_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis: str = ""
    recommendations_for_improvement: list[str] = []

    @field_validator(
        "job_overlap_score",
        "pain_overlap_score",
        "workaround_overlap_score",
        "overall_accuracy",
        mode="before",
    )
    @classmethod
    def _normalize_scores(cls, v):
        return to_score_0_1(v)

    @field_validator("analysis", mode="before")
    @classmethod
    def _to_text_field(cls, v):
        return to_text(v)


# ---------------------------------------------------------------------------
# API response schema
# ---------------------------------------------------------------------------


class CalibrationResponse(BaseModel):
    """Persisted calibration result returned via the API."""

    id: str
    project_id: str
    persona_id: str
    interview_id: str
    job_overlap_score: float
    pain_overlap_score: float
    workaround_overlap_score: float
    overall_accuracy: float
    notes: str
    created_at: str

    model_config = {"from_attributes": True}
