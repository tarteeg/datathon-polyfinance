"""Retrieval layer (master spec section 8.5).

`BedrockKnowledgeBaseRetriever` is the production retriever (Bedrock Knowledge Bases +
a supported vector store). It requires `bedrock:Retrieve` permission, which is not
available on the personal AWS account used for local development (confirmed denied --
see docs/KNOWN_LIMITATIONS.md) and is untested against a live Knowledge Base as a
result; it is included for the hackathon account where Bedrock access is expected to
work, with the same call shape as the local retriever below so swapping one for the
other requires no caller changes.

`LocalLexicalRetriever` is a transparent, dependency-light TF-IDF-style retriever used
for local development and testing without any AWS dependency. It is not a substitute
for semantic (embedding) retrieval, but it is fully inspectable: every score is a
literal term-overlap computation, which is useful while debugging citation accuracy.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from app.riskripple.rag.chunking import DocumentChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Found via the RAG evaluation benchmark (backend/src/riskripple/evaluation/rag_eval.py):
# without filtering these, a query sharing only function words with a large real
# corpus (e.g. "...for homeowners", "...across Europe") still registers nonzero
# cosine similarity against unrelated documents, since common words appear in most
# chunks and their IDF isn't low enough to zero out the dot product. This is a
# standard, minimal English stopword list, not a tuned one.
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "he", "in", "is", "it", "its", "of", "on", "or", "our", "that", "the", "their",
    "this", "to", "was", "we", "were", "will", "with", "you",
})


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class Retriever(Protocol):
    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]: ...


class LocalLexicalRetriever:
    """TF-IDF cosine-similarity retrieval over an in-memory chunk collection."""

    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self._doc_term_counts = [Counter(_tokenize(c.text)) for c in chunks]
        self._df: Counter[str] = Counter()
        for counts in self._doc_term_counts:
            self._df.update(counts.keys())
        self._n_docs = len(chunks)

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        return math.log((self._n_docs + 1) / (df + 1)) + 1.0

    def _vector(self, term_counts: Counter) -> dict[str, float]:
        return {term: count * self._idf(term) for term, count in term_counts.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        common = set(a) & set(b)
        numerator = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

    def retrieve(
        self, query: str, *, top_k: int = 5, metadata_filter: dict | None = None, min_score: float = 0.0
    ) -> list[RetrievedChunk]:
        """`min_score` defaults to 0.0 (any term overlap counts) for backward
        compatibility. The RAG evaluation benchmark
        (`riskripple.evaluation.rag_eval`, run via `scripts/run_rag_eval.py`) found
        that over a realistically-sized real corpus, cosine scores for genuinely
        unrelated queries topped out around 0.06 while true matches started above
        0.23 — callers that need to say "no relevant evidence found" (e.g. before
        asserting a regulatory/exposure link) should pass `min_score=0.15` rather
        than treating "nonempty results" as "relevant results."
        """
        query_vector = self._vector(Counter(_tokenize(query)))
        scored: list[RetrievedChunk] = []
        for chunk, doc_counts in zip(self.chunks, self._doc_term_counts):
            if metadata_filter and not _matches_filter(chunk, metadata_filter):
                continue
            score = self._cosine(query_vector, self._vector(doc_counts))
            if score > min_score:
                scored.append(RetrievedChunk(chunk=chunk, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]


def _matches_filter(chunk: DocumentChunk, metadata_filter: dict) -> bool:
    for key, value in metadata_filter.items():
        if getattr(chunk, key, None) != value:
            return False
    return True


def deduplicate(results: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen_hashes: set[str] = set()
    deduped = []
    for r in results:
        if r.chunk.content_hash in seen_hashes:
            continue
        seen_hashes.add(r.chunk.content_hash)
        deduped.append(r)
    return deduped


def build_evidence_context(results: list[RetrievedChunk], *, max_chunks: int = 8) -> str:
    """Bounded evidence context for an LLM prompt, with inline citation markers that
    the answer-generation step must reference (validated downstream by
    validate_report_citations in tools/persona_tools.py)."""
    parts = []
    for i, r in enumerate(deduplicate(results)[:max_chunks], start=1):
        c = r.chunk
        citation = f"[{i}] {c.title or c.document_id}" + (f" ({c.source_url})" if c.source_url else "")
        parts.append(f"{citation}\n{c.text}")
    return "\n\n---\n\n".join(parts)


class BedrockKnowledgeBaseRetriever:
    """Production retriever backed by Amazon Bedrock Knowledge Bases.

    CONFIRMED WORKING LIVE (2026-11-14, hackathon account 637423589728, us-east-1):
    a real Knowledge Base (id SSYDB0BFCH) backed by Amazon S3 Vectors (Titan Text
    Embeddings v2, 1024 dims) with the 3 real 10-Ks + 20 real Federal Register
    documents indexed. This class needed zero code changes to work against it.
    Retrieving "export restrictions on advanced computing chips to China" correctly
    returned NVDA's and AMD's real export-control risk-factor passages with no
    literal keyword overlap required -- a genuine semantic match the TF-IDF
    `LocalLexicalRetriever` cannot do (see "What's NOT semantic here" in
    docs/RAG_PIPELINE.md). See docs/KNOWLEDGE_BASE.md for setup details.
    """

    def __init__(self, knowledge_base_id: str, region_name: str = "us-east-1"):
        import boto3  # local import: keep boto3 optional for pure-local test runs

        self.knowledge_base_id = knowledge_base_id
        self._client = boto3.client("bedrock-agent-runtime", region_name=region_name)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        response = self._client.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
        )
        results = []
        for item in response.get("retrievalResults", []):
            metadata = item.get("metadata", {})
            chunk = DocumentChunk(
                chunk_id=metadata.get("chunk_id", ""),
                document_id=metadata.get("document_id", ""),
                text=item.get("content", {}).get("text", ""),
                token_count=0,
                position=0,
                source_url=item.get("location", {}).get("s3Location", {}).get("uri"),
                title=metadata.get("title"),
            )
            results.append(RetrievedChunk(chunk=chunk, score=item.get("score", 0.0)))
        return results
