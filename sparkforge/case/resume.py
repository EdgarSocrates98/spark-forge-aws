"""Payload de rehidratação e `handoff.md` — o resumo que atravessa a sessão.

`resume()` produz um dict pronto para ser consumido por um LLM que acabou de
retomar o case (Devin ou Claude Code, tanto faz). `render_handoff()` transforma
esse mesmo payload em markdown fixo, committado em `.sparkforge/handoff.md`,
para que a leitura humana e a leitura de máquina partam do mesmo dado.

Ambas as funções são puras e determinísticas: mesma entrada, mesma saída,
sempre, para que o handoff seja diffável e revisável como qualquer outro
artefato de código.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.case.router import next_step
from sparkforge.case.store import GATES
from sparkforge.findings.models import SEVERITY_ORDER

HANDOFF_SECTIONS = (
    "Onde parou",
    "Runtime detectado",
    "Baseline",
    "Achados principais",
    "Hipoteses abertas",
    "Gates",
    "Artefatos ausentes",
    "Proximo passo",
    "Em voo na interrupcao",
    "Cobertura",
)

_MAX_TOP_FINDINGS = 10


def _severity_rank(finding: dict[str, Any]) -> int:
    severity = finding.get("severity")
    if severity in SEVERITY_ORDER:
        return SEVERITY_ORDER.index(severity)
    return len(SEVERITY_ORDER)


def _missing_artifacts(case: dict[str, Any], root: Path | None) -> list[dict[str, Any]]:
    """Artefatos do case sem o dado presente no disco.

    Sem `root`, a unica fonte de verdade e a flag `present` gravada no case
    (comportamento original, preservado para quem chama `resume()` sem
    acesso a filesystem -- ver tests/test_case_resume.py). Com `root`, o
    manifesto (`sparkforge.collect`) e a fonte de verdade por artefato: ele
    reflete o disco agora, enquanto a flag no case pode estar desatualizada
    desde a ultima vez que o case foi salvo. Importado aqui, nao no topo do
    modulo, para que `resume()` nao force uma dependencia de `collect` em
    quem so quer o payload a partir do case em memoria.
    """
    artifacts = case.get("artifacts") or []
    if root is None:
        return [a for a in artifacts if not a.get("present", False)]

    from sparkforge.collect import verify_all

    verified_by_path = {v["path"]: v for v in verify_all(root)}

    missing = []
    for artifact in artifacts:
        verification = verified_by_path.get(artifact.get("path"))
        if verification is not None:
            is_present = verification["present"]
        else:
            is_present = artifact.get("present", False)
        if not is_present:
            missing.append(artifact)
    return missing


def resume(
    case: dict[str, Any],
    findings: list[dict[str, Any]],
    unresolved_count: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    """Monta o payload de rehidratação: onde o case parou e o que vem a seguir.

    `root`, quando informado, faz `missing_artifacts` consultar o manifesto
    de `sparkforge.collect` em vez de confiar apenas na flag `present`
    gravada no case -- ver `_missing_artifacts`.
    """
    ordered_findings = sorted(
        findings, key=lambda f: (_severity_rank(f), f.get("rule_id", ""))
    )
    top_findings = ordered_findings[:_MAX_TOP_FINDINGS]

    hypotheses = case.get("hypotheses") or []
    open_hypotheses = [h for h in hypotheses if h.get("status") == "open"]

    gates = dict(case.get("gates") or {})
    unsatisfied_gates = [g for g in GATES if not gates.get(g, False)]

    missing_artifacts = _missing_artifacts(case, root)

    baseline = case.get("baseline")

    finding_ids = sorted({f.get("rule_id") for f in findings if f.get("rule_id")})
    step = next_step(case, finding_ids)

    facts_index = case.get("facts_index") or {}
    findings_index = case.get("findings_index") or {}

    return {
        "case_id": case.get("case_id"),
        "phase": case.get("phase"),
        "created_at": case.get("created_at"),
        "runtime": dict(case.get("runtime") or {}),
        "baseline": "ausente" if baseline is None else baseline,
        "top_findings": top_findings,
        "open_hypotheses": open_hypotheses,
        "gates": gates,
        "unsatisfied_gates": unsatisfied_gates,
        "missing_artifacts": missing_artifacts,
        "next_step": step,
        "in_flight": in_flight,
        "coverage": {
            "facts": facts_index.get("count", 0),
            "findings": findings_index.get("count", 0),
            "unresolved": unresolved_count,
        },
        "skills_used": list(case.get("skills_used") or []),
        "open_questions": list(case.get("open_questions") or []),
    }


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "(nenhum)"
    return f"## {title}\n\n{body}"


def _onde_parou_lines(payload: dict[str, Any]) -> list[str]:
    return [
        f"- case: {payload['case_id']}",
        f"- fase: {payload['phase']}",
        f"- criado em: {payload['created_at']}",
    ]


def _runtime_lines(payload: dict[str, Any]) -> list[str]:
    runtime = payload["runtime"]
    return [f"- {key}: {runtime[key]}" for key in sorted(runtime)]


def _baseline_lines(payload: dict[str, Any]) -> list[str]:
    baseline = payload["baseline"]
    if baseline == "ausente":
        return ["- baseline: ausente"]
    if isinstance(baseline, dict):
        return [f"- {key}: {value}" for key, value in sorted(baseline.items())]
    return [f"- baseline: {baseline}"]


def _findings_lines(payload: dict[str, Any]) -> list[str]:
    lines = []
    for finding in payload["top_findings"]:
        subject = finding.get("subject") or {}
        location = ""
        if subject.get("file") is not None:
            location = f" ({subject['file']}:{subject.get('line')})"
        lines.append(
            f"- `{finding.get('rule_id')}` {finding.get('severity')} — "
            f"{finding.get('title')}{location}"
        )
    return lines


def _hypotheses_lines(payload: dict[str, Any]) -> list[str]:
    lines = []
    for hyp in payload["open_hypotheses"]:
        lines.append(
            f"- `{hyp.get('id')}` {hyp.get('statement')} "
            f"→ previsão: {hyp.get('prediction')} "
            f"→ experimento: {hyp.get('experiment')}"
        )
    return lines


def _gates_lines(payload: dict[str, Any]) -> list[str]:
    gates = payload["gates"]
    return [
        f"- {gate}: {'OK' if gates.get(gate) else 'pendente'}"
        for gate in GATES
        if gate in gates
    ]


def _artifacts_lines(payload: dict[str, Any]) -> list[str]:
    lines = []
    for artifact in payload["missing_artifacts"]:
        lines.append(
            f"- {artifact.get('kind')}: `{artifact.get('path')}` — "
            f"coletar com `{artifact.get('collect_command')}`"
        )
    return lines


def _next_step_lines(payload: dict[str, Any]) -> list[str]:
    step = payload["next_step"]
    lines = [
        f"- skill recomendada: {step.get('recommended_skill')}",
        f"- motivo: {step.get('reason')}",
    ]
    if step.get("blocked_by"):
        lines.append(f"- bloqueado por (advisory): {', '.join(step['blocked_by'])}")
    return lines


def _in_flight_lines(payload: dict[str, Any]) -> list[str]:
    in_flight = payload.get("in_flight")
    return [f"- {in_flight}"] if in_flight else []


def _coverage_lines(payload: dict[str, Any]) -> list[str]:
    coverage = payload["coverage"]
    return [
        f"- facts: {coverage['facts']}",
        f"- findings: {coverage['findings']}",
        f"- não resolvidos: {coverage['unresolved']}",
    ]


def render_handoff(payload: dict[str, Any]) -> str:
    """Renderiza o payload de `resume()` em markdown fixo e determinístico."""
    blocks = [
        _section("Onde parou", _onde_parou_lines(payload)),
        _section("Runtime detectado", _runtime_lines(payload)),
        _section("Baseline", _baseline_lines(payload)),
        _section("Achados principais", _findings_lines(payload)),
        _section("Hipoteses abertas", _hypotheses_lines(payload)),
        _section("Gates", _gates_lines(payload)),
        _section("Artefatos ausentes", _artifacts_lines(payload)),
        _section("Proximo passo", _next_step_lines(payload)),
        _section("Em voo na interrupcao", _in_flight_lines(payload)),
        _section("Cobertura", _coverage_lines(payload)),
    ]
    return "\n\n".join(blocks) + "\n"
