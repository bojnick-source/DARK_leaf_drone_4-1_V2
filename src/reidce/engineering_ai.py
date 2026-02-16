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
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
        """Compute TF-IDF index over all chunks.

        Precomputes TF-IDF weighted vectors for each document at index
        time so that search() only needs to compute the query vector
        and dot products — avoids recomputing per-document vectors on
        every query.
        """
        self._doc_tokens = {}
        self._doc_vectors: Dict[int, Dict[str, float]] = {}
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

        # Precompute TF-IDF weighted vectors for each document
        for idx in range(len(self.chunks)):
            tokens = self._doc_tokens.get(idx, [])
            tf = _term_frequency(tokens)
            self._doc_vectors[idx] = {
                t: tf[t] * self._idf.get(t, 0.0) for t in tf
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
            # Use precomputed TF-IDF vector (O(1) lookup vs O(n) recompute)
            doc_vec = self._doc_vectors.get(idx)
            if doc_vec is None:
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


# ── Conversational context engine ────────────────────────────────────

# Tuning constants for intent classification
_INTENT_KEYWORD_THRESHOLD = 0.4
"""Fraction of keywords required for full confidence."""

_INTENT_DECAY_FACTOR = 0.7
"""Decay applied to older intent scores each turn."""


# Competition-specific intent patterns with weighted keyword matching
_COMPETITION_INTENTS: Dict[str, List[str]] = {
    "design_review": [
        "design", "review", "evaluate", "assess", "check", "validate",
        "constraint", "requirement", "spec",
    ],
    "topology_optimize": [
        "topology", "optimize", "optimise", "stiffness", "weight",
        "lightweight", "structural", "strength", "deflection",
    ],
    "cad_generate": [
        "cad", "mesh", "3d", "model", "generate", "render", "stl",
        "geometry", "shape", "autocad", "shapr",
    ],
    "competition_rules": [
        "competition", "darpa", "lift", "rules", "constraint", "payload",
        "ratio", "4:1", "course", "prize", "challenge",
    ],
    "flight_performance": [
        "flight", "fly", "performance", "speed", "endurance", "climb",
        "turn", "hover", "power", "thrust", "energy",
    ],
    "manufacturing": [
        "manufacturing", "build", "fabricate", "material", "process",
        "composite", "carbon", "assembly", "production",
    ],
}


def classify_intent(text: str) -> List[tuple[str, float]]:
    """Classify user intent from free-form text.

    Returns a ranked list of ``(intent_name, confidence)`` pairs where
    confidence is the fraction of intent keywords found in the text.
    Competition-centric intents are prioritised over general ones.
    """
    lower = text.lower()
    tokens = set(_tokenize(lower))
    scores: List[tuple[str, float]] = []
    for intent, keywords in _COMPETITION_INTENTS.items():
        matches = sum(1 for kw in keywords if kw in tokens or kw in lower)
        if matches > 0:
            confidence = min(matches / max(len(keywords) * _INTENT_KEYWORD_THRESHOLD, 1.0), 1.0)
            scores.append((intent, round(confidence, 3)))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation."""

    role: str
    text: str
    intent: str = ""
    confidence: float = 0.0


@dataclass
class ConversationContext:
    """Multi-turn conversational context tracker.

    Maintains conversation history and extracts cumulative intent across
    turns, enabling Claude-like contextual understanding where later
    messages can refine or build on earlier ones.
    """

    turns: List[ConversationTurn] = field(default_factory=list)
    active_intents: Dict[str, float] = field(default_factory=dict)
    design_parameters: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, text: str) -> ConversationTurn:
        """Add a conversation turn and update cumulative intent."""
        intents = classify_intent(text) if role == "user" else []
        top_intent = intents[0][0] if intents else ""
        top_confidence = intents[0][1] if intents else 0.0

        turn = ConversationTurn(
            role=role, text=text, intent=top_intent, confidence=top_confidence,
        )
        self.turns.append(turn)

        # Update cumulative intent scores with decay for older turns
        for intent, conf in intents:
            existing = self.active_intents.get(intent, 0.0)
            self.active_intents[intent] = min(existing * _INTENT_DECAY_FACTOR + conf, 1.0)

        # Extract design parameters from user text
        if role == "user":
            self._extract_parameters(text)

        return turn

    def _extract_parameters(self, text: str) -> None:
        """Extract numeric design parameters from user input."""
        lower = text.lower()
        import re as _re

        # Arm count
        m = _re.search(r"(\d+)\s*(?:arm|motor|rotor|prop)", lower)
        if m:
            self.design_parameters["arm_count"] = int(m.group(1))

        # Mass/weight targets
        m = _re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilogram)", lower)
        if m:
            self.design_parameters["target_mass_kg"] = float(m.group(1))

        # Payload
        m = _re.search(r"payload\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:kg)?", lower)
        if m:
            self.design_parameters["payload_kg"] = float(m.group(1))

    def get_dominant_intent(self) -> tuple[str, float]:
        """Return the highest-confidence cumulative intent."""
        if not self.active_intents:
            return ("", 0.0)
        best = max(self.active_intents.items(), key=lambda x: x[1])
        return best

    def get_context_summary(self) -> str:
        """Build a summary of conversation context for response generation."""
        parts: List[str] = []
        if self.active_intents:
            top = sorted(self.active_intents.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append("Active intents: " + ", ".join(f"{k}({v:.2f})" for k, v in top))
        if self.design_parameters:
            params = ", ".join(f"{k}={v}" for k, v in self.design_parameters.items())
            parts.append("Design parameters: " + params)
        parts.append(f"Turns: {len(self.turns)}")
        return "; ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context state."""
        return {
            "schema": "dark/conversation_context/1.0",
            "turn_count": len(self.turns),
            "active_intents": dict(self.active_intents),
            "design_parameters": dict(self.design_parameters),
            "dominant_intent": self.get_dominant_intent()[0],
        }


# ---------------------------------------------------------------------------
# Hardened AI pipeline — cached queries and cross-engine integration
# ---------------------------------------------------------------------------

_QUERY_CACHE: Dict[Tuple[str, Optional[str]], QueryResult] = {}
_QUERY_CACHE_MAX = 256


def cached_query(
    engine: EngineeringQueryEngine,
    question: str,
    top_k: int = 3,
    domain_filter: Optional[str] = None,
) -> QueryResult:
    """LRU-style cached query — avoids re-searching for repeated questions."""
    cache_key = (question.strip().lower(), domain_filter)
    if cache_key in _QUERY_CACHE:
        return _QUERY_CACHE[cache_key]

    result = engine.query(question, top_k=top_k, domain_filter=domain_filter)

    if len(_QUERY_CACHE) >= _QUERY_CACHE_MAX:
        oldest = next(iter(_QUERY_CACHE))
        del _QUERY_CACHE[oldest]
    _QUERY_CACHE[cache_key] = result
    return result


def clear_query_cache() -> None:
    """Clear the engineering AI query cache."""
    _QUERY_CACHE.clear()


@dataclass(frozen=True)
class PipelineResult:
    """Result from the integrated engineering AI pipeline."""
    query: str
    answer: str
    confidence: float
    domain: str
    intent: str
    intent_confidence: float
    design_parameters: Dict[str, Any]
    passages_used: int


def run_ai_pipeline(
    engine: EngineeringQueryEngine,
    context: ConversationContext,
    user_text: str,
    top_k: int = 3,
) -> PipelineResult:
    """Integrated pipeline: intent classification + retrieval + answer.

    1. Classify intent from user text
    2. Update conversation context
    3. Route query to domain-specific search via intent
    4. Return structured pipeline result with full provenance
    """
    turn = context.add_turn("user", user_text)

    # Route to domain based on detected intent
    intent = turn.intent
    domain_filter: Optional[str] = None
    _INTENT_TO_DOMAIN = {
        "design_review": None,  # search all domains
        "topology_optimize": "structural",
        "cad_generate": "cad",
        "competition_rules": "competition",
        "flight_performance": "aerospace",
        "manufacturing": "manufacturing",
    }
    domain_filter = _INTENT_TO_DOMAIN.get(intent)

    result = cached_query(engine, user_text, top_k=top_k, domain_filter=domain_filter)

    context.add_turn("assistant", result.answer[:200])

    return PipelineResult(
        query=user_text,
        answer=result.answer,
        confidence=result.confidence,
        domain=result.domain,
        intent=intent,
        intent_confidence=turn.confidence,
        design_parameters=dict(context.design_parameters),
        passages_used=len(result.passages),
    )
