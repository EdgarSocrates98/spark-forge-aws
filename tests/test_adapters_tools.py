import json

import jsonschema
import pytest

from sparkforge.adapters.tools import TOOLS, call_tool

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


class TestToolSurface:
    def test_the_full_tool_surface_is_declared(self):
        """Fase 1: a superficie MCP cresceu para cobrir todo verbo da CLI --
        os 10 tools da Fase 0, mais catalog-schema/fuse/call-graph e os
        extratores sem verbo proprio (event-log, terraform, iceberg, sql,
        athena-workgroup), mais os coletores AWS -- SETE que tocam a rede desde
        que a Fase 5d acrescentou `collect_emr_serverless`, mais `collect_verify`,
        que so le disco. Um tool que sai desta
        lista sem querer e um capability reachable-por-CLI-mas-nao-por-MCP
        que `parity.yaml`/`test_capability_parity.py` deveriam pegar -- este
        teste falha primeiro, com um diff legivel."""
        assert set(TOOLS) == {
            "sparkforge_case_open",
            "sparkforge_case_get",
            "sparkforge_case_update",
            "sparkforge_next_step",
            "sparkforge_resume",
            "sparkforge_playbook",
            "sparkforge_runtime_detect",
            "sparkforge_knowledge_path",
            "sparkforge_analyze_pyspark",
            "sparkforge_analyze_catalog_schema",
            "sparkforge_analyze_event_log",
            "sparkforge_analyze_sql_metrics",
            "sparkforge_analyze_cloudwatch",
            "sparkforge_analyze_glue_job_runs",
            "sparkforge_analyze_plan",
            "sparkforge_analyze_terraform",
            "sparkforge_analyze_iceberg",
            "sparkforge_analyze_sql",
            "sparkforge_analyze_athena_workgroup",
            "sparkforge_analyze_emr_cluster",
            "sparkforge_analyze_emr_serverless",
            "sparkforge_analyze_emr_eks",
            "sparkforge_analyze_controlm_jobs",
            "sparkforge_analyze_data_quality",
            "sparkforge_analyze_graph",
            "sparkforge_analyze_call_graph",
            "sparkforge_analyze_s3_listing",
            "sparkforge_analyze_consumers",
            "sparkforge_analyze_terraform_diff",
            "sparkforge_migration_assess",
            "sparkforge_glue_dependency_audit",
            "sparkforge_iceberg_assess_upgrade",
            "sparkforge_release_describe",
            "sparkforge_release_diff",
            "sparkforge_controlm_describe",
            "sparkforge_benchmark",
            "sparkforge_funcval_plan",
            "sparkforge_funcval_compare",
            "sparkforge_fuse",
            "sparkforge_workload",
            "sparkforge_capacity",
            "sparkforge_finops",
            "sparkforge_tune",
            "sparkforge_economy_report",
            "sparkforge_judge",
            "sparkforge_rules_lookup",
            "sparkforge_validate_output",
            "sparkforge_report_sign",
            "sparkforge_report_verify",
            "sparkforge_collect_event_log",
            "sparkforge_collect_glue_job",
            "sparkforge_collect_cloudwatch",
            "sparkforge_collect_glue_job_runs",
            "sparkforge_collect_iceberg_metadata",
            "sparkforge_collect_athena_workgroup",
            "sparkforge_collect_emr_cluster",
            "sparkforge_collect_emr_serverless",
            "sparkforge_collect_emr_eks",
            "sparkforge_collect_verify",
            # SPEC 56-77: SEIS tools de Code Intelligence, e nao as onze que as
            # secoes 57 a 67 listam. A justificativa por nome esta no comentario
            # de bloco de `tools.py` -- resumo: 59+61 colapsam (mesma entrada,
            # profundidade diferente), 63+64+67 colapsam (mesma medicao do estado
            # do indice), 62 e 66 NAO entram porque a implementacao nao existe, e
            # 60 fica separada de proposito por ser a unica que devolve fonte.
            "sparkforge_code_context",
            "sparkforge_code_search",
            "sparkforge_code_path",
            "sparkforge_code_shape",
            "sparkforge_code_symbol",
            "sparkforge_code_read",
            "sparkforge_code_status",
            "sparkforge_code_sync",
        }

    def test_every_tool_declares_an_output_schema(self):
        """`sparkforge_judge` pode devolver sucesso ou o shape de erro de
        fronteira (`facts_path` ausente), entao seu outputSchema usa `oneOf`
        em vez de um `type` plano na raiz -- ver TestOutputSchemasAreReal
        para a verificacao real de cada branch."""
        for name, spec in TOOLS.items():
            schema = spec["outputSchema"]
            assert schema.get("type") == "object" or "oneOf" in schema, name

    def test_every_tool_declares_annotations(self):
        for name, spec in TOOLS.items():
            for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                assert key in spec["annotations"], f"{name} sem {key}"

    def test_no_tool_is_destructive(self):
        assert all(s["annotations"]["destructiveHint"] is False for s in TOOLS.values())

    def test_only_collect_tools_are_open_world(self):
        """O nucleo determinístico e offline; os coletores AWS (`collect_*`,
        exceto `collect_verify`, que so le o manifesto local) sao as
        primeiras ferramentas deste projeto que tocam a rede de verdade.
        Antes da Fase 1 nenhum tool era openWorld -- agora a invariante
        precisa e "so collect_* (menos verify)", nao mais "nenhum"."""
        open_world = {n for n, s in TOOLS.items() if s["annotations"]["openWorldHint"] is True}
        assert open_world == {
            "sparkforge_collect_event_log",
            "sparkforge_collect_glue_job",
            "sparkforge_collect_cloudwatch",
            "sparkforge_collect_glue_job_runs",
            "sparkforge_collect_iceberg_metadata",
            "sparkforge_collect_athena_workgroup",
            "sparkforge_collect_emr_cluster",
            "sparkforge_collect_emr_serverless",
            "sparkforge_collect_emr_eks",
        }

    def test_every_open_world_tool_also_writes_locally(self):
        """Este teste afirmava o CONTRARIO ate a Fase I3, e estava errado --
        ele trancava a mentira em vez de pegar.

        A razao antiga era "os coletores so leem da AWS, nunca escrevem do
        lado AWS", e a parte depois da virgula e verdade. So que
        `readOnlyHint` nao tem lado: ele afirma que a tool nao modifica o
        ambiente dela. Os sete coletores modificam o ambiente LOCAL -- todos
        terminam em `sparkforge.collect.aws._write_and_register`, que grava o
        artefato e depois grava o manifesto `path` + `sha256` que
        `sparkforge_collect_verify` confere.

        A invariante real e esta, e vale a pena tranca-la nos dois sentidos:
        toda tool que sai para a rede TAMBEM persiste o que trouxe. Um coletor
        que tocasse a AWS sem registrar o artefato deixaria o livro-razao de
        integridade sem a entrada correspondente, e o `verify` nao teria como
        saber que ela deveria existir."""
        de_rede = {n for n, s in TOOLS.items() if s["annotations"]["openWorldHint"] is True}
        assert de_rede, "o corpus precisa ter ao menos uma tool de rede"
        for name in de_rede:
            assert TOOLS[name]["annotations"]["readOnlyHint"] is False, name

    def test_only_case_and_report_writers_are_not_read_only(self):
        """A quarta lista manual desta classe, e ela mudou junto com as outras
        tres na Fase 4b: `sparkforge_report_sign` escreve o bloco de assinatura
        DENTRO do relatorio, no lugar. Um `sign` que so devolvesse o bloco para
        alguem colar seria a versao decorativa da capacidade -- e a colagem
        manual e exatamente onde o corpo assinado deixaria de ser o corpo
        escrito. `report_verify` fica de fora: so le.

        A Fase 4c acrescentou `sparkforge_funcval_plan` pela MESMA razao, um
        dominio adiante: o plano nao e saida legivel, e o artefato que
        `sparkforge_funcval_compare` rele e que o gate cobra. Um `plan` que so
        devolvesse `structuredContent` daria a capacidade a quem usa a CLI
        (`--out`) e nao a quem usa o MCP -- a assimetria que `parity.yaml`
        existe para pegar.

        `sparkforge_funcval_compare` ENTROU na lista ao fechar a D-4c-26, e a
        razao e a mesma vista do outro lado: `sparkforge_judge` le facts, e sem
        `out_path` a saida da comparacao so chegava la extraida do envelope a
        mao -- de um envelope que PAGINA. A diferenca para o plano esta no
        schema, nao aqui: `out_path` do plano e `required`, o da comparacao e
        opcional, porque um plano sem arquivo nao serve para nada e uma
        comparacao sem arquivo ainda e legivel.

        A Fase I3 descobriu que os SETE coletores AWS tambem escrevem, e nao
        por mudanca de capacidade: a anotacao deles dizia `readOnlyHint: True`
        e mentia. Eles gravam o artefato e o manifesto de integridade via
        `sparkforge.collect.aws._write_and_register` desde que existem -- ver
        o comentario de `_WRITE_LOCAL_OPEN_WORLD` em `tools.py`.

        Eles NAO entram na lista a mao, e a razao nao e economia de digitacao:
        os sete ja estao garantidos por dois testes desta mesma classe --
        `test_only_collect_tools_are_open_world` fixa o conjunto `openWorld`
        EXATAMENTE nesses sete nomes, e
        `test_every_open_world_tool_also_writes_locally` cobra
        `readOnlyHint is False` de cada tool `openWorld`. Repetir os sete aqui
        somaria garantia zero e cresceria a cada coletor novo. Descontar o
        conjunto de rede e afirmar o resto preserva a garantia inteira e para
        de crescer.

        Os CINCO locais continuam a mao de proposito, e ai a lista carrega
        garantia real: nao ha nenhuma outra propriedade declarada que separe
        `case_open` de `analyze_pyspark` -- derivar de `TOOLS` seria escrever
        `writers == writers` e o teste deixaria de cobrar decisao humana
        quando uma tool trocasse de lado.

        O RISCO desta forma, escrito porque ja se materializou aqui: quando um
        pin escrito a mao falha, o conserto barato e editar a expectativa em
        vez de consertar a anotacao. Foi exatamente o que aconteceu com
        `test_every_open_world_tool_is_still_read_only`, que entrou em
        `afd2c96` (2026-07-30) afirmando o CONTRARIO do que o codigo fazia e
        trancou a mentira por centenas de commits. Um pin que falha nao e um
        pin que protege: quem editar esta lista precisa provar que a tool
        mudou de lado, nao so fazer o vermelho sumir."""
        de_rede = {n for n, s in TOOLS.items() if s["annotations"]["openWorldHint"] is True}
        writers = {n for n, s in TOOLS.items() if not s["annotations"]["readOnlyHint"]}
        assert writers - de_rede == {
            "sparkforge_case_open",
            "sparkforge_case_update",
            "sparkforge_funcval_compare",
            "sparkforge_funcval_plan",
            "sparkforge_report_sign",
            # AS SEIS DE CODIGO, e nao so `sparkforge_code_sync`.
            #
            # A SPEC 65 chama `sync` de "a unica tool de mutacao do Code
            # Intelligence" e a SPEC 57 anota `code_context` como
            # `readOnlyHint: true`. As duas afirmacoes caem pelo mesmo
            # contraexemplo MEDIDO: toda consulta atravessa
            # `staleness.garantir_frescor`, que grava `freshness_checked_ns` e
            # `freshness_verdict` em `metadata` a cada conferencia, e que ate
            # `max_auto_sync_files` roda uma sincronizacao incremental inteira
            # dentro da chamada. Medicao: `mtime_ns` do `.sqlite3` antes e
            # depois de um `sparkforge_code_search`, sem nenhum arquivo de
            # fonte alterado -- DIFERENTES.
            #
            # `readOnlyHint` nao tem lado. O que nunca muda e o FONTE
            # (INV-004), e isso esta trancado em
            # `tests/test_adapters_code_surface.py`, nao aqui.
            "sparkforge_code_context",
            "sparkforge_code_read",
            "sparkforge_code_path",
            "sparkforge_code_shape",
            "sparkforge_code_search",
            "sparkforge_code_status",
            "sparkforge_code_symbol",
            "sparkforge_code_sync",
        }

    def test_every_tool_has_a_description(self):
        for name, spec in TOOLS.items():
            assert len(spec["description"]) > 20, name


