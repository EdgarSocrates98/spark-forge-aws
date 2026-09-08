"""Testes de `unknowns_from` e `experiments_from` -- a secao 5.3 do spec.

## As tres amarras, e por que cada uma tem teste proprio

- **`expected_results` fica VAZIO.** Preve-lo seria estimar ganho, e a regra 13
  proibe. `design_experiment_for_unknown` preenche o campo com
  `"Answer to: <pergunta>"`, entao o teste nao e decorativo: ele trava a
  substituicao, e passaria a acusar se alguem devolvesse o experimento cru.
- **`cost_estimate` e `time_estimate` saem `"unresolved"`.** A entrega original
  da camada agentica fixava "1 Glue job run (DPU-hours)" e "15-30 minutes" em
  texto, e a auditoria de 2026-09-03 pegou isso como um dos catorze defeitos.
  Sem `glue.run_cost` de run comparavel os dois sao recusa nomeada (regra 14),
  nunca numero.
- **`success_criteria` nao pode ser vazio.** Ele e o que separa experimento de
  desejo: descreve a MEDIDA que resolve o `Unknown`, nao um alvo de melhora.

## A varredura de texto, e o que ela realmente prova

`test_nenhum_campo_preve_ganho` varre TODOS os campos de string de todo
`Unknown` e todo `Experiment` gerados sobre o corpus inteiro, procurando `%`,
`econom` e `melhor`. Ela nao prova que o modulo nunca preveria ganho -- prova
que, sobre as 253 fixtures que hoje tem o par de arquivos, nenhuma previsao
vazou por interpolacao de `attrs` do fact. Essa e a rota plausivel de
vazamento: o texto que entra em `evidence_needed` e `resolution_method` vem do
artefato, e nao deste modulo.

## Por que "bloqueante" nao e uma escolha estilistica

Um fact `*.unresolved` que NENHUM finding cita e uma lacuna do case, nao uma
lacuna de um diagnostico: nada depende dela para concluir. Ele vira `Unknown`
-- a lacuna existe e sai nomeada, regra 20 -- e nao vira experimento, porque
gastar um run para medir o que ninguem pediu e desperdicio declarado. Bloqueante
e o fact citado por finding, e o finding cuja ancora nao veio.
"""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from sparkforge.agentic.executor.unknowns import experiments_from, unknowns_from
from sparkforge.agentic.models import Experiment, Unknown, UnknownStatus
from sparkforge.findings.models import Fact

RAIZ = Path(__file__).resolve().parents[1]

# As tres marcas de previsao de ganho. `%` pega "reduz 30%"; `econom` pega
# "economia" e "economizaria"; `melhor` pega "melhora" e "melhoria". A lista e
# curta de proposito -- ela cobre as formas que a regra 13 nomeia, e um regex
# maior daria falso positivo em texto de artefato sem provar mais nada.
_MARCAS_DE_GANHO = re.compile(r"%|econom|melhor", re.IGNORECASE)


def _fact(kind: str, fact_id: str, **attrs: Any) -> dict[str, Any]:
    return {"id": fact_id, "kind": kind, "measures": {}, "attrs": dict(attrs)}


def _finding(rule_id: str, evidence: list[str]) -> dict[str, Any]:
    return {"rule_id": rule_id, "title": f"titulo de {rule_id}", "evidence": evidence}


def _fixtures_com_facts_e_findings() -> list[tuple[Path, list[dict], list[dict]]]:
    """As fixtures que tem os dois arquivos, com a UNIAO dos facts.

    Fixture com so um dos dois nao entra: `unknowns_from` cruza as duas listas, e
    medir sobre metade do par mediria outra coisa.

    Os facts sao a uniao de `input/facts.json` e `expected/facts.json`, sem id
    repetido, porque e esse o conjunto que `judge` recebeu para produzir aqueles
    findings (secao 12.9 do spec). Medir sobre `expected/` sozinho fabricava
    tres claims desancoradas que a execucao real nao produz -- e uma medida
    anterior deste arquivo as publicou como reais.
    """
    corpus: list[tuple[Path, list[dict], list[dict]]] = []
    for pasta in sorted((RAIZ / "fixtures").glob("*/*/expected")):
        arquivo_facts, arquivo_findings = pasta / "facts.json", pasta / "findings.json"
        if not (arquivo_facts.exists() and arquivo_findings.exists()):
            continue
        corpus.append(
            (
                pasta,
                _uniao_de_facts(pasta.parent),
                _lista(json.loads(arquivo_findings.read_text(encoding="utf-8")), "findings"),
            )
        )
    return corpus


