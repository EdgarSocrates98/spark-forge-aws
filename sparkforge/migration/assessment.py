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

DECISAO 1c -- as quatro plataformas atravessam o MESMO motor.

`assess(facts, source, target, platform=...)` nao bifurca nada: o degrau vem de
`version_path.steps(..., platform)` e o runtime do ALVO daquele degrau vem da
matriz DAQUELA plataforma. Nao ha ramo de EMR, e nao pode haver: a matriz de
EMR on EC2 nao descreve EKS nem Serverless -- o sub-projeto 1 mediu que elas
DIVERGEM, Iceberg em 6 de 26 releases comparaveis -- e
`sparkforge/adapters/_core.py::_recusar_emr_sobre_eks` ja fecha uma porta para
essa heranca. Aqui a porta fica fechada por construcao: `_runtime_for` chama
`release_descriptor.describe(platform, alvo)`, que le uma matriz so.

DECISAO 3 -- a cobertura e DECLARADA, e ela e a entrega, nao um enfeite.

Contado no catalogo de 140 regras em 2026-08-31, `runtime_scope` por eixo e
`{glue: 13, spark: 5, iceberg: 1}`. ZERO regras por `emr`. Um `assess` de EMR
que apenas trocasse a plataforma rodaria o catalogo inteiro por degrau, nao
acharia nada, e sairia VERDE -- que o operador leria como "nada quebra". Esse e
o defeito que esta entrega existe para nao cometer.

A ponte que salva o verbo e o Spark: cinco regras sao guardadas por versao de
SPARK, nao de plataforma, e as quatro matrizes publicam a versao de Spark de
cada release. Derivando o runtime de cada degrau da matriz da plataforma, as
cinco passam a ser alcancaveis para EMR pela primeira vez.

Por isso `MigrationAssessment.coverage` sai SEMPRE, com quantas regras cada
eixo de `runtime_scope` tem no catalogo, quantas o caminho alcancou, e a
declaracao em prosa que o operador le. Sem esse campo, assessment sem achado e
indistinguivel de job sem problema. E a §20 do `CLAUDE.md` aplicada ao verbo
inteiro em vez de a uma propriedade -- listar a recusa e a diferenca entre "nao
sei" e "nao perguntei".

O que este modulo NAO faz, e a razao esta registrada: nao escreve regra `SF-MIG`
para EMR (regra exige fonte primaria, golden positivo e negativo e area com
rota; como efeito colateral produziria regra sem corpus) e nao inventa
`runtime_scope: {emr: ...}` (o eixo nao existe em `version_scope`, e
acrescenta-lo sem regra que o use seria mecanismo sem consumidor). O eixo `emr`
aparece na COBERTURA justamente para dizer que ele vale zero.

DECISAO 4 -- o "o que muda de componente" por degrau vem do `ReleaseDiff`.

`component_diff` e uma projecao de `sparkforge/migration/release_diff.py`, uma
entrada por degrau, e nao uma comparacao reimplementada aqui. A projecao separa
duas coisas que tem escalas diferentes: as recusas `component.*` sao do PAR de
releases e ficam no degrau; as cinco dimensoes do §8.2 que a matriz nao sustenta
(`deprecated`, `default_changes`, `compatibility_changes`, `security_changes`,
`performance_changes`) sao constantes do verbo e saem UMA vez, em
`component_diff_unresolved`. Repetir os cinco textos por degrau nao
acrescentaria informacao, e omiti-los faria o operador ler lista vazia como
"nao mudou nada".

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
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sparkforge.facts import runtime_matrix
from sparkforge.findings.models import (
    SEVERITY_ORDER,
    Fact,
    Finding,
    area_of,
    sort_findings,
)
from sparkforge.migration import release_descriptor, release_diff, version_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope
from sparkforge.storage import upgrade as storage_upgrade

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