class TestCallTool:
    def test_analyze_returns_structured_content(self, repo):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        assert result["total_count"] >= 1
        assert result["by_kind"]["pyspark.partitioning"] == 1

    def test_judge_finds_sf_py_005(self, repo):
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        result = call_tool("sparkforge_judge", {"facts": facts["items"], "glue": "5.0"})
        assert [f["rule_id"] for f in result["items"]] == ["SF-PY-005"]

    def test_rules_lookup_returns_thresholds_and_sources(self):
        rule = call_tool("sparkforge_rules_lookup", {"id": ["SF-PY-007"]})["rules"][0]
        assert rule["threshold"] == {"run_length": 10}
        assert rule["sources"]

    def test_validate_output_rejects_unbacked_gain(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40%", "benchmark_ref": "",
        }
        result = call_tool("sparkforge_validate_output", {"finding": payload})
        assert result["valid"] is False
        assert "benchmark_ref" in result["errors"][0]

    def test_validate_output_accepts_a_clean_finding(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
        }
        assert call_tool("sparkforge_validate_output", {"finding": payload})["valid"] is True

    def _gain_finding(self, benchmark_ref):
        return {
            "rule_id": "SF-BENCH-001", "schema_version": 1, "title": "t", "severity": "P2",
            "confidence": "high", "status": "confirmed",
            "subject": {"type": "job_run"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40%", "benchmark_ref": benchmark_ref,
        }

    def test_validate_output_rejects_a_free_text_benchmark_ref(self):
        result = call_tool(
            "sparkforge_validate_output",
            {"finding": self._gain_finding("bench/2026-07-29.json")},
        )
        assert result["valid"] is False
        assert "nao e um fact_id" in result["errors"][0]

    def test_validate_output_accepts_a_well_formed_ref_without_facts_path(self):
        result = call_tool(
            "sparkforge_validate_output", {"finding": self._gain_finding("f_a1b2c3")}
        )
        assert result["valid"] is True

    def test_facts_path_turns_on_the_relevance_layer(self, tmp_path):
        import json as _json

        from sparkforge.findings.models import Fact

        fact = Fact(kind="bench.run_delta", subject={"type": "job_run"}, measures={"n": 1})
        facts_path = tmp_path / "facts.json"
        facts_path.write_text(_json.dumps([fact.to_dict()]), encoding="utf-8")

        absent = call_tool(
            "sparkforge_validate_output",
            {"finding": self._gain_finding("f_a1b2c3"), "facts_path": str(facts_path)},
        )
        assert absent["valid"] is False
        assert "nao esta no conjunto" in absent["errors"][0]

        present = call_tool(
            "sparkforge_validate_output",
            {"finding": self._gain_finding(fact.id), "facts_path": str(facts_path)},
        )
        assert present["valid"] is True

    def test_strict_gates_reaches_mcp_too(self, repo):
        """A assimetria que a Fase 5b corrigiu na flag `--emr` nao pode voltar:
        o rigor e escolha do case, e um cliente MCP precisa poder faze-la."""
        case = call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-08-04T00:00:00Z",
             "glue": "5.0", "strict_gates": True},
        )
        assert case["strict_gates"] is True
        blocked = call_tool(
            "sparkforge_case_update", {"repo": str(repo), "phase": "validation"}
        )
        assert blocked["exit_code"] == 2
        assert "sparkforge benchmark" in blocked["error"]

    def test_case_open_without_strict_gates_stays_advisory(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-08-04T00:00:00Z"},
        )
        result = call_tool(
            "sparkforge_case_update", {"repo": str(repo), "phase": "validation"}
        )
        assert result["phase"] == "validation"

    def test_override_gate_needs_a_reason_over_mcp(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-08-04T00:00:00Z",
             "strict_gates": True},
        )
        recusado = call_tool(
            "sparkforge_case_update",
            {"repo": str(repo), "override_gate": "baseline_captured"},
        )
        assert recusado["exit_code"] == 2
        assert "reason" in recusado["error"]

        aceito = call_tool(
            "sparkforge_case_update",
            {"repo": str(repo), "override_gate": "baseline_captured",
             "reason": "job descontinuado", "now": "2026-08-04T00:00:00Z"},
        )
        assert aceito["gate_overrides"][0]["reason"] == "job descontinuado"

    def test_facts_path_unlocks_the_phase_over_mcp(self, repo, tmp_path):
        from sparkforge.findings.models import Fact

        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-08-04T00:00:00Z",
             "strict_gates": True},
        )
        facts = tmp_path / "gate_facts.json"
        facts.write_text(
            json.dumps(
                [
                    Fact(kind=k, subject={"type": "job_run"}, measures={"n": 1}).to_dict()
                    for k in ("bench.run_delta", "callgraph.reachable_spark_work")
                ]
            ),
            encoding="utf-8",
        )
        result = call_tool(
            "sparkforge_case_update",
            {"repo": str(repo), "phase": "validation", "facts_path": str(facts)},
        )
        assert result["phase"] == "validation"

    def test_resume_carries_the_override_over_mcp(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-08-04T00:00:00Z",
             "strict_gates": True},
        )
        call_tool(
            "sparkforge_case_update",
            {"repo": str(repo), "override_gate": "flows_mapped",
             "reason": "corpus sem trabalho Spark alcancavel",
             "now": "2026-08-04T00:00:00Z"},
        )
        payload = call_tool("sparkforge_resume", {"repo": str(repo)})
        assert payload["strict_gates"] is True
        assert payload["gate_overrides"][0]["reason"] == (
            "corpus sem trabalho Spark alcancavel"
        )
        jsonschema.validate(payload, TOOLS["sparkforge_resume"]["outputSchema"])

    def test_case_open_then_next_step(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-07-30T00:00:00Z", "glue": "5.0"},
        )
        assert call_tool("sparkforge_next_step", {"repo": str(repo)})["recommended_skill"]

    def test_unknown_tool_raises_with_the_valid_names(self):
        with pytest.raises(KeyError, match="sparkforge_judge"):
            call_tool("sparkforge_nope", {})

    def test_error_result_carries_a_collect_command(self, repo):
        result = call_tool("sparkforge_judge", {"facts_path": str(repo / "nope.json")})
        assert "sparkforge analyze pyspark" in json.dumps(result)

    def test_judge_accepts_a_list_of_facts_paths(self, repo, tmp_path):
        """Paridade com `judge --facts` repetivel na CLI: uma regra que cruza
        extratores (SF-GLUE-004) precisa das duas fontes na mesma chamada."""
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(
            'resource "aws_glue_job" "etl" {\n'
            '  name         = "etl"\n'
            '  glue_version = "5.0"\n'
            "  max_retries  = 2\n"
            "\n"
            "  default_arguments = {\n"
            '    "--enable-spark-ui"       = "true"\n'
            '    "--spark-event-logs-path" = "s3://b/logs/"\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        lib = tmp_path / "job"
        lib.mkdir()
        (lib / "w.py").write_text('df.write.mode("append").parquet("s3://b/p")\n', encoding="utf-8")

        tf_facts = tmp_path / "tf.json"
        py_facts = tmp_path / "py.json"
        for tool, target, out in (
            ("sparkforge_analyze_terraform", tf_dir, tf_facts),
            ("sparkforge_analyze_pyspark", lib, py_facts),
        ):
            payload = call_tool(tool, {"path": str(target), "limit": 1000})
            out.write_text(json.dumps(payload["items"], ensure_ascii=False), encoding="utf-8")

        result = call_tool(
            "sparkforge_judge",
            {"facts_path": [str(tf_facts), str(py_facts)], "glue": "5.0", "limit": 1000},
        )
        assert "SF-GLUE-004" in {f["rule_id"] for f in result["items"]}


class TestFuncvalCompareWritesLikeTheCLI:
    """D-4c-26 pelo lado do MCP.

    A divida pedia os DOIS: `--out` na CLI e `out_path` na tool. Fechar so um
    lado trocaria uma assimetria (verbo que grava contra verbo que nao grava)
    por outra (superficie que grava contra superficie que nao grava), e a
    segunda e a que `parity.yaml` existe para pegar -- um cliente MCP nao tem
    shell onde rodar o `jq` que faltava.
    """

    def _compare(self, tmp_path, **extra):
        plan_path = _write_funcval_plan_file(tmp_path)
        before, after = _write_funcval_result_files(tmp_path)
        return call_tool(
            "sparkforge_funcval_compare",
            {
                "plan_path": str(plan_path),
                "before_path": str(before),
                "after_path": str(after),
                **extra,
            },
        )

    def test_out_path_writes_the_list_that_judge_reads(self, tmp_path):
        out = tmp_path / "funcval.json"
        payload = self._compare(tmp_path, out_path=str(out))
        gravado = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(gravado, list)
        assert gravado == payload["items"]
        judged = call_tool(
            "sparkforge_judge", {"facts_path": [str(out)], "glue": "5.0", "limit": 1000}
        )
        assert "SF-FVAL-001" in {f["rule_id"] for f in judged["items"]}

    def test_the_file_is_the_whole_comparison_and_not_the_page(self, tmp_path):
        """`limit` corta o `structuredContent`, nunca o arquivo. O contrario
        seria o motor entregando a primeira pagina com nome de comparacao."""
        out = tmp_path / "funcval.json"
        payload = self._compare(tmp_path, out_path=str(out), limit=1)
        assert len(payload["items"]) == 1
        assert payload["next_cursor"]
        gravado = json.loads(out.read_text(encoding="utf-8"))
        assert len(gravado) == payload["total_count"] > 1

    def test_without_out_path_nothing_is_written(self, tmp_path):
        plan_path = _write_funcval_plan_file(tmp_path)
        before, after = _write_funcval_result_files(tmp_path)
        antes = set(tmp_path.iterdir())
        call_tool(
            "sparkforge_funcval_compare",
            {
                "plan_path": str(plan_path),
                "before_path": str(before),
                "after_path": str(after),
            },
        )
        assert set(tmp_path.iterdir()) == antes

    def test_the_two_surfaces_declare_the_same_optionality(self, tmp_path):
        """A simetria dita no schema, e nao so no comportamento: `out_path` do
        plano e `required`, o da comparacao nao -- e a CLI diz o mesmo, com
        `--out` obrigatorio no `plan` e opcional no `compare`."""
        plano = TOOLS["sparkforge_funcval_plan"]["inputSchema"]
        compare = TOOLS["sparkforge_funcval_compare"]["inputSchema"]
        assert "out_path" in plano["required"]
        assert "out_path" in plano["properties"]
        assert "out_path" in compare["properties"]
        assert "out_path" not in compare["required"]


class TestUnresolvedIsAlwaysReported:
    """Regra 7 do AGENT_PROTOCOL.md: no nao resolvido e ponto cego, nao ausencia
    de problema. Se a tool nao devolve a contagem, o protocolo exige do agente
    algo que a ferramenta nao fornece."""

    def _repo(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "a.py").write_text(
            "getattr(df, metodo)(1)\ndf.coalesce(1)\n", encoding="utf-8"
        )
        return lib

    def test_analyze_reports_unresolved_count(self, tmp_path):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(self._repo(tmp_path))})
        assert result["unresolved"] == 1

    def test_analyze_reports_where_each_blind_spot_is(self, tmp_path):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(self._repo(tmp_path))})
        spot = result["unresolved_at"][0]
        assert spot["reason"] == "getattr"
        assert spot["line"] == 1
        assert spot["file"].endswith("a.py")

    def test_filtering_by_kind_cannot_hide_the_blind_spot(self, tmp_path):
        """Filtrar por kind nao pode fazer o ponto cego sumir do relatorio."""
        result = call_tool(
            "sparkforge_analyze_pyspark",
            {"path": str(self._repo(tmp_path)), "kind": ["pyspark.partitioning"]},
        )
        assert result["by_kind"] == {"pyspark.partitioning": 1}
        assert result["unresolved"] == 1

    def test_clean_source_reports_zero_not_absent(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "a.py").write_text('df.select("a")\n', encoding="utf-8")
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
        assert result["unresolved"] == 0
        assert result["unresolved_at"] == []


