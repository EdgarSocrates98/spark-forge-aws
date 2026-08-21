"""Structured Knowledge Packs and Stale Detection for SparkForge."""
from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class KnowledgePack:
    domain: str
    title: str
    concise_content: str
    patterns_content: str = ""
    anti_patterns_content: str = ""
    last_verified: str = ""
    source_hash: str = ""
    is_stale: bool = False
    stale_reason: Optional[str] = None


class KnowledgePackLoader:
    """Loads modular knowledge packs with stale detection."""

    def __init__(self, root_dir: Optional[Path] = None, max_age_days: int = 90) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.max_age_days = max_age_days

    def load_pack(self, pack_dir: Path) -> KnowledgePack:
        domain = pack_dir.name
        concise_file = pack_dir / "concise.md"
        patterns_file = pack_dir / "patterns.md"
        anti_patterns_file = pack_dir / "anti-patterns.md"
        meta_file = pack_dir / "metadata.json"

        concise_text = concise_file.read_text(encoding="utf-8", errors="ignore") if concise_file.is_file() else ""
        patterns_text = patterns_file.read_text(encoding="utf-8", errors="ignore") if patterns_file.is_file() else ""
        anti_patterns_text = anti_patterns_file.read_text(encoding="utf-8", errors="ignore") if anti_patterns_file.is_file() else ""

        title = domain.replace("-", " ").title()
        last_verified = ""
        if meta_file.is_file():
            try:
                import json
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                title = meta.get("title", title)
                last_verified = meta.get("last_verified", "")
            except Exception:
                pass

        # Check staleness
        is_stale = False
        stale_reason = None
        if last_verified:
            try:
                verified_date = datetime.date.fromisoformat(last_verified)
                age_days = (datetime.date.today() - verified_date).days
                if age_days > self.max_age_days:
                    is_stale = True
                    stale_reason = f"Knowledge pack verified {age_days} days ago (threshold: {self.max_age_days} days)."
            except Exception:
                pass

        content_for_hash = f"{concise_text}{patterns_text}{anti_patterns_text}"
        src_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()[:16]

        return KnowledgePack(
            domain=domain,
            title=title,
            concise_content=concise_text,
            patterns_content=patterns_text,
            anti_patterns_content=anti_patterns_text,
            last_verified=last_verified,
            source_hash=src_hash,
            is_stale=is_stale,
            stale_reason=stale_reason,
        )
