from __future__ import annotations

from typing import Any

import httpx


async def generate_structured(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout: int,
    retries: int,
) -> str:
    url = f"{base_url}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    attempts = max(1, retries + 1)
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "{}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    return f'{{"error": "{last_error}"}}'