class TestOutputSchemasAreReal:
    """Um outputSchema `{"type": "object"}` generico passa no teste e nao entrega
    nada: o cliente volta a adivinhar a forma, que e exatamente o que esta
    arquitetura existe para evitar."""

    def _branches(self, spec):
        """`sparkforge_judge` descreve sucesso e erro via `oneOf`; as demais
        ferramentas sao um schema plano. Normaliza os dois casos para uma
        lista de sub-schemas a inspecionar."""
        schema = spec["outputSchema"]
        return schema.get("oneOf") or [schema]

    def test_every_tool_declares_properties(self):
        for name, spec in TOOLS.items():
            for branch in self._branches(spec):
                assert branch.get("properties"), name

    def test_every_tool_declares_required_keys(self):
        for name, spec in TOOLS.items():
            for branch in self._branches(spec):
                assert branch.get("required"), name

    def test_no_tool_uses_a_bare_object_schema(self):
        for name, spec in TOOLS.items():
            schema = spec["outputSchema"]
            assert set(schema) > {"type"} or "oneOf" in schema, name


_CASE_OPEN_ARGS = {"case_id": "c1", "now": "2026-07-30T00:00:00Z", "glue": "5.0"}

CATALOG_DUMP = json.dumps(
    {
        "tables": [
            {
                "name": "db.eventos",
                "storage_format": "parquet",
                "partition_keys": [{"name": "dt", "type": "string"}],
                "columns": [
                    {"name": "cliente_id", "type": "bigint"},
                    {"name": "dt", "type": "string"},
                ],
            }
        ]
    }
)

_EVENT_LOG_LINE = json.dumps({"Event": "SparkListenerApplicationStart"}) + "\n"

# Event log minimo COM metrica de plano SQL: um no `FileScan parquet
# db.clientes[id#1]` que publica `number of files read` (mapeado para
# `files_read` em knowledge/spark/sql-metrics.yaml), atribuido via
# SparkListenerDriverAccumUpdates. Sem os dois eventos, `extract_sql_metrics`
# so renderiza o fact `spark.sql.unresolved` de `no_sql_events`, e o teste de
# schema validaria o ramo errado -- o de ausencia, nao o de `spark.sql.scan`.
_SQL_METRICS_EVENT_LOG_LINES = "".join(
    json.dumps(e) + "\n"
    for e in [
        {
            "Event": "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "select * from db.clientes",
            "sparkPlanInfo": {
                "nodeName": "FileScan parquet",
                "simpleString": "FileScan parquet db.clientes[id#1]",
                "children": [],
                "metadata": {"Format": "parquet"},
                "metrics": [{"name": "number of files read", "accumulatorId": 1}],
            },
        },
        {
            "Event": "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates",
            "executionId": 0,
            "accumUpdates": [[1, 3]],
        },
        {
            "Event": "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd",
            "executionId": 0,
        },
    ]
)

# Artefato de metricas do CloudWatch no shape que `sparkforge collect cloudwatch`
# grava -- ver `_artifact()` de `tests/test_facts_cloudwatch.py`. Com valores nao
# vazios: uma serie vazia validaria `sparkforge_analyze_cloudwatch` contra o
# schema pelo motivo errado (`glue.metric.unresolved`, nao `glue.metric`).
_CLOUDWATCH_ARTIFACT = json.dumps(
    {
        "job_name": "etl-job",
        "job_run_id": "jr_1",
        "start": "2026-08-26T10:00:00Z",
        "end": "2026-08-26T10:20:00Z",
        "period_seconds": 60,
        "metric_data_results": [
            {
                "Id": "m0",
                "Label": "glue.driver.workerUtilization",
                "Timestamps": ["t1", "t2", "t3"],
                "Values": [0.3, 0.9, 0.6],
            }
        ],
    }
)

# Artefato de UM run Glue no shape que `sparkforge collect glue-job-runs` grava
# -- um JSON por run terminal, nomeado `<job>_<run_id>.json`.
_GLUE_JOB_RUN_ARTIFACT = json.dumps(
    {
        "JobName": "etl-job",
        "Id": "jr_1",
        "JobRunState": "SUCCEEDED",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 2,
        "GlueVersion": "5.0",
        "ExecutionTime": 120,
        "StartedOn": "2026-08-26T10:00:00Z",
        "CompletedOn": "2026-08-26T10:02:00Z",
    }
)

_PLAN_TEXT = (
    "== Physical Plan ==\n"
    "* Project (2)\n"
    "+- Scan parquet db.eventos (1)\n"
    "\n"
    "\n"
    "(1) Scan parquet db.eventos\n"
    "Output [2]: [cliente_id#10, dt#12]\n"
    "Batched: true\n"
    "Location: InMemoryFileIndex [s3://lake/eventos]\n"
    "ReadSchema: struct<cliente_id:bigint>\n"
    "\n"
    "(2) Project [codegen id : 1]\n"
    "Output [1]: [cliente_id#10]\n"
    "Input [2]: [cliente_id#10, dt#12]\n"
)

_TERRAFORM_SOURCE = (
    'resource "aws_glue_job" "etl" {\n'
    '  glue_version = "5.0"\n'
    '  worker_type = "G.1X"\n'
    "  number_of_workers = 10\n"
    "}\n"
)

_ICEBERG_DUMP = json.dumps(
    {
        "table": "db.tbl",
        "files": [
            {"file_path": "s3://b/f1.parquet", "file_size_in_bytes": 1024, "record_count": 10}
        ],
    }
)

_SQL_TEXT = "SELECT a, b FROM db.eventos WHERE dt = '2026-01-01'\n"

_PYSPARK_SQL_SOURCE = 'spark.sql("SELECT a FROM db.eventos")\n'

_ATHENA_WORKGROUP_DUMP = json.dumps(
    {
        "workgroups": [
            {
                "name": "primary",
                "engine_version": {
                    "effective_engine_version": "Athena engine version 2",
                    "selected_engine_version": "AUTO",
                },
                "state": "ENABLED",
                "bytes_scanned_cutoff": 1099511627776,
            }
        ]
    }
)


def _open_case(repo):
    call_tool("sparkforge_case_open", {"repo": str(repo), **_CASE_OPEN_ARGS})


def _write_job(repo):
    lib = repo / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return lib


def _write_facts_file(tmp_path):
    lib = _write_job(tmp_path)
    facts = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(facts["items"], ensure_ascii=False), encoding="utf-8")
    return path


def _write_workload_facts_file(tmp_path):
    """Um fact `spark.stage.task_duration`, o suficiente para `skew_risk` sair
    `measured` -- os demais eixos saem `unknown` de proposito, sem `history_path`."""
    path = tmp_path / "workload_facts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "a" * 16,
                    "schema_version": 1,
                    "kind": "spark.stage.task_duration",
                    "subject": {"type": "stage", "symbol": "stage-1", "stage_id": 1},
                    "measures": {"p50_ms": 100, "p95_ms": 1000, "task_count": 20},
                    "attrs": {},
                    "provenance": {},
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


