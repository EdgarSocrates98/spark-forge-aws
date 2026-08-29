"""Context Funnel Engine for SparkForge.

Filters, extracts, deduplicates, and condenses context to achieve minimal token footprints.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class ContextChunk:
    source_file: str
    chunk_id: str
    content: str
    start_line: int = 1
    end_line: int = 1
    relevance_score: float = 1.0
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.content_hash = hashlib.sha256(self.content.strip().encode("utf-8")).hexdigest()[:16]


@dataclass
class MinimalContext:
    total_tokens_estimate: int
    chunks: list[ContextChunk]
    deduplicated_count: int
    summary: str

    def to_prompt_text(self) -> str:
        blocks = []
        for c in self.chunks:
            blocks.append(
                f"### File: {c.source_file} (Lines {c.start_line}-{c.end_line})\n```\n{c.content}\n"
                f"```"
            )
        return "\n\n".join(blocks)


class ContextFunnel:
    """Implements repository -> candidate files -> relevant chunks -> deduplicated
    evidence -> minimal context."""

    def __init__(self, max_tokens_budget: int = 4000) -> None:
        self.max_tokens_budget = max_tokens_budget

    def filter_candidate_files(self, file_paths: list[str], keywords: list[str]) -> list[str]:
        if not keywords:
            return file_paths
        candidates = []
        kw_lower = [k.lower() for k in keywords]
        for p in file_paths:
            p_lower = p.lower()
            if any(k in p_lower for k in kw_lower):
                candidates.append(p)
        return candidates or file_paths

    def deduplicate_chunks(self, chunks: list[ContextChunk]) -> tuple[list[ContextChunk], int]:
        seen_hashes = set()
        deduped = []
        dropped = 0
        for c in chunks:
            if c.content_hash not in seen_hashes:
                seen_hashes.add(c.content_hash)
                deduped.append(c)
            else:
                dropped += 1
        return deduped, dropped

    def build_minimal_context(self, chunks: list[ContextChunk]) -> MinimalContext:
        # 1. Sort chunks by relevance
        sorted_chunks = sorted(chunks, key=lambda x: x.relevance_score, reverse=True)

        # 2. Deduplicate
        unique_chunks, dropped = self.deduplicate_chunks(sorted_chunks)

        # 3. Fit in budget (estimate 4 chars per token)
        fitted_chunks = []
        total_tokens = 0
        for c in unique_chunks:
            tokens_est = max(1, len(c.content) // 4)
            if total_tokens + tokens_est <= self.max_tokens_budget:
                fitted_chunks.append(c)
                total_tokens += tokens_est
            else:
                break

        summary = (
            f"Packed {len(fitted_chunks)} chunks (~{total_tokens} tokens), dropped "
            f"{dropped} duplicates."
        )
        return MinimalContext(
            total_tokens_estimate=total_tokens,
            chunks=fitted_chunks,
            deduplicated_count=dropped,
            summary=summary,
        )
