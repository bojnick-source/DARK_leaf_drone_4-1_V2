"""Local engineering AI knowledge engine.

Provides a retrieval-augmented inference system that loads the
``docs/ai_knowledge/`` corpus and answers engineering questions by
retrieving the most relevant knowledge passages, scoring them, and
composing a structured response.  No external API calls are made —
the engine runs entirely locally.

Key components
--------------
* ``KnowledgeChunk`` — a passage with source metadata.
* ``EngineeringKnowledgeBase`` — loads markdown documents, splits them
  into chunks, and builds a TF-IDF index for retrieval.
* ``QueryResult`` — structured answer with retrieved passages and
  confidence scores.
* ``EngineeringQueryEngine`` — top-level interface that combines
  retrieval with optional ``MemoryStore`` context for
  engineering-specific question answering.

The knowledge base is intentionally trained on the engineering data
shipped with this repository (aerospace, controls, circuits, thermal,
structural, etc.) so the AI is domain-specific.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from reidce.memory import MemoryStore

# ── Tokenisation helpers (consistent with memory.py) ─────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _term_frequency(tokens: Sequence[str]) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    total = 0.0
    for token in tokens:
        counts[token] = counts.get(token, 0.0) + 1.0
        total += 1.0
    if total <= 0.0:
        return counts
    return {t: c / total for t, c in counts.items()}


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Knowledge chunk ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class KnowledgeChunk:
    """One passage from the engineering knowledge corpus."""

    text: str
    source: str
    heading: str
    domain: str
    chunk_id: int = 0


# ── Knowledge base ───────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)", re.MULTILINE)


def _domain_from_filename(filename: str) -> str:
    """Derive an engineering domain tag from a knowledge file name."""
    stem = filename.replace("_math.md", "").replace(".md", "")
    return stem.replace("_", " ")


def _split_markdown(text: str, source: str, domain: str) -> List[KnowledgeChunk]:
    """Split a markdown document into chunks by heading."""
    sections: List[KnowledgeChunk] = []
    headings = list(_HEADING_RE.finditer(text))
    if not headings:
        stripped = text.strip()
        if stripped:
            sections.append(
                KnowledgeChunk(
                    text=stripped,
                    source=source,
                    heading="(root)",
                    domain=domain,
                    chunk_id=0,
                )
            )
        return sections

    # Content before the first heading
    preamble = text[: headings[0].start()].strip()
    if preamble:
        sections.append(
            KnowledgeChunk(
                text=preamble,
                source=source,
                heading="(preamble)",
                domain=domain,
                chunk_id=0,
            )
        )

    for idx, match in enumerate(headings):
        heading_text = match.group(2).strip()
        start = match.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append(
                KnowledgeChunk(
                    text=body,
                    source=source,
                    heading=heading_text,
                    domain=domain,
                    chunk_id=len(sections),
                )
            )

    return sections


@dataclass
class EngineeringKnowledgeBase:
    """TF-IDF indexed engineering knowledge corpus.

    Loads all markdown files from a knowledge directory, splits them
    into chunks, and indexes them for fast retrieval.
    """

    chunks: List[KnowledgeChunk] = field(default_factory=list)
    _doc_tokens: Dict[int, List[str]] = field(default_factory=dict)
    _idf: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, knowledge_dir: Path) -> EngineeringKnowledgeBase:
        """Load all ``.md`` files from *knowledge_dir*."""
        kb = cls()
        if not knowledge_dir.is_dir():
            return kb
        for md_path in sorted(knowledge_dir.glob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            domain = _domain_from_filename(md_path.name)
            chunks = _split_markdown(text, source=md_path.name, domain=domain)
            kb.chunks.extend(chunks)
        kb._build_index()
        return kb

    @classmethod
    def from_texts(
        cls,
        texts: Sequence[str],
        source: str = "inline",
        domain: str = "general",
    ) -> EngineeringKnowledgeBase:
        """Build a knowledge base from raw text strings."""
        kb = cls()
        for idx, text in enumerate(texts):
            kb.chunks.append(
                KnowledgeChunk(
                    text=text,
                    source=source,
                    heading=f"chunk_{idx}",
                    domain=domain,
                    chunk_id=idx,
                )
            )
        kb._build_index()
        return kb

    def _build_index(self) -> None:
        """Compute TF-IDF index over all chunks."""
        self._doc_tokens = {}
        doc_freq: Dict[str, int] = {}
        for idx, chunk in enumerate(self.chunks):
            tokens = _tokenize(chunk.text)
            self._doc_tokens[idx] = tokens
            for token in set(tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1

        n = max(len(self.chunks), 1)
        self._idf = {
            token: math.log((1.0 + n) / (1.0 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        domain_filter: Optional[str] = None,
    ) -> List[RetrievedPassage]:
        """Retrieve the most relevant chunks for a query."""
        if not query.strip() or not self.chunks:
            return []

        query_tokens = _tokenize(query)
        query_tf = _term_frequency(query_tokens)
        query_vec = {t: query_tf[t] * self._idf.get(t, 0.0) for t in query_tf}

        results: List[RetrievedPassage] = []
        for idx, chunk in enumerate(self.chunks):
            if domain_filter and domain_filter.lower() not in chunk.domain.lower():
                continue
            tokens = self._doc_tokens.get(idx, _tokenize(chunk.text))
            tf = _term_frequency(tokens)
            doc_vec = {t: tf[t] * self._idf.get(t, 0.0) for t in tf}
            score = _cosine_similarity(query_vec, doc_vec)
            if score > 0.0:
                results.append(
                    RetrievedPassage(chunk=chunk, relevance_score=score)
                )

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:top_k]

    @property
    def domains(self) -> List[str]:
        """Unique domain tags in the knowledge base."""
        return sorted({chunk.domain for chunk in self.chunks})


# ── Retrieved passage ────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetrievedPassage:
    """A knowledge chunk with its retrieval relevance score."""

    chunk: KnowledgeChunk
    relevance_score: float


# ── Query result ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class QueryResult:
    """Structured answer to an engineering query."""

    query: str
    answer: str
    passages: List[RetrievedPassage]
    domain: str
    confidence: float


# ── Query engine ─────────────────────────────────────────────────────────


@dataclass
class EngineeringQueryEngine:
    """Local inference engine for engineering questions.

    Combines retrieval from the knowledge base with optional
    ``MemoryStore`` context to produce domain-specific answers.
    Does not call any external APIs — runs entirely locally.
    """

    knowledge_base: EngineeringKnowledgeBase
    memory_store: Optional[MemoryStore] = None

    @classmethod
    def from_knowledge_dir(
        cls,
        knowledge_dir: Path,
        memory_store: Optional[MemoryStore] = None,
    ) -> EngineeringQueryEngine:
        kb = EngineeringKnowledgeBase.from_directory(knowledge_dir)
        return cls(knowledge_base=kb, memory_store=memory_store)

    def query(
        self,
        question: str,
        top_k: int = 3,
        domain_filter: Optional[str] = None,
    ) -> QueryResult:
        """Answer an engineering question using local retrieval.

        Steps:
        1. Retrieve top-k relevant passages from the knowledge base.
        2. Optionally augment with MemoryStore context.
        3. Compose a structured answer from the retrieved passages.
        """
        passages = self.knowledge_base.search(
            question, top_k=top_k, domain_filter=domain_filter
        )

        # Augment with memory context if available
        if self.memory_store is not None:
            memory_results = self.memory_store.search(question, top_k=2)
            for mr in memory_results:
                passages.append(
                    RetrievedPassage(
                        chunk=KnowledgeChunk(
                            text=mr.record.text,
                            source="memory",
                            heading="memory_context",
                            domain="memory",
                        ),
                        relevance_score=mr.score * 0.8,
                    )
                )
            passages.sort(key=lambda r: r.relevance_score, reverse=True)
            passages = passages[:top_k]

        # Compose answer from retrieved passages
        if not passages:
            return QueryResult(
                query=question,
                answer="No relevant engineering knowledge found for this query.",
                passages=[],
                domain="unknown",
                confidence=0.0,
            )

        top_domain = passages[0].chunk.domain
        confidence = passages[0].relevance_score

        answer_parts: List[str] = []
        for p in passages:
            heading = p.chunk.heading
            source = p.chunk.source
            snippet = p.chunk.text[:300]
            if len(p.chunk.text) > 300:
                snippet += "..."
            answer_parts.append(f"[{source} / {heading}]: {snippet}")

        answer = "\n\n".join(answer_parts)

        if self.memory_store is not None:
            self.memory_store.log_event(
                "ai_query",
                f"Engineering query: {question[:100]}",
                {
                    "domain": top_domain,
                    "confidence": round(confidence, 3),
                    "n_passages": len(passages),
                },
            )

        return QueryResult(
            query=question,
            answer=answer,
            passages=passages,
            domain=top_domain,
            confidence=round(confidence, 4),
        )

    def list_domains(self) -> List[str]:
        """Return available engineering domains."""
        return self.knowledge_base.domains

    def to_dict(self) -> Dict[str, Any]:
        """Summary of engine state."""
        return {
            "schema": "dark/engineering_ai/1.0",
            "n_chunks": len(self.knowledge_base.chunks),
            "domains": self.list_domains(),
            "has_memory": self.memory_store is not None,
        }
