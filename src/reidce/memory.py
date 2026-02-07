from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _empty_tags() -> list[str]:
    return []


def _empty_metadata() -> dict[str, Any]:
    return {}


def _now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _term_frequency(tokens: Iterable[str]) -> dict[str, float]:
    counts: dict[str, float] = {}
    total = 0.0
    for token in tokens:
        counts[token] = counts.get(token, 0.0) + 1.0
        total += 1.0
    if total <= 0.0:
        return counts
    return {token: value / total for token, value in counts.items()}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = 0.0
    for key, value in vec_a.items():
        if key in vec_b:
            dot += value * vec_b[key]
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    created_utc: str
    source: str
    text: str
    tags: list[str] = field(default_factory=_empty_tags)
    metadata: dict[str, Any] = field(default_factory=_empty_metadata)


@dataclass(frozen=True)
class MemorySearchResult:
    record: MemoryRecord
    score: float


class MemoryStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path
        self._records: list[MemoryRecord] = []
        self._doc_tokens: dict[str, list[str]] = {}
        if self._path:
            self.load(self._path)

    @property
    def records(self) -> list[MemoryRecord]:
        return list(self._records)

    def add(
        self,
        text: str,
        source: str = "manual",
        tags: Optional[Iterable[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            record_id=str(uuid4()),
            created_utc=_now_utc_iso(),
            source=source,
            text=text,
            tags=list(tags or []),
            metadata=dict(metadata or {}),
        )
        self._records.append(record)
        self._doc_tokens[record.record_id] = _tokenize(record.text)
        return record

    def log_event(
        self,
        event_type: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryRecord:
        tags = ["event", event_type]
        return self.add(text=message, source="event", tags=tags, metadata=metadata)

    def search(
        self,
        query: str,
        top_k: int = 5,
        required_tags: Optional[Iterable[str]] = None,
        source: Optional[str] = None,
    ) -> list[MemorySearchResult]:
        if not query.strip():
            return []
        required = set(required_tags or [])
        records = [
            record
            for record in self._records
            if (not required or required.issubset(record.tags))
            and (source is None or record.source == source)
        ]
        if not records:
            return []

        doc_freq: dict[str, int] = {}
        for record in records:
            tokens = self._doc_tokens.get(record.record_id) or _tokenize(record.text)
            self._doc_tokens[record.record_id] = tokens
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        total_docs = max(len(records), 1)
        idf = {
            token: math.log((1 + total_docs) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }

        query_tokens = _tokenize(query)
        query_tf = _term_frequency(query_tokens)
        query_vec = {token: query_tf[token] * idf.get(token, 0.0) for token in query_tf}

        scored: list[MemorySearchResult] = []
        for record in records:
            tokens = self._doc_tokens.get(record.record_id) or _tokenize(record.text)
            tf = _term_frequency(tokens)
            vector = {token: tf[token] * idf.get(token, 0.0) for token in tf}
            score = _cosine_similarity(query_vec, vector)
            if score > 0.0:
                scored.append(MemorySearchResult(record=record, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k] if top_k > 0 else []

    def save(self, path: Optional[Path] = None) -> Path:
        target = path or self._path
        if target is None:
            raise ValueError("MemoryStore has no target path to save.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for record in self._records:
                handle.write(json.dumps(record.__dict__, sort_keys=True))
                handle.write("\n")
        self._path = target
        return target

    def load(self, path: Path) -> None:
        if not path.exists():
            self._path = path
            return
        records: list[MemoryRecord] = []
        doc_tokens: dict[str, list[str]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                record = MemoryRecord(
                    record_id=payload["record_id"],
                    created_utc=payload["created_utc"],
                    source=payload.get("source", "manual"),
                    text=payload.get("text", ""),
                    tags=list(payload.get("tags", [])),
                    metadata=dict(payload.get("metadata", {})),
                )
                records.append(record)
                doc_tokens[record.record_id] = _tokenize(record.text)
        self._records = records
        self._doc_tokens = doc_tokens
        self._path = path