# Eixos do contrato que TEM produtor no repositorio: area do catalogo que os
# move, e o kind de fact sem o qual o eixo nao foi avaliado. Gate sem produtor e
# gate que ninguem preenche, e um gate que nunca muda de valor e decoracao.
_EIXOS_COM_PRODUTOR: dict[str, tuple[str, str]] = {
    # A topologia de FGAC e declarada em `default_arguments` do job no
    # Terraform, nunca no codigo Python: sem `.tf` composto, o eixo nao foi
    # avaliado.
    "lakeformation": ("SF-LF", "tf.attribute"),
    # `env.consumer`, nao `env.consumers_analyzed`: inventario lido e vazio nao
    # e "sem consumidor". Ausencia de declaracao nao e declaracao de ausencia --
    # ver o docstring de `sparkforge/facts/consumers.py`.
    "consumidor": ("SF-ENV", "env.consumer"),
    # Os tres que a fase H2 registrou como nomeados-sem-produtor. Ganharam area
    # propria de catalogo, e por isso deixaram de ser gate que nunca muda de
    # valor. O fact exigido e `tf.attribute` nos dois primeiros porque as
    # condicoes sao atributos do `aws_glue_job`; em `cross_account` e
    # `tf.spark_conf`, porque o sinal e uma propriedade Spark decomposta de um
    # `--conf`.
    "iam_kms": ("SF-KMS", "tf.attribute"),
    "rede": ("SF-NET", "tf.attribute"),
    "cross_account": ("SF-XACC", "tf.spark_conf"),
}

# Evidencia que destrava cada eixo com produtor, quando o fact dele nao veio.
_EVIDENCIA_DOS_EIXOS: dict[str, str] = {
    "lakeformation": (
        "nenhum `tf.attribute` nos facts -- a topologia de controle de acesso "
        "fino e declarada nos `default_arguments` do job no Terraform, entao "
        "aponte a analise para o diretorio que contem os `.tf` do job"
    ),
    "consumidor": (
        "nenhum `env.consumer` nos facts -- quem consome a tabela nao esta no "
        "codigo do job, no plano fisico nem no metadata Iceberg; declare o "
        "inventario em `.sparkforge/consumers.yaml` (ver "
        "`sparkforge/facts/consumers.py`)"
    ),
    "iam_kms": (
        "nenhum `tf.attribute` nos facts -- security configuration, papel de "
        "execucao e a rota ate o KMS sao declarados no Terraform do job, entao "
        "aponte a analise para o diretorio que contem os `.tf`"
    ),
    "rede": (
        "nenhum `tf.attribute` nos facts -- a conexao que coloca o job dentro "
        "da VPC e declarada no Terraform do job, entao aponte a analise para o "
        "diretorio que contem os `.tf`"
    ),
    "cross_account": (
        "nenhum `tf.spark_conf` nos facts -- leitura de catalogo de outra conta "
        "aparece como propriedade Spark no `default_arguments` do job, e sem "
        "os `.tf` do job nao ha o que ler"
    ),
}

# Eixos que a secao 32 nomeia e que NAO tem produtor nenhum no repositorio.
#
# VAZIO desde que `SF-KMS`, `SF-NET` e `SF-XACC` existem: os tres que moravam
# aqui -- `iam_kms`, `rede`, `cross_account` -- migraram para
# `_EIXOS_COM_PRODUTOR`, que era exatamente o caminho que este comentario
# previa. O dicionario fica, e vazio, porque o mecanismo continua valendo: a
# secao 32 pode nomear um eixo novo antes de existir regra para ele, e o lugar
# certo de declarar isso e aqui, nao um `PASS` silencioso.
_EIXOS_SEM_PRODUTOR: dict[str, str] = {}


# O eixo de `runtime_scope` que NOMEIA a plataforma daquele caminho. As tres de
# EMR compartilham `emr` porque o catalogo, se um dia guardar regra por versao
# de plataforma EMR, guardara por rotulo de release -- e o rotulo e o mesmo
# vocabulario nas tres. Hoje o eixo vale ZERO nas tres, e e exatamente isso que
# a declaracao de cobertura existe para dizer em voz alta.
_EIXO_DA_PLATAFORMA: dict[str, str] = {
    "glue": "glue",
    "emr_ec2": "emr",
    "emr_serverless": "emr",
    "emr_eks": "emr",
}


@dataclass(frozen=True)
class AxisCoverage:
    """Um eixo de `runtime_scope`, com o que o catalogo tem e o que o caminho
    alcancou.

    `catalog_rules` conta as regras do catalogo guardadas por este eixo, e nao
    depende do caminho; `reachable_rules` conta quantas dessas passaram
    `in_scope` em ao menos UM degrau. As duas juntas separam "o catalogo nao
    tem regra para isto" de "tem, e este caminho nao a cruza" -- que sao
    silencios diferentes e destravam com trabalho diferente.

    `runtime_key_present` diz se algum degrau chegou a preencher a chave. Um
    eixo com regra no catalogo e sem chave no runtime nao foi avaliado: toda
    regra dele foi pulada por `runtime_scope`, e ninguem leu isso como ausencia
    de problema por acidente.
    """

    axis: str
    catalog_rules: int
    reachable_rules: int
    runtime_key_present: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "catalog_rules": self.catalog_rules,
            "reachable_rules": self.reachable_rules,
            "runtime_key_present": self.runtime_key_present,
        }


