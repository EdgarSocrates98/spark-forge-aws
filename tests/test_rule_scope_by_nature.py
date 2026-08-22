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

from sparkforge.adapters._core import build_runtime_context
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

# Runtime VAZIO -- o padrao real da CLI, nao um cenario exotico.
# `sparkforge judge` sem `--glue/--spark/--python/--iceberg/--athena` chama
# `build_runtime_context()` sem argumento nenhum, e o resultado e
# `{'glue': '', 'spark': '', 'python': '', 'iceberg': '', 'athena': '', ...}`:
# TODA chave presente e TODA chave vazia, entao `in_scope` falha fechada em
# qualquer `runtime_scope` nao-vazio.
#
# E o caso que os dois EMR acima nao pegam, porque os dois trazem `spark`
# preenchido. Foi por baixo dessa folga que a Task 3c passou: a Task 2 moveu 19
# regras de `{glue: "*"}` para `{spark: ">=3.0"}`, os testes viram `spark`
# detectado nos dois runtimes e aprovaram -- enquanto `sparkforge judge` sobre
# um `.py`, um plano ou um event log apagava SF-PY, SF-PQ, SF-PLAN, SF-UI e
# SF-CG inteiras. Analise estatica nao precisa de Spark detectado para valer.
#
# Passa por `build_runtime_context` e nao por `detect_runtime({})` de proposito:
# e o ponto de entrada que a CLI usa, entao um dia em que ele passe a preencher
# defaults, este teste muda de comportamento junto -- que e o que se quer.
EMPTY_RUNTIME = build_runtime_context().to_dict()

# Os runtimes sem Glue, para as duas pontas abaixo. Nomeados porque o `id`
# do parametrize precisa dizer QUAL cenario falhou.
NON_GLUE_RUNTIMES = [
    ("emr-rico", EMR_LIKE),
    ("emr-pobre", EMR_MINIMAL),
    ("vazio-cli", EMPTY_RUNTIME),
]
NON_GLUE_IDS = [nome for nome, _ in NON_GLUE_RUNTIMES]

# As que dependem de Glue. Listas explicitas porque sao curtas, fechadas, e sao
# a fronteira exata desta fase -- derivar do disco esconderia uma regra nova
# entrando no grupo errado sem ninguem decidir.
#
# Estas ja fixam uma versao de Glue no `runtime_scope`, entao ja sao puladas
# corretamente fora do Glue. Nao sao alvo desta fase; estao aqui para que a
# fronteira fique inteira num lugar so.
#
# SF-ENV-004 SAIU deste conjunto na Task 3c. Ela declarava `{glue: "<4.0"}` mas
# a condicao do `when` e `attrs.spark_minor < 3.2` -- puramente Spark. Num EMR
# com Spark 3.1.1 o guarda a apagava exatamente onde ela e mais necessaria.
# Hoje tem `runtime_scope: {}` e o gate e a propria condicao, que so pode ser
# verdadeira quando a versao FOI resolvida. Ver o comentario dela em
# `rules/catalog/env.yaml`.
#
# SF-MIG-001 e SF-MIG-002 ENTRARAM na Task 7 desta fase, com
# `runtime_scope: {glue: ">=5.0"}`. Nao sao GLUE_INFRA: elas nao leem
# `aws_glue_job` do Terraform, leem sinal de codigo (`mig.sdk_import`,
# `mig.emrfs_config`). O que as torna dependentes de Glue e uma fronteira de
# VERSAO -- o SDK v1 sai do classpath e o EMRFS vira S3A exatamente ao cruzar
# para o Glue 5.0, fronteira ja confirmada em `knowledge/glue/runtime-matrix.yaml`
# -- exatamente a mesma natureza que justifica SF-ENV-002/003 e SF-GLUE-001
# aqui. Ver o comentario acima das regras em `rules/catalog/glue-migration.yaml`.
#
# SF-MIG-003 ENTROU na Task 11 desta fase, com `runtime_scope: {glue: ">=6.0"}`
# real (era `blocked_on` ate `knowledge/glue/runtime-matrix.yaml` ganhar a
# linha do Glue 6.0). Mesma natureza de SF-MIG-001/002: le `mig.ansi_risk`, um
# sinal de codigo, e a fronteira e a versao em que o Spark liga ANSI mode por
# default (confirmado contra migrating-version-60.html), nao a existencia de
# infraestrutura Glue.
GLUE_VERSIONED = {
    "SF-ENV-002",
    "SF-ENV-003",
    "SF-GLUE-001",
    "SF-MIG-001",
    "SF-MIG-002",
    "SF-MIG-003",
}

