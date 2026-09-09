"""Testes de `direct_conflicts` e `conditional_conflicts` -- os dois modos da secao 4.

## Por que a contradicao direta NAO filtra por eixo

Um filtro por `nature: measure` sobre `moves` foi tentado e recusado, e o motivo
esta medido: ele apagava o caso REAL junto com o falso positivo.

- O falso positivo era `SF-PLAN-003` x `SF-PY-009` -- mesmo `target:
  pyspark.join`, direcoes opostas. O defeito nunca foi o eixo: era o `target`
  grosso demais, cobrindo a CONDICAO do join e o HINT do join como se fossem a
  mesma coisa. A correcao foi refinar os targets (`pyspark.join.condition`,
  `pyspark.join.hint`), que e onde o defeito morava.
- O caso real e `SF-GRAPH-005` x `SF-LF-001`, e o unico eixo que os dois
  compartilham -- `dependency.delivered_artifacts` -- e `nature: risk`. Filtrar
  por eixo de medida o teria apagado tambem.

Filtrar o criterio para compensar target impreciso teria escondido o problema em
vez de corrigi-lo. Por isso o teste sobre o catalogo inteiro esta aqui: ele trava
o par real, e passaria a acusar se alguem reintroduzisse o filtro.

## Por que a contradicao condicional devolve `[]` hoje

As quatro guardas `requires_absent` do catalogo sao KINDS DE RECUSA
(`emr.configuration.unapplied` x2, `emrc.pod_template.unresolved`,
`env.unresolved`) -- dizem *nao deu para ler*, nunca *o problema esta presente*.
A regra que guarda contra a recusa nao dispara quando a recusa acontece.

Dois testes cobrem isso, e a divisao e deliberada: um prova com dado sintetico
que a funcao FUNCIONA quando o caso existir, e outro mede o corpus real e
documenta que ele nao produz o caso. Mecanismo sem caso e `unresolved` nomeado,
nunca funcionalidade entregue.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sparkforge.agentic.executor.conflict import conditional_conflicts, direct_conflicts
from sparkforge.rules.loader import load_catalog

RAIZ = Path(__file__).resolve().parents[1]

# As tres guardas `requires_absent` do catalogo, e as regras que as declaram.
# Escritas aqui a mao de proposito: o teste de corpus quer saber se a REGRA
# disparou junto com o fact da guarda, e derivar isso do proprio catalogo faria
# o teste concordar consigo mesmo.
_GUARDA_DE_REGRA = {
    "SF-EMR-001": "emr.configuration.unapplied",
    "SF-EMR-005": "emr.configuration.unapplied",
    "SF-EMRK-002": "emrc.pod_template.unresolved",
    "SF-ENV-002": "env.unresolved",
}


def _acao(**over: Any) -> dict[str, Any]:
    base = {
        "kind": "capacity.change_worker_count",
        "target": "glue.number_of_workers",
        "direction": "increase",
        "requires_absent": [],
        "moves": ["capacity.worker_count"],
        "depends_on": [],
    }
    base.update(over)
    return base


def _finding(rule_id: str, **acao: Any) -> dict[str, Any]:
    return {"rule_id": rule_id, "action": _acao(**acao)}


def _json(caminho: str) -> list[dict[str, Any]]:
    bruto = json.loads((RAIZ / caminho).read_text(encoding="utf-8-sig"))
    if isinstance(bruto, list):
        return bruto
    for chave in ("findings", "facts"):
        if chave in bruto:
            return bruto[chave]
    raise AssertionError(f"{caminho}: nem lista nem envelope conhecido")


@pytest.fixture(scope="module")
def findings_do_catalogo() -> list[dict[str, Any]]:
    """Findings minimos -- so `rule_id` e `action` -- para as 112 regras executaveis."""
    return [
        {"rule_id": regra["id"], "action": regra["action"]}
        for regra in load_catalog()
        if regra.get("action")
    ]


class TestContradicaoDireta:
    def test_mesmo_alvo_com_increase_e_decrease_e_contradicao(self):
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="increase"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == [("SF-A", "SF-B")]

    def test_mesmo_alvo_com_add_e_remove_e_contradicao(self):
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="add"),
                _finding("SF-B", direction="remove"),
            ]
        )
        assert pares == [("SF-A", "SF-B")]

    def test_alvos_diferentes_com_direcoes_opostas_nao_e_contradicao(self):
        """A §4 do spec e explicita: alvo diferente e ORDEM, nao contradicao."""
        pares = direct_conflicts(
            [
                _finding("SF-A", target="glue.number_of_workers", direction="increase"),
                _finding("SF-B", target="spark.sql.shuffle.partitions", direction="decrease"),
            ]
        )
        assert pares == []

    def test_mesma_direcao_no_mesmo_alvo_nao_e_contradicao(self):
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="decrease"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == []

    def test_investigate_nao_e_oposto_de_mudanca(self):
        """Medir e mudar no mesmo alvo nao se contradizem -- eles se ORDENAM."""
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="investigate"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == []

    def test_replace_nao_e_oposto_de_nada(self):
        """`replace` e a direcao de 46 das 112, e nao tem par oposto declarado."""
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="replace"),
                _finding("SF-B", direction="add"),
                _finding("SF-C", direction="replace"),
            ]
        )
        assert pares == []

    def test_finding_sem_action_nao_participa(self):
        pares = direct_conflicts(
            [
                {"rule_id": "SF-SEM-ACTION"},
                {"rule_id": "SF-ACTION-VAZIA", "action": {}},
                _finding("SF-A", direction="increase"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == [("SF-A", "SF-B")]

    def test_par_sai_ordenado_independente_da_ordem_de_entrada(self):
        direta = direct_conflicts(
            [_finding("SF-Z", direction="add"), _finding("SF-A", direction="remove")]
        )
        invertida = direct_conflicts(
            [_finding("SF-A", direction="remove"), _finding("SF-Z", direction="add")]
        )
        assert direta == invertida == [("SF-A", "SF-Z")]

    def test_mesma_regra_duas_vezes_no_mesmo_alvo_nao_contradiz_a_si_mesma(self):
        """Duas ocorrencias da mesma regra sobre sujeitos diferentes sao um
        finding cada, e a regra nao briga consigo -- ela propoe a mesma coisa.

        Sem esta guarda, `(SF-A, SF-A)` sairia como contradicao assim que o
        catalogo tivesse uma regra com direcao oposta a ela mesma; e mesmo com
        direcoes iguais, a repeticao entraria no produto de pares.
        """
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="increase"),
                _finding("SF-A", direction="decrease"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == [("SF-A", "SF-B")]

    def test_par_nao_sai_duplicado_quando_a_regra_repete(self):
        pares = direct_conflicts(
            [
                _finding("SF-A", direction="increase"),
                _finding("SF-B", direction="decrease"),
                _finding("SF-B", direction="decrease"),
            ]
        )
        assert pares == [("SF-A", "SF-B")]

    def test_catalogo_inteiro_produz_exatamente_o_par_documentado(self, findings_do_catalogo):
        """O caso canonico, e o gate contra o filtro por eixo voltar.

        `SF-GRAPH-005` manda declarar o jar de GraphFrames em `--extra-jars` do
        `glue.default_arguments`; `SF-LF-001` manda remove-lo, porque a AWS nao
        oferece modo de FGAC do Lake Formation que aceite JAR adicional. Um job
        que usa GraphFrames sob FGAC dispara as duas, e elas sao incompativeis
        por limitacao de plataforma DOCUMENTADA.

        Se alguem reintroduzir o filtro por `nature: measure`, este par some --
        o unico eixo que os dois compartilham e `nature: risk`.

        O tamanho do fixture nao e fixado a mao: e derivado do mesmo criterio
        (`action` presente) usado para montar `findings_do_catalogo`, contra o
        conjunto de ids sem duplicata -- assim uma regra nova no catalogo nao
        quebra este teste, so a contagem de conflitos abaixo importa.
        """
        esperado = {regra["id"] for regra in load_catalog() if regra.get("action")}
        assert len(findings_do_catalogo) == len(esperado)
        assert direct_conflicts(findings_do_catalogo) == [("SF-GRAPH-005", "SF-LF-001")]


class TestContradicaoCondicional:
    def test_requires_absent_medido_entre_os_facts_dispara_nomeando_o_fact(self):
        findings = [
            _finding("SF-A", requires_absent=["spark.skew.severe"]),
        ]
        facts = [
            {"id": "f_001", "kind": "spark.stage.summary"},
            {"id": "f_002", "kind": "spark.skew.severe"},
        ]
        assert conditional_conflicts(findings, facts) == [
            ("SF-A", "spark.skew.severe", "f_002")
        ]

    def test_o_fact_id_entra_porque_a_contradicao_aponta_a_medida(self):
        """Dois facts do mesmo kind sao duas medidas, e as duas saem nomeadas.

        Devolver so o nome do kind diria "o sintoma esta presente" sem dizer
        ONDE ele foi medido, e a §4 exige os `fact.id` dos dois lados.
        """
        findings = [_finding("SF-A", requires_absent=["spark.skew.severe"])]
        facts = [
            {"id": "f_002", "kind": "spark.skew.severe"},
            {"id": "f_003", "kind": "spark.skew.severe"},
        ]
        assert conditional_conflicts(findings, facts) == [
            ("SF-A", "spark.skew.severe", "f_002"),
            ("SF-A", "spark.skew.severe", "f_003"),
        ]

    def test_requires_absent_nao_medido_cala(self):
        findings = [_finding("SF-A", requires_absent=["spark.skew.severe"])]
        facts = [{"id": "f_001", "kind": "spark.stage.summary"}]
        assert conditional_conflicts(findings, facts) == []

    def test_requires_absent_vazio_nao_participa(self):
        findings = [_finding("SF-A", requires_absent=[])]
        facts = [{"id": "f_001", "kind": "spark.stage.summary"}]
        assert conditional_conflicts(findings, facts) == []

    def test_finding_sem_action_nao_participa(self):
        findings = [
            {"rule_id": "SF-SEM-ACTION"},
            _finding("SF-A", requires_absent=["spark.skew.severe"]),
        ]
        facts = [{"id": "f_002", "kind": "spark.skew.severe"}]
        assert conditional_conflicts(findings, facts) == [
            ("SF-A", "spark.skew.severe", "f_002")
        ]

    def test_case_sem_fact_nenhum_cala(self):
        findings = [_finding("SF-A", requires_absent=["spark.skew.severe"])]
        assert conditional_conflicts(findings, []) == []

    def test_varias_guardas_saem_ordenadas(self):
        findings = [
            _finding("SF-B", requires_absent=["spark.skew.severe"]),
            _finding("SF-A", requires_absent=["spark.stage.spill", "spark.skew.severe"]),
        ]
        facts = [
            {"id": "f_002", "kind": "spark.skew.severe"},
            {"id": "f_001", "kind": "spark.stage.spill"},
        ]
        assert conditional_conflicts(findings, facts) == [
            ("SF-A", "spark.skew.severe", "f_002"),
            ("SF-A", "spark.stage.spill", "f_001"),
            ("SF-B", "spark.skew.severe", "f_002"),
        ]


class TestOCatalogoDeHojeNaoProduzContradicaoCondicional:
    """O estado correto, medido -- nao um bug a corrigir forcando um caso.

    A guarda de sintoma nao existe no catalogo: as quatro `requires_absent` sao
    kinds de RECUSA. Onze candidatas de sintoma foram medidas e recusadas nos
    sete lotes, sempre porque o kind sai sempre (`spark.stage.spill` e
    `spark.stage.gc` saem para todo stage, inclusive com zero byte) ou sai por
    motivos sem relacao (`iceberg.unresolved` cobre `read_error`,
    `malformed_json` e tres de `format_version` no mesmo kind).
    """

    def test_as_quatro_guardas_do_catalogo_sao_kinds_de_recusa(self, findings_do_catalogo):
        guardas = sorted(
            (f["rule_id"], kind)
            for f in findings_do_catalogo
            for kind in f["action"].get("requires_absent") or []
        )
        assert guardas == [
            ("SF-EMR-001", "emr.configuration.unapplied"),
            ("SF-EMR-005", "emr.configuration.unapplied"),
            ("SF-EMRK-002", "emrc.pod_template.unresolved"),
            ("SF-ENV-002", "env.unresolved"),
        ]
        assert all(
            kind.endswith(".unapplied") or kind.endswith(".unresolved")
            for _, kind in guardas
        )

    def test_nenhuma_fixture_do_repositorio_produz_o_caso(self):
        """A prova forte: o fact da guarda EXISTE no corpus, e mesmo assim nao ha caso.

        Medido em 2026-09-08 sobre as 253 fixtures com `facts.json` e
        `findings.json`: `env.unresolved` aparece em 1, `emr.configuration.
        unapplied` em 2, `emrc.pod_template.unresolved` em 1 -- e em nenhuma
        delas a regra que guarda contra aquele kind dispara junto. Nao e que o
        insumo falte; e que a regra nao dispara quando a leitura falhou.
        """
        casos: list[tuple[str, tuple[str, str, str]]] = []
        vistos_com_guarda = 0
        for diretorio in sorted((RAIZ / "fixtures").glob("*/*/expected")):
            arquivo_facts = diretorio / "facts.json"
            arquivo_findings = diretorio / "findings.json"
            if not arquivo_facts.exists() or not arquivo_findings.exists():
                continue
            facts = json.loads(arquivo_facts.read_text(encoding="utf-8-sig"))
            findings = json.loads(arquivo_findings.read_text(encoding="utf-8-sig"))
            if not isinstance(facts, list) or not isinstance(findings, list):
                continue
            kinds = {str(f.get("kind")) for f in facts if isinstance(f, dict)}
            if kinds & set(_GUARDA_DE_REGRA.values()):
                vistos_com_guarda += 1
            for achado in conditional_conflicts(findings, facts):
                casos.append((str(diretorio), achado))

        assert vistos_com_guarda >= 4, (
            "o corpus deixou de conter os facts de guarda; sem eles este teste "
            "nao prova nada sobre a ausencia do caso"
        )
        assert casos == []