def _capacity_fact(kind, subject, measures=None, attrs=None):
    return {
        "id": "0" * 16,
        "schema_version": 1,
        "kind": kind,
        "subject": subject,
        "measures": measures or {},
        "attrs": attrs or {},
        "provenance": {},
    }


def _capacity_scan(bytes_read):
    return _capacity_fact(
        "spark.sql.scan",
        {
            "type": "plan_node",
            "node_id": 1,
            "operator": "Scan parquet",
            "relation": "db.pedidos",
            "symbol": "0:1",
            "execution_id": 0,
        },
        {"bytes_read": bytes_read},
        {"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
    )


def _capacity_run(run_id, segundos, workers, dpu):
    return _capacity_fact(
        "glue.job_run",
        {"type": "job_run", "job_name": "etl", "job_run_id": run_id, "symbol": run_id},
        {"execution_time_s": segundos, "number_of_workers": workers, "dpu_seconds": dpu},
        {
            "state": "SUCCEEDED",
            "worker_type": "G.2X",
            "glue_version": "5.0",
            "autoscaling": False,
            "dpu_source": "derived",
        },
    )


def _write_capacity_facts_files(tmp_path):
    """Facts do run corrente (SLA declarado + scan) e um diretorio de historico
    com runs suficientes para `candidates`/`chosen` sairem preenchidos -- a
    resolucao de 6 runs comparaveis sustenta o alvo padrao de 0.8."""
    facts_path = tmp_path / "capacity_facts.json"
    facts_path.write_text(
        json.dumps(
            [
                _capacity_fact(
                    "workload.declared",
                    {"type": "job_run", "symbol": "etl"},
                    {"sla_minutes": 10, "reliability_target": 0.8},
                ),
                _capacity_scan(1000),
            ]
        ),
        encoding="utf-8",
    )
    history_dir = tmp_path / "capacity_history"
    history_dir.mkdir()
    for i in range(6):
        (history_dir / f"barato{i}.json").write_text(
            json.dumps([_capacity_run(f"b{i}", 500, 10, 1000.0), _capacity_scan(1000)]),
            encoding="utf-8",
        )
    return facts_path, history_dir


def _write_finops_facts_file(tmp_path):
    """Seis `glue.job_run` de DUAS capacidades e um `workload.declared`, para
    `frontier` sair com duas linhas e `per_sla_outcome` render (a resolucao de
    seis runs comparaveis sustenta o alvo padrao de 0.8, mesma amostra de
    `_write_capacity_facts_files`)."""
    facts_path = tmp_path / "finops_facts.json"
    runs = [_capacity_run(f"b{i}", 500, 10, 1000.0) for i in range(6)]
    facts_path.write_text(
        json.dumps(
            runs
            + [
                _capacity_fact(
                    "workload.declared",
                    {"type": "job_run", "symbol": "etl"},
                    {"sla_minutes": 10, "reliability_target": 0.8},
                )
            ]
        ),
        encoding="utf-8",
    )
    return facts_path


def _write_tune_facts_file(tmp_path):
    """Shuffle medido mais a versao, que e o par minimo que sustenta derivacao.

    Sem `spark.runtime_version` o relatorio recusa por `runtime_unknown` e
    `properties` sai vazio -- e lista vazia valida contra qualquer schema de
    array, que e validar pelo motivo errado.
    """
    facts_path = tmp_path / "tune_facts.json"
    facts_path.write_text(
        json.dumps(
            [
                _capacity_fact(
                    "spark.stage.shuffle",
                    {"type": "stage", "symbol": "stage-4", "stage_id": 4},
                    {"write_bytes": 640 * 1024 * 1024, "read_bytes": 0},
                ),
                _capacity_fact(
                    "spark.runtime_version",
                    {"type": "job_run", "symbol": "app-1"},
                    {},
                    {"component": "spark", "version": "3.5.4"},
                ),
            ]
        ),
        encoding="utf-8",
    )
    return facts_path


_FUNCVAL_JOB = 'def gravar(df):\n    df.write.mode("overwrite").saveAsTable("db.eventos")\n'


def _write_funcval_facts_files(tmp_path):
    """Os DOIS arquivos que `sparkforge_funcval_plan` une.

    O alvo sai do `pyspark.write` (`analyze pyspark`) e o schema/os agregados
    saem do `catalog.table_schema` (`analyze catalog-schema`). Nenhum verbo
    produz os dois no mesmo arquivo -- e e exatamente por isso que
    `facts_paths` e lista: com um arquivo so, os eixos de schema e de agregado
    nunca seriam derivaveis.
    """
    lib = tmp_path / "job"
    lib.mkdir()
    (lib / "carga.py").write_text(_FUNCVAL_JOB, encoding="utf-8")
    catalog_dir = tmp_path / "catalog_dump"
    catalog_dir.mkdir()
    (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")

    produced = (
        ("pyspark", call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})),
        (
            "catalog",
            call_tool("sparkforge_analyze_catalog_schema", {"path": str(catalog_dir)}),
        ),
    )
    paths = []
    for name, payload in produced:
        path = tmp_path / f"{name}_facts.json"
        path.write_text(json.dumps(payload["items"], ensure_ascii=False), encoding="utf-8")
        paths.append(str(path))
    return paths


def _write_funcval_plan_file(tmp_path):
    """O artefato que `sparkforge_funcval_compare` rele. `db.eventos` casa com
    o dump, entao o plano sai com os quatro eixos: `count` e `schema` derivados,
    `agg:sum:cliente_id` derivado do tipo declarado, e `key:cliente_id`
    DECLARADO -- que e o unico jeito de o eixo de chaves existir."""
    plan_path = tmp_path / "plano.json"
    call_tool(
        "sparkforge_funcval_plan",
        {
            "facts_paths": _write_funcval_facts_files(tmp_path),
            "out_path": str(plan_path),
            "keys": ["cliente_id"],
        },
    )
    return plan_path


def _write_funcval_result_files(tmp_path):
    """Os dois resultados que o OPERADOR mediu -- o motor nunca os produz."""
    paths = []
    for name, count in (("antes", 1000), ("depois", 998)):
        path = tmp_path / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "target": "db.eventos",
                    "checks": {
                        "count": {"value": count},
                        "key:cliente_id": {"value": 0},
                    },
                }
            ),
            encoding="utf-8",
        )
        paths.append(path)
    return paths[0], paths[1]


def _event_log_lines(run_ms):
    """Event log minimo com UM stage nomeado `scan` e duas tasks.

    `run_ms` e o unico eixo que os dois lados do benchmark precisam variar:
    `total_task_ms` sai de `mean_ms * task_count` sobre `spark.stage.task_duration`.
    `_EVENT_LOG_LINE` nao serve aqui -- ele so tem `ApplicationStart`, entao nao
    produz stage nenhum e o comparador nao teria o que comparar.
    """
    def task(task_id):
        return {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Type": "ResultTask",
            "Task End Reason": {"Reason": "Success"},
            "Task Info": {
                "Task ID": task_id,
                "Index": task_id,
                "Attempt": 0,
                "Launch Time": 1000,
                "Finish Time": 1000 + run_ms,
                "Executor ID": "1",
                "Host": "10.0.0.11",
                "Failed": False,
                "Killed": False,
            },
            "Task Metrics": {
                "Executor Run Time": run_ms,
                "JVM GC Time": 10,
                "Memory Bytes Spilled": 0,
                "Disk Bytes Spilled": 0,
                "Input Metrics": {"Bytes Read": 1000, "Records Read": 10},
            },
        }

    stage_info = {
        "Stage ID": 0,
        "Stage Attempt ID": 0,
        "Stage Name": "scan",
        "Number of Tasks": 2,
        "Parent IDs": [],
        "Details": "",
    }
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "j", "App ID": "a", "Timestamp": 1},
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {**stage_info, "Submission Time": 100},
        },
        task(0),
        task(1),
        {"Event": "SparkListenerStageCompleted", "Stage Info": stage_info},
    ]
    return "".join(json.dumps(e) + "\n" for e in events)


def _write_event_log_facts_files(tmp_path):
    """Os DOIS arquivos de facts que `sparkforge_benchmark` compara, cada um
    produzido pelo caminho real (`sparkforge_analyze_event_log`)."""
    paths = []
    for name, run_ms in (("before", 200), ("after", 100)):
        log = tmp_path / f"{name}.jsonl"
        log.write_text(_event_log_lines(run_ms), encoding="utf-8")
        facts = call_tool("sparkforge_analyze_event_log", {"path": str(log)})
        path = tmp_path / f"{name}_facts.json"
        path.write_text(json.dumps(facts["items"], ensure_ascii=False), encoding="utf-8")
        paths.append(path)
    return paths[0], paths[1]


class _FakeS3Client:
    def list_objects_v2(self, **kwargs):
        return {"Contents": [{"Key": f"{kwargs['Prefix']}part-00000"}]}

    def get_object(self, **kwargs):
        import io

        return {"Body": io.BytesIO(b'{"Event":"SparkListenerJobStart"}\n')}


class _FakeGlueClient:
    def get_job(self, **kwargs):
        return {"Job": {"Name": kwargs.get("JobName", "job"), "GlueVersion": "5.0"}}

    def get_job_runs(self, **kwargs):
        job_name = kwargs.get("JobName", "job")
        return {
            "JobRuns": [
                {
                    "Id": "jr_1",
                    "JobName": job_name,
                    "JobRunState": "SUCCEEDED",
                    "WorkerType": "G.1X",
                    "NumberOfWorkers": 2,
                    "GlueVersion": "5.0",
                    "ExecutionTime": 120,
                    "StartedOn": "2026-08-26T10:00:00Z",
                    "CompletedOn": "2026-08-26T10:02:00Z",
                }
            ]
        }


class _FakeCloudWatchClient:
    def get_metric_data(self, **kwargs):
        return {"MetricDataResults": []}


class _FakeAthenaClient:
    def __init__(self):
        self._exec_id = 0

    def start_query_execution(self, **kwargs):
        self._exec_id += 1
        return {"QueryExecutionId": f"q{self._exec_id}"}

    def get_query_execution(self, **kwargs):
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_query_results(self, **kwargs):
        return {"ResultSet": {"Rows": []}}

    def get_work_group(self, **kwargs):
        return {
            "WorkGroup": {
                "Name": kwargs.get("WorkGroup", "primary"),
                "State": "ENABLED",
                "Configuration": {
                    "EngineVersion": {
                        "EffectiveEngineVersion": "Athena engine version 3",
                        "SelectedEngineVersion": "AUTO",
                    },
                    "BytesScannedCutoffPerQuery": 100,
                    "ResultConfiguration": {"OutputLocation": "s3://bucket/results/"},
                },
            }
        }


