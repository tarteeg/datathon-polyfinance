"""Structure-aware, token-based document chunking (master spec section 8.2).

Uses token counts (not character counts) so chunk sizes are meaningful regardless of
language or markup density.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from uuid import uuid4

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")

DEFAULT_CHUNK_TOKENS = 1000
DEFAULT_OVERLAP_TOKENS = 150

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    text: str
    token_count: int
    position: int  # 0-based order within the document
    source_url: str | None = None
    title: str | None = None
    page_number: int | None = None
    section: str | None = None
    publication_date: str | None = None
    jurisdiction: str | None = None
    related_entities: list[str] = field(default_factory=list)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def chunk_document(
    *,
    document_id: str,
    text: str,
    title: str | None = None,
    source_url: str | None = None,
    jurisdiction: str | None = None,
    related_entities: list[str] | None = None,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[DocumentChunk]:
    """Paragraph-aware chunking: packs whole paragraphs into a chunk up to
    `chunk_tokens`, splitting an over-long paragraph only as a last resort, and carries
    `overlap_tokens` of trailing context into the next chunk so a fact split across a
    chunk boundary isn't lost to either chunk alone.
    """
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[DocumentChunk] = []
    current_paragraphs: list[str] = []
    current_tokens = 0
    position = 0

    def flush() -> None:
        nonlocal current_paragraphs, current_tokens, position
        if not current_paragraphs:
            return
        chunk_text = "\n\n".join(current_paragraphs)
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document_id}_chunk{position}_{uuid4().hex[:8]}",
                document_id=document_id,
                text=chunk_text,
                token_count=count_tokens(chunk_text),
                position=position,
                source_url=source_url,
                title=title,
                jurisdiction=jurisdiction,
                related_entities=related_entities or [],
            )
        )
        position += 1

    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph)

        if paragraph_tokens > chunk_tokens:
            # Oversized paragraph (e.g. a dense table or run-on legal clause): flush
            # what we have, then hard-split this paragraph on token boundaries.
            flush()
            current_paragraphs, current_tokens = [], 0
            tokens = _ENCODING.encode(paragraph)
            start = 0
            while start < len(tokens):
                end = start + chunk_tokens
                piece = _ENCODING.decode(tokens[start:end])
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}_chunk{position}_{uuid4().hex[:8]}",
                        document_id=document_id,
                        text=piece,
                        token_count=end - start,
                        position=position,
                        source_url=source_url,
                        title=title,
                        jurisdiction=jurisdiction,
                        related_entities=related_entities or [],
                    )
                )
                position += 1
                start += chunk_tokens - overlap_tokens
            continue

        if current_tokens + paragraph_tokens > chunk_tokens:
            flush()
            # Carry trailing paragraphs forward until we've covered ~overlap_tokens.
            carried: list[str] = []
            carried_tokens = 0
            for p in reversed(current_paragraphs):
                pt = count_tokens(p)
                if carried_tokens + pt > overlap_tokens:
                    break
                carried.insert(0, p)
                carried_tokens += pt
            current_paragraphs = carried
            current_tokens = carried_tokens

        current_paragraphs.append(paragraph)
        current_tokens += paragraph_tokens

    flush()
    return chunks
