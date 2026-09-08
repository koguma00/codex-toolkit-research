from __future__ import annotations

import asyncio
from typing import Any

import httpx


class Fetcher:
    def __init__(self, timeout: float = 30.0, retries: int = 2) -> None:
        self.retries = retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "ai-paper-search/0.3.1 "
                    "(personal academic research; contact via repository)"
                )
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = await self.client.get(url, **kwargs)
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < self.retries:
                        await asyncio.sleep(1.5 * (2**attempt))
                        continue
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self.retries:
                    await asyncio.sleep(1.5 * (2**attempt))
        assert last_error is not None
        raise last_error
