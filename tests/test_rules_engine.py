from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge

GLUE_50 = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def rule(**over):
    base = {
        "id": "SF-T-001",
        "category": "test",
        "title": "titulo",
        "requires_facts": ["k"],
        "when": {"all": [{"fact": "k", "where": {"attrs.flag": True}}]},
        "status": "structural",
        "severity_default": "P2",
        "runtime_scope": {"glue": "*"},
        "sources": [{"origin": "field-heuristic"}],
        "catalog_version": 1,
        "explanation": "porque custa",
        "proposed_change": ["mudar"],
        "risks": ["risco"],
        "validation": ["contagem total"],
        "rollback": ["reverter"],
    }
    base.update(over)
    return base


def fact(**over):
    base = {
        "kind": "k",
        "subject": {"type": "source_location", "file": "a.py", "line": 1},
        "measures": {},
        "attrs": {"flag": True},
    }
    base.update(over)
    return Fact(**base)


class TestWhereMatching:
    def test_matching_where_produces_finding(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert [f.rule_id for f in found] == ["SF-T-001"]

    def test_non_matching_where_produces_nothing(self):
        assert judge([fact(attrs={"flag": False})], [rule()], GLUE_50) == []

    def test_finding_evidence_points_at_the_fact(self):
        the_fact = fact()
        found = judge([the_fact], [rule()], GLUE_50)
        assert found[0].evidence == [the_fact.id]

    def test_finding_inherits_subject_from_primary_fact(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert found[0].subject == {"type": "source_location", "file": "a.py", "line": 1}

    def test_finding_carries_rule_narrative_fields(self):
        found = judge([fact()], [rule()], GLUE_50)[0]
        assert found.explanation == "porque custa"
        assert found.proposed_change == ["mudar"]
        assert found.validation == ["contagem total"]
        assert found.rollback == ["reverter"]
        assert found.sources == [{"origin": "field-heuristic"}]


class TestRequiresFacts:
    def test_rule_is_skipped_when_required_kind_absent(self):
        """Kind nao extraido nao gera falso negativo silencioso: a regra e reportada
        como skipped, nao avaliada."""
        found, skipped = judge([], [rule()], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["rule_id"] == "SF-T-001"
        assert skipped[0]["reason"] == "requires_facts"


class TestVersionScope:
    def test_out_of_scope_rule_is_skipped_with_reason(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.10.0"})
        found, skipped = judge([fact()], [scoped], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["reason"] == "runtime_scope"
        assert skipped[0]["scope"] == {"iceberg": ">=1.10.0"}

    def test_in_scope_rule_fires(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.7.0"})
        assert len(judge([fact()], [scoped], GLUE_50)) == 1


class TestExprAndThreshold:
    def test_expr_with_threshold_fires_above_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert len(judge([fact(measures={"n": 12})], [r], GLUE_50)) == 1

    def test_expr_with_threshold_does_not_fire_below_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert judge([fact(measures={"n": 9})], [r], GLUE_50) == []

    def test_threshold_and_measured_appear_on_the_finding(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        found = judge([fact(measures={"n": 12})], [r], GLUE_50)[0]
        assert found.threshold == {"n": 10}
        assert found.measured == {"n": 12}


class TestSeverityBy:
    def _rule(self):
        return rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 3},
            severity_by=[
                {"when": "measures.n >= 10", "severity": "P0"},
                {"when": "measures.n >= 3", "severity": "P2"},
            ],
        )

    def test_first_matching_branch_wins(self):
        assert judge([fact(measures={"n": 12})], [self._rule()], GLUE_50)[0].severity == "P0"

    def test_second_branch_when_first_does_not_match(self):
        assert judge([fact(measures={"n": 5})], [self._rule()], GLUE_50)[0].severity == "P2"


class TestAnyAndAbsent:
    def test_any_group_fires_on_one_match(self):
        r = rule(
            when={
                "any": [
                    {"fact": "k", "where": {"attrs.flag": False}},
                    {"fact": "k", "where": {"attrs.flag": True}},
                ]
            }
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_fires_when_kind_missing(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_blocks_when_kind_present(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        facts = [fact(), fact(kind="other.kind")]
        assert judge(facts, [r], GLUE_50) == []


class TestDeterminism:
    def test_findings_are_sorted_and_stable(self):
        r_a = rule(id="SF-T-009", severity_default="P2")
        r_b = rule(id="SF-T-002", severity_default="P0")
        first = [f.to_dict() for f in judge([fact()], [r_a, r_b], GLUE_50)]
        second = [f.to_dict() for f in judge([fact()], [r_b, r_a], GLUE_50)]
        assert first == second
        assert [f["rule_id"] for f in first] == ["SF-T-002", "SF-T-009"]


class TestVerticalSliceEndToEnd:
    """A prova da Fase 0: codigo-fonte entra, Finding ancorado sai."""

    def test_coalesce_one_yields_sf_py_005_at_the_right_line(self):
        from sparkforge.rules.loader import load_catalog

        source = 'df.select("a").coalesce(1).write.parquet("s3://b/p")\n'
        facts = extract_source(source, "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert catalog, "SF-PY-005 ausente do catalogo"

        found = judge(facts, catalog, GLUE_50)
        assert len(found) == 1
        finding = found[0]
        assert finding.rule_id == "SF-PY-005"
        assert finding.severity == "P0"
        assert finding.status == "structural"
        assert finding.subject["file"] == "lib/loader.py"
        assert finding.subject["line"] == 1
        assert len(finding.evidence) == 1
        assert finding.evidence[0].startswith("f_")

    def test_repartition_200_does_not_trigger_coalesce_rule(self):
        from sparkforge.rules.loader import load_catalog

        facts = extract_source("df.repartition(200)\n", "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert judge(facts, catalog, GLUE_50) == []


class TestSameSubjectCorrelation:
    """Sem correlacao por subject, uma regra casa juntando um atributo de uma
    entidade com outro atributo de uma entidade diferente. Cada uma correta
    isoladamente, e a regra acusa. Falso positivo em config correta destroi a
    confianca em todo o resto do relatorio."""

    def _rule(self, same_subject):
        when = {
            "all": [
                {"fact": "tf.attribute", "where": {"attrs.key": "autoscaling"}},
                {"fact": "tf.attribute", "where": {"attrs.key": "workers"}},
            ]
        }
        if same_subject:
            when["same_subject"] = True
        return rule(requires_facts=["tf.attribute"], when=when)

    def _attr(self, symbol, key):
        return Fact(
            kind="tf.attribute",
            subject={"type": "tf_resource", "file": "main.tf", "symbol": symbol},
            attrs={"key": key},
        )

    def test_split_across_entities_does_not_fire_with_same_subject(self):
        facts = [self._attr("job_a", "workers"), self._attr("job_b", "autoscaling")]
        assert judge(facts, [self._rule(True)], GLUE_50) == []

    def test_split_across_entities_does_fire_without_same_subject(self):
        """Comportamento default preservado: regras que falam do conjunto continuam iguais."""
        facts = [self._attr("job_a", "workers"), self._attr("job_b", "autoscaling")]
        assert len(judge(facts, [self._rule(False)], GLUE_50)) == 1

    def test_same_entity_still_fires_with_same_subject(self):
        facts = [self._attr("job_c", "workers"), self._attr("job_c", "autoscaling")]
        found = judge(facts, [self._rule(True)], GLUE_50)
        assert len(found) == 1
        assert found[0].subject["symbol"] == "job_c"

    def test_evidence_comes_only_from_the_matching_entity(self):
        facts = [
            self._attr("job_c", "workers"),
            self._attr("job_c", "autoscaling"),
            self._attr("job_d", "workers"),
        ]
        found = judge(facts, [self._rule(True)], GLUE_50)
        assert len(found[0].evidence) == 2

    def test_result_is_deterministic_regardless_of_fact_order(self):
        a = [self._attr("job_c", "workers"), self._attr("job_c", "autoscaling")]
        b = list(reversed(a))
        assert [f.to_dict() for f in judge(a, [self._rule(True)], GLUE_50)] == [
            f.to_dict() for f in judge(b, [self._rule(True)], GLUE_50)
        ]


class TestSameSubjectReportsEveryOffender:
    """Uma regra `same_subject` afirma algo sobre UMA entidade. Se quatro jobs
    tem o mesmo defeito, sao quatro achados, nao um.

    Devolver so o primeiro grupo que casa faz o relatorio dizer "um job esta
    errado" quando tres estao: o operador corrige aquele, roda de novo, e
    descobre o proximo -- sem nunca saber quantos faltam. Subcontagem e
    enganosa da mesma forma que falso negativo.
    """

    def _rule(self):
        return rule(
            requires_facts=["tf.attribute"],
            when={
                "same_subject": True,
                "all": [
                    {"fact": "tf.attribute", "where": {"attrs.key": "autoscaling"}},
                    {"fact": "tf.attribute", "where": {"attrs.key": "workers"}},
                ],
            },
        )

    def _attr(self, symbol, key):
        return Fact(
            kind="tf.attribute",
            subject={"type": "tf_resource", "file": "main.tf", "symbol": symbol},
            attrs={"key": key},
        )

    def _facts(self):
        offenders = [
            f
            for symbol in ("job_a", "job_b", "job_c")
            for f in (self._attr(symbol, "workers"), self._attr(symbol, "autoscaling"))
        ]
        # Um quarto recurso correto: nao pode virar achado nem emprestar evidencia.
        return [*offenders, self._attr("job_ok", "workers")]

    def test_every_offending_subject_gets_its_own_finding(self):
        found = judge(self._facts(), [self._rule()], GLUE_50)
        assert [f.subject["symbol"] for f in found] == ["job_a", "job_b", "job_c"]

    def test_evidence_never_leaks_across_subjects(self):
        facts = self._facts()
        by_id = {f.id: f for f in facts}
        for finding in judge(facts, [self._rule()], GLUE_50):
            symbols = {by_id[fid].subject["symbol"] for fid in finding.evidence}
            assert symbols == {finding.subject["symbol"]}

    def test_order_is_stable_regardless_of_fact_order(self):
        facts = self._facts()
        forward = [f.to_dict() for f in judge(facts, [self._rule()], GLUE_50)]
        backward = [f.to_dict() for f in judge(list(reversed(facts)), [self._rule()], GLUE_50)]
        assert forward == backward


TWO_JOBS_ONE_OBSERVED = '''resource "aws_glue_job" "com_ui" {
  name         = "job-com-ui"
  glue_version = "5.0"

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://b/spark-logs/"
  }
}

resource "aws_glue_job" "sem_ui" {
  name         = "job-sem-ui"
  glue_version = "5.0"

  default_arguments = {
    "--TempDir" = "s3://b/temp/"
  }
}
'''


class TestObservabilityIsJudgedPerResource:
    """SF-GLUE-002 pergunta "este job tem como ser diagnosticado depois do fato?".
    A pergunta e por recurso, nunca pelo arquivo: num `.tf` com varios
    `aws_glue_job`, um unico job com Spark UI habilitado nao prova nada sobre os
    outros. Checar `absent: tf.observability.spark_ui` contra a lista inteira de
    facts mascara todos os jobs sem observabilidade assim que UM deles a tem --
    falso negativo caro, porque observabilidade ausente e justamente o que faz
    toda investigacao futura comecar sem evidencia.
    """

    def _judge_002(self, source):
        from sparkforge.facts.terraform import extract_terraform
        from sparkforge.rules.loader import load_catalog

        facts = extract_terraform(source, "main.tf")
        catalog = [r for r in load_catalog() if r["id"] == "SF-GLUE-002"]
        assert catalog, "SF-GLUE-002 ausente do catalogo"
        return judge(facts, catalog, GLUE_50)

    def test_job_without_observability_is_reported_even_when_a_sibling_has_it(self):
        found = self._judge_002(TWO_JOBS_ONE_OBSERVED)
        assert [f.subject.get("symbol") for f in found] == ["aws_glue_job.sem_ui"]

    def test_correctly_configured_job_is_never_accused(self):
        """A guarda contra o "conserto" ingenuo (`same_subject: true` sobre
        `tf.module_analyzed`, cujo subject e o arquivo): ali o grupo do arquivo
        nunca contem fact de observabilidade, `absent` fica satisfeito, e a regra
        acusa TODO modulo -- inclusive o configurado corretamente."""
        only_observed = TWO_JOBS_ONE_OBSERVED.split('resource "aws_glue_job" "sem_ui"')[0]
        assert self._judge_002(only_observed) == []


def _catalog_table(name, *, projection, partition_count=250000):
    entry = {
        "name": name,
        "storage_format": "parquet",
        "partition_keys": [{"name": "dt", "type": "string"}],
        "columns": [{"name": "valor", "type": "bigint"}],
        "partition_count": partition_count,
    }
    if projection:
        entry["properties"] = {"projection.enabled": "true"}
    return entry


class TestPartitionProjectionIsJudgedPerTable:
    """SF-ATH-003 pergunta "esta TABELA resolve particao por lookup no catalogo?".
    A pergunta e por tabela, nunca pelo dump: um dump do Glue Data Catalog
    descreve todas as tabelas do banco, e uma unica tabela com partition
    projection habilitada nao diz nada sobre as outras.

    Checar `absent: catalog.table_property.projection_enabled` contra a lista
    inteira de facts mascara TODA tabela sobre-particionada assim que UMA delas
    tem projection -- e a tabela bem configurada e justamente a que se espera
    encontrar num catalogo real, entao o mascaramento e a regra, nao a excecao.
    O relatorio diz "nenhuma tabela com problema de metadados" sobre um catalogo
    cheio delas.
    """

    def _judge_003(self, *tables):
        from sparkforge.facts.catalog_schema import extract_catalog_schema
        from sparkforge.rules.loader import load_catalog

        facts = extract_catalog_schema({"tables": list(tables)}, "catalog.json")
        catalog = [r for r in load_catalog() if r["id"] == "SF-ATH-003"]
        assert catalog, "SF-ATH-003 ausente do catalogo"
        return judge(facts, catalog, GLUE_50)

    def test_table_without_projection_is_reported_even_when_a_sibling_has_it(self):
        found = self._judge_003(
            _catalog_table("db.sem_projection", projection=False),
            _catalog_table("db.com_projection", projection=True),
        )
        assert [f.subject.get("symbol") for f in found] == ["db.sem_projection"]

    def test_every_offending_table_gets_its_own_finding(self):
        found = self._judge_003(
            _catalog_table("db.a", projection=False),
            _catalog_table("db.b", projection=False),
            _catalog_table("db.ok", projection=True),
        )
        assert [f.subject.get("symbol") for f in found] == ["db.a", "db.b"]

    def test_correctly_configured_table_is_never_accused(self):
        """A guarda contra o "conserto" ingenuo: o dump tambem emite
        `catalog.analyzed` e `catalog.table_property`, cujos grupos nunca contem
        `catalog.table_partitions`. Se a ancora escorregasse para um subject de
        arquivo, `absent` ficaria satisfeito e a regra acusaria o dump inteiro.
        """
        assert self._judge_003(_catalog_table("db.com_projection", projection=True)) == []

    def test_table_below_the_threshold_is_never_accused(self):
        assert self._judge_003(
            _catalog_table("db.pequena", projection=False, partition_count=10)
        ) == []


TWO_QUERIES_ONE_FILTERED = '''spark.sql("SELECT valor FROM db.eventos LIMIT 10")
spark.sql("SELECT valor FROM db.eventos WHERE dt = '2026-01-01' LIMIT 10")
'''


class TestPartitionFilterIsJudgedPerQuery:
    """SF-ATH-002 pergunta "esta QUERY escaneia a tabela inteira?". A pergunta e
    por query, nunca pelo conjunto analisado: uma query em qualquer lugar do
    repositorio que filtre a coluna de particao faz
    `sql.predicate.partition_filter` existir globalmente, `absent` falha, e a
    regra nao dispara para NENHUMA das queries sem filtro.

    Agrupar por arquivo tambem nao basta: dois `spark.sql(...)` no mesmo modulo
    sao duas queries independentes, e a boa esconderia a ruim. O subject de um
    fact de SQL e `source_location` -- a entidade que ele identifica e a
    LOCALIZACAO da query, nao o arquivo.
    """

    def _judge_002(self, source):
        from sparkforge.facts.catalog_schema import extract_catalog_schema
        from sparkforge.facts.fusion import fuse
        from sparkforge.facts.sql_literal import extract_sql_from_pyspark
        from sparkforge.rules.loader import load_catalog

        catalog_facts = extract_catalog_schema(
            {"tables": [_catalog_table("db.eventos", projection=False)]}, "catalog.json"
        )
        facts = fuse([*extract_sql_from_pyspark(source, "a.py"), *catalog_facts])
        catalog = [r for r in load_catalog() if r["id"] == "SF-ATH-002"]
        assert catalog, "SF-ATH-002 ausente do catalogo"
        return judge(facts, catalog, GLUE_50)

    def test_unfiltered_query_is_reported_even_when_a_sibling_query_filters(self):
        found = self._judge_002(TWO_QUERIES_ONE_FILTERED)
        assert [(f.subject["file"], f.subject["line"]) for f in found] == [("a.py", 1)]

    def test_filtered_query_is_never_accused(self):
        only_filtered = TWO_QUERIES_ONE_FILTERED.splitlines(keepends=True)[1]
        assert self._judge_002(only_filtered) == []

    def test_every_unfiltered_query_gets_its_own_finding(self):
        source = (
            'spark.sql("SELECT valor FROM db.eventos LIMIT 10")\n'
            'spark.sql("SELECT valor FROM db.eventos WHERE dt = \'2026-01-01\' LIMIT 10")\n'
            'spark.sql("SELECT valor FROM db.eventos LIMIT 20")\n'
        )
        found = self._judge_002(source)
        assert [f.subject["line"] for f in found] == [1, 3]


class TestBlockedOnIsDistinctFromMissingData:
    """Regra bloqueada por capacidade inexistente e regra sem dados nesta execucao
    sao situacoes diferentes: a primeira nunca dispara ate alguem construir o
    extrator, a segunda dispara assim que o artefato for coletado. Reportar as duas
    igual faria o operador esperar por dado que nao esta a caminho."""

    def test_blocked_rule_reports_blocked_on_not_requires_facts(self):
        blocked = rule(blocked_on="extrator-de-diff-terraform")
        _, skipped = judge([fact()], [blocked], GLUE_50, return_skipped=True)
        assert skipped[0]["reason"] == "blocked_on"
        assert skipped[0]["blocked_on"] == "extrator-de-diff-terraform"

    def test_blocked_rule_never_fires_even_with_all_facts_present(self):
        blocked = rule(blocked_on="capacidade-futura")
        assert judge([fact()], [blocked], GLUE_50) == []

    def test_unblocked_rule_with_missing_kind_still_says_requires_facts(self):
        _, skipped = judge([], [rule()], GLUE_50, return_skipped=True)
        assert skipped[0]["reason"] == "requires_facts"

    # `blocked_on` que sobrevive a este teste tem que ser uma decisao CONSCIENTE,
    # registrada aqui com o motivo -- nao uma excecao muda herdada de quem
    # passou pelo teste sem olhar. Mesmo padrao de `BLOQUEIO_SEM_KIND_ORFAO` em
    # `tests/test_rules_catalog_reachability.py`: allowlist nomeada + teste-par
    # que reprova a entrada assim que ela parar de ser verdade
    # (`test_bloqueio_consciente_nao_sobrevive_ao_desbloqueio` abaixo).
    # SF-MIG-003 saiu daqui na Task 11: a fronteira (Glue 6.0, onde ANSI mode
    # passa a default) foi confirmada contra `migrating-version-60.html` e
    # `release-notes.html`, e a regra trocou `blocked_on` por
    # `runtime_scope: {glue: ">=6.0"}` real. Allowlist vazia e o estado
    # honesto: nenhum `blocked_on` sobrevive no catalogo hoje.
    BLOQUEIO_CONSCIENTE: dict[str, str] = {}

    def test_the_real_catalog_has_no_blocked_rule_left(self):
        """Este teste era o inverso: fixava SF-GLUE-005 como bloqueada em
        `extrator-de-diff-terraform`. O extrator existe agora
        (`terraform.extract_terraform_diff`), e com ele as cinco ultimas regras
        inertes do catalogo passaram a disparar.

        A checagem vira uma varredura, e nao volta a citar regra por nome de
        proposito: o proximo `blocked_on` a aparecer no catalogo tem que ser uma
        decisao consciente de quem o escreve, e nao herdar a passagem por um
        teste que so olhava uma regra. `BLOQUEIO_CONSCIENTE` acima E essa
        decisao -- registrada com o motivo, nao uma excecao muda -- e qualquer
        `blocked_on` que nao esteja nela continua reprovando aqui, sem
        excecao."""
        from sparkforge.rules.loader import load_catalog

        blocked = {r["id"]: r["blocked_on"] for r in load_catalog() if r.get("blocked_on")}
        inesperados = {k: v for k, v in blocked.items() if k not in self.BLOQUEIO_CONSCIENTE}
        assert inesperados == {}, inesperados

    def test_bloqueio_consciente_nao_sobrevive_ao_desbloqueio(self):
        """Entrada obsoleta em `BLOQUEIO_CONSCIENTE` esconderia um `blocked_on`
        morto para sempre -- mesmo risco que
        `test_bloqueio_sem_kind_orfao_nao_guarda_regra_que_ja_foi_corrigida`
        cobre em `tests/test_rules_catalog_reachability.py` para a allowlist
        irma. Quando a Task 11 confirmar a fronteira e SF-MIG-003 trocar
        `blocked_on` por `runtime_scope`, esta asserção reprova ate alguem
        tirar a entrada da allowlist -- a isencao nao pode sobreviver ao motivo
        que a justifica."""
        from sparkforge.rules.loader import load_catalog

        by_id = {r["id"]: r for r in load_catalog()}
        for rule_id in self.BLOQUEIO_CONSCIENTE:
            regra = by_id.get(rule_id)
            assert regra is not None, (
                f"{rule_id} esta em BLOQUEIO_CONSCIENTE e nao existe no catalogo."
            )
            assert regra.get("blocked_on"), f"{rule_id} perdeu `blocked_on`; remova da allowlist."
