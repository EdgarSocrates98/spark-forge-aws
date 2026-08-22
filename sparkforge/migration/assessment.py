"""Aplica o catalogo `SF-MIG` uma vez por degrau do caminho e agrega o resultado.

NAO bifurca o motor: cada degrau chama o `judge` (`sparkforge/rules/engine.py`) que
ja existe, com o runtime do ALVO daquele degrau. O que este modulo acrescenta e
so agregacao -- em qual salto cada finding nasceu -- e a declaracao honesta do
que esta analise nao pode julgar sem job real e AWS viva.

DECISAO 1 -- duplicata entre degraus e o sinal pretendido, nao defeito.

Um finding cujo `runtime_scope` cobre mais de um degrau do caminho (ex.:
`{glue: ">=5.0"}` num caminho 4.0->5.0->5.1) nasce em CADA degrau que o inclui,
nao so no primeiro. Deduplicar mantendo o mais antigo apagaria a informacao de
que o breaking change continua valendo depois do proximo salto -- que e
exatamente o que `sparkforge/migration/version_path.py` existe para nao
esconder (ver o docstring daquele modulo: "os breaking changes se acumulam
degrau a degrau e um salto esconde os do meio"). `by_step` registra cada
nascimento com o degrau; `findings` e a lista completa, na mesma cardinalidade.
`docs/superpowers/plans/2026-08-21-glue-migration-compat.md` (Task 8, Step 4)
registra esta mesma escolha como o comportamento pretendido.

DECISAO 1b -- o RELATORIO deduplica; o dado por degrau nao.

As duas visoes respondem perguntas diferentes e por isso convivem. `findings` e
`by_step` respondem "isto ainda vale depois do proximo salto?", e precisam da
cardinalidade por degrau. `report()` responde a pergunta de quem LE: "quantos
problemas eu tenho?" -- e ali o mesmo problema tres vezes, porque o caminho tem
tres degraus, faz um assessment de 4.0 para 6.0 parecer tres vezes pior que o
mesmo job de 5.1 para 6.0 sem que nada de fato seja pior. `report()` colapsa por
`(rule_id, subject, evidence)`, guarda a instancia mais severa e lista TODOS os
degraus em que o problema vale -- deduplicar sem dizer onde vale trocaria ruido
por perda de informacao.

DECISAO 2 -- o gate de compatibilidade usa severidade, nao so presenca.

Presenca de finding sozinha nao diferencia um P2 (config EMRFS morta, silenciosa,
corrigivel sem pressa) de um P0/P1 (import que estoura em runtime, cast que muda
resultado). Colapsar os dois em `FAIL` trataria risco baixo como bloqueio total,
e colapsar em `PASS_WITH_RISK` esconderia um P0/P1 atras de uma bandeira de
"risco" generica. A regra aplicada: `FAIL` se existir finding com severidade P0
ou P1 (breaking change ou risco alto sem mitigacao textual); `PASS_WITH_RISK` se
so houver P2 a P4; `PASS` sem nenhum finding.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sparkforge.facts import runtime_matrix
from sparkforge.findings.models import SEVERITY_ORDER, Fact, Finding, sort_findings
from sparkforge.migration import version_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

# Severidades que fecham o gate de compatibilidade: breaking change confirmado
# ou risco que a regra classificou como alto. Ver SEVERITY_ORDER em
# `sparkforge/findings/models.py` -- P0 e P1 sao as duas primeiras.
_SEVERITIES_QUE_FALHAM_O_GATE = frozenset({"P0", "P1"})

# Gates que exigem execucao real do job no runtime alvo, contra AWS viva. Nem
# job real nem AWS existem nesta analise -- so codigo-fonte e a matriz de
# versoes -- entao os quatro nascem BLOCKED, nomeando a evidencia que falta.
# Gate sem evidencia e BLOCKED, nunca PASS: e o invariante que esta fase existe
# para nao violar (ver cabecalho de `docs/superpowers/specs/
# 2026-08-21-glue-migration-compat-design.md`, secao 6).
_EXECUTION_GATES: dict[str, str] = {
    "dados": (
        "reconciliacao de dados exige rodar o job no runtime alvo e comparar a "
        "saida com o job de origem sobre a mesma entrada -- nenhuma execucao "
        "coletada nesta analise"
    ),
    "performance": (
        "comparacao de performance exige metricas reais (Spark UI ou event log) "
        "do job rodando nos dois runtimes -- nenhuma execucao coletada"
    ),
    "custo": (
        "comparacao de custo exige DPU-hours medidos nos dois runtimes -- "
        "nenhuma execucao nem fatura da AWS coletada"
    ),
    "canary": (
        "canary exige execucao paralela controlada em producao, com trafego "
        "real, contra os dois runtimes -- nenhum canary executado"
    ),
}


@dataclass
class ReportedFinding:
    """Um problema, uma vez, com todos os degraus em que ele vale.

    `finding` e a instancia MAIS SEVERA entre as duplicatas, nao a primeira:
    uma regra com `severity_by` condicionado ao runtime pode nascer P2 num
    degrau e P1 no seguinte, e reportar a primeira subestimaria o risco pelo
    unico motivo de a ordem do caminho ser essa. `steps` preserva a informacao
    que a deduplicacao poderia apagar -- que o breaking change continua valendo
    depois do proximo salto.
    """

    finding: Finding
    steps: list[tuple[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"finding": self.finding.to_dict(), "steps": [list(s) for s in self.steps]}


def _chave_de_problema(finding: Finding) -> tuple[str, str, tuple[str, ...]]:
    """Identidade de um problema, para deduplicar entre degraus.

    NAO e `rule_id` sozinho: dois `SF-MIG-001` em imports diferentes sao dois
    problemas distintos, e colapsa-los esconderia um deles -- o oposto exato do
    que a deduplicacao existe para fazer. `subject` localiza a entidade e
    `evidence` nomeia os facts que sustentam o juizo; duas instancias do mesmo
    problema nascidas em degraus diferentes coincidem nos tres, porque o motor
    julga os MESMOS facts uma vez por degrau.
    """
    subject = json.dumps(finding.subject, sort_keys=True, separators=(",", ":"))
    return (finding.rule_id, subject, tuple(finding.evidence))


@dataclass
class MigrationAssessment:
    """Resultado de julgar `SF-MIG` sobre todo o caminho origem->alvo.

    `findings` e `by_step` tem a MESMA cardinalidade: todo finding em `findings`
    aparece uma vez em `by_step` emparelhado com o degrau que o produziu, e um
    finding que nasce em mais de um degrau aparece mais de uma vez nos dois --
    ver DECISAO 1 no docstring do modulo.
    """

    source: str
    target: str
    steps: list[tuple[str, str]]
    findings: list[Finding] = field(default_factory=list)
    by_step: list[tuple[Finding, tuple[str, str]]] = field(default_factory=list)
    gates: dict[str, str] = field(default_factory=dict)
    missing_evidence: dict[str, str] = field(default_factory=dict)
    recommendation: str = "NO_GO"

    def report(self) -> list[ReportedFinding]:
        """A visao para o RELATORIO: cada problema uma vez so.

        `findings` e `by_step` continuam com a cardinalidade por degrau, que e a
        DECISAO 1 do modulo e nao muda -- quem pergunta "isto ainda vale depois
        do proximo salto?" precisa dela. Esta e a outra pergunta, a de quem le o
        relatorio: "quantos problemas eu tenho?". Mostrar o mesmo problema tres
        vezes porque o caminho tem tres degraus e ruido que faz um assessment de
        `4.0` para `6.0` parecer tres vezes pior que o mesmo job em `5.1` para
        `6.0`, sem que nada de fato seja pior.

        Ordem: a de `findings`, que ja passou por `sort_findings` -- determinista,
        por severidade. O primeiro aparecimento de cada problema fixa a posicao.
        """
        agrupado: dict[tuple[str, str, tuple[str, ...]], ReportedFinding] = {}
        for finding, degrau in self.by_step:
            chave = _chave_de_problema(finding)
            atual = agrupado.get(chave)
            if atual is None:
                agrupado[chave] = ReportedFinding(finding=finding, steps=[degrau])
                continue
            if degrau not in atual.steps:
                atual.steps.append(degrau)
            if SEVERITY_ORDER.index(finding.severity) < SEVERITY_ORDER.index(
                atual.finding.severity
            ):
                atual.finding = finding

        posicao: dict[tuple[str, str, tuple[str, ...]], int] = {}
        for indice, finding in enumerate(self.findings):
            posicao.setdefault(_chave_de_problema(finding), indice)
        return sorted(
            agrupado.values(), key=lambda r: posicao[_chave_de_problema(r.finding)]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_runtime": self.source,
            "target_runtime": self.target,
            "steps": [list(step) for step in self.steps],
            "findings": [f.to_dict() for f in self.findings],
            "by_step": [
                {"finding": f.to_dict(), "step": list(step)} for f, step in self.by_step
            ],
            # A visao deduplicada entra AO LADO das outras duas, nunca no lugar
            # delas: um consumidor que ja lia `findings` continua lendo o mesmo,
            # e quem monta relatorio para humano tem de onde tirar a contagem
            # honesta sem reimplementar a deduplicacao.
            "report": [r.to_dict() for r in self.report()],
            "gates": dict(self.gates),
            "missing_evidence": dict(self.missing_evidence),
            "recommendation": self.recommendation,
        }


def _runtime_for(target_version: str) -> dict[str, str]:
    """Runtime do ALVO de um degrau, no formato que `judge`/`in_scope` esperam.

    O julgamento de um degrau `(a, b)` usa o runtime de `b`, nao de `a`: uma
    regra como SF-MIG-001 (`runtime_scope: {glue: ">=5.0"}`) descreve o que
    quebra depois que o job passa a rodar no alvo, nao no que ele roda hoje.
    """
    linha = runtime_matrix.load()[target_version]
    runtime = {"glue": target_version}
    for chave in ("spark", "python", "iceberg"):
        if linha.get(chave):
            runtime[chave] = linha[chave]
    return runtime


def _compatibility_gate(findings: list[Finding]) -> str:
    if not findings:
        return "PASS"
    if any(f.severity in _SEVERITIES_QUE_FALHAM_O_GATE for f in findings):
        return "FAIL"
    return "PASS_WITH_RISK"


def assess(facts: list[Fact], source: str, target: str) -> MigrationAssessment:
    """Julga `facts` contra o catalogo `SF-MIG`, uma vez por degrau de `source`
    ate `target`.

    Propaga os `ValueError` de `version_path.steps` (versao fora da matriz,
    alvo anterior a origem) em vez de engoli-los: um assessment vazio devolvido
    para um par invalido pareceria "sem breaking change encontrado", quando o
    par nem chegou a ser avaliado. Melhor estourar aqui do que produzir um
    NO_GO ou GO que ninguem pediu.
    """
    degraus = version_path.steps(source, target)
    catalogo = load_catalog()

    findings: list[Finding] = []
    by_step: list[tuple[Finding, tuple[str, str]]] = []
    for degrau in degraus:
        _, alvo = degrau
        runtime = _runtime_for(alvo)
        for finding in judge(facts, catalogo, runtime):
            findings.append(finding)
            by_step.append((finding, degrau))

    findings = sort_findings(findings)

    gates: dict[str, str] = {nome: "BLOCKED" for nome in _EXECUTION_GATES}
    gates["compatibilidade"] = _compatibility_gate(findings)
    missing_evidence = dict(_EXECUTION_GATES)

    if gates["compatibilidade"] == "FAIL":
        recommendation = "NO_GO"
    else:
        # Os quatro gates de execucao real nascem sempre BLOCKED nesta analise
        # (nenhum job nem AWS viva): GO exigiria todo gate em PASS, entao o
        # melhor desfecho possivel aqui e CONDITIONAL_GO -- nunca GO.
        recommendation = "CONDITIONAL_GO"

    return MigrationAssessment(
        source=source,
        target=target,
        steps=degraus,
        findings=findings,
        by_step=by_step,
        gates=gates,
        missing_evidence=missing_evidence,
        recommendation=recommendation,
    )