# Estas leem infraestrutura Glue do Terraform mas declaram `{glue: "*"}`, que
# hoje nao filtra nada -- sao o alvo da fase.
GLUE_INFRA = {"SF-GLUE-002", "SF-GLUE-003", "SF-GLUE-004", "SF-GLUE-005", "SF-GLUE-006"}

GLUE_DEPENDENT = GLUE_VERSIONED | GLUE_INFRA

def _minor(spark: str) -> tuple[int, int]:
    """(major, minor) da versao de Spark, ignorando patch e sufixo de vendor.

    `3.3.2-amzn-0.1` e `4.1.1` chegam aqui como vem do runtime detectado, entao
    o parser tem que aguentar o sufixo -- comparar string crua poria
    `3.10` antes de `3.9` e a faixa erraria em silencio.
    """
    partes = spark.split("-")[0].split(".")
    return (int(partes[0]), int(partes[1]))


# Guardadas por versao de SPARK, e nao por Glue. Grupo proprio porque a razao e
# outra: nao e "esta infraestrutura nao existe neste runtime", e sim "a
# afirmacao desta regra so e verdadeira nesta FAIXA de versao".
#
# SF-GRAPH-002 diz "nao ha artefato de GraphFrames publicado para este Spark", e
# isso e verdade para Spark 3.3.x e falso para 3.2 e para 3.4 -- os dois tem jar
# publicado. Sem `spark` detectado a afirmacao e impossivel de fazer, entao
# regra PULADA com `reason: runtime_scope` e a resposta certa, e nao perda de
# cobertura: a §D-4 do spec da Fase 6a registra a decisao, e ela e o inverso
# exato da de `emr-infra.yaml:8-19`, onde a release vinha do proprio fact.
#
# A area SF-GRAPH NAO some com isso: SF-GRAPH-001, -003 e -004 declaram
# `runtime_scope: {}`, e sao elas que sustentam o invariante de area la embaixo.
# SF-SPARK4-001/002/003 ENTRARAM aqui com a area SF-SPARK4. Sao guardadas por
# versao de SPARK e nao de Glue porque quem mudou o produto foi o APACHE, nao a
# AWS: o Spark 4.0 renomeou `spark.sql.legacy.parquet.*` e removeu as APIs de
# pandas-on-Spark, e o 4.1 subiu o piso do PyArrow para 15.0.0. As tres
# afirmacoes valem igual num EMR com Spark 4, num EMR Serverless e num cluster
# on-prem -- guardar por Glue amarraria a afirmacao a um empacotamento que nao
# a produziu e apagaria a area em todo runtime nao-Glue com Spark 4, que e o
# falso negativo que a Fase 5a acabou.
#
# Contraste com GLUE_VERSIONED logo acima: SF-MIG-001/002 tambem leem sinal de
# codigo, mas as fronteiras delas (classpath sem SDK v1, EMRFS virando S3A) sao
# do empacotamento da AWS. Mesma forma, origem diferente.
#
# A fronteira NAO e a mesma para as tres: -001 e -002 declaram `>=4.0.0` e -003
# declara `>=4.1.0`, porque o piso de 15.0.0 e do 4.1 (no 4.0 era 11.0.0).
# Acusar `pyarrow==11.0.0` num runtime 4.0 seria acusar a versao que a
# documentacao daquele release declara suficiente.
#
# MAPA e nao conjunto, desde que SF-SPARK4 entrou. A faixa e propriedade DA
# REGRA, nao do grupo: enquanto SF-GRAPH-002 era a unica aqui, a faixa dela
# (`3.3.x`) ficava escrita como constante da classe de teste, e qualquer regra
# nova que entrasse no grupo era medida contra a faixa do GraphFrames. Cada
# entrada declara agora a propria faixa, como predicado sobre a versao de Spark,
# mais as PERTURBACOES DE LIMITE que provam que cada ponta do `runtime_scope`
# esta sustentando peso.
SPARK_VERSIONED: dict[str, tuple] = {
    "SF-GRAPH-002": (
        lambda spark: _minor(spark) == (3, 3),
        # Ambas as pontas sustentam peso: sem o `<3.4` a regra acusaria Glue
        # 5.0/5.1; sem o `>=3.3` acusaria Glue 3.0.
        [("3.3.2-amzn-0.1", True), ("3.2.1-amzn-0", False), ("3.4.0-amzn-0", False)],
    ),
    "SF-SPARK4-001": (
        lambda spark: _minor(spark) >= (4, 0),
        [("4.0.0", True), ("4.1.1-amzn-0", True), ("3.5.6", False)],
    ),
    "SF-SPARK4-002": (
        lambda spark: _minor(spark) >= (4, 0),
        [("4.0.0", True), ("4.1.1-amzn-0", True), ("3.5.6", False)],
    ),
    # A ponta de baixo desta e 4.1 e nao 4.0, e a diferenca e o limiar da propria
    # regra: o piso de 15.0.0 do PyArrow e do Spark 4.1 -- no 4.0 o piso era
    # 11.0.0. Um `>=4.0.0` aqui acusaria `pyarrow==11.0.0` num runtime 4.0, onde
    # a documentacao daquele release declara essa versao suficiente.
    "SF-SPARK4-003": (
        lambda spark: _minor(spark) >= (4, 1),
        [("4.1.0", True), ("4.1.1-amzn-0", True), ("4.0.0", False), ("3.5.6", False)],
    ),
}