@dataclass(frozen=True)
class CoverageDeclaration:
    """Quanto do catalogo este caminho podia alcancar, e a frase que diz isso.

    Ver DECISAO 3 no docstring do modulo. `statement` e o campo que o operador
    LE; os numeros ao lado sao o que o sustenta, para que a frase possa ser
    conferida em vez de acreditada.
    """

    platform: str
    platform_axis: str
    source: str
    target: str
    steps: int
    catalog_rules: int
    version_guarded_rules: int
    unguarded_rules: int
    reachable_rules: int
    axes: tuple[AxisCoverage, ...]
    activated_axes: tuple[str, ...]

    @property
    def statement(self) -> str:
        """A frase que o operador LE, derivada dos numeros ao lado.

        Propriedade e nao campo para que ela NAO POSSA divergir deles: uma
        declaracao guardada como texto solto sobrevive a mudanca do numero que
        a sustentava, e a frase errada aqui e pior que frase nenhuma -- ela
        afirma cobertura. Escrita neste modulo, e nao em quem consome, porque a
        leitura errada que ela previne ("saiu verde, entao nada quebra") e
        exatamente a que acontece quando cada superficie escreve a sua.
        """
        return _declaracao_de_cobertura(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "platform_axis": self.platform_axis,
            "source_runtime": self.source,
            "target_runtime": self.target,
            "steps": self.steps,
            "catalog_rules": self.catalog_rules,
            "version_guarded_rules": self.version_guarded_rules,
            "unguarded_rules": self.unguarded_rules,
            "reachable_rules": self.reachable_rules,
            "axes": [eixo.to_dict() for eixo in self.axes],
            "activated_axes": list(self.activated_axes),
            "statement": self.statement,
        }


@dataclass(frozen=True)
class StepComponentDiff:
    """O que muda de COMPONENTE num degrau, projetado do `ReleaseDiff`.

    Ver DECISAO 4. `unresolved` carrega so as recusas que sao DAQUELE par de
    releases (as chaves `component.*`); as cinco dimensoes do §8.2 sem lastro
    saem uma vez so, ao lado, porque sao constantes do verbo.
    """

    step: tuple[str, str]
    changed: tuple[dict[str, Any], ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]
    unresolved: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": list(self.step),
            "changed": [dict(entrada) for entrada in self.changed],
            "added": list(self.added),
            "removed": list(self.removed),
            "unchanged": list(self.unchanged),
            "unresolved": dict(sorted(self.unresolved.items())),
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
    # Plataforma com DEFAULT, e o par de versoes sem: `migrate glue` foi a
    # interface publicada antes das quatro plataformas existirem, e obrigar
    # `platform=` em quem ja chamava trocaria uma extensao por uma quebra.
    platform: str = version_path.DEFAULT_PLATFORM
    # `None` so no objeto montado a mao (os testes que fixam a deduplicacao o
    # fazem). Todo `MigrationAssessment` que sai de `assess()` carrega a
    # declaracao -- e o invariante que a DECISAO 3 existe para sustentar, e ha
    # teste que reprova se o campo sumir da saida.
    coverage: CoverageDeclaration | None = None
    component_diff: list[StepComponentDiff] = field(default_factory=list)
    component_diff_unresolved: dict[str, str] = field(default_factory=dict)

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
            "platform": self.platform,
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
            # A cobertura entra ao lado dos gates, e nao dentro deles, porque
            # ela nao e um veredito: um gate diz se algo passou, e este campo
            # diz o que sequer podia ser perguntado. Confundir os dois faria
            # "0 regras por `emr`" parecer um gate verde.
            "coverage": self.coverage.to_dict() if self.coverage else None,
            "component_diff": [entrada.to_dict() for entrada in self.component_diff],
            "component_diff_unresolved": dict(
                sorted(self.component_diff_unresolved.items())
            ),
        }


