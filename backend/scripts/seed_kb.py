"""Seed the global knowledge base from backend/knowledge/*.md.

Run inside the backend container:
    python -m scripts.seed_kb

Idempotent — re-running skips unchanged documents (matched by content hash).
"""

from __future__ import annotations

from pathlib import Path

import structlog

from app.config import settings
from app.db.base import session_scope
from app.kb.ingest import seed_global_kb

log = structlog.get_logger(__name__)


def main() -> None:
    knowledge_dir = Path(__file__).resolve().parent.parent / settings.KB_KNOWLEDGE_DIR
    with session_scope() as session:
        results = seed_global_kb(session, knowledge_dir)
        session.commit()
    total_chunks = sum(r.chunks_indexed for r in results)
    seeded = sum(1 for r in results if not r.skipped)
    log.info(
        "kb_seed_done",
        documents=len(results),
        newly_indexed=seeded,
        chunks=total_chunks,
    )
    print(
        f"KB seed: {len(results)} docs ({seeded} new), "
        f"{total_chunks} chunks indexed."
    )


if __name__ == "__main__":
    main()
