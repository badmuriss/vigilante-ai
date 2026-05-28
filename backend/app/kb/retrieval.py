"""Hybrid retrieval: pgvector cosine + Portuguese FTS, merged via RRF, reranked.

Tenant isolation: every query matches `tenant_id = :t OR tenant_id IS NULL`
so a tenant sees its own docs plus the global manual/NR content.

On SQLite (tests / keyless dev) the vector + tsvector columns don't exist,
so we degrade to a simple LIKE scan — enough to keep the agent functional.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.kb.embeddings import embed_query, embeddings_available
from app.kb.reranker import rerank
from app.observability import kb_retrievals_total

log = structlog.get_logger(__name__)

_RRF_K = 60


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    doc_title: str
    score: float


def _is_postgres(session: Session) -> bool:
    return session.bind.dialect.name == "postgresql"


def _vector_candidates(
    session: Session, tenant_id: str, query_vec: list[float], k: int
) -> list[tuple[str, str, str]]:
    """Return [(chunk_id, document_id, content)] by cosine similarity."""
    # pgvector expects the literal '[...]' form for a query parameter.
    vec_literal = "[" + ",".join(str(x) for x in query_vec) + "]"
    rows = session.execute(
        text(
            """
            SELECT c.id, c.document_id, c.content
            FROM kb_chunks c
            WHERE (c.tenant_id = :t OR c.tenant_id IS NULL)
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> (:vec)::vector
            LIMIT :k
            """
        ),
        {"t": tenant_id, "vec": vec_literal, "k": k},
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]


def _fts_candidates(
    session: Session, tenant_id: str, query: str, k: int
) -> list[tuple[str, str, str]]:
    rows = session.execute(
        text(
            """
            SELECT c.id, c.document_id, c.content
            FROM kb_chunks c
            WHERE (c.tenant_id = :t OR c.tenant_id IS NULL)
              AND c.tsv @@ plainto_tsquery('portuguese', :q)
            ORDER BY ts_rank_cd(c.tsv, plainto_tsquery('portuguese', :q)) DESC
            LIMIT :k
            """
        ),
        {"t": tenant_id, "q": query, "k": k},
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]


def _like_candidates(
    session: Session, tenant_id: str, query: str, k: int
) -> list[tuple[str, str, str]]:
    """SQLite fallback — naive term match."""
    terms = [t for t in query.lower().split() if len(t) > 2][:6]
    if not terms:
        terms = [query.lower()]
    like_clauses = " OR ".join(f"lower(c.content) LIKE :p{i}" for i in range(len(terms)))
    params = {"t": tenant_id, "k": k}
    for i, term in enumerate(terms):
        params[f"p{i}"] = f"%{term}%"
    rows = session.execute(
        text(
            f"""
            SELECT c.id, c.document_id, c.content
            FROM kb_chunks c
            WHERE (c.tenant_id = :t OR c.tenant_id IS NULL)
              AND ({like_clauses})
            LIMIT :k
            """
        ),
        params,
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]


def _rrf_merge(
    *result_lists: list[tuple[str, str, str]],
) -> list[tuple[str, str, str, float]]:
    """Reciprocal Rank Fusion. Returns [(id, doc_id, content, score)] sorted."""
    scored: dict[str, list] = {}
    for results in result_lists:
        for rank, (cid, did, content) in enumerate(results):
            entry = scored.setdefault(cid, [did, content, 0.0])
            entry[2] += 1.0 / (_RRF_K + rank + 1)
    fused = [(cid, v[0], v[1], v[2]) for cid, v in scored.items()]
    fused.sort(key=lambda x: x[3], reverse=True)
    return fused


def _doc_titles(session: Session, doc_ids: set[str]) -> dict[str, str]:
    if not doc_ids:
        return {}
    from app.db.entities import KBDocument

    rows = session.execute(
        select(KBDocument.id, KBDocument.title).where(KBDocument.id.in_(doc_ids))
    ).all()
    return {r[0]: r[1] for r in rows}


def hybrid_search(
    session: Session,
    *,
    tenant_id: str,
    query: str,
    k: int | None = None,
    top_n: int | None = None,
) -> list[RetrievedChunk]:
    """Vector + FTS retrieval, RRF-merged then cross-encoder reranked."""
    k = k or settings.KB_TOP_K
    top_n = top_n or settings.KB_TOP_N
    kb_retrievals_total.inc()

    if _is_postgres(session):
        vec_results: list[tuple[str, str, str]] = []
        if embeddings_available():
            try:
                vec_results = _vector_candidates(
                    session, tenant_id, embed_query(query), k
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("vector_search_failed", error=str(exc))
        fts_results = _fts_candidates(session, tenant_id, query, k)
        fused = _rrf_merge(vec_results, fts_results)
    else:
        like_results = _like_candidates(session, tenant_id, query, k)
        fused = _rrf_merge(like_results)

    if not fused:
        return []

    # Rerank the fused top-k down to top_n.
    candidates = fused[:k]
    scores = rerank(query, [c[2] for c in candidates])
    reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    top = reranked[:top_n]

    doc_ids = {c[0][1] for c in top}
    titles = _doc_titles(session, doc_ids)
    # str() the ids: Postgres returns UUID objects which aren't JSON
    # serializable when citations get persisted in the conversation JSONB.
    return [
        RetrievedChunk(
            chunk_id=str(c[0]),
            document_id=str(c[1]),
            content=c[2],
            doc_title=titles.get(str(c[1]), "documento"),
            score=float(score),
        )
        for (c, score) in top
    ]