def _runtime_for(
    target_version: str, platform: str = version_path.DEFAULT_PLATFORM
) -> dict[str, str]:
    """Runtime do ALVO de um degrau, no formato que `judge`/`in_scope` esperam.

    O julgamento de um degrau `(a, b)` usa o runtime de `b`, nao de `a`: uma
    regra como SF-MIG-001 (`runtime_scope: {glue: ">=5.0"}`) descreve o que
    quebra depois que o job passa a rodar no alvo, nao no que ele roda hoje.

    O CAMINHO DE GLUE FICOU COMO ESTAVA, e de proposito: mesma matriz, mesmas
    quatro chaves, mesmo valor. Zero regressao no assessment de Glue e criterio
    de conclusao deste sub-projeto, e a forma barata de garanti-lo e nao mexer
    no ramo que ja passava.

    O CAMINHO DE EMR LE A MATRIZ DAQUELA PLATAFORMA, E SO DELA (D-2 da spec).
    `describe(platform, ...)` e a unica fonte, e ele nao tem fallback: a matriz
    de EC2 nao descreve EKS nem Serverless, e o sub-projeto 1 mediu a
    divergencia em celulas reais (Iceberg em 6 de 26 releases comparaveis).
    Herdar valor de uma plataforma para outra aqui reabriria por dentro a porta
    que `_recusar_emr_sobre_eks` fecha por fora.

    NAO HA CHAVE `emr` NO RUNTIME, e a ausencia e a decisao. O eixo nao existe
    em `runtime_scope` de regra nenhuma; acrescenta-lo aqui seria mecanismo sem
    consumidor, e daria a impressao de cobertura que a declaracao de cobertura
    existe justamente para desmentir. Componente publicado como CONJUNTO
    (`python_installed`, os interpretadores instalados no EMR on EC2) tambem
    fica de fora: `in_scope` compara VERSAO, e achatar um conjunto num valor
    escolheria por conta propria qual deles o PySpark usa.
    """
    if platform == version_path.DEFAULT_PLATFORM:
        linha = runtime_matrix.load()[target_version]
        runtime = {"glue": target_version}
        for chave in ("spark", "python", "iceberg"):
            if linha.get(chave):
                runtime[chave] = linha[chave]
        return runtime

    descritor = release_descriptor.describe(platform, target_version)
    return {
        nome: componente.version
        for nome, componente in sorted(descritor.components.items())
        if not componente.is_set
    }


def _cobertura(
    catalogo: list[dict[str, Any]],
    platform: str,
    source: str,
    target: str,
    runtimes: list[dict[str, str]],
) -> CoverageDeclaration:
    """Quantas regras do catalogo este caminho podia alcancar, por eixo.

    "Alcancavel" e uma medida sobre `in_scope`, nao sobre disparo: uma regra
    alcancavel pode nao disparar porque o fact nao esta la, e essa e outra
    lacuna, ja nomeada em `missing_evidence`. O que este campo separa e a
    lacuna anterior a todas -- a regra que NAO EXISTE, e que nenhum artefato
    coletado faria aparecer.
    """
    eixo_da_plataforma = _EIXO_DA_PLATAFORMA[platform]

    no_catalogo: Counter[str] = Counter()
    guardadas = 0
    for regra in catalogo:
        escopo = regra.get("runtime_scope") or {}
        if escopo:
            guardadas += 1
        for chave in escopo:
            no_catalogo[chave] += 1

    alcancadas: set[str] = set()
    for runtime in runtimes:
        for regra in catalogo:
            if in_scope(regra.get("runtime_scope") or {}, runtime):
                alcancadas.add(regra["id"])

    alcancadas_por_eixo: Counter[str] = Counter()
    for regra in catalogo:
        if regra["id"] not in alcancadas:
            continue
        for chave in regra.get("runtime_scope") or {}:
            alcancadas_por_eixo[chave] += 1

    chaves_no_runtime = {chave for runtime in runtimes for chave in runtime}
    eixos = tuple(
        AxisCoverage(
            axis=eixo,
            catalog_rules=no_catalogo.get(eixo, 0),
            reachable_rules=alcancadas_por_eixo.get(eixo, 0),
            runtime_key_present=eixo in chaves_no_runtime,
        )
        # O eixo da PLATAFORMA entra mesmo valendo zero: e o unico jeito de a
        # saida dizer "nenhuma regra deste catalogo descreve breaking change de
        # EMR" em vez de simplesmente nao falar do assunto.
        for eixo in sorted(set(no_catalogo) | {eixo_da_plataforma})
    )
    return CoverageDeclaration(
        platform=platform,
        platform_axis=eixo_da_plataforma,
        source=source,
        target=target,
        steps=len(runtimes),
        catalog_rules=len(catalogo),
        version_guarded_rules=guardadas,
        unguarded_rules=len(catalogo) - guardadas,
        reachable_rules=len(alcancadas),
        axes=eixos,
        activated_axes=tuple(e.axis for e in eixos if e.reachable_rules),
    )


