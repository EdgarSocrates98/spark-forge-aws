"""Decision Memory — memória de decisões cross-case.

Três níveis de memória:
1. Working memory — contexto da sessão atual (não persiste)
2. Case memory — decisões dentro de um case (persiste no blackboard)
3. Institutional memory — decisões cross-case, "what worked in similar problems"

Institutional memory é um índice de decisões passadas que pode ser consultado
para evitar repetir erros e reusar soluções provadas. É armazenado em
`.sparkforge/memory/decisions.jsonl` no root do repositório.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sparkforge.agentic.models import Decision
from sparkforge.case.store import CASE_DIR

MEMORY_DIR = "memory"
DECISIONS_FILE = "decisions.jsonl"
# §35 do prompt_evo_runtime: `decisions.jsonl` com `status` canonico e a unica
# autoridade de quarentena. `quarantine.jsonl` continua lido (historico
# legado), mas nenhuma escrita nova cai nela -- duas autoridades divergindo
# era exatamente o que a secao mandava fechar.
QUARANTINE_FILE = "quarantine.jsonl"

_FRESHNESS_RANK = {"fresh": 1.0, "unknown": 0.5, "stale": 0.25, "expired": 0.0}
_FRESHNESS_STATES = frozenset(_FRESHNESS_RANK)
_TRUST_RANK = {"verified": 3, "provisional": 2, "stale": 1, "hypothesis-like": 1}


def freshness_state(record: Mapping[str, Any], *, now: str | None = None) -> str:
    """Estado efetivo de freshness: `expired` prevalece sobre o campo gravado.

    `expires_at` no passado vence qualquer `freshness` declarado -- o campo e
    uma declaracao, o prazo e um fato. Sem `expires_at`, o valor gravado vale;
    ausente ou fora do vocabulario, `unknown` e o honesto.
    """
    expires = record.get("expires_at")
    if expires:
        try:
            if datetime.fromisoformat(str(expires)) < datetime.fromisoformat(now or _now()):
                return "expired"
        except (TypeError, ValueError):
            # Prazo gravado num formato que nao se le: nao se afirma expirado
            # nem fresh -- `unknown` e o honesto.
            return "unknown"
    valor = str(record.get("freshness", "unknown"))
    return valor if valor in _FRESHNESS_STATES - {"expired"} else "unknown"


def _version_tuple(value: Any) -> tuple[int, ...] | None:
    """Tupla numerica de versao -- o mesmo idiom da runtime_matrix."""
    texto = str(value or "").strip()
    if not texto:
        return None
    partes = texto.split(".")
    try:
        return tuple(int(p) for p in partes)
    except ValueError:
        return None


def evaluate_runtime(
    stored: Mapping[str, Any], requested: Mapping[str, Any]
) -> dict[str, str]:
    """Compatibilidade por componente: exact/compatible/incompatible/unresolved.

    §41-42: nao e igualdade literal. "3.5" pedido cobre "3.5.2" gravado
    (prefixo = mesma familia); divergencia de prefixo numerico e
    incompativel; chave pedida que o registro nunca gravou e `unresolved`,
    nao incompativel -- ausencia de evidencia nao vira evidencia de ausencia.
    """
    resultado: dict[str, str] = {}
    for key, want in requested.items():
        got = stored.get(key)
        if got in (None, "", [], {}):
            resultado[key] = "unresolved"
            continue
        if isinstance(got, (list, tuple)) or isinstance(want, (list, tuple)):
            got_set = {str(v) for v in (got if isinstance(got, (list, tuple)) else [got])}
            want_set = {str(v) for v in (want if isinstance(want, (list, tuple)) else [want])}
            resultado[key] = (
                "exact" if want_set <= got_set else "incompatible"
            )
            continue
        if str(got) == str(want):
            resultado[key] = "exact"
            continue
        got_t, want_t = _version_tuple(got), _version_tuple(want)
        if got_t is None or want_t is None:
            resultado[key] = "incompatible"
        elif got_t[: len(want_t)] == want_t or want_t[: len(got_t)] == got_t:
            resultado[key] = "compatible"
        else:
            resultado[key] = "incompatible"
    return resultado


@dataclass(frozen=True, slots=True)
class RuntimeCompatibilityPolicy:
    """Reduce o mapa por componente a um veredito de compatibilidade."""

    def verdict(self, components: Mapping[str, str]) -> str:
        if not components:
            return "unknown"
        estados = set(components.values())
        if "incompatible" in estados:
            return "incompatible"
        if estados == {"exact"}:
            return "exact"
        if "unresolved" in estados:
            return "partial"
        return "compatible"


@dataclass(frozen=True, slots=True)
class MemoryConflict:
    """Duas memorias relevantes que divergem na decisao para o mesmo problema.

    `resolution`: `prefer` quando evidencia/trust/freshness desempatam,
    `review` quando nao ha diferenciador, `unresolved` reservado para quando
    nem o grupo de comparacao e bem-formado.
    """

    record_ids: tuple[str, ...]
    resolution: str
    preferred: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_ids": list(self.record_ids),
            "resolution": self.resolution,
            "preferred": self.preferred,
            "reason": self.reason,
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]{3,}", value.lower())}


def _fingerprint(value: Any) -> str:
    def canonical(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): canonical(nested) for key, nested in item.items()}
        if isinstance(item, (set, frozenset)):
            return sorted((canonical(nested) for nested in item), key=repr)
        if isinstance(item, (list, tuple)):
            return [canonical(nested) for nested in item]
        return item

    raw = json.dumps(canonical(value), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class DecisionMemoryRecord:
    """Structured institutional memory with applicability and lifecycle."""

    id: str
    case_id: str
    problem: str
    problem_fingerprint: str
    environment_fingerprint: str
    workload_type: str = "unknown"
    runtime: dict[str, Any] | None = None
    spark_version: str = ""
    glue_version: str = ""
    emr_version: str = ""
    iceberg_version: str = ""
    aws_services: tuple[str, ...] = ()
    decision: str = ""
    decision_evidence: tuple[str, ...] = ()
    outcome: str = ""
    outcome_evidence: tuple[str, ...] = ()
    confidence: str = "low"
    trust: str = "hypothesis-like"
    freshness: str = "unknown"
    created_at: str = ""
    observed_at: str = ""
    expires_at: str | None = None
    applicability: tuple[str, ...] = ()
    invalidated_by: str | None = None
    superseded_by: str | None = None
    tags: tuple[str, ...] = ()
    status: str = "quarantine"

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "case_id": self.case_id,
            "problem": self.problem,
            "problem_fingerprint": self.problem_fingerprint,
            "environment_fingerprint": self.environment_fingerprint,
            "workload_type": self.workload_type,
            "runtime": dict(self.runtime or {}),
            "spark_version": self.spark_version,
            "glue_version": self.glue_version,
            "emr_version": self.emr_version,
            "iceberg_version": self.iceberg_version,
            "aws_services": list(self.aws_services),
            "decision": self.decision,
            "decision_evidence": list(self.decision_evidence),
            "outcome": self.outcome,
            "outcome_evidence": list(self.outcome_evidence),
            "confidence": self.confidence,
            "trust": self.trust,
            "freshness": self.freshness,
            "created_at": self.created_at,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "applicability": list(self.applicability),
            "invalidated_by": self.invalidated_by,
            "superseded_by": self.superseded_by,
            "tags": list(self.tags),
            "status": self.status,
        }
        return result

    @classmethod
    def from_decision(
        cls, decision: Decision, *, case_id: str = "", outcome: str = ""
    ) -> DecisionMemoryRecord:
        runtime = dict(decision.runtime or {})
        environment = {"runtime": runtime, "services": runtime.get("aws_services", [])}
        created = decision.created_at or _now()
        return cls(
            id=decision.id,
            case_id=case_id,
            problem=decision.problem,
            problem_fingerprint=_fingerprint(_tokens(decision.problem)),
            environment_fingerprint=_fingerprint(environment),
            runtime=runtime,
            spark_version=str(runtime.get("spark", runtime.get("spark_version", ""))),
            glue_version=str(runtime.get("glue", runtime.get("glue_version", ""))),
            emr_version=str(runtime.get("emr", runtime.get("emr_version", ""))),
            iceberg_version=str(runtime.get("iceberg", runtime.get("iceberg_version", ""))),
            aws_services=tuple(str(v) for v in runtime.get("aws_services", [])),
            decision=decision.selected_option,
            decision_evidence=tuple(decision.evidence_refs),
            outcome=outcome,
            confidence=decision.confidence,
            created_at=created,
            observed_at=created if outcome else "",
            applicability=tuple(decision.assumptions),
            tags=("legacy-compatible",),
        )


@dataclass(frozen=True)
class MemoryCandidate:
    record: DecisionMemoryRecord
    evidence_valid: bool
    outcome_valid: bool
    trust: str
    reason: str

    @property
    def persistable(self) -> bool:
        return self.evidence_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "evidence_valid": self.evidence_valid,
            "outcome_valid": self.outcome_valid,
            "trust": self.trust,
            "reason": self.reason,
            "persistable": self.persistable,
        }


def classify_memory_candidate(
    record: DecisionMemoryRecord,
    *,
    valid_evidence_refs: Iterable[str] = (),
) -> MemoryCandidate:
    valid = set(valid_evidence_refs)
    evidence_valid = bool(record.decision_evidence) and (
        not valid or set(record.decision_evidence).issubset(valid)
    )
    outcome_valid = bool(record.outcome and record.outcome_evidence)
    if not evidence_valid:
        trust, reason = "hypothesis-like", "missing_or_unverified_evidence"
    elif outcome_valid:
        trust, reason = "verified", "evidence_and_outcome_validated"
    else:
        trust, reason = "provisional", "evidence_valid_outcome_missing"
    status = "accepted" if evidence_valid else "quarantine"
    normalized = DecisionMemoryRecord(**{**record.to_dict(), "status": status, "trust": trust})
    return MemoryCandidate(normalized, evidence_valid, outcome_valid, trust, reason)


def persist_memory_candidate(
    candidate: MemoryCandidate,
    root: Path | str,
    *,
    allow_quarantine: bool = True,
) -> Path:
    """Persist an accepted candidate or an auditable quarantine record."""
    if not candidate.persistable and not allow_quarantine:
        raise ValueError("memory candidate rejected: evidence validation required")
    return _write_record(root, candidate.record, quarantine=not candidate.persistable)


def memory_path(root: Path | str) -> Path:
    """Retorna o path do diretório de memória institucional."""
    return Path(root) / CASE_DIR / MEMORY_DIR


def decisions_file_path(root: Path | str) -> Path:
    """Retorna o path do arquivo de decisões institucionais."""
    return memory_path(root) / DECISIONS_FILE


def init_memory(root: Path | str) -> Path:
    """Cria a estrutura de diretório de memória se não existir."""
    p = memory_path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_record(
    root: Path | str, record: DecisionMemoryRecord, *, quarantine: bool = False
) -> Path:
    """Append-only no ledger canonico.

    `quarantine` permanece no parametro para compatibilidade de assinatura,
    mas o destino e sempre `decisions.jsonl`: o `status` dentro do registro
    ja e a autoridade (§35), e um segundo arquivo era a segunda autoridade
    que a secao mandava eliminar.
    """
    init_memory(root)
    path = memory_path(root) / DECISIONS_FILE
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=True, sort_keys=True) + "\n")
    return path


def _read_quarantine_legacy(root: Path | str) -> list[dict[str, Any]]:
    """Le `quarantine.jsonl` legado -- leitura apenas, para nao perder
    historico; escrita nova nao volta aqui."""
    path = memory_path(root) / QUARANTINE_FILE
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def record_decision(decision: Decision, root: Path | str, case_id: str = "") -> Path:
    """Registra uma decisão na memória institucional.

    A decisão é armazenada com:
    - decision data
    - case_id (para rastreabilidade)
    - outcome (inicialmente empty — updated later)
    """
    record = DecisionMemoryRecord.from_decision(decision, case_id=case_id)
    # Check for duplicate
    existing = _read_decisions(root)
    for e in existing:
        if e.get("id") == decision.id:
            raise ValueError(f"Decision {decision.id!r} já existe na memória institucional.")
    # Backward-compatible history keeps the record visible, but it is explicitly
    # quarantined until evidence is supplied. New consumers use retrieve_memory.
    candidate = classify_memory_candidate(record)
    return _write_record(root, candidate.record, quarantine=False)


def update_outcome(
    decision_id: str,
    outcome: str,
    root: Path | str,
    evidence: list[str] | None = None,
) -> None:
    """Atualiza o outcome de uma decisão registrada.

    Outcome descreve se a decisão funcionou, falhou, ou foi revertida.
    Isso é o "learning" que alimenta decisões futuras.
    """
    decisions = _read_decisions(root)
    updated = False
    for d in decisions:
        if d.get("id") == decision_id:
            d["outcome"] = outcome
            d["outcome_evidence"] = evidence or []
            d["observed_at"] = _now()
            d["outcome_valid"] = bool(evidence)
            if evidence and d.get("status") == "accepted":
                d["trust"] = "verified"
            updated = True
            break

    if not updated:
        raise ValueError(f"Decision {decision_id!r} não encontrada na memória institucional.")

    # Rewrite file
    path = decisions_file_path(root)
    with path.open("w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=True, sort_keys=True) + "\n")


def _read_decisions(root: Path | str) -> list[dict[str, Any]]:
    """Lê todas as decisões da memória institucional."""
    path = decisions_file_path(root)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def find_similar_decisions(
    problem: str,
    root: Path | str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Encontra decisões passadas com problema similar.

    Heurística simples: matching de keywords no problem.
    Retorna decisões ordenadas por relevância (keyword overlap).
    """
    decisions = _read_decisions(root)
    if not decisions:
        return []

    problem_words = _tokens(problem)
    scored: list[tuple[float, dict[str, Any]]] = []
    for d in decisions:
        d_problem = d.get("problem", "").lower()
        d_words = _tokens(d_problem)
        overlap = len(problem_words & d_words)
        if overlap > 0:
            # Boost decisions with positive outcomes
            outcome = d.get("outcome", "").lower()
            boost = 1.5 if "success" in outcome or "worked" in outcome else 1.0
            scored.append((overlap * boost, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:limit]]


