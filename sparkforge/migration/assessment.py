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
from sparkforge.findings.models import (
    SEVERITY_ORDER,
    Fact,
    Finding,
    area_of,
    sort_findings,
)
from sparkforge.migration import version_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
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
