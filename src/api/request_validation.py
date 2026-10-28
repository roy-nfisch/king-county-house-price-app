"""Check raw JSON keys before a parsed request reaches prediction."""

import json
from typing import Any

from fastapi import HTTPException, Request


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Return a JSON object, or reject repeated decoded keys with HTTP 422."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise HTTPException(
                status_code=422, detail="Duplicate JSON keys are not allowed."
            )
        result[key] = value
    return result


async def validate_unique_json_keys(request: Request) -> None:
    """Inspect raw body pairs without changing values; return None or HTTP 422.

    Dictionaries have already lost duplicate-key information. Recheck the cached
    raw bytes using a pairs hook, including escaped names and nested objects.
    Pydantic remains responsible for the house's fields, types, and values.
    """
    try:
        json.loads(await request.body(), object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=422, detail="Request body must contain valid JSON."
        ) from exc
