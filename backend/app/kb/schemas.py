"""Request/response models for the KB admin API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class KBDocumentResponse(BaseModel):
    id: str
    title: str
    source: str
    is_global: bool
    chunks_indexed: int
    created_at: datetime


class KBDocumentListResponse(BaseModel):
    documents: list[KBDocumentResponse]


class KBIngestResponse(BaseModel):
    document_id: str
    title: str
    chunks_indexed: int
    skipped: bool


class KBReindexResponse(BaseModel):
    documents_reindexed: int
    chunks_reindexed: int
