"""Cross-encoder reranker via Hugging Face Inference API.

Scores (query, document) pairs with BAAI/bge-reranker-v2-m3. Falls back to
identity ordering (preserving the upstream RRF order) when `HF_TOKEN` is
missing or the API errors — degradation is graceful, never fatal.
"""

from __future__ import annotations

import httpx
import structlog

from app.config import settings
from app.observability import kb_rerank_failures_total

log = structlog.get_logger(__name__)


def reranker_available() -> bool:
    return bool(settings.HF_TOKEN.strip())


def rerank(query: str, documents: list[str]) -> list[float]:
    """Return a relevance score per document (higher = more relevant).

    On any failure returns descending scores that preserve input order so
    callers can sort uniformly.
    """
    n = len(documents)
    if n == 0:
        return []
    if not reranker_available():
        return [float(n - i) for i in range(n)]

    url = f"https://api-inference.huggingface.co/models/{settings.RERANKER_MODEL}"
    headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}
    payload = {
        "inputs": {"source_sentence": query, "sentences": documents},
        "options": {"wait_for_model": True},
    }
    try:
        with httpx.Client(timeout=settings.LLM_HTTP_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            scores = resp.json()
        if isinstance(scores, list) and len(scores) == n:
            return [float(s) for s in scores]
        log.warning("rerank_unexpected_shape", got=type(scores).__name__)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        log.warning("rerank_failed", error=str(exc))
    kb_rerank_failures_total.inc()
    return [float(n - i) for i in range(n)]
