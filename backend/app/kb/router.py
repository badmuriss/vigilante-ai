"""Knowledge-base admin endpoints (admin-only).

Lets an admin upload markdown docs that become tenant-scoped KB content for
the assistant. Global docs (the seeded manual + NRs) are read-only here and
listed with `is_global=true`.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth.dependencies import CurrentUser, require_role
from app.db.base import get_session
from app.db.entities import KBChunk, KBDocument
from app.kb.ingest import ingest_text
from app.kb.schemas import (
    KBDocumentListResponse,
    KBDocumentResponse,
    KBIngestResponse,
)

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])

_ADMIN_ONLY = require_role("admin")


def _chunk_counts(session: Session, doc_ids: list[str]) -> dict[str, int]:
    if not doc_ids:
        return {}
    rows = session.execute(
        select(KBChunk.document_id, func.count())
        .where(KBChunk.document_id.in_(doc_ids))
        .group_by(KBChunk.document_id)
    ).all()
    return {r[0]: int(r[1]) for r in rows}


@router.get("/documents", response_model=KBDocumentListResponse)
def list_documents(
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> KBDocumentListResponse:
    # Tenant's own docs + global docs.
    docs = session.scalars(
        select(KBDocument)
        .where(
            (KBDocument.tenant_id == user.tenant_id)
            | (KBDocument.tenant_id.is_(None))
        )
        .order_by(KBDocument.created_at.desc())
    ).all()
    counts = _chunk_counts(session, [d.id for d in docs])
    return KBDocumentListResponse(
        documents=[
            KBDocumentResponse(
                id=d.id,
                title=d.title,
                source=d.source,
                is_global=d.tenant_id is None,
                chunks_indexed=counts.get(d.id, 0),
                created_at=d.created_at,
            )
            for d in docs
        ]
    )


@router.post("/documents", response_model=KBIngestResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> KBIngestResponse:
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 markdown/text")
    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    doc_title = title or (file.filename or "documento").rsplit(".", 1)[0]
    result = ingest_text(
        session,
        content=content,
        title=doc_title,
        source="upload",
        tenant_id=user.tenant_id,
    )
    session.commit()
    return KBIngestResponse(
        document_id=result.document_id,
        title=result.title,
        chunks_indexed=result.chunks_indexed,
        skipped=result.skipped,
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
):
    doc = session.get(KBDocument, document_id)
    # 404 (not 403) for global or other-tenant docs to avoid leaking existence.
    if doc is None or doc.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    session.delete(doc)
    session.commit()
    from fastapi import Response

    return Response(status_code=204)
