"""Toda regra do catalogo precisa ser alcancavel, ou dizer que nao e.

O motor (`sparkforge/rules/engine.py`) reporta uma regra nao avaliada de duas
formas, e a diferenca e operacional, nao cosmetica:

    requires_facts -> "dispara assim que voce coletar o artefato"
    blocked_on     -> "nao dispara ate alguem construir o extrator"

Uma regra que exige um fact kind que NENHUM extrator emite, e que nao carrega
`blocked_on`, e reportada como `requires_facts`. Isso instrui o operador a
coletar um dado que nao esta a caminho, e ele espera por ele. Foi exatamente o
que aconteceu com as cinco regras SF-PQ-*, que dependem de `s3.prefix_summary`
e `plan.file_scan` -- dois kinds sem extrator nenhum -- e ficaram anos
parecendo apenas "sem dados coletados".

Estes testes fecham essa classe de drift na origem: uma regra nova que
referencie um kind inexistente falha aqui, em vez de virar uma espera
silenciosa meses depois.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.facts import (
    athena_workgroup,
    benchmark,
    call_graph,
    catalog_schema,
    cloudwatch,
    consumers,
    data_quality,
    emr_cluster,
    emr_serverless,
    event_log,
    funcval,
    fusion,
    glue_job_run,
    graph,
    iceberg_metadata,
    migration,
    pyspark_ast,
    runtime_detect,
    s3_listing,
    spark_plan,
    sql_literal,
    sql_metrics,
    terraform,
    workload,
)
from sparkforge.rules.loader import catalog_dir, load_catalog

EXTRACTORS = (
    athena_workgroup,
    benchmark,
    call_graph,
    catalog_schema,
    # Os TRES abaixo entraram atrasados, e a omissao tinha o custo que os
    # comentarios vizinhos ja descrevem: kind emitido por extrator que existe,
    # mas ausente desta lista, conta como orfao, e a primeira regra que o
    # consumir e forcada a `blocked_on` sobre um modulo que ja esta no
    # repositorio. `cloudwatch` e `glue_job_run` chegaram com o coletor de
    # historico de runs Glue; `sql_metrics`, com a metrica por no do plano.
    cloudwatch,
    consumers,
    # Esta lista e manual e duplicada em `tests/test_fixtures_kind_coverage.py`:
    # extrator novo entra nas DUAS, e esquecer uma nao quebra nada aqui.
    data_quality,
    # `emr_cluster` faltava aqui, e a omissao era invisivel enquanto a area
    # SF-EMR nao existia: sem ele, todo kind `emr.*` conta como orfao, e a
    # primeira regra de EMR seria obrigada a declarar `blocked_on` sobre um
    # extrator que ja esta no repositorio desde a Task 3 da Fase 5b.
    emr_cluster,
    # `emr_serverless` pela mesma razao, uma fase depois: sem ele aqui, os seis
    # kinds `emrs.*` contam como orfaos e as regras SF-EMRS da Task 5 seriam
    # obrigadas a declarar `blocked_on` sobre um extrator que ja esta no
    # repositorio desde a Task 2 desta fase.
    emr_serverless,
    event_log,
    # `funcval` entra nas DUAS listas no mesmo commit da Fase 4c: sem ele aqui,
    # os quatro kinds `funcval.*` contam como orfaos e as cinco regras SF-FVAL
    # da Task 6 seriam obrigadas a declarar `blocked_on` sobre um modulo que ja
    # esta no repositorio.
    funcval,
    fusion,
    glue_job_run,
    # `graph` pela mesma razao, uma fase depois: sem ele aqui, os seis kinds
    # `graph.*` contam como orfaos e as regras SF-GRAPH da Task 5 seriam
    # obrigadas a declarar `blocked_on` sobre um extrator que ja esta no
    # repositorio desde a Task 2 desta fase.
    graph,
    iceberg_metadata,
    # `migration` entra nas DUAS listas no mesmo commit da Task 7 desta fase,
    # mesma razao de `funcval`/`graph`: as Tasks 4-6 ja deixaram o extrator no
    # repositorio emitindo `mig.sdk_import`, `mig.emrfs_config` e `mig.ansi_risk`
    # (entre outros); sem ele aqui, esses tres kinds contam como orfaos e
    # SF-MIG-001 e SF-MIG-002 -- que NAO estao bloqueadas por falta de extrator,
    # so por `runtime_scope` confirmado -- seriam forcadas a `blocked_on` por um
    # motivo que nao e o delas. `test_fixtures_kind_coverage.py` cobra golden
    # para os OITO kinds de `EMITTED_KINDS` assim que o modulo entra la tambem;
    # essa fixture e trabalho da Task 9, nao desta.
    migration,
    pyspark_ast,
    runtime_detect,
    s3_listing,
    spark_plan,
    sql_literal,
    sql_metrics,
    terraform,
    # `workload` entra nas DUAS listas no mesmo commit da Task 6 do plano
    # `workload-fingerprint`: sem ele aqui, os tres kinds `workload.*`
    # (`workload.declared`, `workload.unresolved`, `workload.declared_analyzed`)
    # contam como orfaos, e a primeira regra que os consumir seria forcada a
    # `blocked_on` sobre um extrator que ja esta no repositorio desde
    # `sparkforge/facts/workload.py`.
    workload,
)

EMITTABLE: frozenset[str] = frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))

RULES = load_catalog(catalog_dir())
RULE_IDS = [r["id"] for r in RULES]


def _referenced_kinds(condition_group: dict) -> tuple[set[str], set[str]]:
    """(kinds exigidos presentes, kinds exigidos ausentes) de um bloco `when`."""
    present: set[str] = set()
    absent: set[str] = set()
    for group in ("all", "any"):
        for condition in condition_group.get(group) or []:
            if "fact" in condition:
                present.add(condition["fact"])
            if "absent" in condition:
                absent.add(condition["absent"])
    return present, absent


def test_o_registro_de_kinds_nao_esta_vazio() -> None:
    """Guarda contra o teste passar por nao ter carregado nada."""
    assert len(EMITTABLE) >= 50, sorted(EMITTABLE)
    assert len(RULES) >= 40, len(RULES)


@pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
def test_kind_exigido_tem_extrator_ou_a_regra_declara_blocked_on(rule: dict) -> None:
    required = set(rule.get("requires_facts") or [])
    present, _ = _referenced_kinds(rule.get("when") or {})
    orphans = sorted((required | present) - EMITTABLE)
    if not orphans:
        return
    assert rule.get("blocked_on"), (
        f"{rule['id']} exige {orphans}, que nenhum extrator emite, e nao declara "
        f"`blocked_on`. Sem isso o judge reporta 'requires_facts' e o operador "
        f"espera por um artefato que ninguem vai conseguir coletar. Ou construa o "
        f"extrator, ou marque a regra com `blocked_on: <capacidade-que-falta>`."
    )


@pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
def test_condicao_absent_nao_e_vacuamente_verdadeira(rule: dict) -> None:
    """`absent:` sobre um kind que ninguem emite dispara em QUALQUER entrada.

    Nao e silencio: e falso positivo sistematico. A regra acusa todo mundo,
    inclusive quem esta configurado corretamente, e acusar configuracao correta
    destroi a confianca no resto do relatorio.
    """
    _, absent = _referenced_kinds(rule.get("when") or {})
    orphans = sorted(absent - EMITTABLE)
    if not orphans:
        return
    assert rule.get("blocked_on"), (
        f"{rule['id']} testa `absent:` sobre {orphans}, que nenhum extrator emite. "
        f"A condicao e vacuamente verdadeira, entao a regra dispara em toda entrada. "
        f"Precisa de um fact sentinela que prove que o artefato foi analisado."
    )


# `blocked_on` sobre capacidade que NAO e kind de extrator.
#
# `test_blocked_on_obsoleto_e_mentira_silenciosa` so enxerga uma forma de
# capacidade faltando: kind sem extrator. O proprio docstring de
# `test_toda_regra_bloqueada_explica_o_bloqueio_em_comentario` ja registra que
# essa granularidade nao cobre tudo -- cita SF-ICE-004 (hoje desbloqueada) como
# exemplo hipotetico de bloqueio por ATRIBUTO que uma checagem de kind nao
# enxerga. SF-MIG-003 era o primeiro caso REAL disso e saiu daqui na Task 11:
# `knowledge/glue/runtime-matrix.yaml` ganhou a linha do Glue 6.0, confirmada
# contra `migrating-version-60.html` e `release-notes.html`, e a regra trocou
# `blocked_on` por `runtime_scope: {glue: ">=6.0"}` real. Allowlist vazia e o
# estado honesto: nenhum `blocked_on` sobrevive no catalogo hoje.
BLOQUEIO_SEM_KIND_ORFAO: dict[str, str] = {}


@pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
def test_blocked_on_obsoleto_e_mentira_silenciosa(rule: dict) -> None:
    """`blocked_on` que sobrevive ao extrator e pior que nao ter regra.

    O motor NAO avalia regra com `blocked_on` -- ele pula antes de olhar os
    facts (`engine.judge`). Entao um `blocked_on` esquecido depois de a
    capacidade existir nao e um detalhe de documentacao: a regra continua
    inerte para sempre, e `judge --show-skipped` diz ao operador que "ninguem
    construiu o extrator" enquanto o extrator esta ali, emitindo o fact, sendo
    ignorado. Falso negativo com explicacao errada colada em cima -- o operador
    nem sequer procura o problema.

    Foi exatamente o risco ao desbloquear SF-PQ-002/SF-PQ-004: sem este teste,
    construir o parser de plano e esquecer de tirar o `blocked_on` deixaria
    todo o trabalho invisivel, e nada falharia.

    Excecao: regra em `BLOQUEIO_SEM_KIND_ORFAO`, cujo bloqueio e sobre uma
    capacidade que este teste nao consegue enxergar (ver comentario acima).
    """
    if not rule.get("blocked_on"):
        return
    if rule["id"] in BLOQUEIO_SEM_KIND_ORFAO:
        return
    required = set(rule.get("requires_facts") or [])
    present, absent = _referenced_kinds(rule.get("when") or {})
    orphans = sorted((required | present | absent) - EMITTABLE)
    assert orphans, (
        f"{rule['id']} declara `blocked_on: {rule['blocked_on']}`, mas TODO kind que ela "
        f"exige ja tem extrator. O motor pula a regra antes de olhar os facts, entao ela "
        f"nunca vai disparar e o operador le 'falta construir o extrator' sobre uma "
        f"capacidade que existe. Remova o `blocked_on`."
    )


def test_bloqueio_sem_kind_orfao_nao_guarda_regra_que_ja_foi_corrigida() -> None:
    """Entrada obsoleta em `BLOQUEIO_SEM_KIND_ORFAO` esconde `blocked_on` morto.

    Mesmo padrao de `TestAbsentSemSameSubjectSeJustifica.test_a_allowlist_nao_
    guarda_regra_que_ja_foi_corrigida`: se a regra saiu do catalogo, perdeu
    `blocked_on`, ou passou a ter um kind genuinamente orfao, a entrada aqui
    vira permissao para o defeito que o teste acima existe para pegar.
    """
    by_id = {r["id"]: r for r in RULES}
    for rule_id in BLOQUEIO_SEM_KIND_ORFAO:
        rule = by_id.get(rule_id)
        assert rule is not None, (
            f"{rule_id} esta em BLOQUEIO_SEM_KIND_ORFAO e nao existe no catalogo."
        )
        assert rule.get("blocked_on"), f"{rule_id} perdeu `blocked_on`; remova da allowlist."


class TestAbsentSemSameSubjectSeJustifica:
    """`absent: X` sem `same_subject` e avaliado contra a lista INTEIRA de facts.

    Se a regra fala de uma entidade (um job, uma tabela, uma query), basta UMA
    entidade correta em qualquer lugar do conjunto analisado para o fact `X`
    existir globalmente, `absent` falhar, e a regra nao disparar para NINGUEM --
    mascarando todas as entidades genuinamente quebradas. E o pior erro que esta
    ferramenta pode cometer, porque le como "nenhum problema encontrado": o
    operador nao tem sinal nenhum de que houve subnotificacao.

    Aconteceu tres vezes: SF-GLUE-002 (um job com Spark UI escondia os outros
    tres), SF-ATH-003 (uma tabela com partition projection escondia todas as
    sobre-particionadas do mesmo dump) e SF-ATH-002 (uma query com filtro de
    particao escondia todas as que escaneiam a tabela inteira). Os tres foram
    corrigidos ancorando num fact por entidade com `same_subject: true`.

    Nem toda regra com `absent:` e esse defeito: existe pergunta legitimamente
    sobre o CONJUNTO. Mas ela tem que ser declarada aqui, com o motivo escrito,
    em vez de subnotificar em silencio -- mesmo padrao de
    `test_capability_parity.py::TestNoCliVerbIsAnUndeclaredMcpGap.ALLOWED_CLI_ONLY`.
    """

    ALLOWED_SET_LEVEL = {
        # A pergunta e "este CODIGO-BASE inicializa glueContext em algum lugar?".
        # `--enable-observability-metrics` esta no recurso Terraform e
        # `glueContext` esta no codigo Python: artefatos diferentes, subjects que
        # nunca coincidem (`tf_resource` vs `source_location`). Verificado: com
        # `same_subject: true` a regra deixa de disparar em qualquer entrada, pois
        # nenhum grupo contem as duas metades. Um fact `pyspark.glue_context_init`
        # em qualquer modulo do repositorio e de fato a resposta correta.
        "SF-ENV-003": (
            "correlaciona Terraform com codigo Python; a pergunta e sobre o "
            "codigo-base inteiro, e `same_subject` faria a regra nunca disparar."
        ),
        # A pergunta e sobre o DUMP inteiro: "este cluster tem alguma
        # reconfiguracao de instance group pedida e nao aplicada?". Um dump de
        # EMR descreve UM cluster, entao "o conjunto" e "o cluster" sao a mesma
        # coisa aqui, e a afirmacao da regra tambem e sobre o cluster inteiro
        # (`spark.dynamicAllocation.enabled` no nivel cluster, sem nenhum grupo
        # redefinindo). Verificado: os tres facts que a regra correlaciona tem
        # simbolos distintos por construcao -- `<cluster>/configuration/...`,
        # `<cluster>/managed-scaling` e `<cluster>/<grupo>` --, entao com
        # `same_subject: true` nenhum grupo conteria as tres condicoes e a regra
        # deixaria de disparar em qualquer entrada.
        "SF-EMR-003": (
            "o guarda `emr.configuration.unapplied` pergunta pela qualidade da "
            "evidencia do DUMP inteiro, e um dump descreve um cluster; "
            "`same_subject` faria a regra nunca disparar."
        ),
        # Mesma natureza de SF-EMR-003, e pelo mesmo motivo de forma: os tres
        # facts que a regra correlaciona tem simbolos distintos por construcao
        # -- `<cluster>` (`emr.cluster`), `<cluster>/<grupo>`
        # (`emr.instance_capacity`) e `<cluster>/yarn/am-node-label` (o fact
        # derivado) --, entao nenhum grupo de subject conteria as tres condicoes
        # e `same_subject: true` faria a regra nunca disparar. E a pergunta e
        # genuinamente sobre o conjunto: `yarn.node-labels.am.default-node-label-expression`
        # e lida pelo ResourceManager, que e UM por cluster, entao "o AM esta
        # preso?" nao tem versao por grupo. Verificado: com `same_subject` a
        # regra deixa de disparar em `instance_groups_spot_task`.
        "SF-EMR-008": (
            "`absent: emr.yarn.am_node_label` pergunta se o CLUSTER restringe "
            "onde o ApplicationMaster roda -- o ResourceManager e um so, entao "
            "nao ha versao por grupo dessa pergunta; `same_subject` faria a "
            "regra nunca disparar."
        ),
        # SF-GLUE-005 saiu desta lista ao ser desbloqueada. A isencao existia
        # para justificar `absent: spark.stage.spill` sem `same_subject`, e
        # desbloquear a regra mostrou que o `absent:` era errado por um motivo
        # mais profundo: o extrator emite `spark.stage.spill` para todo stage
        # analisado, com zero byte inclusive, entao a ausencia nunca significa
        # "nao houve spill" -- significa "nao analisei event log". A regra
        # passou a perguntar no nivel certo, com `spark.job.spill_summary`, e
        # com isso nao usa mais `absent:` nenhum.
    }

    @pytest.mark.parametrize("rule", RULES, ids=RULE_IDS)
    def test_regra_com_absent_ancora_por_entidade_ou_se_declara(self, rule: dict) -> None:
        when = rule.get("when") or {}
        _, absent = _referenced_kinds(when)
        if not absent or when.get("same_subject"):
            return
        assert rule["id"] in self.ALLOWED_SET_LEVEL, (
            f"{rule['id']} usa `absent: {sorted(absent)}` sem `same_subject: true`. "
            f"O motor avalia `absent:` contra a lista inteira de facts, entao UMA "
            f"entidade correta em qualquer lugar da analise faz a regra nao disparar "
            f"para NENHUMA das quebradas -- e o relatorio diz 'nenhum problema "
            f"encontrado'. Ancore num fact por entidade com `same_subject: true` "
            f"(ver SF-GLUE-002, SF-ATH-002, SF-ATH-003), ou, se a pergunta e mesmo "
            f"sobre o conjunto, declare a regra em ALLOWED_SET_LEVEL com o motivo."
        )

    def test_a_allowlist_nao_guarda_regra_que_ja_foi_corrigida(self) -> None:
        """Entrada obsoleta na allowlist e permissao silenciosa para o defeito
        voltar: se a regra ganhou `same_subject`, a justificativa nao vale mais."""
        by_id = {r["id"]: r for r in RULES}
        for rule_id in self.ALLOWED_SET_LEVEL:
            rule = by_id.get(rule_id)
            assert rule is not None, f"{rule_id} esta na allowlist e nao existe no catalogo."
            when = rule.get("when") or {}
            _, absent = _referenced_kinds(when)
            assert absent and not when.get("same_subject"), (
                f"{rule_id} nao precisa mais da isencao: ou perdeu o `absent:`, ou "
                f"ganhou `same_subject`. Remova a entrada de ALLOWED_SET_LEVEL."
            )


def test_toda_regra_bloqueada_explica_o_bloqueio_em_comentario() -> None:
    """`blocked_on` sozinho nao diz por que a capacidade falta.

    Nao da para verificar automaticamente que um `blocked_on` e legitimo: o
    bloqueio nem sempre e um kind faltando. SF-ICE-004 tem todos os kinds, e
    esta bloqueada por um ATRIBUTO (`written_before_sort_order`) que exigiria
    comparar dois instantes no tempo -- granularidade que uma checagem de kind
    nao enxerga. O que da para exigir e que alguem tenha escrito o motivo perto
    da regra, para que a proxima pessoa nao precise redescobrir por que ela
    nunca dispara.
    """
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        rules = _rules_of(path)
        # Area inteiramente bloqueada e explicada uma vez no cabecalho, nao
        # cinco vezes: repetir o mesmo paragrafo por regra e ruido, e o teste
        # de cabecalho abaixo ja cobre esse caso.
        if rules and all(r.get("blocked_on") for r in rules):
            continue
        for rule in rules:
            blocker = rule.get("blocked_on")
            if not blocker:
                continue
            before = text.split(f"- id: {rule['id']}")[0]
            preamble = before.rsplit("\n\n", 1)[-1]
            assert "#" in preamble, (
                f"{rule['id']} declara `blocked_on: {blocker}` sem nenhum comentario "
                f"logo acima explicando qual capacidade falta e por que. Sem isso a "
                f"regra vira ruido permanente: ninguem sabe se ainda faz sentido."
            )


def test_area_inteiramente_inerte_avisa_no_cabecalho() -> None:
    """Quem abre `parquet.yaml` e ve que nada dispara merece saber no topo."""
    for path in sorted(Path(catalog_dir()).glob("*.yaml")):
        rules = _rules_of(path)
        if not rules or not all(r.get("blocked_on") for r in rules):
            continue
        header = path.read_text(encoding="utf-8").split("rules:")[0]
        assert "blocked_on" in header, (
            f"{path.name}: todas as {len(rules)} regras estao bloqueadas, mas o "
            f"cabecalho nao explica que a area inteira esta inerte hoje."
        )


def _rules_of(path: Path) -> list[dict]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("rules") or []
