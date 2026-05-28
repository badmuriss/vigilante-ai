"""KB ingestion: markdown text -> chunks -> embeddings -> rows.

Idempotent on `(tenant_id, content_hash)` — re-ingesting an unchanged file
is a no-op. Embeddings are written through raw SQL because the pgvector
column is not declared on the ORM model (keeps the model backend-agnostic).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.entities import KBChunk, KBDocument
from app.kb.chunker import chunk_markdown
from app.kb.embeddings import embed_texts

log = structlog.get_logger(__name__)


@dataclass
class IngestResult:
    document_id: str
    title: str
    chunks_indexed: int
    skipped: bool


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _is_postgres(session: Session) -> bool:
    return session.bind.dialect.name == "postgresql"


def ingest_text(
    session: Session,
    *,
    content: str,
    title: str,
    source: str,
    tenant_id: str | None,
) -> IngestResult:
    """Ingest raw markdown. Caller owns the transaction (commits)."""
    content_hash = _hash(content)

    existing = session.scalar(
        select(KBDocument).where(
            KBDocument.tenant_id.is_(tenant_id)
            if tenant_id is None
            else KBDocument.tenant_id == tenant_id,
            KBDocument.content_hash == content_hash,
        )
    )
    if existing is not None:
        log.info("kb_ingest_skip", title=title, reason="unchanged")
        return IngestResult(
            document_id=existing.id,
            title=existing.title,
            chunks_indexed=0,
            skipped=True,
        )

    doc = KBDocument(
        tenant_id=tenant_id,
        title=title,
        source=source,
        content_hash=content_hash,
        doc_metadata={},
    )
    session.add(doc)
    session.flush()

    chunks = chunk_markdown(
        content,
        target_tokens=settings.KB_CHUNK_TARGET_TOKENS,
        overlap_tokens=settings.KB_CHUNK_OVERLAP_TOKENS,
    )
    if not chunks:
        return IngestResult(doc.id, doc.title, 0, skipped=False)

    vectors = embed_texts([c.text for c in chunks])
    is_pg = _is_postgres(session)

    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        if is_pg:
            vec_literal = "[" + ",".join(str(x) for x in vector) + "]"
            session.execute(
                text(
                    """
                    INSERT INTO kb_chunks
                        (id, tenant_id, document_id, chunk_index, content,
                         embedding, metadata)
                    VALUES
                        (gen_random_uuid(), :tenant_id, :document_id, :chunk_index,
                         :content, (:embedding)::vector, '{}'::jsonb)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "document_id": doc.id,
                    "chunk_index": idx,
                    "content": chunk.text,
                    "embedding": vec_literal,
                },
            )
        else:
            session.add(
                KBChunk(
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk.text,
                    chunk_metadata=chunk.metadata,
                )
            )

    log.info("kb_ingest_ok", title=title, chunks=len(chunks), tenant_id=tenant_id)
    return IngestResult(doc.id, doc.title, len(chunks), skipped=False)


def ingest_file(
    session: Session,
    path: Path,
    *,
    tenant_id: str | None,
    source: str,
) -> IngestResult:
    content = path.read_text(encoding="utf-8")
    return ingest_text(
        session,
        content=content,
        title=path.stem.replace("_", " ").title(),
        source=source,
        tenant_id=tenant_id,
    )


_SOURCE_BY_STEM = {
    "vigilante_manual": "manual",
    "nr06_epi": "nr06",
    "nr18_construcao": "nr18",
}


def seed_global_kb(session: Session, knowledge_dir: Path) -> list[IngestResult]:
    """Ingest every *.md under `knowledge_dir` as global docs (tenant_id NULL)."""
    results: list[IngestResult] = []
    if not knowledge_dir.exists():
        log.warning("kb_seed_dir_missing", path=str(knowledge_dir))
        return results
    for md in sorted(knowledge_dir.glob("*.md")):
        source = _SOURCE_BY_STEM.get(md.stem, "manual")
        results.append(ingest_file(session, md, tenant_id=None, source=source))
    return results