def _declaracao_de_cobertura(cobertura: CoverageDeclaration) -> str:
    """O texto de `CoverageDeclaration.statement`. Ver a propriedade.

    Tres frases, e cada uma responde uma pergunta diferente: o que existe no
    catalogo, o que ESTE caminho alcancou, e como ler o silencio. A terceira e
    a que importa -- ela e a unica coisa entre um assessment sem achado e a
    leitura "nada quebra".

    A distincao entre JULGAVEL e ALCANCADA e deliberada e foi medida: no
    caminho de EMR on EC2 entre as duas series, as cinco regras de `spark` sao
    julgaveis (a matriz publica a versao de Spark de cada degrau, entao a chave
    existe no runtime) e NENHUMA e alcancada (as quatro de `SF-SPARK4` pedem
    Spark 4, e a serie 7.x do EMR ainda esta na 3.5). Dizer "cinco alcancaveis"
    seria mentira; dizer so "zero" esconderia que a ponte existe e funciona.
    """
    nome = release_descriptor.platform_label(cobertura.platform)
    eixo = cobertura.platform_axis
    da_plataforma = next(e for e in cobertura.axes if e.axis == eixo)
    contagens_por_eixo = sum(e.catalog_rules for e in cobertura.axes)

    por_eixo = "; ".join(
        f"`{e.axis}`: {e.catalog_rules} no catalogo, "
        f"{e.reachable_rules} alcancadas por este caminho, chave de runtime "
        f"{'presente' if e.runtime_key_present else 'AUSENTE'}"
        for e in cobertura.axes
    )
    partes = [
        f"COBERTURA DECLARADA. Plataforma: {nome}. Caminho: {cobertura.source} -> "
        f"{cobertura.target}, {cobertura.steps} degrau(s). Catalogo: "
        f"{cobertura.catalog_rules} regras, das quais "
        f"{cobertura.version_guarded_rules} guardadas por versao "
        f"({contagens_por_eixo} contagens por eixo -- uma regra com dois eixos "
        f"conta nos dois) e {cobertura.unguarded_rules} sem guarda, alcancaveis "
        f"em qualquer runtime.",
        f"Por eixo de `runtime_scope` -- {por_eixo}.",
    ]
    if da_plataforma.catalog_rules == 0:
        de_spark = next((e for e in cobertura.axes if e.axis == "spark"), None)
        no_catalogo = de_spark.catalog_rules if de_spark else 0
        alcancadas = de_spark.reachable_rules if de_spark else 0
        julgavel = bool(de_spark and de_spark.runtime_key_present)
        partes.append(
            f"NENHUMA regra deste catalogo declara `{eixo}` em `runtime_scope`: "
            f"nada aqui descreve breaking change de {nome} por versao de "
            f"plataforma, e este assessment nao pode encontrar o que ninguem "
            f"escreveu. O que foi avaliado e Spark e componente. A ponte e a "
            f"matriz de {nome}, que publica a versao de Spark de cada release: "
            f"com ela, as {no_catalogo} regras guardadas por `spark` ficam "
            f"{'julgaveis' if julgavel else 'sem chave de runtime e portanto mudas'} "
            f"neste caminho, e {alcancadas} delas entraram no escopo. O que muda "
            f"de componente por degrau esta em `component_diff`."
        )
    else:
        partes.append(
            f"O eixo `{eixo}` tem {da_plataforma.catalog_rules} regras neste "
            f"catalogo, e este caminho alcancou "
            f"{da_plataforma.reachable_rules} delas."
        )
    partes.append(
        "Portanto: assessment sem achado significa `nenhuma das regras "
        "alcancaveis disparou`, e nunca `nada quebra`. O que este verbo nao "
        "cobre esta nomeado -- aqui, em `missing_evidence` e em "
        "`component_diff_unresolved` --, porque listar a recusa e a diferenca "
        "entre nao saber e nao ter perguntado."
    )
    return " ".join(partes)