class _FakeEmrClient:
    """Cluster de instance GROUPS: `list_instance_fleets` levanta, como a API
    real faz quando o modelo nao se aplica -- e o caminho que prova que o
    coletor omite a secao em vez de gravar lista vazia."""

    def describe_cluster(self, **kwargs):
        return {
            "Cluster": {
                "Id": kwargs.get("ClusterId", "j-1EXAMPLE"),
                "Name": "etl",
                "ReleaseLabel": "emr-7.5.0",
                "Applications": [{"Name": "Spark", "Version": "3.5.2-amzn-1"}],
                "InstanceCollectionType": "INSTANCE_GROUP",
                "LogUri": "s3://bucket/elasticmapreduce/",
                "AutoTerminate": False,
                "Status": {"State": "RUNNING"},
            }
        }

    def list_instance_groups(self, **kwargs):
        return {
            "InstanceGroups": [
                {
                    "Id": "ig-1",
                    "InstanceGroupType": "MASTER",
                    "Market": "ON_DEMAND",
                    "InstanceType": "m5.xlarge",
                    "RequestedInstanceCount": 1,
                }
            ]
        }

    def list_instance_fleets(self, **kwargs):
        raise RuntimeError("InvalidRequestException: cluster nao usa instance fleets")

    def list_bootstrap_actions(self, **kwargs):
        return {"BootstrapActions": []}

    def get_managed_scaling_policy(self, **kwargs):
        return {}

    def get_auto_termination_policy(self, **kwargs):
        return {"AutoTerminationPolicy": {"IdleTimeout": 3600}}


class _FakeEmrServerlessClient:
    """Uma chamada so: `GetApplication` ja devolve capacidade, auto-stop,
    `runtimeConfiguration` e monitoramento no mesmo objeto -- nao ha o par de
    secoes opcionais que o cluster on EC2 tem."""

    def get_application(self, **kwargs):
        return {
            "application": {
                "applicationId": kwargs.get("applicationId", "00fEXAMPLE"),
                "arn": "arn:aws:emr-serverless:us-east-1:123456789012:/applications/00fEXAMPLE",
                "name": "etl",
                "releaseLabel": "emr-7.5.0",
                "type": "Spark",
                "state": "STARTED",
                "architecture": "X86_64",
                "autoStopConfiguration": {"enabled": True, "idleTimeoutMinutes": 15},
                "initialCapacity": {
                    "DRIVER": {
                        "workerCount": 1,
                        "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"},
                    }
                },
                "runtimeConfiguration": [
                    {
                        "classification": "spark-defaults",
                        "properties": {"spark.executor.cores": "4"},
                    }
                ],
                "monitoringConfiguration": {
                    "s3MonitoringConfiguration": {"logUri": "s3://bucket/emrs-logs/"}
                },
            }
        }


class _FakeEmrContainersClient:
    """DUAS chamadas, em contraste com `_FakeEmrServerlessClient` (uma):
    `DescribeVirtualCluster` e `DescribeJobRun` sao APIs separadas do
    `emr-containers`, e o coletor precisa das duas para montar o arquivo
    autocontido."""

    def describe_virtual_cluster(self, **kwargs):
        return {
            "virtualCluster": {
                "id": kwargs["id"],
                "name": "meu-cluster",
                "state": "RUNNING",
                "containerProvider": {
                    "type": "EKS",
                    "id": "meu-cluster-eks",
                    "info": {"eksInfo": {"namespace": "spark-jobs"}},
                },
            }
        }

    def describe_job_run(self, **kwargs):
        return {
            "jobRun": {
                "id": kwargs["id"],
                "name": "etl-diario",
                "virtualClusterId": kwargs["virtualClusterId"],
                "state": "COMPLETED",
                "releaseLabel": "emr-7.5.0-latest",
            }
        }


class _FakeBoto3ForCollect:
    def __init__(self):
        self._clients = {
            "s3": _FakeS3Client(),
            "glue": _FakeGlueClient(),
            "cloudwatch": _FakeCloudWatchClient(),
            "athena": _FakeAthenaClient(),
            "emr": _FakeEmrClient(),
            "emr-serverless": _FakeEmrServerlessClient(),
            "emr-containers": _FakeEmrContainersClient(),
        }

    def client(self, name, **kwargs):
        return self._clients[name]


_S3_LISTING = json.dumps(
    {
        "Name": "lake",
        "Prefix": "analytics/pedidos/",
        "IsTruncated": False,
        "Contents": [
            {"Key": "analytics/pedidos/dt=2026-07-30/part-0.snappy.parquet", "Size": 4194304}
        ],
    }
)

_EMR_CLUSTER_DUMP = json.dumps(
    {
        "Cluster": {
            "Id": "j-1EXAMPLE",
            "ReleaseLabel": "emr-7.5.0",
            "InstanceCollectionType": "INSTANCE_GROUP",
            "LogUri": "s3://bucket/elasticmapreduce/",
            "AutoTerminate": False,
            "Applications": [{"Name": "Spark", "Version": "3.5.2-amzn-1"}],
            "Configurations": [
                {
                    "Classification": "spark-defaults",
                    "Properties": {"spark.dynamicAllocation.enabled": "true"},
                }
            ],
        },
        "InstanceGroups": [
            {
                "Id": "ig-1",
                "InstanceGroupType": "MASTER",
                "Market": "ON_DEMAND",
                "InstanceType": "m5.xlarge",
                "RequestedInstanceCount": 1,
            }
        ],
    }
)

_EMR_SERVERLESS_DUMP = json.dumps(
    {
        "application": {
            "applicationId": "00fEXAMPLE",
            "name": "etl",
            "releaseLabel": "emr-7.5.0",
            "type": "Spark",
            "state": "STARTED",
            "architecture": "X86_64",
            "autoStopConfiguration": {"enabled": False},
            "initialCapacity": {
                "DRIVER": {
                    "workerCount": 1,
                    "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"},
                },
                "EXECUTOR": {
                    "workerCount": 10,
                    "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"},
                },
            },
            "maximumCapacity": {"cpu": "400vCPU", "memory": "3000GB", "disk": "20000GB"},
            "runtimeConfiguration": [
                {
                    "classification": "spark-defaults",
                    "properties": {"spark.dynamicAllocation.enabled": "true"},
                }
            ],
            "monitoringConfiguration": {
                "s3MonitoringConfiguration": {"logUri": "s3://bucket/emrs-logs/"}
            },
        }
    }
)

_EMR_EKS_DUMP = json.dumps(
    {
        "virtualCluster": {
            "id": "0abcEXAMPLE",
            "name": "analytics",
            "state": "RUNNING",
            "containerProvider": {
                "type": "EKS",
                "id": "analytics-eks",
                "info": {"eksInfo": {"namespace": "spark-jobs"}},
            },
        },
        "jobRun": {
            "id": "0runEXAMPLE",
            "name": "etl-diario",
            "virtualClusterId": "0abcEXAMPLE",
            "state": "COMPLETED",
            "releaseLabel": "emr-7.5.0-latest",
            "executionRoleArn": "arn:aws:iam::123456789012:role/emr-eks",
            "jobDriver": {
                "sparkSubmitJobDriver": {
                    "entryPoint": "s3://bucket/job.py",
                    "sparkSubmitParameters": "--conf spark.executor.cores=4",
                }
            },
            "configurationOverrides": {
                "applicationConfiguration": [
                    {
                        "classification": "spark-defaults",
                        "properties": {"spark.dynamicAllocation.enabled": "true"},
                    }
                ],
                "monitoringConfiguration": {
                    "s3MonitoringConfiguration": {"logUri": "s3://bucket/emrc-logs/"}
                },
            },
        },
    }
)

# Definicao `Jobs-as-Code` com o UNICO job type que a matriz do Automation API
# data dentro da faixa. E de proposito: um payload com `Job:Command` validaria
# contra o schema pelo motivo errado -- nenhum fact de capacidade sairia, e o
# bloco derivado que esta tool existe para produzir ficaria vazio. Objeto vazio
# passa em qualquer schema de objeto.
_CONTROLM_JOBS = json.dumps(
    {
        "PagamentosDiarios": {
            "Type": "Folder",
            "Application": "Financeiro",
            "ExtraiExtrato": {
                "Type": "Job:DetachedEmbeddedScript",
                "RunAs": "ctmagent",
                "Script": "extrai.sh",
            },
        }
    }
)

_CONSUMER_INVENTORY = """consumers:
  - table: glue_catalog.curated.pedidos
    service: athena
"""

# Validacao artesanal COM consequencia: rende `dq.check`, `dq.enforcement` e
# `dq.module_analyzed` no mesmo arquivo, entao o branch exercita o extrator de
# verdade e nao so o fact sentinela que sai de qualquer `.py`.
_DQ_SOURCE = """def validar(vendas):
    ruins = vendas.filter(vendas.valor < 0).count()
    if ruins > 0:
        raise ValueError("valor negativo")
"""

# Mesma exigencia para `analyze graph`: o fonte precisa produzir `graph.import`,
# `graph.construction` e `graph.algorithm` -- nao so o `graph.module_analyzed`
# que sai de qualquer `.py` -- para que o schema declarado seja validado contra
# a saida cheia do extrator, e nao contra a de um arquivo sem grafo nenhum.
_GRAPH_SOURCE = """from graphframes import GraphFrame

def rodar(spark, vertices, arestas):
    v = vertices.cache()
    g = GraphFrame(v, arestas.cache())
    return g.connectedComponents()
"""


def _fake_collect_boto3(monkeypatch):
    """Injeta um client AWS falso para as ferramentas `collect_*` -- nunca toca
    rede nem credenciais de verdade, mesma convencao de `tests/test_collect_aws.py`."""
    from sparkforge.collect import aws as collect_aws
    monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3ForCollect())


_CODE_JOB = (
    "def carregar_particao(df):\n"
    '    """Repartition explicito para o teste ter o que ranquear."""\n'
    "    return df.repartition(200)\n"
    "\n"
    "\n"
    "def principal():\n"
    "    return carregar_particao(None)\n"
)


