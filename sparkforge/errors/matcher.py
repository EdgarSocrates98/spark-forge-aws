"""O matcher tem DOIS caminhos, e so um deles e fato.

`build_signature_matches` constata que a excecao ja estruturada casa com uma
assinatura de `knowledge/errors/`. Isso e observacao: a classe lancada contem o
texto que a assinatura declara, ou nao contem. O que fazer a respeito --
`likely_causes`, `fixes`, `diagnostic_steps`, `unsafe_fixes` -- e JUIZO, e juizo
mora no catalogo de regras, nao aqui.

`match_log` e `ErrorMatchResult` continuam existindo porque
`sparkforge forge errors match` os usa. Eles casam SUBSTRING de log cru e
carregam o juizo junto -- e e por isso que precisam de `confidence=0.98`, que e
constante literal, nunca medida (regra 28 do `CLAUDE.md`: antes de afirmar,
leia o numero; aqui nao ha numero para ler). O caminho de fact nao carrega
`confidence` nenhum, porque nao finge julgar.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "error_signature@0.1.0"

EMITTED_KINDS = frozenset({"error.signature_match", "error.signature.unresolved"})


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

    def __init__(self, errors_dir: Path | None = None) -> None:
        self.errors_dir = errors_dir or (
            Path(__file__).parent.parent.parent / "knowledge" / "errors"
        )
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
            except Exception:  # noqa: S110 -- assinatura invalida nao derruba o catalogo inteiro
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
                        # CONSTANTE LITERAL, e ela nao mede nada: nenhum
                        # experimento calibrou 0.98, e nao ha o que ler
                        # (regra 28). Ela existe porque este caminho devolve
                        # juizo junto com a constatacao, e juizo pede um numero
                        # de confianca. `build_signature_matches` nao devolve
                        # juizo, e por isso nao carrega confidence nenhum.
                        confidence=0.98,
                        matched_snippet=snippet,
                    )
                )

        return matches


def build_signature_matches(facts: Sequence[Fact]) -> list[Fact]:
    """Casa `spark.exception` contra `knowledge/errors/`, e nada mais.

    Funcao PURA sobre Facts: consome a excecao ja ESTRUTURADA por
    `sparkforge/facts/exception.py`, nunca texto de log cru. `attrs.caused_by`
    entra na busca junto com `attrs.exception_class`, porque a assinatura que
    importa costuma estar na causa raiz e nao no `SparkException` que a
    embrulha -- e `matched_on` diz por qual dos dois ela entrou, para que a
    regra que consumir isso saiba do que esta falando.

    Lista vazia so acontece quando NAO HA `spark.exception` no case. Havendo,
    sai `error.signature_match` ou sai `error.signature.unresolved`: a
    diferenca entre "nenhuma assinatura conhecida cobre esta excecao" e
    "ninguem perguntou" e o que a recusa nomeada guarda.
    """
    assinaturas = DeterministicErrorMatcher().signatures
    saida: list[Fact] = []
    for fact in facts:
        if fact.kind != "spark.exception":
            continue
        subject = dict(fact.subject)
        attrs = fact.attrs or {}
        provenance = _fact_provenance(fact)

        classe = str(attrs.get("exception_class") or "")
        causas = [str(c) for c in (attrs.get("caused_by") or [])]

        casados: list[tuple[str, str, str]] = []
        for sig in assinaturas:
            padrao = str(sig.get("signature") or "")
            if not padrao:
                continue
            alvo = padrao.lower()
            if alvo in classe.lower():
                casados.append((str(sig["id"]), "exception_class", classe))
                continue
            causa = next((c for c in causas if alvo in c.lower()), None)
            if causa is not None:
                casados.append((str(sig["id"]), "caused_by", causa))

        if not casados:
            saida.append(
                Fact(
                    kind="error.signature.unresolved",
                    subject=subject,
                    measures={},
                    attrs={
                        "reason": "nenhuma_assinatura_casou",
                        "exception_class": classe,
                    },
                    provenance=provenance,
                )
            )
            continue

        for sig_id, onde, valor in casados:
            saida.append(
                Fact(
                    kind="error.signature_match",
                    # `signature_id` entra no subject porque duas assinaturas
                    # podem casar a MESMA excecao, e o id do Fact e derivado de
                    # (kind, subject, measures): sem ele, o segundo match
                    # colidiria com o primeiro.
                    subject={**subject, "signature_id": sig_id},
                    measures={},
                    attrs={
                        "signature_id": sig_id,
                        "matched_on": onde,
                        "matched_class": valor,
                    },
                    provenance=provenance,
                )
            )
    return sort_facts(saida)


def _fact_provenance(fact: Fact) -> dict[str, Any]:
    """Herda o artefato do fact de origem, e assina com ESTE extrator."""
    origem = fact.provenance or {}
    return {
        "artifact": origem.get("artifact", "facts"),
        "artifact_sha256": origem.get("artifact_sha256", ""),
        "extractor": EXTRACTOR_ID,
    }


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "DeterministicErrorMatcher",
    "ErrorMatchResult",
    "build_signature_matches",
]