VERSION_DEPENDENT = GLUE_DEPENDENT | set(SPARK_VERSIONED)


def _rules() -> list[dict]:
    return load_catalog()


class TestAgnosticRulesSurviveWithoutGlue:
    """Regra de codigo, plano, armazenamento ou execucao nao pode sumir so
    porque o runtime nao e Glue."""

    # `ids` como lista pre-computada, NUNCA `ids=lambda`. Com `parametrize` sobre
    # lista vazia -- o que acontece se `load_catalog()` falhar -- o pytest 8.x
    # chama o callable sobre um sentinela interno e estoura DENTRO do coletor,
    # abortando a suite inteira em vez de pular. Mordeu na Fase 4.
    _AGNOSTICAS = [r for r in _rules() if r["id"] not in VERSION_DEPENDENT]

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


class TestSparkVersionedRulesFireOnlyInsideTheirBand:
    """A outra ponta de `SPARK_VERSIONED`, e ela mede as DUAS direcoes.

    Um `runtime_scope` de faixa erra em dois sentidos, e so um deles doi rapido:
    faixa larga demais faz a regra acusar runtime onde a afirmacao e falsa;
    faixa estreita demais a apaga em silencio onde ela e verdadeira. As nove
    celulas sem jar sao Glue 4.0 e EMR 6.8.0-6.11.1, e o discriminador e o minor
    de Spark -- por isso o teste caminha a matriz de Glue inteira em vez de
    conferir uma versao so.
    """

    @pytest.mark.parametrize("rule_id", sorted(SPARK_VERSIONED))
    @pytest.mark.parametrize("glue_version", sorted(GLUE_MATRIX))
    def test_the_band_matches_exactly_the_declared_spark_versions(
        self, rule_id, glue_version
    ):
        rule = next(r for r in _rules() if r["id"] == rule_id)
        banda, _probes = SPARK_VERSIONED[rule_id]
        runtime = _detected(terraform={"glue_version": glue_version})
        esperado = banda(GLUE_MATRIX[glue_version]["spark"])
        assert in_scope(rule.get("runtime_scope") or {}, runtime) is esperado, (
            f"{rule_id} em Glue {glue_version} (Spark "
            f"{GLUE_MATRIX[glue_version]['spark']}): esperado in_scope={esperado}. "
            f"A faixa declarada em SPARK_VERSIONED e o `runtime_scope` do "
            f"catalogo discordam -- um dos dois esta errado, e o catalogo nao e "
            f"automaticamente o certo."
        )

    @pytest.mark.parametrize("nome,runtime", NON_GLUE_RUNTIMES, ids=NON_GLUE_IDS)
    @pytest.mark.parametrize("rule_id", sorted(SPARK_VERSIONED))
    def test_it_is_skipped_when_spark_is_unknown_or_outside_the_band(
        self, rule_id, nome, runtime
    ):
        rule = next(r for r in _rules() if r["id"] == rule_id)
        assert not in_scope(rule.get("runtime_scope") or {}, runtime), (
            f"{rule_id} e avaliada no runtime `{nome}` ({runtime}). Ela afirma que "
            f"nao ha artefato publicado para ESTE Spark: sem Spark detectado a "
            f"afirmacao e impossivel, e com Spark fora de 3.3.x ela e falsa."
        )

    @pytest.mark.parametrize("rule_id", sorted(SPARK_VERSIONED))
    def test_every_end_of_the_band_is_load_bearing(self, rule_id):
        """Perturbacao de limite, uma versao de cada lado de cada ponta.

        `in_scope` conjuga a lista de specs, entao um spec que sobre ou que
        falte passa despercebido na leitura do catalogo: a faixa continua com
        cara de faixa. As probes de cada regra vivem em `SPARK_VERSIONED`, ao
        lado da faixa que elas provam, porque perturbacao de limite so tem
        sentido contra o limite DAQUELA regra."""
        scope = next(r for r in _rules() if r["id"] == rule_id)["runtime_scope"]
        _banda, probes = SPARK_VERSIONED[rule_id]
        for spark, esperado in probes:
            assert in_scope(scope, {"spark": spark}) is esperado, (
                f"{rule_id} com Spark {spark}: esperado in_scope={esperado}. "
                f"Uma ponta do `runtime_scope` deixou de sustentar peso."
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


# Runtimes conhecidos. Os de Glue saem de `GLUE_MATRIX` para que uma versao
# nova na matriz seja coberta sem editar este arquivo; os sem Glue saem de
# `NON_GLUE_RUNTIMES`, entao o runtime VAZIO -- o padrao real de `sparkforge
# judge` -- e exercitado aqui pela mesma definicao usada la em cima, sem
# segunda copia que possa divergir.
ALL_RUNTIMES: list[tuple[str, dict[str, str]]] = [
    (f"glue-{version}", _detected(terraform={"glue_version": version}))
    for version in sorted(GLUE_MATRIX)
] + NON_GLUE_RUNTIMES
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
    # SF-MIG SAIU DAQUI quando SF-MIG-004 entrou no catalogo.
    #
    # A excecao existia porque as tres regras de entao eram todas
    # GLUE_VERSIONED (001/002 `>=5.0`, 003 `>=6.0`): num runtime sem Glue, ou
    # com Glue abaixo de 5.0, nenhuma delas tinha fronteira cruzada para
    # acusar, e a area sumia inteira por versao.
    #
    # SF-MIG-004 afirma outra coisa -- que o diff de Terraform MUDOU
    # `glue_version` -- e isso vale para 3.0->4.0 tanto quanto para 5.1->6.0,
    # sem depender de runtime detectado. Ela declara `runtime_scope: {}` e e
    # gateada por `requires_facts: [tf.attribute]`, que e exatamente o criterio
    # escrito no comentario acima deste mapa. Consequencia: num runtime EMR a
    # area SF-MIG passa a ser AVALIADA e simplesmente nao casa, por falta do
    # fact -- estado diferente de "area inteira pulada", e o estado certo.
    # Manter a excecao aqui seria letra morta pre-aprovando um sumico que ja
    # nao acontece, que e o que
    # `test_declared_exceptions_really_vanish_when_their_condition_holds`
    # existe para impedir.
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


class TestNoRuleVanishesFromBothSides:
    """Regra que nao dispara TEM que aparecer em `skipped`, com motivo.

    `judge --show-skipped` e o mecanismo de ausencia explicada, e ele funciona --
    mas so ve regra que foi barrada por `runtime_scope`, `blocked_on` ou
    `requires_facts`. Uma regra cujo `requires_facts` e satisfeito por um
    sentinela generico passa pela barreira, avalia o `when`, da falso, e some dos
    dois lados. Para quem le o relatorio isso e indistinguivel de "esta tudo bem".
    """

    def test_a_glue_rule_without_glue_job_terraform_is_reported(self, tmp_path):
        from sparkforge.facts.terraform import extract_terraform_tree
        from sparkforge.rules.engine import judge

        (tmp_path / "main.tf").write_text(
            'resource "aws_emr_cluster" "x" {\n  release_label = "emr-7.5.0"\n}\n',
            encoding="utf-8",
        )
        facts = extract_terraform_tree(tmp_path, repo_root=tmp_path)
        runtime = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}
        findings, skipped = judge(facts, load_catalog(), runtime, return_skipped=True)

        visiveis = {f.rule_id for f in findings} | {s["rule_id"] for s in skipped}
        sumidas = sorted(GLUE_INFRA - visiveis)
        assert not sumidas, (
            f"{sumidas} nao aparecem nem em findings nem em skipped. O operador nao "
            f"fica sabendo que o eixo de infraestrutura Glue nao foi coberto."
        )
