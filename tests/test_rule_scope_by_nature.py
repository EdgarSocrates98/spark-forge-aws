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

from sparkforge.facts.runtime_detect import GLUE_MATRIX, detect_runtime
from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope

# Runtime EMR-like: Spark e Iceberg detectados, NENHUMA chave `glue`.
# E o cenario que a Fase 5 existe para servir.
EMR_LIKE = {"spark": "3.5.1", "python": "3.11", "iceberg": "1.7.1"}


def _detected(**sources: dict[str, str]) -> dict[str, str]:
    """Runtime COMO O PRODUTO PRODUZ, nao como o teste imagina.

    `EMR_LIKE` acima e escrito a mao e traz `iceberg: "1.7.1"` fixo. Isso e
    otimista de duas formas: omite as chaves que `RuntimeContext.to_dict()`
    sempre emite (`glue`, `athena`) e, sobretudo, presume Iceberg detectado.
    Iceberg NAO e observado por extrator nenhum -- `runtime_detect.py` so o
    preenche derivando de `GLUE_MATRIX` (logo, so quando ha Glue) ou de uma
    flag `--iceberg` digitada a mao. Por causa desse otimismo, o furo que a
    Task 3b da Fase 5a consertou -- `{iceberg: ">=1.0.0"}` apagando a area
    SF-ICE inteira em EMR -- passou por baixo da suite inteira.
    Passar por `detect_runtime` e nao por literal fecha essa classe de furo:
    o teste nao consegue mais inventar um campo que a deteccao nunca produz.
    """
    context, _facts = detect_runtime(sources)
    return context.to_dict()


# Runtime EMR pobre: um job EMR real em que so o event log observou Spark.
# Produz `{'glue': '', 'spark': '3.5.1', 'python': '', 'iceberg': '',
# 'athena': '', ...}` -- e o caso que EMR_LIKE nunca exercitou.
EMR_MINIMAL = _detected(event_log={"spark_version": "3.5.1"})

# Os dois runtimes sem Glue, para as duas pontas abaixo. Nomeados porque o `id`
# do parametrize precisa dizer QUAL cenario falhou.
NON_GLUE_RUNTIMES = [("emr-rico", EMR_LIKE), ("emr-pobre", EMR_MINIMAL)]
NON_GLUE_IDS = [nome for nome, _ in NON_GLUE_RUNTIMES]

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

    @pytest.mark.parametrize("nome,runtime", NON_GLUE_RUNTIMES, ids=NON_GLUE_IDS)
    @pytest.mark.parametrize("rule", _AGNOSTICAS, ids=[r["id"] for r in _AGNOSTICAS])
    def test_agnostic_rule_is_evaluated_on_a_non_glue_runtime(self, rule, nome, runtime):
        assert in_scope(rule.get("runtime_scope") or {}, runtime), (
            f"{rule['id']} some no runtime `{nome}` ({runtime}), que nao tem `glue`. "
            f"Se ela depende mesmo de Glue, acrescente-a a GLUE_INFRA ou GLUE_VERSIONED "
            f"e justifique; se nao, o `runtime_scope` esta errado."
        )