def _code_tree(tmp_path):
    """Arvore minima COM aresta e COM termo de dominio.

    As duas propriedades sao exigidas e nao decorativas: sem `principal`
    chamando `carregar_particao` nao ha aresta, e `callers`/`impact` sairiam
    vazios -- lista vazia valida contra qualquer schema de array, e o teste
    passaria pelo motivo errado. Sem `repartition` no nome e no corpo, a
    expansao de `code_context` nao casaria nenhum cluster de dominio e a secao
    `rules` da SPEC 77 sairia vazia pela mesma razao.
    """
    raiz = tmp_path / "arvore"
    (raiz / "jobs").mkdir(parents=True)
    (raiz / "jobs" / "etl.py").write_text(_CODE_JOB, encoding="utf-8")
    (raiz / ".gitignore").write_text(".sparkforge/local\n", encoding="utf-8")
    call_tool("sparkforge_code_sync", {"repo": str(raiz)})
    return raiz


def _real_code_output_for(name, tmp_path):
    """Saida REAL das oito tools de Code Intelligence, sobre uma arvore de verdade.

    Cada uma passa pela porta de frescor da SPEC 43 antes de responder, entao
    construir o indice com `sparkforge_code_sync` aqui nao e conveniencia: e o
    unico caminho que existe. Uma chamada sem indice devolveria o ramo de ERRO
    do `oneOf`, e o teste validaria o schema pelo motivo errado -- por isso as
    asercoes abaixo travam o ramo de sucesso.
    """
    if name == "sparkforge_code_sync":
        raiz = tmp_path / "arvore"
        (raiz / "jobs").mkdir(parents=True)
        (raiz / "jobs" / "etl.py").write_text(_CODE_JOB, encoding="utf-8")
        resultado = call_tool("sparkforge_code_sync", {"repo": str(raiz)})
        assert resultado["nodes"] == 2, "a amostra precisa render dois simbolos"
        return resultado

    raiz = _code_tree(tmp_path)

    if name == "sparkforge_code_status":
        resultado = call_tool("sparkforge_code_status", {"repo": str(raiz)})
        assert resultado["initialized"] is True
        assert resultado["security"]["not_measured"], (
            "o bloco de seguranca precisa declarar o que NAO foi medido"
        )
        return resultado

    if name == "sparkforge_code_context":
        resultado = call_tool(
            "sparkforge_code_context",
            {"repo": str(raiz), "task": "otimizar o repartition da carga por particao"},
        )
        assert resultado["entry_points"], "a amostra precisa render pelo menos um ponto de entrada"
        assert resultado["rules"], (
            "a SPEC 77 so esta exercida se a consulta casar cluster de dominio"
        )
        return resultado

    achados = call_tool(
        "sparkforge_code_search", {"repo": str(raiz), "query": "carregar_particao"}
    )
    assert achados["results"], "a busca precisa achar o simbolo da amostra"
    if name == "sparkforge_code_search":
        return achados

    if name == "sparkforge_code_shape":
        resultado = call_tool("sparkforge_code_shape", {"repo": str(raiz)})
        # O ALGORITMO e o que este teste prende: sem ele no corpo, a particao
        # sairia com cara de canonica, e ela nao e.
        assert resultado["communities"]["algorithm"]
        assert resultado["communities"]["total"] >= 1
        return resultado

    node_id = achados["results"][0]["node_id"]
    if name == "sparkforge_code_path":
        # Origem e destino SAO o mesmo no, e de proposito: a amostra tem um
        # chamador resolvido mas nao garante um par a distancia conhecida, e um
        # caminho de zero saltos exercita o schema inteiro -- `found`, `reason`
        # nulo, `path` de um item e as cinco contagens de `graph`. O que este
        # teste prende e a FORMA da resposta; a topologia esta em
        # `tests/test_codeintel_graph_caminho.py`, sobre corpus sintetico.
        resultado = call_tool(
            "sparkforge_code_path",
            {"repo": str(raiz), "origem": node_id, "destino": node_id},
        )
        assert resultado["found"] is True
        assert resultado["reason"] is None
        return resultado

    if name == "sparkforge_code_symbol":
        resultado = call_tool(
            "sparkforge_code_symbol", {"repo": str(raiz), "node_id": node_id}
        )
        assert resultado["callers"], "a amostra precisa ter um chamador resolvido"
        return resultado

    resultado = call_tool("sparkforge_code_read", {"repo": str(raiz), "node_id": node_id})
    assert resultado["snippet"]["code"], "o trecho nao pode sair vazio"
    return resultado