_RUNTIME_WEIGHT = {"exact": 1.0, "compatible": 0.75, "partial": 0.25, "unknown": 0.0}


def retrieve_memory(
    problem: str,
    root: Path | str,
    *,
    limit: int = 5,
    runtime: Mapping[str, Any] | None = None,
    environment_fingerprint: str = "",
    workload_type: str = "",
    include_quarantine: bool = False,
    expired: str = "exclude",
    runtime_policy: RuntimeCompatibilityPolicy | None = None,
) -> list[dict[str, Any]]:
    """Hybrid local retrieval with an explicit trust gate.

    Ordering is exact → freshness → lexical → runtime → environment →
    outcome. `expired` governs expired records: "exclude" (default) drops
    them, "stale" returns them demoted -- `trust` vira "stale" na copia
    devolvida e `retrieval.freshness` diz "expired". Nunca iguais a fresh.
    Runtime passa pela `RuntimeCompatibilityPolicy`: incompativel sai,
    unresolved fica e e reportado. Graph and semantic retrieval remain
    optional hooks: absent indexes are reported by score fields instead of
    silently pretending similarity exists.
    """
    if expired not in {"exclude", "stale"}:
        raise ValueError("expired must be 'exclude' or 'stale'")
    policy = runtime_policy or RuntimeCompatibilityPolicy()
    query_tokens = _tokens(problem)
    runtime = runtime or {}
    ranked: list[tuple[tuple[float, ...], dict[str, Any]]] = []
    for record in _read_decisions(root):
        if record.get("status") not in {"accepted", "verified"} and not include_quarantine:
            continue
        if record.get("invalidated_by") or record.get("superseded_by"):
            continue
        if workload_type and record.get("workload_type") not in {workload_type, "unknown"}:
            continue
        fresh = freshness_state(record)
        if fresh == "expired" and expired == "exclude":
            continue
        stored_runtime = record.get("runtime") or {}
        compat_verdict = (
            policy.verdict(evaluate_runtime(stored_runtime, runtime)) if runtime else "unknown"
        )
        if compat_verdict == "incompatible":
            continue
        stored_tokens = _tokens(str(record.get("problem", "")))
        lexical = len(query_tokens & stored_tokens) / max(len(query_tokens), 1)
        exact = 1.0 if record.get("problem_fingerprint") == _fingerprint(query_tokens) else 0.0
        env = (
            1.0
            if environment_fingerprint
            and record.get("environment_fingerprint") == environment_fingerprint
            else 0.0
        )
        if not exact and lexical == 0 and not env:
            continue
        outcome = 1.0 if record.get("outcome") and record.get("outcome_evidence") else 0.0
        ranked.append(
            (
                (
                    exact,
                    _FRESHNESS_RANK[fresh],
                    lexical,
                    _RUNTIME_WEIGHT[compat_verdict],
                    env,
                    outcome,
                ),
                record,
                fresh,
                compat_verdict,
            )
        )
    ranked.sort(key=lambda item: item[0], reverse=True)
    result: list[dict[str, Any]] = []
    for scores, record, fresh, compat_verdict in ranked[:limit]:
        item = dict(record)
        if fresh == "expired":
            # §40: expirado devolvido nunca carrega a confianca gravada -- a
            # copia desce para "stale" e o estado expirado fica nomeado.
            item["trust"] = "stale"
        item["retrieval"] = {
            "exact": scores[0],
            "freshness": fresh,
            "lexical": scores[2],
            "runtime_compatibility": compat_verdict,
            "environment": scores[4],
            "outcome": scores[5],
            "graph": "unresolved",
            "semantic": "disabled",
        }
        result.append(item)
    return result