def _uniao_de_facts(caso: Path) -> list[dict]:
    """`input/facts.json` mais `expected/facts.json`, sem `fact.id` repetido.

    Os ids da entrada nao vem no artefato: eles sao computados por `Fact.id`,
    content-addressed sobre kind, subject e measures. Escreve-los a mao aqui os
    congelaria, e fixture e teste divergiriam no dia em que uma medida mudasse.
    """
    brutos: list[dict] = []
    entrada = caso / "input" / "facts.json"
    if entrada.exists():
        for bruto in _lista(json.loads(entrada.read_text(encoding="utf-8")), "facts"):
            if not isinstance(bruto, dict):
                continue
            fact = Fact(
                kind=str(bruto.get("kind") or ""),
                subject=bruto.get("subject") or {},
                measures=bruto.get("measures") or {},
                attrs=bruto.get("attrs") or {},
                provenance=bruto.get("provenance") or {},
            )
            brutos.append({**bruto, "id": bruto.get("id") or fact.id})
    esperados = caso / "expected" / "facts.json"
    if esperados.exists():
        brutos += _lista(json.loads(esperados.read_text(encoding="utf-8")), "facts")

    vistos: set[str] = set()
    uniao: list[dict] = []
    for fact_bruto in brutos:
        fact_id = str(fact_bruto.get("id") or "").strip()
        if fact_id and fact_id in vistos:
            continue
        if fact_id:
            vistos.add(fact_id)
        uniao.append(fact_bruto)
    return uniao


def _lista(documento: Any, chave: str) -> list[dict]:
    return documento if isinstance(documento, list) else documento.get(chave, [])


def _textos(entidade: Any) -> list[str]:
    """Todo campo de string da entidade, mais os itens de campo de lista."""
    saida: list[str] = []
    for campo in fields(entidade):
        valor = getattr(entidade, campo.name)
        if isinstance(valor, str):
            saida.append(valor)
        elif isinstance(valor, (list, tuple)):
            saida.extend(str(item) for item in valor)
    return saida


# --------------------------------------------------------------------------
# Origem 1 -- fact `*.unresolved`
# --------------------------------------------------------------------------


def test_fact_unresolved_vira_unknown_com_a_razao_em_evidence_needed() -> None:
    facts = [_fact("athena.unresolved", "f_1", reason="unparseable_engine_version")]
    findings = [_finding("SF-ATH-001", ["f_1"])]

    (unknown,) = unknowns_from(findings, facts)

    assert isinstance(unknown, Unknown)
    assert unknown.status == UnknownStatus.OPEN
    assert "athena.unresolved" in unknown.question
    assert "f_1" in unknown.question
    assert any("unparseable_engine_version" in item for item in unknown.evidence_needed)


def test_fact_resolvido_nao_vira_unknown() -> None:
    """Kind sem o sufixo nao e lacuna. Ele e a medida que o motor conseguiu."""
    facts = [_fact("athena.engine_version", "f_1", name="v3")]

    assert unknowns_from([_finding("SF-ATH-001", ["f_1"])], facts) == []


def test_unblocked_by_do_fact_vira_resolution_method() -> None:
    """O artefato ja diz o que destravaria; reescrever isso seria inventar."""
    facts = [
        _fact(
            "bridge.unresolved",
            "f_1",
            reason="sem_callsite_resolvido",
            unblocked_by="extraia o event log com `analyze event-log`",
        )
    ]

    (unknown,) = unknowns_from([_finding("SF-BRIDGE-001", ["f_1"])], facts)

    assert unknown.resolution_method == "extraia o event log com `analyze event-log`"


def test_fact_sem_unblocked_by_sai_com_resolution_method_none() -> None:
    facts = [_fact("catalog.unresolved", "f_1", reason="missing_table_name")]

    (unknown,) = unknowns_from([_finding("SF-CAT-001", ["f_1"])], facts)

    assert unknown.resolution_method is None


def test_fact_unresolved_citado_por_finding_e_bloqueante() -> None:
    facts = [_fact("plan.unresolved", "f_1", reason="no_physical_plan")]

    (unknown,) = unknowns_from([_finding("SF-PLAN-001", ["f_1"])], facts)

    assert unknown.blocking is True
    assert "SF-PLAN-001" in unknown.impact


