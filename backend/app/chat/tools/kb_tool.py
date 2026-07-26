"""KB search tool — wraps hybrid retrieval and returns citeable results."""

from __future__ import annotations

from app.chat.tools import Tool, ToolContext, ToolResult
from app.kb.retrieval import hybrid_search


def _search_knowledge_base(args: dict, ctx: ToolContext) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult(payload={"results": [], "note": "query vazia"})

    chunks = hybrid_search(ctx.session, tenant_id=ctx.tenant_id, query=query)
    results = []
    citations = []
    for i, chunk in enumerate(chunks, start=1):
        results.append(
            {"idx": i, "doc_title": chunk.doc_title, "content": chunk.content}
        )
        citations.append(
            {
                "idx": i,
                "doc_title": chunk.doc_title,
                "snippet": chunk.content[:240],
                "document_id": chunk.document_id,
            }
        )
    return ToolResult(payload={"results": results}, citations=citations)


KB_TOOLS = [
    Tool(
        name="search_knowledge_base",
        description=(
            "Busca na base de conhecimento (manual do Vigilante.AI e normas de "
            "segurança do trabalho; a base inicial inclui NR-6 sobre EPI e NR-18 "
            "sobre construção civil). Use para dúvidas de uso da plataforma ou de "
            "normas de segurança. Retorna trechos numerados para citação."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pergunta ou termos de busca em português.",
                }
            },
            "required": ["query"],
        },
        handler=_search_knowledge_base,
    )
]
