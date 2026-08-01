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


# Quem pode usar curinga, por chave de `runtime_scope`. Uma entrada `{X: "*"}`
# so e legitima quando a regra depende MESMO da infraestrutura X e a presenca de
# X e detectada por algum extrator -- porque desde a Fase 5a o curinga exige a
# chave presente, e o que nao e detectado vira regra apagada em silencio.
#
# Mapa e nao lista solta: a pergunta "quem pode usar curinga" tem uma resposta
# por chave, e um curinga numa chave sem entrada aqui e um curinga que ninguem
# decidiu. `athena` NAO esta aqui de proposito -- `RuntimeContext.athena` so e
# preenchido pela flag `--athena` da CLI, entao `{athena: "*"}` apagaria a area
# SF-ATH inteira em todo runtime real; aquelas 5 sao gateadas por
# `requires_facts` e tem `runtime_scope: {}`.
WILDCARD_ALLOWED_BY_KEY: dict[str, set[str]] = {"glue": GLUE_INFRA}


class TestNoRuleUsesTheAmbiguousWildcardAnymore:
    """A checagem e sobre QUALQUER chave com `"*"`, nao sobre a string literal
    `{'glue': '*'}` que a versao anterior deste teste procurava. Foi essa
    literalidade que deixou `{athena: "*"}` -- a mesma confusao de camada, em
    outra chave -- passar despercebida ate a Fase 5a. Uma familia nova de
    curinga que alguem acrescente amanha cai aqui por construcao."""

    def test_no_rule_declares_a_wildcard_outside_its_declared_allowlist(self):
        offenders: list[str] = []
        for rule in _rules():
            for key, spec in (rule.get("runtime_scope") or {}).items():
                if str(spec).strip() != "*":
                    continue
                if rule["id"] not in WILDCARD_ALLOWED_BY_KEY.get(key, set()):
                    offenders.append(f"{rule['id']} -> {{{key}: '*'}}")

        assert not offenders, (
            f"curinga de `runtime_scope` sem dependencia declarada: {sorted(offenders)}.\n"
            f"`{{X: '*'}}` diz 'qualquer VERSAO de X', nao 'qualquer runtime': desde a "
            f"Fase 5a ele exige que a chave X esteja PRESENTE no runtime detectado.\n"
            f"Escolha uma das tres:\n"
            f"  1. a regra depende mesmo de X e X e detectado -> acrescente o id ao "
            f"conjunto de WILDCARD_ALLOWED_BY_KEY['{{X}}'] (criando a entrada se for "
            f"chave nova) e justifique no comentario;\n"
            f"  2. a regra so precisa de uma versao minima -> troque por um range "
            f"de verdade, ex. `{{spark: '>=3.0'}}`;\n"
            f"  3. o curinga era etiqueta de servico e o gate real e a natureza do "
            f"artefato -> use `runtime_scope: {{}}` e deixe `requires_facts` gatear, "
            f"como SF-ATH-001..005.\n"
            f"Chave que NAO e detectada por nenhum extrator nunca pode entrar em (1): "
            f"apaga a regra em todo runtime, que e o silencio que a Fase 5a acabou."
        )

    def test_the_allowlist_itself_names_only_rules_that_exist(self):
        """Guarda contra a allowlist virar letra morta: id renomeado ou removido
        deixaria uma excecao aberta que ninguem mais usa, e o teste acima
        passaria a nao cobrar nada naquela chave."""
        known = {r["id"] for r in _rules()}
        for key, allowed in WILDCARD_ALLOWED_BY_KEY.items():
            missing = sorted(allowed - known)
            assert not missing, f"WILDCARD_ALLOWED_BY_KEY['{key}'] cita ids inexistentes: {missing}"

    def test_every_allowlisted_rule_actually_uses_the_wildcard(self):
        """A outra ponta: se a regra deixou de usar curinga, a excecao tem que
        sair da allowlist -- senao ela fica pre-aprovando um curinga futuro que
        ninguem examinou."""
        scopes = {r["id"]: (r.get("runtime_scope") or {}) for r in _rules()}
        for key, allowed in WILDCARD_ALLOWED_BY_KEY.items():
            stale = sorted(
                rule_id
                for rule_id in allowed
                if str(scopes.get(rule_id, {}).get(key, "")).strip() != "*"
            )
            assert not stale, (
                f"WILDCARD_ALLOWED_BY_KEY['{key}'] ainda libera curinga para {stale}, "
                f"mas essas regras nao declaram mais `{{{key}: '*'}}`. Remova-as da "
                f"allowlist."
            )