def test_fact_unresolved_que_ninguem_cita_nao_e_bloqueante() -> None:
    """A lacuna existe e sai nomeada; o que ela nao faz e travar diagnostico."""
    facts = [
        _fact("s3.unresolved", "f_1", reason="listing_truncated"),
        _fact("pyspark.udf", "f_2"),
    ]
    findings = [_finding("SF-PY-001", ["f_2"])]

    (unknown,) = unknowns_from(findings, facts)

    assert unknown.blocking is False
    assert "nenhum finding" in unknown.impact


# --------------------------------------------------------------------------
# Origem 2 -- finding cuja evidencia nao esta no case
# --------------------------------------------------------------------------


def test_finding_com_evidencia_ausente_vira_unknown_nomeando_o_fact() -> None:
    facts = [_fact("pyspark.udf", "f_1")]
    findings = [_finding("SF-PY-009", ["f_1", "f_ausente"])]

    (unknown,) = unknowns_from(findings, facts)

    assert "f_ausente" in unknown.question
    assert "SF-PY-009" in unknown.question
    assert "f_ausente" in unknown.evidence_needed
    assert unknown.blocking is True


def test_finding_totalmente_ancorado_nao_vira_unknown() -> None:
    facts = [_fact("pyspark.udf", "f_1")]

    assert unknowns_from([_finding("SF-PY-009", ["f_1"])], facts) == []


def test_o_mesmo_fact_ausente_citado_por_duas_regras_sai_duas_vezes() -> None:
    """Duas claims desancoradas sao dois problemas, ainda que a ancora seja uma.

    Deduplicar por `fact_id` diria que uma das duas regras esta ancorada.
    """
    facts: list[dict] = []
    findings = [_finding("SF-A-001", ["f_x"]), _finding("SF-B-002", ["f_x"])]

    unknowns = unknowns_from(findings, facts)

    assert len(unknowns) == 2
    assert {"SF-A-001", "SF-B-002"} == {
        u.question.split()[1] for u in unknowns  # "finding <rule_id> cita ..."
    }


# --------------------------------------------------------------------------
# Experimentos
# --------------------------------------------------------------------------


def test_unknown_nao_bloqueante_nao_vira_experimento() -> None:
    facts = [_fact("s3.unresolved", "f_1", reason="listing_truncated")]

    unknowns = unknowns_from([], facts)

    assert [u.blocking for u in unknowns] == [False]
    assert experiments_from(unknowns) == []


def test_experimento_sai_com_custo_e_tempo_unresolved() -> None:
    """A auditoria de 2026-09-03 removeu os dois textos fixos. Este teste os barra."""
    facts = [_fact("glue.run_cost.unresolved", "f_1", reason="autoscaling_sem_dpu_seconds")]

    (experimento,) = experiments_from(unknowns_from([_finding("SF-FIN-001", ["f_1"])], facts))

    assert isinstance(experimento, Experiment)
    assert experimento.cost_estimate == "unresolved"
    assert experimento.time_estimate == "unresolved"


def test_experimento_sai_com_expected_results_vazio() -> None:
    facts = [_fact("spark.unresolved", "f_1", reason="no_stage_metrics")]

    (experimento,) = experiments_from(unknowns_from([_finding("SF-UI-001", ["f_1"])], facts))

    assert experimento.expected_results == ""


def test_experimento_sai_com_success_criteria_nao_vazio() -> None:
    facts = [_fact("spark.unresolved", "f_1", reason="no_stage_metrics")]

    (experimento,) = experiments_from(unknowns_from([_finding("SF-UI-001", ["f_1"])], facts))

    assert experimento.success_criteria.strip()
    assert "spark.unresolved" in experimento.success_criteria


def test_experimento_nomeia_a_medida_como_variavel() -> None:
    facts = [_fact("tf.unresolved", "f_1", reason="hcl_parse_error")]

    (experimento,) = experiments_from(unknowns_from([_finding("SF-TF-001", ["f_1"])], facts))

    assert experimento.variable == "tf.unresolved"
    assert "unresolved" in experimento.baseline


def test_um_experimento_por_unknown_bloqueante_na_mesma_ordem() -> None:
    facts = [
        _fact("emr.unresolved", "f_1", reason="a"),
        _fact("emrs.unresolved", "f_2", reason="b"),
        _fact("s3.unresolved", "f_3", reason="c"),
    ]
    findings = [_finding("SF-EMR-001", ["f_1"]), _finding("SF-EMRS-001", ["f_2"])]

    unknowns = unknowns_from(findings, facts)
    experimentos = experiments_from(unknowns)

    assert [u.blocking for u in unknowns] == [True, True, False]
    assert [e.variable for e in experimentos] == ["emr.unresolved", "emrs.unresolved"]