def _diff_de_componentes(
    platform: str, degraus: list[tuple[str, str]]
) -> tuple[list[StepComponentDiff], dict[str, str]]:
    """`ReleaseDiff` por degrau, projetado. Ver DECISAO 4 no docstring.

    A projecao separa a recusa que e do DEGRAU da que e da PLATAFORMA, e a
    segunda sobe uma vez so. Uma recusa `PLATFORM_DOES_NOT_PUBLISH` dos dois
    lados -- `hudi` e `delta` em EMR on EC2, `hadoop` em EMR on EKS -- nao
    muda entre degraus: a fonte daquela plataforma nao publica aquele eixo em
    release nenhuma, e repetir o texto inteiro seis vezes num caminho de seis
    degraus e payload sem informacao nova. Ja `RELEASE_CELL_ABSENT` e de um
    LADO especifico (a celula de `iceberg` em `emr-6.4.0`), e por isso fica no
    degrau que a encontrou.
    """
    descritores: dict[str, release_descriptor.ReleaseDescriptor] = {}

    def _descritor(release: str) -> release_descriptor.ReleaseDescriptor:
        if release not in descritores:
            descritores[release] = release_descriptor.describe(platform, release)
        return descritores[release]

    por_degrau: list[StepComponentDiff] = []
    da_plataforma: dict[str, str] = {}
    for origem, alvo in degraus:
        esquerda, direita = _descritor(origem), _descritor(alvo)
        comparacao = release_diff.diff(esquerda, direita)
        do_degrau: dict[str, str] = {}
        for chave, razao in comparacao.unresolved.items():
            if chave in release_diff.DIMENSOES_SEM_LASTRO:
                da_plataforma.setdefault(chave, razao)
                continue
            nome = chave[len("component.") :] if chave.startswith("component.") else ""
            eixo_inexistente = bool(nome) and all(
                nome in lado.refused
                and lado.refused[nome].kind
                == release_descriptor.PLATFORM_DOES_NOT_PUBLISH
                for lado in (esquerda, direita)
            )
            if eixo_inexistente:
                da_plataforma.setdefault(chave, esquerda.refused[nome].reason)
            else:
                do_degrau[chave] = razao
        por_degrau.append(
            StepComponentDiff(
                step=(origem, alvo),
                changed=tuple(entrada.to_dict() for entrada in comparacao.changed),
                added=comparacao.added,
                removed=comparacao.removed,
                unchanged=comparacao.unchanged,
                unresolved=do_degrau,
            )
        )
    return por_degrau, da_plataforma


def _compatibility_gate(findings: list[Finding]) -> str:
    if not findings:
        return "PASS"
    if any(f.severity in _SEVERITIES_QUE_FALHAM_O_GATE for f in findings):
        return "FAIL"
    return "PASS_WITH_RISK"


def _eixo_de(finding: Finding) -> str:
    """Qual eixo do contrato este achado move.

    Um achado conta em UM eixo, nunca em dois: se `SF-LF-001` movesse tambem
    `compatibilidade`, o eixo nomeado seria decoracao para o veredito -- o mesmo
    problema fechando dois gates parece dois problemas.

    `compatibilidade` e o eixo RESIDUAL, e de proposito. Uma area sem eixo
    proprio (`SF-GLUE`, `SF-ICE`) cai nele em vez de nao mover gate nenhum:
    achado P0 que nao fecha gate viraria `CONDITIONAL_GO` com um P0 na lista, e
    entre bloquear demais e passar de menos este repositorio escolhe fail-closed.
    """
    area = area_of(finding.rule_id)
    for eixo, (area_do_eixo, _) in _EIXOS_COM_PRODUTOR.items():
        if area == area_do_eixo:
            return eixo
    return "compatibilidade"


# Ordem do pior para o melhor. Quando duas evidencias falam do mesmo eixo -- um
# achado do catalogo e a matriz de suporte --, o eixo fica com a PIOR: um gate
# que escolhesse a melhor esconderia a evidencia que importa.
_ORDEM_DE_GATE = ("FAIL", "BLOCKED", "PASS_WITH_RISK", "PASS")


def _pior(*estados: str) -> str:
    return min(estados, key=_ORDEM_DE_GATE.index)


