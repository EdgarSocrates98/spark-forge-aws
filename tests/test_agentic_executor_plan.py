"""Testes de `debate_plan` -- a secao 6 do spec, o limite declarado da entrega.

## O defeito que estes testes impedem de voltar

Ate 2026-09-03 `sparkforge budget show` imprimia `CaseBudget()` de fabrica --
`max_total_tokens: 50000`, `max_debates: 2` -- sem nenhuma marca de que o numero
era template e nao estado do case. Quem lesse a saida concluiria que o case
declarava aqueles tetos.

`test_sem_budget_nao_vaza_numero_de_fabrica` varre a saida inteira atras de
QUALQUER default de `CaseBudget`, derivado do proprio dataclass. Derivar em vez
de escrever os numeros a mao importa: se alguem mudar o default de
`max_agents` de 5 para 8, o teste passa a procurar 8 sozinho, e uma lista fixa
teria envelhecido em silencio.

## `rounds` e `unresolved` mesmo COM budget declarado

Isto surpreende, e por isso tem teste proprio. O bloco `budget:` do `case.yaml`
aceita sete chaves (`case_budget_from_case`), e nenhuma delas e numero de
rodadas: `max_debates` conta DEBATES, nao rodadas dentro de um. O numero de
rodadas so existe em `DebateBudget.max_rounds`, que e default de codigo -- exato
tipo de valor que `budget show --template` isola. Copia-lo para o plano seria o
defeito de 2026-09-03 reencenado num campo novo.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from sparkforge.agentic.budget import CaseBudget
from sparkforge.agentic.executor.plan import agent_for_area, area_of, debate_plan


def _texto(plano: dict[str, Any]) -> str:
    return json.dumps(plano, ensure_ascii=False, sort_keys=True)


def _defaults_de_fabrica() -> set[Any]:
    """Os valores default de `CaseBudget`, derivados do dataclass."""
    return {
        campo.default
        for campo in dataclasses.fields(CaseBudget)
        if campo.name.startswith("max_") and campo.default is not dataclasses.MISSING
    }


def _numeros(no: Any) -> list[Any]:
    """Todo valor NUMERICO do plano, em qualquer profundidade.

    A busca e por VALOR e nao por substring de texto. Procurar `"2"` dentro do
    JSON serializado casaria com "regra 23" e com a data da auditoria -- o
    teste acusaria vazamento onde ha prosa, e a primeira reacao de quem o visse
    falhar seria afrouxa-lo.
    """
    if isinstance(no, bool):
        return []
    if isinstance(no, (int, float)):
        return [no]
    if isinstance(no, dict):
        return [n for valor in no.values() for n in _numeros(valor)]
    if isinstance(no, (list, tuple)):
        return [n for item in no for n in _numeros(item)]
    return []


# --------------------------------------------------------------------------
# Derivacao de participante
# --------------------------------------------------------------------------


def test_area_sai_do_rule_id_sem_o_ordinal() -> None:
    assert area_of("SF-GLUE-001") == "SF-GLUE"
    assert area_of("SF-STEP-FUNCTIONS-004") == "SF-STEP-FUNCTIONS"
    assert area_of("SF-PY-9") == "SF-PY"


def test_rule_id_sem_ordinal_nao_inventa_area() -> None:
    assert area_of("SF-GLUE") == ""
    assert area_of("") == ""


def test_routing_declara_agente_para_as_areas_do_catalogo() -> None:
    """A derivacao e possivel: `routing.yaml` casa `findings_area` com agente."""
    assert agent_for_area("SF-GLUE") == "glue-infra-reviewer"
    assert agent_for_area("SF-ICE") == "iceberg-performance-engineer"
    assert agent_for_area("SF-INEXISTENTE") is None


def test_plano_nomeia_participantes_e_contexto() -> None:
    plano = debate_plan(
        ["SF-GLUE-001", "SF-ICE-004"],
        {"SF-GLUE-001": ["f_a", "f_b"], "SF-ICE-004": ["f_c"]},
        None,
    )

    por_agente = {p["agent"]: p for p in plano["participants"]}
    assert set(por_agente) == {"glue-infra-reviewer", "iceberg-performance-engineer"}
    assert por_agente["glue-infra-reviewer"]["rules"] == ["SF-GLUE-001"]
    assert por_agente["glue-infra-reviewer"]["context_fact_ids"] == ["f_a", "f_b"]
    assert por_agente["iceberg-performance-engineer"]["context_fact_ids"] == ["f_c"]


def test_duas_regras_do_mesmo_agente_viram_um_participante_so() -> None:
    """`SF-PY` e `SF-PLAN` roteiam para o mesmo coordenador. Ele fala uma vez.

    Duplicar o participante inflaria a contagem de agentes contra o
    `max_agents` declarado, e faria o mesmo coordenador debater consigo mesmo.
    """
    plano = debate_plan(
        ["SF-PY-009", "SF-PLAN-003"],
        {"SF-PY-009": ["f_a"], "SF-PLAN-003": ["f_a", "f_b"]},
        None,
    )

    (participante,) = plano["participants"]
    assert participante["agent"] == "pyspark-code-reviewer"
    assert participante["rules"] == ["SF-PY-009", "SF-PLAN-003"]
    assert participante["context_fact_ids"] == ["f_a", "f_b"]


def test_regra_sem_agente_sai_declarada_e_nao_escondida() -> None:
    """Limitacao vai no proprio plano, nunca em comentario."""
    plano = debate_plan(["SF-NAOEXISTE-001"], {"SF-NAOEXISTE-001": ["f_a"]}, None)

    assert plano["participants"] == []
    (lacuna,) = plano["participants_unresolved"]
    assert lacuna["rule_id"] == "SF-NAOEXISTE-001"
    assert lacuna["area"] == "SF-NAOEXISTE"
    assert "routing.yaml" in lacuna["reason"]


def test_toda_area_executavel_do_catalogo_resolve_participante() -> None:
    """O §26 do prompt de origem pede ONZE especialistas de Lake Formation, IAM,
    S3, KMS, Iceberg e migracao, "e eles devem poder debater entre si".

    Medido: os onze NOMES nao existem, e nao devem -- cada area que eles
    cobririam ja tem dono em `routing.yaml`, e o §32 do mesmo prompt proibe
    duplicar ("nao duplicar funcionalidades existentes; antes de criar qualquer
    novo modulo, localizar o que ja existe e estender quando possivel").

    O que o §26 pede DE VERDADE e a capacidade: participante resolvido para toda
    area em disputa, senao o `DebatePlan` sai com `participants_unresolved` e o
    debate nao tem quem o faca. Este teste trava isso como INVARIANTE em vez de
    afirmacao -- area de regra nova sem rota passa a derrubar aqui, e o alarme
    aparece antes de alguem descobrir que o plano nao acha o especialista.

    Uma area COM regra executavel e sem agente e o defeito; area `structural`
    (declaracao de coordenacao, sem `action`) nao entra, porque ela nao propoe
    mudanca e portanto nao entra em contradicao com ninguem.
    """
    from sparkforge.findings.models import area_of
    from sparkforge.rules.loader import load_catalog

    regras = [r for r in load_catalog() if r.get("action")]
    por_area: dict[str, str] = {}
    for regra in regras:
        por_area.setdefault(area_of(regra["id"]), regra["id"])

    plano = debate_plan(
        sorted(por_area.values()),
        {rid: ["f_a"] for rid in por_area.values()},
        None,
    )
    assert plano["participants_unresolved"] == [], plano["participants_unresolved"]
    # E o outro lado: todo participante resolvido tem area e regra, nunca um
    # agente pendurado sem o que julgar.
    for participante in plano["participants"]:
        assert participante["agent"]
        assert participante["areas"]
        assert participante["rules"]


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------


def test_sem_budget_o_plano_sai_unresolved_nomeando_a_lacuna() -> None:
    plano = debate_plan(["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, None)

    assert plano["budget"]["status"] == "unresolved"
    assert "budget" in plano["budget"]["reason"]
    assert "case.yaml" in plano["budget"]["reason"]


def test_sem_budget_nao_vaza_numero_de_fabrica() -> None:
    plano = debate_plan(["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, None)

    presentes = sorted(set(_numeros(plano)) & _defaults_de_fabrica())
    assert not presentes, f"default de CaseBudget vazou para o plano: {presentes}"
    # Sem budget declarado o plano nao tem numero NENHUM. E a afirmacao mais
    # forte que se pode fazer aqui, e ela nao depende de quais defaults o
    # `CaseBudget` tem hoje.
    assert _numeros(plano) == []


def test_budget_vazio_conta_como_ausente() -> None:
    """`budget: {}` no case.yaml nao declara teto nenhum."""
    assert debate_plan(["SF-GLUE-001"], {}, {})["budget"]["status"] == "unresolved"


def test_com_budget_declarado_os_limites_viajam() -> None:
    plano = debate_plan(
        ["SF-GLUE-001"],
        {"SF-GLUE-001": ["f_a"]},
        {"max_debates": 1, "max_agents": 3, "max_total_tokens": 12000},
    )

    limites = plano["budget"]
    assert limites["status"] == "declared"
    assert limites["max_debates"] == 1
    assert limites["max_agents"] == 3
    assert limites["max_total_tokens"] == 12000


def test_budget_declarado_vira_criterio_de_parada() -> None:
    plano = debate_plan(
        ["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, {"max_debates": 1, "max_agents": 3}
    )

    parada = " | ".join(plano["stop_criteria"])
    assert "max_debates" in parada
    assert "max_agents" in parada


def test_sem_budget_o_criterio_de_parada_tambem_e_unresolved() -> None:
    plano = debate_plan(["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, None)

    assert plano["stop_criteria"] == []
    assert plano["stop_criteria_status"] == "unresolved"


def test_rodadas_saem_unresolved_mesmo_com_budget_declarado() -> None:
    plano = debate_plan(["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, {"max_debates": 1})

    assert plano["rounds"]["status"] == "unresolved"
    assert "max_rounds" in plano["rounds"]["reason"]


def test_budget_invalido_nao_derruba_o_plano() -> None:
    """Regra 27: instrumentacao que quebra o produto e defeito.

    A validacao e a mesma de `budget show` -- `case_budget_from_case` levanta
    `ValueError` com a mensagem que nomeia a chave errada. Aqui ela vira
    `unresolved` com a mensagem dentro, em vez de matar a emissao do plano.
    """
    plano = debate_plan(["SF-GLUE-001"], {}, {"max_agentes": 3})

    assert plano["budget"]["status"] == "unresolved"
    assert "max_agentes" in plano["budget"]["reason"]


# --------------------------------------------------------------------------
# A parada
# --------------------------------------------------------------------------


def test_o_plano_nao_executa_e_o_motivo_cita_agentruntime() -> None:
    plano = debate_plan(["SF-GLUE-001"], {"SF-GLUE-001": ["f_a"]}, None)

    assert plano["executed"] is False
    assert plano["unresolved"]["reason"] == "debate.unresolved"
    assert "AgentRuntime" in plano["unresolved"]["unblocked_by"]


def test_o_plano_nao_nomeia_vencedor() -> None:
    """Ele emite quem debateria, nunca quem ganhou. Nao ha executor para decidir."""
    plano = debate_plan(["SF-GLUE-001", "SF-ICE-004"], {}, None)

    assert "winner" not in _texto(plano)
    assert "vencedor" not in _texto(plano)


@pytest.mark.parametrize("regras", [None, [], ["", "   "]])
def test_sem_regra_o_plano_ainda_sai_e_ainda_declara_a_parada(regras: Any) -> None:
    plano = debate_plan(regras, None, None)

    assert plano["participants"] == []
    assert plano["executed"] is False
