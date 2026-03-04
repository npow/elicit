"""Pydantic schemas for simulated personas and chat sessions."""

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Persona generation
# ---------------------------------------------------------------------------


class PersonaGenerateRequest(BaseModel):
    """Parameters for batch-generating simulated personas."""

    count: int = Field(default=3, ge=1)
    is_adversarial: bool = False


class PersonaExtracted(BaseModel):
    """A simulated user persona produced by the LLM."""

    name: str = ""
    role: str = ""
    company_type: str = ""
    background: str = ""
    goals: list[str] = []
    frustrations: list[str] = []
    current_tools: list[str] = []
    behavioral_traits: list[str] = []

    @field_validator("current_tools", mode="before")
    @classmethod
    def _normalize_tools(cls, v):
        """LLM returns list[{tool, usage, satisfaction}]; extract tool name."""
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(str(item.get("tool") or next(iter(item.values()), "")))
            else:
                result.append(str(item))
        return result

    @field_validator("behavioral_traits", mode="before")
    @classmethod
    def _normalize_traits(cls, v):
        """LLM returns {tech_savviness: ..., change_tolerance: ...}; flatten to list."""
        if isinstance(v, dict):
            return [f"{k}: {val}" for k, val in v.items()]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return []


class PersonaResponse(BaseModel):
    """Persisted persona returned via the API."""

    id: str
    project_id: str
    name: str
    role: str
    company_type: str
    background: str
    goals: list[str]
    frustrations: list[str]
    current_tools: list[str]
    behavioral_traits: list[str]
    is_adversarial: bool
    model_used: str
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Chat session
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single message in a simulated interview conversation."""

    role: str
    content: str


class SessionResponse(BaseModel):
    """Persisted chat session returned via the API."""

    id: str
    persona_id: str
    messages: list[dict]
    mom_test_violations: list[dict]
    insights_extracted: list[dict]
    session_quality_score: float
    status: str
    created_at: str

    model_config = {"from_attributes": True}
