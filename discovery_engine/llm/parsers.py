"""JSON extraction and Pydantic validation from LLM output."""

import json
import re
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> dict | list:
    """Extract JSON from LLM output, handling fenced blocks and embedded JSON.

    Tries in order:
    1. Direct JSON parse
    2. Fenced code block (```json ... ```)
    3. First { ... } or [ ... ] block
    """
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Fenced code block
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. First JSON object or array
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching close bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract JSON from LLM output: {text[:200]}...")


def parse_llm_output(text: str, schema: Type[T]) -> T:
    """Parse LLM output into a Pydantic model.

    Args:
        text: Raw LLM response text.
        schema: Pydantic model class to validate against.

    Returns:
        Validated Pydantic model instance.
    """
    data = extract_json(text)
    return schema.model_validate(data)


def parse_llm_list(text: str, schema: Type[T]) -> list[T]:
    """Parse LLM output into a list of Pydantic models.

    Handles both:
    - Direct array output: [{"a": 1}, {"a": 2}]
    - Wrapped: {"items": [{"a": 1}, {"a": 2}]}
    """
    data = extract_json(text)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Find the first list value in the dict
        items = None
        for v in data.values():
            if isinstance(v, list):
                items = v
                break
        if items is None:
            # Single object — wrap in list
            items = [data]
    else:
        raise ValueError(f"Expected list or dict, got {type(data)}")

    return [schema.model_validate(item) for item in items]
