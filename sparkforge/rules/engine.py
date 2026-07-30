"""Motor de regras: Facts + RuntimeContext + catalogo -> Findings.

Nao le artefato bruto. So ve Facts. Regra fora do runtime_scope, ou cujo kind
nao foi extraido, e reportada como skipped com motivo, nunca silenciosamente
descartada: skip silencioso e falso negativo disfarcado.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sparkforge.findings.models import Fact, Finding, sort_facts, sort_findings
from sparkforge.rules.expr import ExprError, evaluate
from sparkforge.rules.version_scope import in_scope


def _dotted(container: dict[str, Any], path: str) -> tuple[bool, Any]:
    """Resolve 'attrs.udf_type' em {'attrs': {'udf_type': ...}}."""
    current: Any = container
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _fact_context(fact: Fact, threshold: dict[str, Any]) -> dict[str, Any]:
    return {"measures": fact.measures, "attrs": fact.attrs, "threshold": threshold}


def _where_matches(fact: Fact, where: dict[str, Any]) -> bool:
    payload = {"measures": fact.measures, "attrs": fact.attrs, "subject": fact.subject}
    for path, expected in (where or {}).items():
        present, actual = _dotted(payload, path)
        if not present or actual != expected:
            return False
    return True


def _expr_matches(fact: Fact, expr: str, threshold: dict[str, Any]) -> bool:
    try:
        return bool(evaluate(expr, _fact_context(fact, threshold)))
    except ExprError:
        # Caminho ausente significa que este fact nao tem a measure exigida.
        return False


def _condition_candidates(
    condition: dict[str, Any], facts: Sequence[Fact], threshold: dict[str, Any]
) -> list[Fact]:
    """Facts que satisfazem uma condicao. Lista vazia = condicao nao satisfeita."""
    kind = condition.get("fact")
    if kind is None:
        return []

    matched = []
    for fact in facts:
        if fact.kind != kind:
            continue
        if "where" in condition and not _where_matches(fact, condition["where"]):
            continue
        if "expr" in condition and not _expr_matches(fact, condition["expr"], threshold):
            continue
        matched.append(fact)
    return matched


def _absent_satisfied(condition: dict[str, Any], facts: Sequence[Fact]) -> bool:
    kind = condition.get("absent")
    return not any(f.kind == kind for f in facts)


def _subject_group_key(fact: Fact) -> str:
    """Chave que identifica a entidade a que o fact se refere.

    Para um recurso Terraform e `<tipo>.<nome>`; para uma tabela do catalogo e o
    nome da tabela; para um stage Spark e o stage. Usada apenas quando a regra
    pede `same_subject`.

    Sem `symbol`, a entidade e a LOCALIZACAO, nunca o arquivo: um subject
    `source_location` identifica um ponto do codigo, e agrupar so por `file`
    juntaria coisas independentes. Dois `spark.sql(...)` no mesmo modulo sao
    duas queries; se uma filtra a coluna de particao e a outra nao, a chave por
    arquivo poe as duas no mesmo grupo, `absent` falha, e a query ruim fica
    mascarada pela boa -- exatamente o falso negativo que `same_subject` existe
    para evitar, so que dentro do arquivo em vez de entre arquivos.

    Isso funciona porque todos os facts de uma unica query compartilham UM
    subject, construido uma vez por query (`facts/sql_literal.py::_scan_sql`,
    `subject = _sql_subject(path, line)`) e propagado intacto pelos facts
    `.enriched` da fusao (`facts/fusion.py`). A linha e portanto a identidade
    estavel da query, nao um detalhe de formatacao.

    Sentinela de arquivo (`sql.analyzed`, `pyspark.module_analyzed`,
    `tf.module_analyzed`, ancoradas em `line: 0`) cai no seu proprio grupo, o
    que e correto: ela prova que o arquivo foi varrido, nao afirma nada sobre
    uma localizacao especifica dentro dele.
    """
    subject = fact.subject or {}
    symbol = subject.get("symbol")
    if symbol:
        return str(symbol)
    file = subject.get("file")
    if not file:
        return ""
    return f"{file}:{subject.get('line', 0)}"


def _evaluate_when(
    when: dict[str, Any], facts: Sequence[Fact], threshold: dict[str, Any]
) -> list[list[Fact]]:
    """Grupos de evidencia de `when`: um por Finding a emitir. Lista vazia = nao casa.

    Com `same_subject: true` no grupo, todas as condicoes precisam ser satisfeitas
    pelo MESMO subject. Sem isso, um arquivo Terraform com dois `aws_glue_job`
    faria uma regra casar juntando um atributo de um recurso com outro atributo
    de um recurso diferente — cada job correto isoladamente, e a regra acusando.
    Acusar configuracao correta destroi a confianca em todo o resto do relatorio,
    entao regras que correlacionam atributos de uma mesma entidade declaram isso.

    E a regra `same_subject` afirma algo sobre UMA entidade, entao ela produz um
    Finding POR entidade que casa, nunca so o primeiro. Parar no primeiro grupo
    faria o relatorio dizer "um job esta errado" quando tres estao: o operador
    corrige aquele, roda de novo, e descobre o proximo -- sem nunca saber quantos
    faltam. Subcontar e enganoso da mesma forma que um falso negativo.

    Regra sem `same_subject` continua produzindo no maximo um grupo: ela fala do
    CONJUNTO de facts, nao de uma entidade, e nao ha por que particionar.
    """
    if when.get("same_subject"):
        narrowed = {k: v for k, v in when.items() if k != "same_subject"}
        groups: list[list[Fact]] = []
        for subject_key in sorted({_subject_group_key(f) for f in facts}):
            scoped = [f for f in facts if _subject_group_key(f) == subject_key]
            groups.extend(_evaluate_when(narrowed, scoped, threshold))
        return groups

    for group, require_all in (("all", True), ("any", False)):
        conditions = when.get(group)
        if not conditions:
            continue

        evidence: list[Fact] = []
        satisfied_count = 0

        for condition in conditions:
            if "absent" in condition:
                if _absent_satisfied(condition, facts):
                    satisfied_count += 1
                elif require_all:
                    return []
                continue

            matched = _condition_candidates(condition, facts, threshold)
            if matched:
                satisfied_count += 1
                evidence.extend(matched)
            elif require_all:
                return []

        # Evidencia vazia (grupo so de condicoes `absent`) nao vira Finding:
        # Finding sem Fact e invalido por contrato (`Finding.__post_init__`).
        if not evidence:
            return []
        if require_all or satisfied_count:
            return [evidence]
        return []

    return []


def _severity_for(rule: dict[str, Any], fact: Fact) -> str:
    branches = rule.get("severity_by")
    if not branches:
        return rule["severity_default"]

    context = _fact_context(fact, rule.get("threshold") or {})
    for branch in branches:
        try:
            if evaluate(branch["when"], context):
                return branch["severity"]
        except ExprError:
            continue
    return rule.get("severity_default", "P3")


def _build_finding(rule: dict[str, Any], evidence: Sequence[Fact]) -> Finding:
    primary = evidence[0]
    return Finding(
        rule_id=rule["id"],
        catalog_version=rule.get("catalog_version", 1),
        title=rule["title"],
        severity=_severity_for(rule, primary),
        confidence=rule.get("confidence", "high"),
        status=rule["status"],
        subject=primary.subject,
        evidence=[f.id for f in evidence],
        measured=dict(primary.measures),
        threshold=dict(rule.get("threshold") or {}),
        runtime_scope=dict(rule.get("runtime_scope") or {}),
        explanation=(rule.get("explanation") or "").strip(),
        proposed_change=list(rule.get("proposed_change") or []),
        expected_effect=(rule.get("expected_effect") or "").strip(),
        benchmark_ref=rule.get("benchmark_ref", ""),
        risks=list(rule.get("risks") or []),
        tradeoffs=list(rule.get("tradeoffs") or []),
        validation=list(rule.get("validation") or []),
        rollback=list(rule.get("rollback") or []),
        sources=list(rule.get("sources") or []),
    )


def judge(
    facts: Iterable[Fact],
    rules: Iterable[dict[str, Any]],
    runtime: dict[str, str],
    return_skipped: bool = False,
) -> list[Finding] | tuple[list[Finding], list[dict[str, Any]]]:
    """Aplica `rules` sobre `facts`. Ordem de saida deterministica.

    Com return_skipped=True devolve (findings, skipped), onde skipped explica por
    que cada regra nao foi avaliada.
    """
    # sort_facts aqui, nao list(facts): _build_finding usa evidence[0] como fact
    # primario (subject, measured). Sem ordenar, "primario" dependeria da ordem
    # de entrada do chamador, nao do conteudo -- quebrando determinismo se um
    # chamador futuro (ex.: fusao de facts de multiplos extratores) nao entregar
    # a lista ja ordenada.
    fact_list = sort_facts(facts)
    present_kinds = {f.kind for f in fact_list}
    findings: list[Finding] = []
    skipped: list[dict[str, Any]] = []

    for rule in rules:
        scope = rule.get("runtime_scope") or {}
        if not in_scope(scope, runtime):
            skipped.append({"rule_id": rule["id"], "reason": "runtime_scope", "scope": scope})
            continue

        # Regra bloqueada por capacidade que ainda nao existe e diferente de regra
        # que so nao teve dados nesta execucao. A primeira nunca vai disparar ate
        # alguem construir o extrator; a segunda dispara assim que o artefato for
        # coletado. Reportar as duas como "requires_facts" faria o operador esperar
        # por um dado que nao esta a caminho.
        blocked_on = rule.get("blocked_on")
        if blocked_on:
            skipped.append(
                {"rule_id": rule["id"], "reason": "blocked_on", "blocked_on": blocked_on}
            )
            continue

        required = set(rule.get("requires_facts") or [])
        if required and not required.issubset(present_kinds):
            skipped.append(
                {
                    "rule_id": rule["id"],
                    "reason": "requires_facts",
                    "missing": sorted(required - present_kinds),
                }
            )
            continue

        threshold = rule.get("threshold") or {}
        # Um grupo de evidencia por Finding: regra `same_subject` devolve um
        # grupo por entidade que casa, cada um ancorado no proprio recurso e
        # carregando so os facts daquele recurso. `sort_findings` no fim
        # reordena tudo, entao a ordem de saida nao depende da ordem em que os
        # subjects foram visitados.
        for evidence in _evaluate_when(rule.get("when") or {}, fact_list, threshold):
            findings.append(_build_finding(rule, evidence))

    ordered = sort_findings(findings)
    return (ordered, skipped) if return_skipped else ordered