def _tabelas_em_v3(facts: list[Fact]) -> tuple[bool, set[str]]:
    """`(pede v3?, tabelas nomeadas que vao para v3)`.

    Duas fontes, e as duas contam. `mig.table_format` e a observacao no CODIGO
    do job; ela carrega `attrs.table` QUANDO o nome esta na mesma linha do
    `format-version` (um `CREATE`/`ALTER TABLE`), e nao carrega quando nao esta.
    `iceberg.table_property` vem do dump de metadados de uma tabela real, e o
    subject dela E a tabela.

    O conjunto pode ficar VAZIO com o booleano `True`: e o caso de um job que
    fixa `format-version` num dicionario de configuracao, sem nomear a tabela na
    linha. Ai a unica pergunta respondivel volta a ser a do JOB -- "esta
    migracao vai escrever v3, e quem le isso?" --, e o gate degrada para ela em
    vez de fingir precisao que o artefato nao tem.
    """
    pede = False
    tabelas: set[str] = set()
    for fact in facts:
        if fact.kind == "mig.table_format" and str(fact.attrs.get("format_version")) == "3":
            pede = True
            nome = str(fact.attrs.get("table", "")).strip()
            if nome:
                tabelas.add(nome)
        elif (
            fact.kind == "iceberg.table_property"
            and fact.attrs.get("key") == "format-version"
            and str(fact.attrs.get("value")) == "3"
        ):
            pede = True
            nome = str(fact.subject.get("symbol", "")).strip()
            if nome:
                tabelas.add(nome)
    return pede, tabelas


def _mesma_tabela(declarada: str, observada: str) -> bool:
    """Casamento de nome de tabela, com o mesmo recorte de `facts/fusion.py`.

    Igualdade do nome inteiro, sem diferenciar maiuscula. Se falhar, o ULTIMO
    segmento contra o ultimo segmento -- `glue_catalog.curated.pedidos` casa com
    `curated.pedidos` e com `pedidos`. Nao ha aqui a guarda de ambiguidade que a
    fusao tem, porque o conjunto comparado e pequeno e a consequencia de casar
    demais e BLOQUEAR uma migracao a mais, nao aprovar uma a menos: entre
    bloquear demais e passar de menos, este repositorio escolhe fail-closed.
    """
    a, b = declarada.strip().lower(), observada.strip().lower()
    if not a or not b:
        return False
    return a == b or a.split(".")[-1] == b.split(".")[-1]


def _gate_de_consumidor(facts: list[Fact], por_regra: str) -> tuple[str, str]:
    """Cruza o inventario de consumidores com a matriz de suporte de feature.

    Devolve `(estado, evidencia_faltante)`. A evidencia so e preenchida quando
    o eixo fica BLOCKED -- gate BLOCKED sem dizer o que o destravaria e a mesma
    coisa que silencio.

    NAO emite `Finding`. `SF-ENV-002` continua sendo o achado do caso
    documentado (tabela v3 lida por Athena, com o erro textual "Cannot read
    unsupported version 3"); este cruzamento move o GATE. Um caso ja coberto
    pela regra produz um achado e um gate fechado, nunca dois achados.
    """
    pede_v3, tabelas_v3 = _tabelas_em_v3(facts)
    if not pede_v3:
        # Nada nesta migracao pede v3. Bloquear aqui acusaria o job pelo que
        # ele NAO faz, e o inventario continua servindo as regras do catalogo.
        return por_regra, ""

    consumidores = [f for f in facts if f.kind == "env.consumer" and f.attrs.get("service")]
    if tabelas_v3:
        # A tabela e observavel: pergunte por ELA. Consultar todo consumidor
        # declarado acusaria esta migracao por causa do consumidor de OUTRA
        # tabela -- e nome de tabela errado num achado manda alguem conferir a
        # tabela errada.
        consumidores = [
            f
            for f in consumidores
            if any(_mesma_tabela(str(f.attrs.get("table", "")), t) for t in tabelas_v3)
        ]
    engines = sorted({str(f.attrs["service"]) for f in consumidores})

    veredito = storage_upgrade.assess_upgrade(engines, target_spec_version=3)
    if veredito.verdict == "BLOCKED":
        return _pior(por_regra, "FAIL"), ""
    if veredito.verdict == "UNRESOLVED":
        faltante = "; ".join(veredito.unresolved)
        if tabelas_v3:
            # Dizer QUAL tabela vai para v3 e o que transforma "declare o
            # inventario" numa instrucao acionavel.
            faltante = f"tabelas que vao para format v3: {sorted(tabelas_v3)} -- {faltante}"
        return _pior(por_regra, "BLOCKED"), faltante
    if veredito.verdict == "CONDITIONAL":
        return _pior(por_regra, "PASS_WITH_RISK"), ""
    return por_regra, ""


