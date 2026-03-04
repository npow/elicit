"""Pydantic schemas for simulated personas and chat sessions."""

from pydantic import BaseModel, Field


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