def _real_output_for(name, tmp_path, monkeypatch=None):
    """Chama `name` com argumentos realistas, criando qualquer estado
    (case, facts) de que a ferramenta dependa, e devolve o dict cru que um
    cliente MCP receberia como `structuredContent`."""
    if name == "sparkforge_case_open":
        return call_tool("sparkforge_case_open", {"repo": str(tmp_path), **_CASE_OPEN_ARGS})

    if name == "sparkforge_case_get":
        _open_case(tmp_path)
        return call_tool("sparkforge_case_get", {"repo": str(tmp_path)})

    if name == "sparkforge_case_update":
        _open_case(tmp_path)
        return call_tool(
            "sparkforge_case_update",
            {
                "repo": str(tmp_path),
                "phase": "facts",
                "gate": "baseline_captured",
                "gate_value": True,
                "skill": "analyze-spark-plan",
                "now": "2026-07-30T01:00:00Z",
                "outcome": "ok",
            },
        )

    if name == "sparkforge_next_step":
        _open_case(tmp_path)
        return call_tool("sparkforge_next_step", {"repo": str(tmp_path)})

    if name == "sparkforge_resume":
        _open_case(tmp_path)
        return call_tool(
            "sparkforge_resume", {"repo": str(tmp_path), "findings": [], "unresolved": 0}
        )

    if name == "sparkforge_playbook":
        return call_tool(
            "sparkforge_playbook",
            {"coordinator": "glue-infra-reviewer", "repo": str(tmp_path)},
        )

    if name == "sparkforge_runtime_detect":
        return call_tool("sparkforge_runtime_detect", {"glue": "5.0"})

    if name == "sparkforge_knowledge_path":
        return call_tool("sparkforge_knowledge_path", {"file": "glue/runtime-matrix.md"})

    if name == "sparkforge_analyze_pyspark":
        lib = _write_job(tmp_path)
        return call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})

    if name == "sparkforge_judge":
        lib = _write_job(tmp_path)
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
        return call_tool(
            "sparkforge_judge",
            {"facts": facts["items"], "glue": "5.0", "show_skipped": True},
        )

    if name == "sparkforge_rules_lookup":
        return call_tool("sparkforge_rules_lookup", {"id": ["SF-PY-007"]})

    if name == "sparkforge_validate_output":
        payload = {
            "rule_id": "SF-PY-005",
            "schema_version": 1,
            "title": "t",
            "severity": "P0",
            "confidence": "high",
            "status": "structural",
            "subject": {"type": "source_location"},
            "evidence": ["f_abc123"],
        }
        return call_tool("sparkforge_validate_output", {"finding": payload})

    if name == "sparkforge_analyze_catalog_schema":
        catalog_dir = tmp_path / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_catalog_schema", {"path": str(catalog_dir)})

    if name == "sparkforge_analyze_event_log":
        log_path = tmp_path / "log.jsonl"
        log_path.write_text(_EVENT_LOG_LINE, encoding="utf-8")
        return call_tool("sparkforge_analyze_event_log", {"path": str(log_path)})

    if name == "sparkforge_analyze_sql_metrics":
        log_path = tmp_path / "sql_metrics_log.jsonl"
        log_path.write_text(_SQL_METRICS_EVENT_LOG_LINES, encoding="utf-8")
        resultado = call_tool("sparkforge_analyze_sql_metrics", {"path": str(log_path)})
        assert any(item["kind"] == "spark.sql.scan" for item in resultado["items"]), (
            "a amostra precisa render pelo menos um fact spark.sql.scan"
        )
        return resultado

    if name == "sparkforge_analyze_cloudwatch":
        cw_path = tmp_path / "cw.json"
        cw_path.write_text(_CLOUDWATCH_ARTIFACT, encoding="utf-8")
        return call_tool("sparkforge_analyze_cloudwatch", {"path": str(cw_path)})

    if name == "sparkforge_analyze_glue_job_runs":
        runs_dir = tmp_path / "glue_job_run"
        runs_dir.mkdir()
        (runs_dir / "etl-job_jr_1.json").write_text(_GLUE_JOB_RUN_ARTIFACT, encoding="utf-8")
        return call_tool(
            "sparkforge_analyze_glue_job_runs",
            {"path": str(runs_dir), "job_name": "etl-job"},
        )

    if name == "sparkforge_analyze_plan":
        plan_path = tmp_path / "plan.txt"
        plan_path.write_text(_PLAN_TEXT, encoding="utf-8")
        return call_tool("sparkforge_analyze_plan", {"path": str(plan_path)})

    if name == "sparkforge_analyze_terraform":
        tf_path = tmp_path / "main.tf"
        tf_path.write_text(_TERRAFORM_SOURCE, encoding="utf-8")
        return call_tool("sparkforge_analyze_terraform", {"path": str(tf_path)})

    if name == "sparkforge_analyze_iceberg":
        ice_path = tmp_path / "iceberg.json"
        ice_path.write_text(_ICEBERG_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_iceberg", {"path": str(ice_path)})

    if name == "sparkforge_analyze_sql":
        sql_path = tmp_path / "q.sql"
        sql_path.write_text(_SQL_TEXT, encoding="utf-8")
        return call_tool("sparkforge_analyze_sql", {"path": str(sql_path)})

    if name == "sparkforge_analyze_athena_workgroup":
        wg_path = tmp_path / "wg.json"
        wg_path.write_text(_ATHENA_WORKGROUP_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_athena_workgroup", {"path": str(wg_path)})

    if name == "sparkforge_analyze_emr_cluster":
        emr_path = tmp_path / "cluster.json"
        emr_path.write_text(_EMR_CLUSTER_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_emr_cluster", {"path": str(emr_path)})

    if name == "sparkforge_analyze_emr_serverless":
        emrs_path = tmp_path / "application.json"
        emrs_path.write_text(_EMR_SERVERLESS_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_emr_serverless", {"path": str(emrs_path)})

    if name == "sparkforge_analyze_emr_eks":
        emrc_path = tmp_path / "job_run.json"
        emrc_path.write_text(_EMR_EKS_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_emr_eks", {"path": str(emrc_path)})

    if name == "sparkforge_analyze_controlm_jobs":
        # `version` DECLARADA e abaixo da fronteira que a matriz le em
        # `9.0.22.005`: e a unica combinacao que resolve os tres blocos que esta
        # tool existe para produzir -- inventario, `ctm.version_declared` e o
        # kind derivado do cruzamento. Sem `version` o derivado sairia como
        # recusa, e a saida validaria contra o schema sem provar o cruzamento.
        ctm_path = tmp_path / "jobs.json"
        ctm_path.write_text(_CONTROLM_JOBS, encoding="utf-8")
        resultado = call_tool(
            "sparkforge_analyze_controlm_jobs",
            {"path": str(ctm_path), "version": "9.0.21.300"},
        )
        assert resultado["by_kind"].get("ctm.capability_incompatible") == 1, resultado["by_kind"]
        assert resultado["by_kind"].get("ctm.version_declared") == 1, resultado["by_kind"]
        return resultado

    if name == "sparkforge_analyze_data_quality":
        dq_path = tmp_path / "validacao.py"
        dq_path.write_text(_DQ_SOURCE, encoding="utf-8")
        return call_tool("sparkforge_analyze_data_quality", {"path": str(dq_path)})

    if name == "sparkforge_analyze_graph":
        graph_path = tmp_path / "grafo.py"
        graph_path.write_text(_GRAPH_SOURCE, encoding="utf-8")
        return call_tool("sparkforge_analyze_graph", {"path": str(graph_path)})

    if name == "sparkforge_analyze_s3_listing":
        listing = tmp_path / "listing.json"
        listing.write_text(_S3_LISTING, encoding="utf-8")
        return call_tool("sparkforge_analyze_s3_listing", {"path": str(listing)})

    if name == "sparkforge_analyze_consumers":
        inventory = tmp_path / "consumers.yaml"
        inventory.write_text(_CONSUMER_INVENTORY, encoding="utf-8")
        return call_tool("sparkforge_analyze_consumers", {"path": str(inventory)})

    if name == "sparkforge_analyze_terraform_diff":
        before = tmp_path / "before"
        after = tmp_path / "after"
        before.mkdir()
        after.mkdir()
        (before / "main.tf").write_text(_TERRAFORM_SOURCE, encoding="utf-8")
        (after / "main.tf").write_text(
            _TERRAFORM_SOURCE.replace("G.1X", "G.4X"), encoding="utf-8"
        )
        return call_tool(
            "sparkforge_analyze_terraform_diff", {"before": str(before), "after": str(after)}
        )

    if name == "sparkforge_analyze_call_graph":
        facts_path = _write_facts_file(tmp_path)
        return call_tool("sparkforge_analyze_call_graph", {"facts_path": str(facts_path)})

    if name == "sparkforge_benchmark":
        before, after = _write_event_log_facts_files(tmp_path)
        return call_tool(
            "sparkforge_benchmark", {"before_path": str(before), "after_path": str(after)}
        )

    if name == "sparkforge_funcval_plan":
        return call_tool(
            "sparkforge_funcval_plan",
            {
                "facts_paths": _write_funcval_facts_files(tmp_path),
                "out_path": str(tmp_path / "plano.json"),
                "keys": ["cliente_id"],
            },
        )

    if name == "sparkforge_funcval_compare":
        plan_path = _write_funcval_plan_file(tmp_path)
        before, after = _write_funcval_result_files(tmp_path)
        return call_tool(
            "sparkforge_funcval_compare",
            {
                "plan_path": str(plan_path),
                "before_path": str(before),
                "after_path": str(after),
            },
        )

    if name == "sparkforge_fuse":
        facts_path = _write_facts_file(tmp_path)
        return call_tool("sparkforge_fuse", {"facts_paths": [str(facts_path)]})

    if name == "sparkforge_workload":
        facts_path = _write_workload_facts_file(tmp_path)
        return call_tool(
            "sparkforge_workload",
            {"facts_path": str(facts_path), "job_name": "etl", "job_run_id": "jr_1"},
        )

    if name == "sparkforge_capacity":
        facts_path, history_dir = _write_capacity_facts_files(tmp_path)
        result = call_tool(
            "sparkforge_capacity",
            {
                "facts_path": str(facts_path),
                "job_name": "etl",
                "job_run_id": "jr_hoje",
                "history_path": str(history_dir),
            },
        )
        assert result["chosen"], "a amostra precisa render uma capacidade escolhida"
        return result

    if name == "sparkforge_finops":
        facts_path = _write_finops_facts_file(tmp_path)
        result = call_tool(
            "sparkforge_finops", {"facts_path": str(facts_path), "job_name": "etl"}
        )
        assert result["frontier"], "a amostra precisa render ao menos uma capacidade"
        return result

    if name == "sparkforge_tune":
        facts_path = _write_tune_facts_file(tmp_path)
        result = call_tool("sparkforge_tune", {"facts_path": str(facts_path)})
        assert result["properties"], "a amostra precisa render ao menos uma proposta"
        return result

    if name == "sparkforge_economy_report":
        result = call_tool("sparkforge_economy_report", {"run_id": "run_inexistente"})
        assert result["unresolved"], "a amostra precisa render ao menos uma lacuna"
        return result

    if name == "sparkforge_glue_dependency_audit":
        # Pin abaixo do piso que `SF-SPARK4-003` declara para Spark 4.1: a
        # amostra precisa render achado, senao valida contra o schema pelo
        # motivo errado -- lista vazia passa em qualquer schema de array.
        job = tmp_path / "dep-audit"
        job.mkdir()
        (job / "job.py").write_text("import pyarrow\n", encoding="utf-8")
        (job / "requirements.txt").write_text("pyarrow==8.0.0\n", encoding="utf-8")
        result = call_tool(
            "sparkforge_glue_dependency_audit", {"path": str(job), "glue": "6.0"}
        )
        assert result["dependencies"], "a amostra precisa observar ao menos um pin"
        return result

    if name == "sparkforge_iceberg_assess_upgrade":
        job = tmp_path / "assess-upgrade"
        (job / ".sparkforge").mkdir(parents=True)
        (job / "job.py").write_text("x = 1\n", encoding="utf-8")
        (job / ".sparkforge" / "consumers.yaml").write_text(
            "consumers:\n  - table: db.t\n    service: athena\n", encoding="utf-8"
        )
        result = call_tool(
            "sparkforge_iceberg_assess_upgrade",
            {"path": str(job), "source": 2, "target": 3},
        )
        assert result["cells"], "a amostra precisa consultar ao menos uma celula"
        return result

    if name == "sparkforge_release_describe":
        # `emr_ec2`/`7.7.0` de proposito: a release resolve cinco componentes E
        # recusa quatro. Uma release sem recusa nenhuma validaria contra o
        # schema pelo motivo errado -- `unresolved` vazio passa em qualquer
        # schema de array.
        resultado = call_tool(
            "sparkforge_release_describe", {"platform": "emr_ec2", "release": "7.7.0"}
        )
        assert resultado["components"], "a amostra precisa resolver ao menos um componente"
        assert resultado["unresolved"], "a amostra precisa recusar ao menos um componente"
        return resultado

    if name == "sparkforge_release_diff":
        # O CONTRAFACTUAL DE PLATAFORMA, e nao duas releases da mesma: o mesmo
        # rotulo `7.7.0` publica Iceberg e Spark diferentes no EC2 e no EKS, e e
        # esse par que faz `changed` sair nao-vazio com `axis == ["platform"]`.
        resultado = call_tool(
            "sparkforge_release_diff",
            {
                "left_platform": "emr_ec2",
                "left_release": "7.7.0",
                "right_platform": "emr_eks",
                "right_release": "7.7.0",
            },
        )
        assert resultado["axis"] == ["platform"], resultado["axis"]
        assert resultado["changed"], "a amostra precisa render ao menos uma mudanca"
        assert resultado["unresolved"], "as cinco dimensoes sem lastro saem sempre"
        return resultado

    if name == "sparkforge_controlm_describe":
        # `9.0.22.010` de proposito: e a versao que resolve os DOIS eixos de uma
        # vez -- capacidades introduzidas, uma capacidade DEPRECIADA
        # (`config em:param::set`, de `9.0.21.300`) e exigencia de componente
        # (`java`, `python`, `pip`). Uma versao do piso da faixa validaria contra
        # o schema pelo motivo errado: `deprecated` e `components` sairiam
        # vazios, e objeto vazio passa em qualquer schema de objeto.
        resultado = call_tool("sparkforge_controlm_describe", {"version": "9.0.22.010"})
        assert resultado["capabilities"], "a amostra precisa resolver capacidade"
        assert resultado["deprecated"], "a amostra precisa render o eixo de depreciacao"
        assert resultado["components"], "a amostra precisa render exigencia de componente"
        assert resultado["unresolved"], "as recusas nomeadas saem sempre"
        return resultado

    if name == "sparkforge_migration_assess":
        # Um job com SDK v1 e um pin de PyArrow abaixo do piso do Spark 4.1:
        # o primeiro faz `SF-MIG-001` nascer, o segundo faz `SF-SPARK4-003`
        # nascer -- e o segundo so aparece porque a entrada e um DIRETORIO.
        # Assessment vazio validaria contra o schema pelo motivo errado.
        job = tmp_path / "job"
        job.mkdir()
        (job / "job.py").write_text(
            "import com.amazonaws.services.s3.AmazonS3\n", encoding="utf-8"
        )
        (job / "requirements.txt").write_text("pyarrow==14.0.0\n", encoding="utf-8")
        result = call_tool(
            "sparkforge_migration_assess",
            {"path": str(job), "source": "4.0", "target": "6.0"},
        )
        assert result["findings"], "a amostra precisa render pelo menos um finding"
        return result

    if name in (
        "sparkforge_collect_event_log",
        "sparkforge_collect_glue_job",
        "sparkforge_collect_cloudwatch",
        "sparkforge_collect_glue_job_runs",
        "sparkforge_collect_iceberg_metadata",
        "sparkforge_collect_athena_workgroup",
        "sparkforge_collect_emr_cluster",
        "sparkforge_collect_emr_serverless",
        "sparkforge_collect_emr_eks",
    ):
        assert monkeypatch is not None, f"{name} precisa de monkeypatch para o client AWS falso"
        _fake_collect_boto3(monkeypatch)
        args = {
            "sparkforge_collect_event_log": {
                "repo": str(tmp_path),
                "job_run_id": "jr_1",
                "bucket": "my-bucket",
                "prefix": "spark-logs",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_glue_job": {
                "repo": str(tmp_path),
                "job_name": "etl-job",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_cloudwatch": {
                "repo": str(tmp_path),
                "job_name": "etl-job",
                "job_run_id": "jr_1",
                "start": "2026-07-29T00:00:00Z",
                "end": "2026-07-30T00:00:00Z",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_glue_job_runs": {
                "repo": str(tmp_path),
                "job_name": "etl-job",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_iceberg_metadata": {
                "repo": str(tmp_path),
                "table": "db.tbl",
                "workgroup": "primary",
                "output_location": "s3://athena-results/",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_athena_workgroup": {
                "repo": str(tmp_path),
                "workgroup": "primary",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_emr_cluster": {
                "repo": str(tmp_path),
                "cluster_id": "j-1EXAMPLE",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_emr_serverless": {
                "repo": str(tmp_path),
                "application_id": "00fEXAMPLE",
                "now": "2026-07-30T00:00:00Z",
            },
            # Os DOIS ids, porque `DescribeJobRun` exige `virtualClusterId`
            # junto do `id` -- nao ha forma de pedir um job run sozinho.
            "sparkforge_collect_emr_eks": {
                "repo": str(tmp_path),
                "virtual_cluster_id": "0abcEXAMPLE",
                "job_run_id": "0runEXAMPLE",
                "now": "2026-07-30T00:00:00Z",
            },
        }[name]
        return call_tool(name, args)

    if name in ("sparkforge_report_sign", "sparkforge_report_verify"):
        lib = _write_job(tmp_path)
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
        judged = call_tool("sparkforge_judge", {"facts": facts["items"], "glue": "5.0"})
        # Sem finding, `report sign` recusa por desenho -- e o dict de erro
        # validaria contra o ramo de erro do `oneOf`, fazendo o teste passar
        # pelo motivo errado. A asercao trava o branch no caminho de sucesso.
        assert judged["items"], "o job de amostra precisa render pelo menos um finding"
        findings_path = tmp_path / "findings.json"
        findings_path.write_text(json.dumps(judged["items"]), encoding="utf-8")
        report = tmp_path / "relatorio.md"
        report.write_text(
            "# Relatorio de Performance\n\n## 1. Resumo executivo\n\n"
            "- Gargalo dominante: escrita com coalesce(1)\n",
            encoding="utf-8",
        )
        args = {"report_path": str(report), "findings_path": str(findings_path)}
        signed = call_tool("sparkforge_report_sign", args)
        if name == "sparkforge_report_sign":
            return signed
        return call_tool("sparkforge_report_verify", args)

    if name == "sparkforge_collect_verify":
        return call_tool("sparkforge_collect_verify", {"repo": str(tmp_path)})

    if name in (
        "sparkforge_code_context",
        "sparkforge_code_search",
        "sparkforge_code_symbol",
        "sparkforge_code_path",
        "sparkforge_code_shape",
        "sparkforge_code_read",
        "sparkforge_code_status",
        "sparkforge_code_sync",
    ):
        return _real_code_output_for(name, tmp_path)

    raise AssertionError(f"sem construtor de argumentos reais para {name}")


class TestRealOutputValidatesAgainstItsOwnSchema:
    """O ponto do trabalho: sem isto, os schemas sao documentacao que pode
    apodrecer a qualquer refactor de `_core.py` sem que nenhum teste perceba."""

    @pytest.mark.parametrize("name", sorted(TOOLS))
    def test_real_output_matches_declared_schema(self, name, tmp_path, monkeypatch):
        result = _real_output_for(name, tmp_path, monkeypatch)
        jsonschema.validate(result, TOOLS[name]["outputSchema"])

    def test_judge_error_shape_also_matches_its_schema(self, tmp_path):
        """`facts_path` ausente e o outro branch do `oneOf` de sparkforge_judge:
        um dict de erro de fronteira, nunca uma excecao."""
        result = call_tool("sparkforge_judge", {"facts_path": str(tmp_path / "nope.json")})
        assert "error" in result
        jsonschema.validate(result, TOOLS["sparkforge_judge"]["outputSchema"])


class TestErrorShapesValidateToo:
    """`call_tool` converte AdapterError em `{"error", "exit_code"}` em vez de
    propagar excecao. Um schema so-de-sucesso e promessa falsa: o cliente que
    validar uma resposta de "case nao existe" recebe falha de validacao em cima
    de um erro que a tool ja tratou corretamente."""

    FAILABLE = (
        ("sparkforge_case_get", {"repo": "<tmp>"}),
        ("sparkforge_case_update", {"repo": "<tmp>", "phase": "diagnosis"}),
        ("sparkforge_next_step", {"repo": "<tmp>"}),
        ("sparkforge_resume", {"repo": "<tmp>"}),
        ("sparkforge_playbook", {"coordinator": "nao-existe", "repo": "<tmp>"}),
        ("sparkforge_analyze_pyspark", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_catalog_schema", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_event_log", {"path": "<tmp>/inexistente.jsonl"}),
        ("sparkforge_analyze_plan", {"path": "<tmp>/inexistente.txt"}),
        ("sparkforge_analyze_terraform", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_iceberg", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_sql", {"path": "<tmp>/inexistente.sql"}),
        ("sparkforge_analyze_athena_workgroup", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_emr_cluster", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_emr_serverless", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_emr_eks", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_controlm_jobs", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_data_quality", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_graph", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_call_graph", {"facts_path": "<tmp>/nao-existe.json"}),
        (
            "sparkforge_migration_assess",
            {"path": "<tmp>/inexistente", "source": "4.0", "target": "6.0"},
        ),
        (
            "sparkforge_glue_dependency_audit",
            {"path": "<tmp>/inexistente", "glue": "6.0"},
        ),
        (
            "sparkforge_iceberg_assess_upgrade",
            {"path": "<tmp>/inexistente", "source": 2, "target": 3},
        ),
        # Release desconhecida, e nao plataforma desconhecida, porque
        # `platform` declara `enum` no inputSchema: um valor fora dele seria
        # entrada invalida antes de ser erro de fronteira, e o que este teste
        # cobra e o SEGUNDO. A plataforma fora das quatro tem o seu proprio
        # caminho, com a lista das quatro na mensagem.
        ("sparkforge_release_describe", {"platform": "glue", "release": "99.9"}),
        # Versao ACIMA do teto da faixa, e ela existe de verdade na fonte
        # (`9.0.22.125`, agosto de 2026). O erro que se cobra nao e "numero
        # invalido": e a recusa de EXTRAPOLAR para fora do passado fechado que a
        # matriz leu.
        ("sparkforge_controlm_describe", {"version": "9.0.22.125"}),
        (
            "sparkforge_release_diff",
            {
                "left_platform": "glue",
                "left_release": "5.0",
                "right_platform": "glue",
                "right_release": "99.9",
            },
        ),
        (
            "sparkforge_benchmark",
            {"before_path": "<tmp>/nao-existe.json", "after_path": "<tmp>/nao-existe.json"},
        ),
        (
            "sparkforge_funcval_plan",
            {"facts_paths": ["<tmp>/nao-existe.json"], "out_path": "<tmp>/plano.json"},
        ),
        (
            "sparkforge_funcval_compare",
            {
                "plan_path": "<tmp>/nao-existe.json",
                "before_path": "<tmp>/antes.json",
                "after_path": "<tmp>/depois.json",
            },
        ),
        ("sparkforge_fuse", {"facts_paths": ["<tmp>/nao-existe.json"]}),
        (
            "sparkforge_workload",
            {
                "facts_path": "<tmp>/nao-existe.json",
                "job_name": "etl",
                "job_run_id": "jr_1",
            },
        ),
        ("sparkforge_judge", {"facts_path": "<tmp>/nao-existe.json"}),
        (
            "sparkforge_report_sign",
            {"report_path": "<tmp>/nao-existe.md", "findings_path": "<tmp>/nada.json"},
        ),
        (
            "sparkforge_report_verify",
            {"report_path": "<tmp>/nao-existe.md", "findings_path": "<tmp>/nada.json"},
        ),
    )

    @staticmethod
    def _resolve(value, tmp_path):
        """Substitui `<tmp>` pelo tmp_path real, preservando listas -- `str(v)`
        num valor de lista (`facts_paths`) produziria `"['<tmp>/x.json']"`, uma
        string malformada em vez de uma lista real."""
        if isinstance(value, list):
            return [str(v).replace("<tmp>", str(tmp_path)) for v in value]
        return str(value).replace("<tmp>", str(tmp_path))

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_response_validates_against_its_own_schema(self, name, args, tmp_path):
        import jsonschema

        resolved = {k: self._resolve(v, tmp_path) for k, v in args.items()}
        result = call_tool(name, resolved)
        assert "error" in result, f"{name} deveria ter falhado neste input"
        jsonschema.validate(result, TOOLS[name]["outputSchema"])

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_message_is_actionable(self, name, args, tmp_path):
        resolved = {k: self._resolve(v, tmp_path) for k, v in args.items()}
        message = call_tool(name, resolved)["error"]
        assert "sparkforge" in message, f"{name}: erro sem comando que resolve"

    def test_every_failable_tool_declares_both_shapes(self):
        for name, _ in self.FAILABLE:
            assert "oneOf" in TOOLS[name]["outputSchema"], name


class TestGlueJobRunTools:
    def test_the_three_new_tools_are_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        novas = {
            "sparkforge_collect_glue_job_runs",
            "sparkforge_analyze_cloudwatch",
            "sparkforge_analyze_glue_job_runs",
        }
        assert novas <= set(tools.TOOLS)
        assert novas <= set(tools._HANDLERS)

    def test_the_three_new_tools_are_listed_in_the_manifest(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        listadas = set(manifest["tools"])
        assert {
            "sparkforge_analyze_cloudwatch",
            "sparkforge_analyze_glue_job_runs",
            "sparkforge_collect_glue_job_runs",
        } <= listadas


class TestSqlMetricsTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_analyze_sql_metrics" in tools.TOOLS
        assert "sparkforge_analyze_sql_metrics" in tools._HANDLERS

    def test_the_tool_is_listed_in_the_manifest(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert "sparkforge_analyze_sql_metrics" in set(manifest["tools"])


class TestWorkloadTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_workload" in tools.TOOLS
        assert "sparkforge_workload" in tools._HANDLERS

    def test_the_tool_is_listed_in_the_manifest(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert "sparkforge_workload" in set(manifest["tools"])


class TestCapacityTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_capacity" in tools.TOOLS
        assert "sparkforge_capacity" in tools._HANDLERS


class TestFinopsTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_finops" in tools.TOOLS
        assert "sparkforge_finops" in tools._HANDLERS
