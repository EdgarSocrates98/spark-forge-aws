"""Regra que propoe trocar a implementacao que PRODUZ O VALOR cobra o valor.

O catalogo se contradizia sobre a MESMA recomendacao, e a contradicao era
medivel: `SF-PY-001`, `SF-PLAN-001`, `SF-PLAN-002`, `SF-PQ-002` e `SF-PQ-004`
propoem tirar UDF Python do caminho e todas exigem, no `validation`, comparacao
linha a linha com nulls e bordas. `SF-UI-004` e `SF-UI-005` propunham a MESMA
troca -- "eliminar UDF Python" com essas palavras -- e mediam so razao de GC,
runtime e memoria non-heap. A troca nao fica mais barata por ter chegado pela
via da Spark UI em vez da via do codigo.

POR QUE NAO E BUSCA POR FRASE MAGICA: o teste pergunta ao catalogo QUAIS regras
propoem a troca (varre `proposed_change` de `load_catalog()`), e so entao cobra
o eixo. No dia em que alguem escrever uma regra nova recomendando trocar UDF por
nativa, ela entra na parametrizacao sozinha e o teste cobra o eixo dela --
ninguem precisa lembrar de vir aqui. A lista de marcadores de eixo e ampla de
proposito, porque o que importa e que o eixo EXISTA, nao a redacao dele.

O limite deste teste, declarado porque ele e o mesmo dos quatro proxies de
`SF-FVAL`: presenca de eixo no texto nao prova que o eixo e suficiente. Ele pega
a regra que cala, que era o estado medido, e nao a que fala pouco.
"""
from __future__ import annotations

import pytest

from sparkforge.rules.loader import load_catalog


def _rules() -> list[dict]:
    """As 81 regras, ja achatadas pelo loader -- nenhuma lista escrita a mao aqui."""
    return list(load_catalog())


def _text(rule: dict, field: str) -> str:
    return " ".join(str(v) for v in (rule.get(field) or [])).lower()


# A populacao sai de DUAS perguntas ao catalogo, e as duas sao necessarias.
# So "udf" pegaria `SF-UI-002`, que manda INVESTIGAR UDF e nao trocar nenhuma --
# cobrar eixo de dado de uma regra que so roteia seria o defeito simetrico, texto
# decorativo em regra que nao muda nada. So o verbo pegaria toda reescrita do
# catalogo. O cruzamento pega exatamente a troca que muda a implementacao que
# PRODUZ O VALOR: nulo, precisao decimal, fuso, ordenacao de string e borda
# diferem entre a UDF e a funcao nativa que a substitui.
_UDF_MENTION = ("udf",)
_SWAP_VERB = (
    "substituir",
    "reescrever",
    "eliminar",
    "remover",
    "migrar para",
    "expressável com fun",
    "expressável com fun",
)

# Eixo do DADO, em qualquer redacao que o catalogo ja usa.
_VALUE_AXIS = (
    "linha a linha",
    "valor a valor",
    "contagem de nulls",
    "nulls e valores de borda",
    "nulls e bordas",
    "resultado funcional",
    "resultado idêntico",
    "contagem total",
)

def _swaps_a_udf(rule: dict) -> bool:
    proposed = _text(rule, "proposed_change")
    blob = proposed + " " + str(rule.get("title", "")).lower()
    return any(m in blob for m in _UDF_MENTION) and any(v in proposed for v in _SWAP_VERB)


_UDF_RULES = [r for r in _rules() if _swaps_a_udf(r)]


def test_the_survey_found_the_rules_it_is_supposed_to_guard():
    """Se o marcador parar de casar, o teste vira verde vazio -- o pior estado.

    Cinco regras propunham a troca antes desta rodada e duas foram acrescentadas
    ao conjunto ao ganharem o eixo; o piso existe para que uma reescrita de
    `proposed_change` que mude o vocabulario derrube ESTE teste, e nao silencie
    os de baixo.
    """
    achadas = sorted(r["id"] for r in _UDF_RULES)
    assert len(_UDF_RULES) >= 6, f"a varredura achou so {len(_UDF_RULES)}: {achadas}"
    # As duas que estavam mudas antes desta rodada. Se uma delas sair da
    # populacao, e porque o `proposed_change` dela mudou -- e a saida precisa ser
    # deliberada, nao um efeito colateral de reescrita.
    assert "SF-UI-004" in achadas and "SF-UI-005" in achadas, achadas


@pytest.mark.parametrize("rule", _UDF_RULES, ids=lambda r: r["id"])
def test_a_rule_that_swaps_the_udf_validates_the_value(rule: dict):
    validation = _text(rule, "validation")
    assert any(axis in validation for axis in _VALUE_AXIS), (
        f"{rule['id']} propoe trocar a implementacao que produz o valor e nao cobra o "
        f"valor no `validation`. Contagem, schema, chaves e agregados iguais nao provam "
        f"que o dado e o mesmo -- ver SF-FVAL e a regra 10 do AGENT_PROTOCOL.md."
    )


def test_removing_a_broadcast_hint_names_what_changes_without_changing_the_count():
    """`SF-PY-009` e a unica regra que propoe mudar a ESTRATEGIA FISICA de um join.

    O conjunto de linhas do equi-join nao muda entre BroadcastHashJoin e
    SortMergeJoin -- e por isso a regra media tempo e heap e passava. O que muda e
    o particionamento e a ordem, e com eles todo operador nao deterministico a
    jusante: os quatro eixos de `SF-FVAL` passam INTEIROS enquanto a linha que
    sobreviveu e outra. `risks` precisa dizer isso, e `validation` precisa cobrar
    valor, nao contagem.
    """
    rule = next(r for r in _rules() if r["id"] == "SF-PY-009")
    risks = _text(rule, "risks")
    validation = _text(rule, "validation")
    assert "ordem" in risks and "particionamento" in risks, "risks nao nomeia o que muda"
    assert "dropduplicates" in validation, "validation nao cobra o operador que troca a linha"
    assert "contagem" in validation, "validation nao cobra nenhum eixo de contagem"
