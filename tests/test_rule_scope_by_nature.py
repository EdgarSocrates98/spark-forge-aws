"""Escopo de regra tem que dizer o que a regra significa.

`runtime_scope: {glue: "*"}` foi lido como "qualquer runtime" quando significa
"qualquer versao de Glue" -- e o ramo do curinga em `version_scope.py` nem
checa presenca da chave, entao ele nunca filtrou nada.

O resultado: 20 regras agnosticas marcadas como de Glue, e 5 regras de infra
Glue avaliando em silencio num runtime que nao e Glue. Silencio, para um agente
autonomo, le como "nada encontrado" -- e a versao de orientacao do defeito que
`pyspark.unresolved` existe para impedir no analisador.
"""

import pytest

from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope

# Runtime EMR-like: Spark e Iceberg detectados, NENHUMA chave `glue`.
# E o cenario que a Fase 5 existe para servir.
EMR_LIKE = {"spark": "3.5.1", "python": "3.11", "iceberg": "1.7.1"}

# As que dependem de Glue. Listas explicitas porque sao curtas, fechadas, e sao
# a fronteira exata desta fase -- derivar do disco esconderia uma regra nova
# entrando no grupo errado sem ninguem decidir.
#
# Estas ja fixam uma versao de Glue no `runtime_scope`, entao ja sao puladas
# corretamente fora do Glue. Nao sao alvo desta fase; estao aqui para que a
# fronteira fique inteira num lugar so.
GLUE_VERSIONED = {"SF-ENV-002", "SF-ENV-003", "SF-ENV-004", "SF-GLUE-001"}

# Estas leem infraestrutura Glue do Terraform mas declaram `{glue: "*"}`, que
# hoje nao filtra nada -- sao o alvo da fase.
GLUE_INFRA = {"SF-GLUE-002", "SF-GLUE-003", "SF-GLUE-004", "SF-GLUE-005", "SF-GLUE-006"}

GLUE_DEPENDENT = GLUE_VERSIONED | GLUE_INFRA


def _rules() -> list[dict]:
    return load_catalog()


class TestAgnosticRulesSurviveWithoutGlue:
    """Regra de codigo, plano, armazenamento ou execucao nao pode sumir so
    porque o runtime nao e Glue."""

    # `ids` como lista pre-computada, NUNCA `ids=lambda`. Com `parametrize` sobre
    # lista vazia -- o que acontece se `load_catalog()` falhar -- o pytest 8.x
    # chama o callable sobre um sentinela interno e estoura DENTRO do coletor,
    # abortando a suite inteira em vez de pular. Mordeu na Fase 4.
    _AGNOSTICAS = [r for r in _rules() if r["id"] not in GLUE_DEPENDENT]

    @pytest.mark.parametrize("rule", _AGNOSTICAS, ids=[r["id"] for r in _AGNOSTICAS])
    def test_agnostic_rule_is_evaluated_on_a_non_glue_runtime(self, rule):
        assert in_scope(rule.get("runtime_scope") or {}, EMR_LIKE), (
            f"{rule['id']} some num runtime sem `glue`. Se ela depende mesmo de "
            f"Glue, acrescente-a a GLUE_INFRA ou GLUE_VERSIONED e justifique; se nao, "
            f"o `runtime_scope` esta errado."
        )


class TestGlueInfraRulesAreSkippedWithoutGlue:
    """A outra ponta. Sem isto, elas avaliam e nunca disparam -- silencio."""

    @pytest.mark.parametrize("rule_id", sorted(GLUE_DEPENDENT))
    def test_glue_infra_rule_is_out_of_scope_without_glue(self, rule_id):
        rule = next(r for r in _rules() if r["id"] == rule_id)
        assert not in_scope(rule.get("runtime_scope") or {}, EMR_LIKE), (
            f"{rule_id} e avaliada num runtime sem `glue`. Ela le `aws_glue_job` do "
            f"Terraform: vai avaliar e nunca disparar, e o operador nao fica sabendo "
            f"que esse eixo nao foi coberto."
        )


class TestNoRuleUsesTheAmbiguousWildcardAnymore:
    def test_glue_wildcard_is_gone_from_agnostic_rules(self):
        """`{glue: "*"}` so pode sobrar nas regras que sao mesmo de Glue."""
        offenders = sorted(
            r["id"]
            for r in _rules()
            if str(r.get("runtime_scope")) == "{'glue': '*'}" and r["id"] not in GLUE_DEPENDENT
        )
        assert not offenders, (
            f"regras agnosticas ainda com `{{glue: '*'}}`: {offenders}. "
            f"O curinga diz 'qualquer versao de Glue', nao 'qualquer runtime'."
        )
