"""Deterministic Error Signature Matcher for SparkForge."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from sparkforge.facts.scan import iter_source_files


@dataclass
class ErrorMatchResult:
    error_id: str
    signature: str
    service: str
    likely_causes: list[str]
    diagnostic_steps: list[str]
    fixes: list[str]
    confidence: float
    matched_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeterministicErrorMatcher:
    """Matches stacktraces and logs against local Error KB signatures with zero LLM calls."""

    def __init__(self, errors_dir: Optional[Path] = None) -> None:
        self.errors_dir = errors_dir or (Path(__file__).parent.parent.parent / "knowledge" / "errors")
        self.signatures: list[dict[str, Any]] = []
        self._load_signatures()

    def _load_signatures(self) -> None:
        # `errors_dir` vem do construtor, entao o default embarcado nao e
        # garantia: quem instancia pode apontar para fora do `knowledge/`, e a
        # partir dai isto e varredura de arvore de terceiro como qualquer outra.
        if not self.errors_dir.is_dir():
            return
        for err_file in iter_source_files(self.errors_dir, "*.json"):
            try:
                data = json.loads(err_file.read_text(encoding="utf-8"))
                if "id" in data and "signature" in data:
                    self.signatures.append(data)
            except Exception:
                pass

    def match_log(self, log_content: str) -> list[ErrorMatchResult]:
        matches: list[ErrorMatchResult] = []
        log_lower = log_content.lower()

        for sig in self.signatures:
            sig_pattern = sig["signature"].lower()
            if sig_pattern in log_lower or re.search(re.escape(sig_pattern), log_lower):
                # Find matching snippet
                idx = log_lower.find(sig_pattern)
                start = max(0, idx - 40)
                end = min(len(log_content), idx + len(sig_pattern) + 40)
                snippet = log_content[start:end].strip()

                matches.append(
                    ErrorMatchResult(
                        error_id=sig["id"],
                        signature=sig["signature"],
                        service=sig.get("service", "unknown"),
                        likely_causes=sig.get("likely_causes", []),
                        diagnostic_steps=sig.get("diagnostic_steps", []),
                        fixes=sig.get("fixes", []),
                        confidence=0.98,
                        matched_snippet=snippet,
                    )
                )

        return matches