def assess(
    facts: list[Fact],
    source: str,
    target: str,
    platform: str = version_path.DEFAULT_PLATFORM,
) -> MigrationAssessment:
    """Julga `facts` contra o catalogo, uma vez por degrau de `source` ate
    `target`, na matriz de `platform`.

    Propaga os `ValueError` de `version_path.steps` (versao fora da matriz,
    alvo anterior a origem, rotulo fora do padrao de versao, plataforma
    desconhecida) em vez de engoli-los: um assessment vazio devolvido para um
    par invalido pareceria "sem breaking change encontrado", quando o par nem
    chegou a ser avaliado. Melhor estourar aqui do que produzir um NO_GO ou GO
    que ninguem pediu.

    `source` e `target` saem normalizados na chave da matriz -- `emr-7.5.0`
    entra e `7.5.0` sai --, para que o par relatado seja o par conferivel
    contra `known_releases()`.
    """
    degraus = version_path.steps(source, target, platform)
    catalogo = load_catalog()

    findings: list[Finding] = []
    by_step: list[tuple[Finding, tuple[str, str]]] = []
    runtimes: list[dict[str, str]] = []
    for degrau in degraus:
        _, alvo = degrau
        runtime = _runtime_for(alvo, platform)
        runtimes.append(runtime)
        for finding in judge(facts, catalogo, runtime):
            findings.append(finding)
            by_step.append((finding, degrau))

    findings = sort_findings(findings)

    por_eixo: dict[str, list[Finding]] = {}
    for finding in findings:
        por_eixo.setdefault(_eixo_de(finding), []).append(finding)

    # Ordem declarada, nao ordem de construcao: `compatibilidade` primeiro
    # porque e o eixo residual e o unico que sempre tem produtor, depois os
    # eixos nomeados com produtor, depois os que so declaram o que falta. Quem
    # le o JSON le nesta ordem, e ela nao pode mudar por causa de refatoracao.
    gates: dict[str, str] = {
        "compatibilidade": _compatibility_gate(por_eixo.get("compatibilidade", []))
    }
    missing_evidence: dict[str, str] = {}

    kinds = {f.kind for f in facts}
    for eixo, (_, kind_exigido) in _EIXOS_COM_PRODUTOR.items():
        if kind_exigido not in kinds:
            # Fail-closed: o eixo nao foi avaliado, e isso e diferente de ter
            # passado. Quem le precisa distinguir "nao achei problema" de "nao
            # olhei" -- o invariante que esta secao do contrato existe para nao
            # violar.
            gates[eixo] = "BLOCKED"
            missing_evidence[eixo] = _EVIDENCIA_DOS_EIXOS[eixo]
            continue
        estado = _compatibility_gate(por_eixo.get(eixo, []))
        if eixo == "consumidor":
            estado, faltante = _gate_de_consumidor(facts, estado)
            if faltante:
                missing_evidence[eixo] = faltante
        gates[eixo] = estado

    gates.update({nome: "BLOCKED" for nome in _EIXOS_SEM_PRODUTOR})
    missing_evidence.update(_EIXOS_SEM_PRODUTOR)

    gates.update({nome: "BLOCKED" for nome in _EXECUTION_GATES})
    missing_evidence.update(_EXECUTION_GATES)

    if any(estado == "FAIL" for estado in gates.values()):
        recommendation = "NO_GO"
    else:
        # Os gates de execucao real nascem sempre BLOCKED nesta analise (nenhum
        # job nem AWS viva): GO exigiria todo gate em PASS, entao o melhor
        # desfecho possivel aqui e CONDITIONAL_GO -- nunca GO.
        recommendation = "CONDITIONAL_GO"

    origem = release_descriptor.normalize_release(platform, source)
    alvo_final = release_descriptor.normalize_release(platform, target)
    componentes, sem_lastro = _diff_de_componentes(platform, degraus)
    return MigrationAssessment(
        source=origem,
        target=alvo_final,
        steps=degraus,
        findings=findings,
        by_step=by_step,
        gates=gates,
        missing_evidence=missing_evidence,
        recommendation=recommendation,
        platform=platform,
        coverage=_cobertura(catalogo, platform, origem, alvo_final, runtimes),
        component_diff=componentes,
        component_diff_unresolved=sem_lastro,
    )
