"""OpenAI embeddings client (text-embedding-3-small, 1536-dim).

Batches up to 100 inputs per request. When `OPENAI_API_KEY` is not set the
client returns zero vectors — this keeps ingestion and local dev working
without an API key (vector search becomes a no-op but FTS still functions).
"""

from __future__ import annotations

import httpx
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

_BATCH_SIZE = 100


def embeddings_available() -> bool:
    return bool(settings.OPENAI_API_KEY.strip())


def _zero_vector() -> list[float]:
    return [0.0] * settings.EMBEDDING_DIM


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns one vector per input, in order."""
    if not texts:
        return []
    if not embeddings_available():
        log.warning("embeddings_disabled", reason="OPENAI_API_KEY missing")
        return [_zero_vector() for _ in texts]

    out: list[list[float]] = []
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    url = f"{settings.OPENAI_BASE_URL}/embeddings"
    with httpx.Client(timeout=settings.LLM_HTTP_TIMEOUT) as client:
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            resp = client.post(
                url,
                headers=headers,
                json={"model": settings.EMBEDDING_MODEL, "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # API guarantees order by `index`; sort defensively.
            data.sort(key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