# --------------------------------------------------------------------------
# Robustez e corpus
# --------------------------------------------------------------------------


@pytest.mark.parametrize("entrada", [None, [], [{}], ["nao e dict"], [{"kind": None}]])
def test_entrada_degenerada_nao_derruba(entrada: Any) -> None:
    """Regra 27: medicao nunca derruba a chamada."""
    assert unknowns_from(entrada, entrada) == []


def test_nenhum_campo_preve_ganho() -> None:
    """Varredura de texto sobre o corpus inteiro -- regra 13.

    Falha nomeando a fixture e o campo, porque "algum campo do corpus tem `%`"
    seria impossivel de remediar sem reexecutar a busca a mao.
    """
    ofensas: list[str] = []
    for pasta, facts, findings in _fixtures_com_facts_e_findings():
        unknowns = unknowns_from(findings, facts)
        for entidade in [*unknowns, *experiments_from(unknowns)]:
            for texto in _textos(entidade):
                if _MARCAS_DE_GANHO.search(texto):
                    ofensas.append(f"{pasta.parent.name}: {texto[:120]}")

    assert not ofensas, "previsao de ganho vazou para o Unknown/Experiment: " + "; ".join(
        ofensas[:5]
    )


def test_no_corpus_nenhuma_recusa_e_citada_por_finding() -> None:
    """Medida, nao suposicao: hoje nenhum fact `*.unresolved` ancora finding.

    E o mesmo achado que `conflict.py` registrou sobre as guardas
    `requires_absent`: kind de recusa diz *nao deu para ler*, e regra nao
    dispara sobre "nao li". Consequencia -- os 61 `Unknown` de origem 1 que o
    corpus produz sobre a uniao dos facts sao todos NAO bloqueantes, e nenhum
    experimento sai deles.

    Se este teste cair, o corpus ganhou o caso que hoje nao tem. A remediacao e
    atualizar a nota, nunca afrouxar o criterio de `blocking`.
    """
    bloqueantes_de_recusa = [
        (pasta.parent.name, unknown.question)
        for pasta, facts, findings in _fixtures_com_facts_e_findings()
        for unknown in unknowns_from(findings, facts)
        if unknown.blocking and not unknown.question.startswith("finding ")
    ]

    assert not bloqueantes_de_recusa, (
        "o corpus passou a citar fact de recusa como ancora: " f"{bloqueantes_de_recusa[:3]}"
    )


def test_no_corpus_com_a_uniao_nenhuma_claim_fica_desancorada() -> None:
    """A correcao da secao 12.9, travada -- e o que ela substitui.

    Ate 2026-09-08 este arquivo media `unknowns_from` sobre `expected/facts.json`
    sozinho e publicava tres "claims desancoradas reais": dois `SF-UI-005` e um
    `SF-UI-001`, em `fixtures/timeout/`. **A afirmacao era falsa.** `f_c77ad7` e
    o id content-addressed de `spark.executor.lost`, que mora no
    `input/facts.json` daquelas fixtures; `expected/facts.json` guarda apenas o
    que o extrator daquele dominio emite, enquanto `expected/findings.json` e o
    julgamento sobre a UNIAO. Errada estava a entrada do teste.

    Com a uniao, origem 2 nao tem caso nenhum no corpus de hoje. O ramo continua
    coberto pelos testes sinteticos acima -- mecanismo sem caso e `unresolved`
    nomeado, e o lugar de dize-lo e aqui, nao um numero inflado.

    Se este teste cair, um finding passou a citar fact que nem a entrada nem os
    derivados carregam, e ai a lacuna e real: a remediacao e olhar a fixture,
    nunca voltar a medir sobre o subconjunto.
    """
    desancoradas = [
        (pasta.parent.name, unknown.question)
        for pasta, facts, findings in _fixtures_com_facts_e_findings()
        for unknown in unknowns_from(findings, facts)
        if unknown.question.startswith("finding ")
    ]

    assert not desancoradas, (
        "finding citando fact que a uniao do case nao carrega: " f"{desancoradas[:3]}"
    )


def test_o_corpus_produz_unknown_de_verdade() -> None:
    """Mecanismo sem caso e `unresolved` nomeado. Este mede que ha caso.

    Se o numero cair para zero, o modulo passou a nao ver o corpus -- e os
    testes sinteticos acima continuariam verdes.
    """
    total = sum(
        len(unknowns_from(findings, facts))
        for _, facts, findings in _fixtures_com_facts_e_findings()
    )

    assert total > 0