class TestGlueInfraRulesAreSkippedWithoutGlue:
    """A outra ponta. Sem isto, elas avaliam e nunca disparam -- silencio."""

    @pytest.mark.parametrize("nome,runtime", NON_GLUE_RUNTIMES, ids=NON_GLUE_IDS)
    @pytest.mark.parametrize("rule_id", sorted(GLUE_DEPENDENT))
    def test_glue_infra_rule_is_out_of_scope_without_glue(self, rule_id, nome, runtime):
        rule = next(r for r in _rules() if r["id"] == rule_id)
        assert not in_scope(rule.get("runtime_scope") or {}, runtime), (
            f"{rule_id} e avaliada no runtime `{nome}` ({runtime}), que nao tem `glue`. "
            f"Ela le `aws_glue_job` do Terraform: vai avaliar e nunca disparar, e o "
            f"operador nao fica sabendo que esse eixo nao foi coberto."
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


# --------------------------------------------------------------------------- #
# Invariante de area: nenhuma area do catalogo pode desaparecer INTEIRA.
#
# As classes acima raciocinam regra a regra, a partir de listas escritas a mao
# (GLUE_INFRA, GLUE_VERSIONED). Foi por isso que a Task 3b passou despercebida:
# SF-ICE-001..005 nao estavam em nenhuma lista, entao caiam em _AGNOSTICAS -- e
# `EMR_LIKE`, com `iceberg: "1.7.1"` escrito a mao, as aprovava. O furo nao
# estava na regra individual, estava no AGREGADO: cinco regras somem juntas e o
# relatorio inteiro perde um eixo sem dizer nada.
#
# Esta secao mede o agregado e deriva as areas DO CATALOGO, nunca de uma lista.
# Uma area nova que alguem acrescente amanha entra aqui por construcao: ou ela
# sobrevive em todo runtime conhecido, ou alguem tem que declarar e justificar a
# excecao abaixo. Os runtimes tambem sao derivados -- de `GLUE_MATRIX`, entao
# uma versao de Glue nova tambem entra sozinha.
# --------------------------------------------------------------------------- #


def _area(rule_id: str) -> str:
    return "-".join(rule_id.split("-")[:2])


def _catalog_areas() -> set[str]:
    return {_area(rule["id"]) for rule in _rules()}


def _vanished_areas(runtime: dict[str, str]) -> set[str]:
    """Areas em que NENHUMA regra e avaliada -- silencio total sobre um eixo."""
    evaluated: dict[str, int] = {}
    for rule in _rules():
        area = _area(rule["id"])
        evaluated.setdefault(area, 0)
        if in_scope(rule.get("runtime_scope") or {}, runtime):
            evaluated[area] += 1
    return {area for area, count in evaluated.items() if count == 0}


# Runtimes conhecidos, todos vindos de `detect_runtime`. Os de Glue saem de
# `GLUE_MATRIX` para que uma versao nova na matriz seja coberta sem editar
# este arquivo.
ALL_RUNTIMES: list[tuple[str, dict[str, str]]] = [
    (f"glue-{version}", _detected(terraform={"glue_version": version}))
    for version in sorted(GLUE_MATRIX)
] + [("emr-rico", EMR_LIKE), ("emr-pobre", EMR_MINIMAL)]
ALL_RUNTIME_IDS = [nome for nome, _ in ALL_RUNTIMES]

# UNICA excecao ao invariante, com a condicao exata em que vale.
#
# SF-GLUE deve mesmo sumir quando nao ha Glue, e sumir e o OBJETIVO da Fase 5a:
# aquelas regras leem `aws_glue_job` do Terraform, entao num runtime EMR nao ha
# infraestrutura Glue para revisar. Antes da fase elas avaliavam em silencio e
# nunca disparavam -- indistinguivel de "revisei e esta tudo bem". Agora aparecem
# como PULADAS, com motivo, e o operador sabe que o eixo nao foi coberto.
#
# A diferenca para SF-ICE, que motivou a Task 3b: tabela Iceberg existe em EMR.
# SF-ICE sumia porque ninguem DETECTA a versao de Iceberg fora do Glue, nao
# porque a area nao se aplicava. Isso e falso negativo, nao escopo.
#
# Criterio para acrescentar uma entrada aqui: a area tem que ser sobre a
# EXISTENCIA de uma infraestrutura que o runtime comprovadamente nao tem. Nunca
# sobre uma versao que simplesmente nao foi detectada -- para isso o gate certo
# e `requires_facts`, e o `runtime_scope` deve ser `{}`.
AREA_MAY_VANISH_WHEN: dict[str, tuple] = {
    "SF-GLUE": (lambda runtime: not runtime.get("glue"), "runtime sem `glue` detectado"),
}


class TestNoCatalogAreaVanishesEntirely:
    @pytest.mark.parametrize("nome,runtime", ALL_RUNTIMES, ids=ALL_RUNTIME_IDS)
    def test_every_area_keeps_at_least_one_rule_in_scope(self, nome, runtime):
        vanished = _vanished_areas(runtime)
        allowed = {
            area
            for area, (condition, _why) in AREA_MAY_VANISH_WHEN.items()
            if condition(runtime)
        }
        offenders = sorted(vanished - allowed)
        assert not offenders, (
            f"no runtime `{nome}` ({runtime}) as areas {offenders} desapareceram "
            f"INTEIRAS: nenhuma regra delas e avaliada.\n"
            f"Para um agente autonomo isso le como 'nada encontrado nesse eixo', que e "
            f"o falso negativo que a Fase 5a existe para eliminar.\n"
            f"Quase sempre a causa e um `runtime_scope` de versao sobre um componente "
            f"que NENHUM extrator detecta -- foi o caso de `{{iceberg: '>=1.0.0'}}` em "
            f"SF-ICE-001..005. Se o gate real e a natureza do artefato analisado, use "
            f"`runtime_scope: {{}}` e deixe `requires_facts` gatear.\n"
            f"Se a area depende MESMO de infraestrutura ausente neste runtime, declare "
            f"a excecao em AREA_MAY_VANISH_WHEN com a condicao e a justificativa."
        )

    @pytest.mark.parametrize("nome,runtime", ALL_RUNTIMES, ids=ALL_RUNTIME_IDS)
    def test_declared_exceptions_really_vanish_when_their_condition_holds(self, nome, runtime):
        """A outra ponta: excecao que nunca se realiza e letra morta pre-aprovando
        um sumico futuro que ninguem examinou."""
        vanished = _vanished_areas(runtime)
        for area, (condition, why) in sorted(AREA_MAY_VANISH_WHEN.items()):
            if not condition(runtime):
                continue
            assert area in vanished, (
                f"AREA_MAY_VANISH_WHEN['{area}'] diz que a area pode sumir em "
                f"'{why}', e o runtime `{nome}` ({runtime}) satisfaz essa condicao -- "
                f"mas a area continua sendo avaliada. Ou a condicao esta errada, ou "
                f"alguma regra de {area} deixou de exigir a infraestrutura que "
                f"justificava a excecao. Nos dois casos, a excecao precisa ser "
                f"reexaminada, nao mantida."
            )

    def test_exception_map_names_only_areas_that_exist(self):
        unknown = sorted(set(AREA_MAY_VANISH_WHEN) - _catalog_areas())
        assert not unknown, (
            f"AREA_MAY_VANISH_WHEN cita areas inexistentes: {unknown}. Area renomeada "
            f"deixa a excecao aberta sem cobrir nada."
        )