def detect_memory_conflicts(root: Path | str) -> list[MemoryConflict]:
    """Agrupa memorias elegiveis por problema e nomeia divergencias (§43-44).

    Conflicto e mesmo `problem_fingerprint` com `decision` divergente.
    Resolucao deterministica por evidencia: trust > outcome com evidencia >
    freshness. Quando nada diferencia, `review` -- nunca preferencia
    silenciosa.
    """
    elegiveis = [
        record
        for record in _read_decisions(root)
        if record.get("status") in {"accepted", "verified"}
        and not record.get("invalidated_by")
        and not record.get("superseded_by")
    ]
    por_problema: dict[str, list[dict[str, Any]]] = {}
    for record in elegiveis:
        por_problema.setdefault(str(record.get("problem_fingerprint", "")), []).append(record)

    def _forca(record: dict[str, Any]) -> tuple[float, ...]:
        return (
            float(_TRUST_RANK.get(str(record.get("trust", "")), 0)),
            1.0 if record.get("outcome") and record.get("outcome_evidence") else 0.0,
            _FRESHNESS_RANK[freshness_state(record)],
        )

    conflicts: list[MemoryConflict] = []
    for grupo in por_problema.values():
        decisoes = {str(record.get("decision", "")) for record in grupo}
        if len(grupo) < 2 or len(decisoes) < 2:
            continue
        ordenado = sorted(grupo, key=_forca, reverse=True)
        melhor, segundo = ordenado[0], ordenado[1]
        ids = tuple(sorted(str(record.get("id", "")) for record in grupo))
        if _forca(melhor) > _forca(segundo):
            conflicts.append(
                MemoryConflict(
                    ids,
                    "prefer",
                    preferred=str(melhor.get("id", "")),
                    reason="trust_outcome_freshness_differentiates",
                )
            )
        else:
            conflicts.append(
                MemoryConflict(
                    ids,
                    "review",
                    reason="no_evidence_differentiator",
                )
            )
    return conflicts


