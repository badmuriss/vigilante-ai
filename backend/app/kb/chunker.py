"""Markdown → token-bounded chunks.

Splits on headings first (keeps semantic sections together), then packs
sections into ~`target_tokens` chunks with `overlap_tokens` carry-over so a
fact that straddles a boundary is still retrievable. Token counting uses
tiktoken `cl100k_base`; if tiktoken is unavailable we fall back to a
words≈tokens heuristic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text))

    def _split_tokens(text: str, max_tokens: int) -> list[str]:
        ids = _ENC.encode(text)
        return [
            _ENC.decode(ids[i : i + max_tokens])
            for i in range(0, len(ids), max_tokens)
        ]

except Exception:  # pragma: no cover - tiktoken always present in prod
    _ENC = None

    def _count_tokens(text: str) -> int:
        return max(1, len(text.split()))

    def _split_tokens(text: str, max_tokens: int) -> list[str]:
        words = text.split()
        return [
            " ".join(words[i : i + max_tokens])
            for i in range(0, len(words), max_tokens)
        ]


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Return [(heading_path, body)] splitting on markdown headings."""
    matches = list(_HEADING_RE.finditer(markdown))
    if not matches:
        return [("", markdown.strip())]

    sections: list[tuple[str, str]] = []
    preamble = markdown[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for idx, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        if body:
            sections.append((heading, body))
    return sections


def chunk_markdown(
    markdown: str,
    *,
    target_tokens: int = 600,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    """Chunk markdown into overlapping, heading-aware pieces."""
    sections = _split_sections(markdown)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    current_heading = ""

    def flush() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        if text:
            chunks.append(Chunk(text=text, metadata={"heading": current_heading}))
        buf = []
        buf_tokens = 0

    for heading, body in sections:
        block = f"## {heading}\n\n{body}" if heading else body
        block_tokens = _count_tokens(block)

        # A single oversized section gets hard-split on token windows.
        if block_tokens > target_tokens:
            flush()
            current_heading = heading
            for piece in _split_tokens(block, target_tokens):
                chunks.append(
                    Chunk(text=piece.strip(), metadata={"heading": heading})
                )
            continue

        if buf_tokens + block_tokens > target_tokens and buf:
            flush()
            # Carry overlap from the end of the previous chunk.
            if overlap_tokens > 0 and chunks:
                tail = chunks[-1].text
                tail_piece = _split_tokens(tail, overlap_tokens)
                if tail_piece:
                    buf.append(tail_piece[-1])
                    buf_tokens += _count_tokens(tail_piece[-1])

        current_heading = heading or current_heading
        buf.append(block)
        buf_tokens += block_tokens

    flush()
    # Drop empties + reindex.
    return [c for c in chunks if c.text.strip()]
