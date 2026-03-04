"""LiteLLM Router wrapper with prompt rendering."""

from pathlib import Path
from typing import Any

import litellm
from jinja2 import Environment, FileSystemLoader

from discovery_engine.config import settings

PROMPTS_DIR = Path(__file__).parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    keep_trailing_newline=True,
)

# Temperature presets by task type
TEMPERATURE = {
    "extraction": 0.1,
    "synthesis": 0.3,
    "recommendation": 0.3,
    "coaching": 0.3,
    "simulation": 0.7,
    "calibration": 0.1,
}


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """Render a Jinja2 prompt template."""
    template = _jinja_env.get_template(template_name)
    return template.render(**kwargs)


def _get_model(tier: str = "primary") -> str:
    """Resolve model name from tier."""
    return {
        "primary": settings.primary_model,
        "fallback": settings.fallback_model,
        "cheap": settings.cheap_model,
    }.get(tier, settings.primary_model)


async def complete(
    prompt: str,
    *,
    tier: str = "primary",
    task_type: str = "extraction",
    system_message: str | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> str:
    """Send a prompt to the LLM with automatic fallback.

    Args:
        prompt: The user prompt content.
        tier: Model tier — "primary", "fallback", or "cheap".
        task_type: Used to select temperature if not overridden.
        system_message: Optional system prompt.
        max_tokens: Max output tokens.
        temperature: Override default temperature for task_type.

    Returns:
        The LLM response text.
    """
    temp = temperature if temperature is not None else TEMPERATURE.get(task_type, 0.3)
    model = _get_model(tier)

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    json_mode = {"type": "json_object"} if "json" in prompt.lower() else None
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temp,
            response_format=json_mode,
        )
        return response.choices[0].message.content
    except Exception:
        if tier == "primary":
            # Retry with fallback model, preserving response_format constraint
            fallback = _get_model("fallback")
            response = await litellm.acompletion(
                model=fallback,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temp,
                response_format=json_mode,
            )
            return response.choices[0].message.content
        raise


async def chat(
    messages: list[dict[str, str]],
    *,
    tier: str = "primary",
    task_type: str = "simulation",
    max_tokens: int = 2048,
    temperature: float | None = None,
) -> str:
    """Multi-turn chat completion for synthetic interviews."""
    temp = temperature if temperature is not None else TEMPERATURE.get(task_type, 0.7)
    model = _get_model(tier)

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temp,
        )
        return response.choices[0].message.content
    except Exception:
        if tier == "primary":
            fallback = _get_model("fallback")
            response = await litellm.acompletion(
                model=fallback,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temp,
            )
            return response.choices[0].message.content
        raise