def invalidate_memory(
    root: Path | str,
    *,
    reason: str,
    runtime: Mapping[str, Any] | None = None,
    record_ids: Iterable[str] = (),
) -> int:
    """Invalidate records explicitly; no silent expiry or inferred drift."""
    records = _read_decisions(root)
    requested = set(record_ids)
    changed = 0
    for record in records:
        same_runtime = bool(runtime) and record.get("runtime") != dict(runtime)
        if record.get("id") in requested or same_runtime:
            record["invalidated_by"] = reason
            record["status"] = "invalidated"
            changed += 1
    if changed:
        path = decisions_file_path(root)
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    return changed


def get_decision_history(root: Path | str) -> list[dict[str, Any]]:
    """Retorna todas as decisões registradas, em ordem cronológica."""
    return _read_decisions(root)


@dataclass
class MemoryStats:
    """Estatísticas da memória institucional."""

    total_decisions: int
    decisions_with_outcome: int
    successful_outcomes: int
    failed_outcomes: int
    reverted_outcomes: int
    unique_problems: int
    quarantined_decisions: int = 0
    verified_decisions: int = 0


def memory_stats(root: Path | str) -> MemoryStats:
    """Computa estatísticas da memória institucional.

    O ledger canonico e `decisions.jsonl`; `quarantine.jsonl` legado entra
    somente para leitura de historico, senao registros quarantinados antes
    da consolidacao sumiriam das metricas.
    """
    decisions = _read_decisions(root) + _read_quarantine_legacy(root)
    total = len(decisions)
    with_outcome = sum(1 for d in decisions if d.get("outcome"))
    successful = sum(
        1
        for d in decisions
        if "success" in d.get("outcome", "").lower() or "worked" in d.get("outcome", "").lower()
    )
    failed = sum(1 for d in decisions if "fail" in d.get("outcome", "").lower())
    reverted = sum(1 for d in decisions if "revert" in d.get("outcome", "").lower())
    problems = {d.get("problem", "") for d in decisions}
    quarantined = sum(1 for d in decisions if d.get("status") == "quarantine")
    verified = sum(1 for d in decisions if d.get("trust") == "verified")

    return MemoryStats(
        total_decisions=total,
        decisions_with_outcome=with_outcome,
        successful_outcomes=successful,
        failed_outcomes=failed,
        reverted_outcomes=reverted,
        unique_problems=len(problems),
        quarantined_decisions=quarantined,
        verified_decisions=verified,
    )


__all__ = [
    "DecisionMemoryRecord",
    "MemoryCandidate",
    "MemoryConflict",
    "MemoryStats",
    "RuntimeCompatibilityPolicy",
    "classify_memory_candidate",
    "decisions_file_path",
    "detect_memory_conflicts",
    "evaluate_runtime",
    "find_similar_decisions",
    "freshness_state",
    "get_decision_history",
    "init_memory",
    "invalidate_memory",
    "memory_path",
    "memory_stats",
    "persist_memory_candidate",
    "record_decision",
    "retrieve_memory",
    "update_outcome",
]
