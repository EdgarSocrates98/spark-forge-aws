import io
import json

import pytest

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import call_tool
from sparkforge.collect import aws as collect_aws

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


def run(args, capsys):
    code = main(args)
    return code, capsys.readouterr().out


class TestAnalyze:
    def test_writes_facts_json(self, repo, capsys):
        out = repo / "facts.json"
        code, _ = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "pyspark.partitioning" for f in facts)

    def test_prints_summary_to_stdout(self, repo, capsys):
        _, output = run(["analyze", "pyspark", "--path", str(repo / "lib")], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "by_kind" in payload

    def test_filter_by_kind(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--kind", "pyspark.partitioning"],
            capsys,
        )
        assert set(json.loads(output)["by_kind"]) == {"pyspark.partitioning"}

    def test_limit_reports_truncation(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--limit", "1"], capsys
        )
        payload = json.loads(output)
        assert payload["returned_count"] == 1
        assert payload["filters_applied"]["limit"] == 1


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


class TestAnalyzeCatalogSchema:
    def _dump(self, repo):
        catalog_dir = repo / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        return catalog_dir

    def test_writes_facts_json(self, repo, capsys):
        catalog_dir = self._dump(repo)
        out = repo / "catalog_facts.json"
        code, _ = run(
            ["analyze", "catalog-schema", "--path", str(catalog_dir), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "catalog.table_schema" for f in facts)

    def test_prints_summary_to_stdout(self, repo, capsys):
        catalog_dir = self._dump(repo)
        _, output = run(["analyze", "catalog-schema", "--path", str(catalog_dir)], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "by_kind" in payload

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(
            ["analyze", "catalog-schema", "--path", str(repo / "nope")], capsys
        )
        assert code == 2


class TestFuse:
    def _sql_facts(self, repo, capsys):
        lib = repo / "sql"
        lib.mkdir()
        (lib / "q.sql").write_text("SELECT * FROM db.eventos\n", encoding="utf-8")
        # Nao ha `analyze sql` na CLI (extrator de SQL nao esta cabeado, mesmo
        # gap dos outros extratores da Fase 1) -- gera o arquivo de facts
        # direto pela API Python, como um coletor externo faria.
        from sparkforge.facts.sql_literal import extract_sql_path

        facts = extract_sql_path(lib / "q.sql", repo_root=lib)
        path = repo / "sql_facts.json"
        path.write_text(
            json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _catalog_facts(self, repo, capsys):
        catalog_dir = repo / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        out = repo / "catalog_facts.json"
        run(["analyze", "catalog-schema", "--path", str(catalog_dir), "--out", str(out)], capsys)
        return out

    def test_combines_two_sources_and_produces_enriched_facts(self, repo, capsys):
        sql_path = self._sql_facts(repo, capsys)
        catalog_path = self._catalog_facts(repo, capsys)
        out = repo / "fused.json"
        code, output = run(
            [
                "fuse",
                "--facts", str(sql_path),
                "--facts", str(catalog_path),
                "--out", str(out),
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["summary"]["measures"]["enriched_count"] == 1
        fused = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "sql.projection.enriched" for f in fused)

    def test_fused_facts_feed_judge_directly(self, repo, capsys):
        sql_path = self._sql_facts(repo, capsys)
        catalog_path = self._catalog_facts(repo, capsys)
        fused_path = repo / "fused.json"
        run(
            [
                "fuse",
                "--facts", str(sql_path),
                "--facts", str(catalog_path),
                "--out", str(fused_path),
            ],
            capsys,
        )
        _, output = run(
            ["judge", "--facts", str(fused_path), "--athena", "*"], capsys
        )
        payload = json.loads(output)
        assert "SF-ATH-001" in {f["rule_id"] for f in payload["items"]}

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        code, _ = run(["fuse", "--facts", str(repo / "nope.json")], capsys)
        assert code == 2


class TestJudge:
    def _facts(self, repo, capsys):
        path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(path)], capsys)
        return path

    def test_produces_sf_py_005(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        out = repo / "findings.json"
        code, _ = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--out", str(out)], capsys
        )
        assert code == 0
        assert [f["rule_id"] for f in json.loads(out.read_text(encoding="utf-8"))] == ["SF-PY-005"]

    def test_severity_filter(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--severity", "P4"], capsys
        )
        assert json.loads(output)["returned_count"] == 0

    def test_reports_skipped_rules_with_reason(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--show-skipped"], capsys
        )
        payload = json.loads(output)
        assert payload["skipped"]
        assert {"requires_facts", "runtime_scope"} & {s["reason"] for s in payload["skipped"]}


TF_WITH_RETRIES = '''resource "aws_glue_job" "etl" {
  name         = "etl"
  glue_version = "5.0"
  max_retries  = 2

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://b/logs/"
  }
}
'''

APPEND_WRITE = 'df.write.mode("append").parquet("s3://b/p")\n'


class TestJudgeCombinesFactsFromSeveralExtractors:
    """`SF-GLUE-004` correlaciona `tf.attribute` (max_retries) com
    `pyspark.write` (mode append) -- metade da evidencia vem do Terraform,
    metade do codigo. Com `judge --facts` aceitando um unico arquivo, avaliar
    essa regra exigia o operador concatenar dois arrays JSON na mao; quem nao
    fizesse isso simplesmente nunca via a regra disparar. `fuse --facts` ja e
    repetivel pela mesma razao."""

    def _tf_facts(self, repo, capsys):
        tf_dir = repo / "infra"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(TF_WITH_RETRIES, encoding="utf-8")
        out = repo / "tf_facts.json"
        run(["analyze", "terraform", "--path", str(tf_dir), "--out", str(out)], capsys)
        return out

    def _py_facts(self, repo, capsys):
        lib = repo / "job"
        lib.mkdir()
        (lib / "w.py").write_text(APPEND_WRITE, encoding="utf-8")
        out = repo / "py_facts.json"
        run(["analyze", "pyspark", "--path", str(lib), "--out", str(out)], capsys)
        return out

    def test_repeated_facts_flag_lets_sf_glue_004_fire(self, repo, capsys):
        tf_path = self._tf_facts(repo, capsys)
        py_path = self._py_facts(repo, capsys)
        code, output = run(
            [
                "judge",
                "--facts", str(tf_path),
                "--facts", str(py_path),
                "--glue", "5.0",
            ],
            capsys,
        )
        assert code == 0
        assert "SF-GLUE-004" in {f["rule_id"] for f in json.loads(output)["items"]}

    def test_each_file_alone_never_fires_the_correlated_rule(self, repo, capsys):
        for path in (self._tf_facts(repo, capsys), self._py_facts(repo, capsys)):
            _, output = run(["judge", "--facts", str(path), "--glue", "5.0"], capsys)
            assert "SF-GLUE-004" not in {f["rule_id"] for f in json.loads(output)["items"]}

    def test_single_file_invocation_is_unchanged(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(["judge", "--facts", str(facts_path), "--glue", "5.0"], capsys)
        assert [f["rule_id"] for f in json.loads(output)["items"]] == ["SF-PY-005"]

    def test_overlapping_files_do_not_duplicate_evidence(self, repo, capsys):
        """O mesmo arquivo duas vezes nao pode virar duas evidencias do mesmo
        fact: evidencia repetida faz um achado parecer duas vezes mais
        sustentado do que e."""
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--facts", str(facts_path), "--glue", "5.0"],
            capsys,
        )
        items = json.loads(output)["items"]
        assert [f["rule_id"] for f in items] == ["SF-PY-005"]
        assert len(items[0]["evidence"]) == len(set(items[0]["evidence"]))


class TestCaseLifecycle:
    def _open(self, repo, capsys):
        return run(
            ["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", "2026-07-30T00:00:00Z", "--glue", "5.0"],
            capsys,
        )

    def test_open_then_get(self, repo, capsys):
        assert self._open(repo, capsys)[0] == 0
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["case_id"] == "c1"

    def test_next_step_after_open(self, repo, capsys):
        self._open(repo, capsys)
        _, output = run(["next-step", "--repo", str(repo)], capsys)
        assert json.loads(output)["recommended_skill"]

    def test_handoff_writes_markdown(self, repo, capsys):
        self._open(repo, capsys)
        code, _ = run(["handoff", "--repo", str(repo)], capsys)
        assert code == 0
        assert (repo / ".sparkforge" / "handoff.md").is_file()


class TestStrictGatesNaCLI:
    """D-3 e D-4: o rigor entra na abertura e vale pela investigacao inteira;
    o override existe, exige motivo, e fica gravado."""

    NOW = "2026-08-04T00:00:00Z"

    def _open(self, repo, capsys, strict):
        args = ["case", "open", "--repo", str(repo), "--case-id", "c1",
                "--now", self.NOW, "--glue", "5.0"]
        if strict:
            args.append("--strict-gates")
        return run(args, capsys)

    def _bench_facts(self, repo, kinds):
        from sparkforge.findings.models import Fact

        path = repo / "facts_gate.json"
        path.write_text(
            json.dumps(
                [
                    Fact(kind=k, subject={"type": "job_run"}, measures={"n": 1}).to_dict()
                    for k in kinds
                ]
            ),
            encoding="utf-8",
        )
        return path

    def test_open_sem_a_flag_grava_rigor_desligado(self, repo, capsys):
        _, output = self._open(repo, capsys, strict=False)
        assert json.loads(output)["strict_gates"] is False

    def test_open_com_a_flag_grava_a_escolha_no_case(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["strict_gates"] is True

    def test_sem_rigor_a_transicao_passa_como_sempre(self, repo, capsys):
        self._open(repo, capsys, strict=False)
        code, output = run(
            ["case", "update", "--repo", str(repo), "--phase", "validation"], capsys
        )
        assert code == 0
        assert json.loads(output)["phase"] == "validation"

    def test_com_rigor_a_transicao_e_bloqueada_com_o_comando_que_destrava(
        self, repo, capsys
    ):
        self._open(repo, capsys, strict=True)
        assert main(["case", "update", "--repo", str(repo), "--phase", "validation"]) == 2
        err = capsys.readouterr().err
        assert "baseline_captured" in err
        assert "sparkforge benchmark" in err

    def test_o_booleano_manual_nao_destrava_sob_rigor(self, repo, capsys):
        """D-4b-2: `--gate-value true` seria override sem motivo e sem registro."""
        self._open(repo, capsys, strict=True)
        run(["case", "update", "--repo", str(repo),
             "--gate", "baseline_captured", "--gate-value", "true"], capsys)
        assert main(["case", "update", "--repo", str(repo), "--phase", "validation"]) == 2

    def test_o_fact_produtor_informado_em_facts_destrava(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        facts = self._bench_facts(
            repo, ["bench.run_delta", "callgraph.reachable_spark_work"]
        )
        code, output = run(
            ["case", "update", "--repo", str(repo), "--phase", "validation",
             "--facts", str(facts)],
            capsys,
        )
        assert code == 0
        assert json.loads(output)["phase"] == "validation"

    def test_override_sem_motivo_e_recusado(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        assert main(["case", "update", "--repo", str(repo),
                     "--override-gate", "baseline_captured"]) == 2
        assert "--reason" in capsys.readouterr().err

    def test_motivo_sem_override_e_recusado(self, repo, capsys):
        """Motivo sem gate nao tem sujeito: ignora-lo em silencio e a familia de
        defeito que esta fase existe para nao cometer."""
        self._open(repo, capsys, strict=True)
        assert main(["case", "update", "--repo", str(repo), "--reason", "porque sim"]) == 2
        assert "--override-gate" in capsys.readouterr().err

    def test_override_com_motivo_grava_e_deixa_transitar(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        facts = self._bench_facts(repo, ["callgraph.reachable_spark_work"])
        code, output = run(
            ["case", "update", "--repo", str(repo), "--phase", "validation",
             "--facts", str(facts),
             "--override-gate", "baseline_captured",
             "--reason", "job descontinuado, sem ambiente para reexecutar",
             "--now", self.NOW],
            capsys,
        )
        assert code == 0
        case = json.loads(output)
        assert case["phase"] == "validation"
        assert case["gate_overrides"] == [
            {
                "gate": "baseline_captured",
                "reason": "job descontinuado, sem ambiente para reexecutar",
                "at": self.NOW,
            }
        ]

    def test_dois_overrides_do_mesmo_gate_sobrevivem_no_arquivo(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        for motivo in ("primeiro motivo", "segundo motivo"):
            run(["case", "update", "--repo", str(repo),
                 "--override-gate", "flows_mapped", "--reason", motivo,
                 "--now", self.NOW], capsys)
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert [o["reason"] for o in json.loads(output)["gate_overrides"]] == [
            "primeiro motivo",
            "segundo motivo",
        ]

    def test_o_rigor_atravessa_a_sessao_pelo_arquivo(self, repo, capsys):
        """A escolha e do case, nao da invocacao: quem retoma nao passa flag
        nenhuma e mesmo assim herda o rigor de quem abriu."""
        self._open(repo, capsys, strict=True)
        assert main(["case", "update", "--repo", str(repo), "--phase", "hypothesis"]) == 2
        assert "flows_mapped" in capsys.readouterr().err

    def test_o_handoff_mostra_o_override(self, repo, capsys):
        self._open(repo, capsys, strict=True)
        run(["case", "update", "--repo", str(repo),
             "--override-gate", "flows_mapped",
             "--reason", "corpus sem trabalho Spark alcancavel",
             "--now", self.NOW], capsys)
        run(["handoff", "--repo", str(repo)], capsys)
        text = (repo / ".sparkforge" / "handoff.md").read_text(encoding="utf-8")
        assert "## Overrides de gate" in text
        assert "corpus sem trabalho Spark alcancavel" in text


class TestCaseOpenNaoApagaRigorEmSilencio:
    """D-3: quem retoma herda o rigor de quem abriu -- inclusive quem retoma
    digitando `case open` de novo.

    Medido antes da correcao, sobre um case estrito com um override gravado:
    `case open --repo . --case-id c1 --now ...` sem flag nenhuma sobrescrevia o
    arquivo com `strict_gates: false`, `gate_overrides: []` e `phase: intake`, e
    a transicao seguinte -- que estava bloqueada -- passava com rc=0. Uma
    invocacao sem a flag apagava o rigor, que e exatamente a familia de defeito
    que o D-3 recusou ao tirar a escolha da invocacao.

    A correcao preserva o caminho de reabrir do zero, atras de `--reopen`: ele
    existe, tem nome, e nao acontece por omissao.
    """

    NOW = "2026-08-04T09:00:00Z"

    def _open(self, repo, capsys, *extra):
        return run(
            ["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", self.NOW, *extra],
            capsys,
        )

    def _estrito_com_override(self, repo, capsys):
        self._open(repo, capsys, "--strict-gates")
        run(["case", "update", "--repo", str(repo),
             "--override-gate", "baseline_captured",
             "--reason", "job descontinuado", "--now", self.NOW], capsys)

    def test_abrir_sobre_um_case_existente_e_recusado(self, repo, capsys):
        self._estrito_com_override(repo, capsys)
        assert main(["case", "open", "--repo", str(repo), "--case-id", "c1",
                     "--now", self.NOW]) == 2

    def test_a_recusa_nomeia_o_que_seria_perdido_e_a_saida(self, repo, capsys):
        self._estrito_com_override(repo, capsys)
        main(["case", "open", "--repo", str(repo), "--case-id", "c1",
              "--now", self.NOW])
        err = capsys.readouterr().err
        assert "strict_gates" in err
        assert "1 override" in err
        assert "--reopen" in err

    def test_a_recusa_nao_toca_no_arquivo(self, repo, capsys):
        self._estrito_com_override(repo, capsys)
        antes = (repo / ".sparkforge" / "case.yaml").read_text(encoding="utf-8")
        main(["case", "open", "--repo", str(repo), "--case-id", "c1",
              "--now", self.NOW])
        assert (repo / ".sparkforge" / "case.yaml").read_text(encoding="utf-8") == antes

    def test_reopen_recria_o_case_do_zero(self, repo, capsys):
        """O caminho legitimo continua existindo -- com nome."""
        self._estrito_com_override(repo, capsys)
        run(["case", "update", "--repo", str(repo), "--phase", "diagnosis"], capsys)
        code, output = self._open(repo, capsys, "--reopen")
        assert code == 0
        case = json.loads(output)
        assert case["phase"] == "intake"
        assert case["gate_overrides"] == []

    def test_reopen_herda_o_rigor_de_quem_abriu(self, repo, capsys):
        """Rigor sobe, nunca desce dentro do mesmo arquivo de case: `--reopen`
        sem `--strict-gates` reabre a investigacao, nao a garantia."""
        self._estrito_com_override(repo, capsys)
        _, output = self._open(repo, capsys, "--reopen")
        assert json.loads(output)["strict_gates"] is True
        assert main(["case", "update", "--repo", str(repo), "--phase", "report"]) == 2

    def test_reopen_pode_subir_o_rigor_de_um_case_frouxo(self, repo, capsys):
        self._open(repo, capsys)
        _, output = self._open(repo, capsys, "--reopen", "--strict-gates")
        assert json.loads(output)["strict_gates"] is True

    def test_reopen_de_case_frouxo_continua_frouxo(self, repo, capsys):
        self._open(repo, capsys)
        _, output = self._open(repo, capsys, "--reopen")
        assert json.loads(output)["strict_gates"] is False

    def test_o_primeiro_open_nao_precisa_de_reopen(self, repo, capsys):
        code, output = self._open(repo, capsys, "--strict-gates")
        assert code == 0
        assert json.loads(output)["strict_gates"] is True

    def test_case_ilegivel_tambem_exige_reopen(self, repo, capsys):
        """Arquivo que `load_case` recusa ainda e um case ocupando o lugar:
        sobrescreve-lo em silencio apagaria o estado que alguem precisa ver
        antes de decidir."""
        alvo = repo / ".sparkforge"
        alvo.mkdir(parents=True, exist_ok=True)
        (alvo / "case.yaml").write_text("schema_version: 99\n", encoding="utf-8")
        assert main(["case", "open", "--repo", str(repo), "--case-id", "c1",
                     "--now", self.NOW]) == 2
        assert self._open(repo, capsys, "--reopen")[0] == 0

    def test_a_tool_mcp_recusa_pelo_mesmo_caminho(self, repo, capsys):
        """Os tres adaptadores chegam ao mesmo lugar -- senao a garantia seria
        so da CLI, e o MCP viraria a porta dos fundos."""
        from sparkforge.adapters.tools import call_tool

        self._estrito_com_override(repo, capsys)
        recusa = call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": self.NOW},
        )
        assert recusa["exit_code"] == 2
        assert "reopen" in recusa["error"]
        reaberto = call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": self.NOW, "reopen": True},
        )
        assert reaberto["strict_gates"] is True


class TestErrorsAreActionable:
    def test_missing_case_names_the_command_that_fixes_it(self, repo, capsys):
        assert main(["case", "get", "--repo", str(repo)]) == 2
        assert "sparkforge case open" in capsys.readouterr().err

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        assert main(["judge", "--facts", str(repo / "nope.json"), "--glue", "5.0"]) == 2
        assert "sparkforge analyze pyspark" in capsys.readouterr().err


class TestRuntimeAndRules:
    def test_runtime_detect_reports_matrix(self, capsys):
        _, output = run(["runtime", "detect", "--glue", "5.0"], capsys)
        payload = json.loads(output)
        assert payload["spark"] == "3.5.4"
        assert payload["iceberg"] == "1.7.1"

    def test_rules_lookup_by_id_returns_full_rule(self, capsys):
        _, output = run(["rules", "lookup", "--id", "SF-PY-005"], capsys)
        rule = json.loads(output)["rules"][0]
        assert rule["id"] == "SF-PY-005"
        assert rule["sources"]
        assert rule["validation"]

    def test_rules_lookup_by_category(self, capsys):
        _, output = run(["rules", "lookup", "--category", "athena"], capsys)
        assert json.loads(output)["total_count"] == 5

    def test_validate_rejects_unbacked_gain(self, tmp_path, capsys):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40% do runtime", "benchmark_ref": "",
        }
        path = tmp_path / "f.json"
        path.write_text(json.dumps([payload]), encoding="utf-8")
        assert main(["validate", "--findings", str(path)]) == 1
        assert "benchmark_ref" in capsys.readouterr().err


class TestValidateChecksTheBenchmarkRef:
    """`--facts` e a camada de pertinencia do `benchmark_ref` na CLI.

    Sem a flag o verbo so cobra a FORMA do campo (`f_` + 6 hex), porque
    `validate_finding` nao ve fact nenhum. Com ela, o `fact_id` citado precisa
    estar no arquivo -- e um achado que cita medicao ausente da evidencia cai.
    """

    def _finding(self, benchmark_ref):
        return {
            "rule_id": "SF-BENCH-001", "schema_version": 1, "title": "t", "severity": "P2",
            "confidence": "high", "status": "confirmed",
            "subject": {"type": "job_run"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40% do runtime", "benchmark_ref": benchmark_ref,
        }

    def _facts_file(self, tmp_path, *ids_source):
        """Facts REAIS, para que os ids saiam de `Fact.id` e nao de literais."""
        from sparkforge.findings.models import Fact

        facts = [
            Fact(kind="bench.run_delta", subject={"type": "job_run"}, measures={"n": n})
            for n in ids_source
        ]
        path = tmp_path / "facts.json"
        path.write_text(
            json.dumps([f.to_dict() for f in facts]), encoding="utf-8"
        )
        return path, [f.id for f in facts]

    def _findings_file(self, tmp_path, benchmark_ref):
        path = tmp_path / "findings.json"
        path.write_text(json.dumps([self._finding(benchmark_ref)]), encoding="utf-8")
        return path

    def test_free_text_ref_is_rejected_without_any_facts_file(self, tmp_path, capsys):
        path = self._findings_file(tmp_path, "bench/2026-07-29.json")
        assert main(["validate", "--findings", str(path)]) == 1
        assert "nao e um fact_id" in capsys.readouterr().err

    def test_well_formed_ref_passes_without_a_facts_file(self, tmp_path, capsys):
        path = self._findings_file(tmp_path, "f_a1b2c3")
        assert main(["validate", "--findings", str(path)]) == 0
        assert json.loads(capsys.readouterr().out)["valid"] is True

    def test_facts_file_makes_an_absent_ref_fail(self, tmp_path, capsys):
        facts_path, _ = self._facts_file(tmp_path, 1, 2)
        path = self._findings_file(tmp_path, "f_a1b2c3")
        assert main(
            ["validate", "--findings", str(path), "--facts", str(facts_path)]
        ) == 1
        assert "nao esta no conjunto" in capsys.readouterr().err

    def test_facts_file_accepts_a_ref_that_is_really_there(self, tmp_path, capsys):
        facts_path, ids = self._facts_file(tmp_path, 1, 2)
        path = self._findings_file(tmp_path, ids[0])
        assert main(
            ["validate", "--findings", str(path), "--facts", str(facts_path)]
        ) == 0
        assert json.loads(capsys.readouterr().out)["valid"] is True

    def test_a_missing_facts_file_names_the_verb_that_produces_the_fact_id(
        self, tmp_path, capsys
    ):
        """O `fact_id` que este caminho procura e o de um `bench.run_delta`.
        Mandar rodar `analyze pyspark` produziria um arquivo onde ele nunca vai
        estar -- e era o que a mensagem fazia."""
        path = self._findings_file(tmp_path, "f_a1b2c3")
        assert main(
            ["validate", "--findings", str(path), "--facts", str(tmp_path / "nope.json")]
        ) == 2
        err = capsys.readouterr().err
        assert "sparkforge benchmark --before" in err
        assert "analyze pyspark" not in err


class _FakeS3Client:
    def __init__(self):
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return {"Contents": [{"Key": f"{kwargs['Prefix']}part-00000"}]}

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))
        return {"Body": io.BytesIO(b'{"Event":"SparkListenerJobStart"}\n')}


class _FakeBoto3:
    def __init__(self, **clients):
        self._clients = clients

    def client(self, name, **kwargs):
        return self._clients[name]


class TestCollect:
    def test_event_log_writes_artifact_and_prints_manifest_entry(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))

        code, output = run(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_1",
                "--bucket", "my-bucket",
                "--prefix", "spark-logs",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["kind"] == "event_log"
        assert payload["cache_hit"] is False
        assert (repo / payload["path"]).is_file()

    def test_event_log_second_call_is_a_cache_hit(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))
        args = [
            "collect", "event-log",
            "--repo", str(repo),
            "--job-run", "jr_2",
            "--bucket", "b",
            "--prefix", "p",
            "--now", "2026-07-30T00:00:00Z",
        ]
        run(args, capsys)
        args[-1] = "2026-07-30T01:00:00Z"
        code, output = run(args, capsys)
        assert code == 0
        assert json.loads(output)["cache_hit"] is True

    def test_missing_boto3_names_pip_install_and_manual_path(self, repo, capsys, monkeypatch):
        from sparkforge.collect.base import CollectorUnavailable

        def boom():
            raise CollectorUnavailable(
                "boto3 nao disponivel. Instale com `pip install 'sparkforge-aws[aws]'` "
                "para usar coletores AWS, ou colete o artefato manualmente (AWS CLI ou "
                "console) e registre-o com `sparkforge.collect.register_artifact`."
            )

        monkeypatch.setattr(collect_aws, "require_boto3", boom)
        code = main(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_3",
                "--bucket", "b",
                "--prefix", "p",
                "--now", "2026-07-30T00:00:00Z",
            ]
        )
        assert code == 2
        err = capsys.readouterr().err
        assert "pip install 'sparkforge-aws[aws]'" in err
        assert "Alternativa manual" in err
        assert "jr_3.jsonl" in err

    def test_verify_reports_missing_artifact_with_recollect_command(self, repo, capsys):
        from sparkforge.collect.base import ArtifactEntry, register_artifact

        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_gone.jsonl",
            sha256="a" * 64,
            source="s3://bucket/prefix/jr_gone/",
            collect_command="sparkforge collect event-log --job-run jr_gone",
            collected_at="2026-07-29T00:00:00Z",
        )
        register_artifact(entry, repo)

        code, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["missing_count"] == 1
        assert payload["artifacts"][0]["present"] is False
        assert payload["artifacts"][0]["collect_command"] == entry.collect_command

    def test_verify_reports_hash_mismatch_after_local_corruption(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))
        run(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_corrupt",
                "--bucket", "b",
                "--prefix", "p",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        target = repo / ".sparkforge" / "artifacts" / "eventlog" / "jr_corrupt.jsonl"
        target.write_bytes(b"corrupted")

        code, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["mismatched_count"] == 1
        assert payload["artifacts"][0]["present"] is True
        assert payload["artifacts"][0]["hash_matches"] is False


EVENT_LOG_LINE = json.dumps({"Event": "SparkListenerApplicationStart"}) + "\n"

TERRAFORM_SOURCE = (
    'resource "aws_glue_job" "etl" {\n'
    '  glue_version = "5.0"\n'
    '  worker_type = "G.1X"\n'
    "  number_of_workers = 10\n"
    "}\n"
)

ICEBERG_DUMP = json.dumps(
    {
        "table": "db.tbl",
        "files": [
            {"file_path": "s3://b/f1.parquet", "file_size_in_bytes": 1024, "record_count": 10}
        ],
    }
)

SQL_TEXT = "SELECT a, b FROM db.eventos WHERE dt = '2026-01-01'\n"

PYSPARK_SQL_SOURCE = 'spark.sql("SELECT a FROM db.eventos")\n'

ATHENA_WORKGROUP_DUMP = json.dumps(
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


class TestAnalyzeEventLog:
    def test_prints_summary_and_reports_unresolved(self, repo, capsys):
        log_path = repo / "log.jsonl"
        log_path.write_text(EVENT_LOG_LINE, encoding="utf-8")
        code, output = run(["analyze", "event-log", "--path", str(log_path)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert payload["unresolved"] == 0
        assert payload["unresolved_at"] == []

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "event-log", "--path", str(repo / "nope.jsonl")], capsys)
        assert code == 2


class TestAnalyzeTerraform:
    def test_writes_facts_json(self, repo, capsys):
        tf_path = repo / "main.tf"
        tf_path.write_text(TERRAFORM_SOURCE, encoding="utf-8")
        out = repo / "tf_facts.json"
        code, _ = run(
            ["analyze", "terraform", "--path", str(tf_path), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "tf.resource" for f in facts)

    def test_directory_is_accepted(self, repo, capsys):
        tf_dir = repo / "infra"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(TERRAFORM_SOURCE, encoding="utf-8")
        _, output = run(["analyze", "terraform", "--path", str(tf_dir)], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert payload["unresolved"] == 0


PLAN_TEXT = (
    "== Physical Plan ==\n"
    "* Project (2)\n"
    "+- Scan parquet analytics.eventos (1)\n"
    "\n"
    "\n"
    "(1) Scan parquet analytics.eventos\n"
    "Output [3]: [cliente_id#10, valor#11, dt#12]\n"
    "Batched: true\n"
    "Location: InMemoryFileIndex [s3://lake/analytics/eventos]\n"
    "ReadSchema: struct<cliente_id:bigint,valor:double>\n"
    "\n"
    "(2) Project [codegen id : 1]\n"
    "Output [1]: [cliente_id#10]\n"
    "Input [3]: [cliente_id#10, valor#11, dt#12]\n"
)


class TestAnalyzePlan:
    def test_writes_facts_json(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        out = repo / "plan_facts.json"
        code, _ = run(["analyze", "plan", "--path", str(plan_path), "--out", str(out)], capsys)
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "plan.file_scan" for f in facts)
        assert any(f["kind"] == "plan.analyzed" for f in facts)

    def test_prints_summary_and_reports_unresolved(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        code, output = run(["analyze", "plan", "--path", str(plan_path)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "unresolved" in payload
        assert "unresolved_at" in payload

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "plan", "--path", str(repo / "nope.txt")], capsys)
        assert code == 2

    def test_mcp_tool_matches_the_cli(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        _, output = run(["analyze", "plan", "--path", str(plan_path), "--limit", "50"], capsys)
        from_cli = json.loads(output)
        from_mcp = call_tool("sparkforge_analyze_plan", {"path": str(plan_path)})
        assert from_cli["items"] == from_mcp["items"]


class TestAnalyzeIceberg:
    def test_prints_summary(self, repo, capsys):
        ice_path = repo / "iceberg.json"
        ice_path.write_text(ICEBERG_DUMP, encoding="utf-8")
        _, output = run(["analyze", "iceberg", "--path", str(ice_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["iceberg.files_summary"] == 1
        assert payload["unresolved"] == 0


class TestAnalyzeSql:
    def test_path_mode(self, repo, capsys):
        sql_path = repo / "q.sql"
        sql_path.write_text(SQL_TEXT, encoding="utf-8")
        _, output = run(["analyze", "sql", "--path", str(sql_path)], capsys)
        payload = json.loads(output)
        assert "sql.projection" in payload["by_kind"]

    def test_from_pyspark_mode(self, repo, capsys):
        py_path = repo / "q.py"
        py_path.write_text(PYSPARK_SQL_SOURCE, encoding="utf-8")
        _, output = run(["analyze", "sql", "--from-pyspark", str(py_path)], capsys)
        payload = json.loads(output)
        assert "sql.projection" in payload["by_kind"]

    def test_neither_path_nor_from_pyspark_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "sql"], capsys)
        assert code == 2


class TestAnalyzeAthenaWorkgroup:
    def test_prints_summary(self, repo, capsys):
        wg_path = repo / "wg.json"
        wg_path.write_text(ATHENA_WORKGROUP_DUMP, encoding="utf-8")
        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["athena.workgroup"] == 1
        assert payload["unresolved"] == 0

    def test_unparseable_engine_version_is_reported_as_unresolved_not_fabricated(
        self, repo, capsys
    ):
        dump = json.dumps(
            {
                "workgroups": [
                    {"name": "primary", "engine_version": {"effective_engine_version": "AUTO"}}
                ]
            }
        )
        wg_path = repo / "wg.json"
        wg_path.write_text(dump, encoding="utf-8")
        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("athena.workgroup", 0) == 0
        assert payload["unresolved"] == 1
        assert payload["unresolved_at"][0]["reason"] == "unparseable_engine_version"


class TestAnalyzeEmrCluster:
    _DUMP = json.dumps(
        {
            "Cluster": {
                "Id": "j-1EXAMPLE",
                "ReleaseLabel": "emr-7.5.0",
                "InstanceCollectionType": "INSTANCE_GROUP",
                "LogUri": "s3://bucket/elasticmapreduce/",
                "AutoTerminate": False,
                "Status": {"State": "RUNNING"},
            },
            "InstanceGroups": [
                {
                    "Id": "ig-TASK",
                    "InstanceGroupType": "TASK",
                    "Market": "SPOT",
                    "InstanceType": "r5.xlarge",
                    "RequestedInstanceCount": 4,
                }
            ],
        }
    )

    def test_prints_summary(self, repo, capsys):
        dump = repo / "cluster.json"
        dump.write_text(self._DUMP, encoding="utf-8")
        _, output = run(["analyze", "emr-cluster", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["emr.instance_capacity"] == 1
        assert payload["unresolved"] == 0

    def test_dump_without_instance_lists_reports_unresolved_not_zero_capacity(
        self, repo, capsys
    ):
        """Pelo verbo, a mesma disciplina do extrator: lista de instancias nao
        coletada aparece como ponto cego, nao como cluster sem capacidade."""
        dump = repo / "cluster.json"
        dump.write_text(json.dumps({"Cluster": {"Id": "j-1", "ReleaseLabel": "emr-7.5.0"}}))
        _, output = run(["analyze", "emr-cluster", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("emr.instance_capacity", 0) == 0
        assert payload["unresolved"] == 1
        assert payload["unresolved_at"][0]["reason"] == "missing_instance_model"

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "emr-cluster", "--path", str(repo / "nope.json")], capsys)
        assert code == 2


class TestAnalyzeEmrServerless:
    _DUMP = json.dumps(
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
                    "EXECUTOR": {
                        "workerCount": 10,
                        "workerConfiguration": {
                            "cpu": "4vCPU",
                            "memory": "16GB",
                            "disk": "20GB",
                        },
                    }
                },
                "maximumCapacity": {
                    "cpu": "400vCPU",
                    "memory": "3000GB",
                    "disk": "20000GB",
                },
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

    def test_prints_summary(self, repo, capsys):
        dump = repo / "application.json"
        dump.write_text(self._DUMP, encoding="utf-8")
        _, output = run(["analyze", "emr-serverless", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["emrs.initial_capacity"] == 1
        assert payload["by_kind"]["emrs.monitoring"] == 1
        assert payload["unresolved"] == 0

    def test_unit_it_cannot_read_is_a_counted_blind_spot_not_a_guessed_number(
        self, repo, capsys
    ):
        """`"16 gigabytes"` nao esta no conjunto documentado (`GB|gb|gB|Gb`).
        O verbo tem que reportar ponto cego CONTADO -- um numero adivinhado ali
        viraria capacidade inventada com aparencia de medida."""
        dump = repo / "application.json"
        dump.write_text(
            json.dumps(
                {
                    "application": {
                        "applicationId": "00fEXAMPLE",
                        "releaseLabel": "emr-7.5.0",
                        "initialCapacity": {
                            "EXECUTOR": {
                                "workerCount": 2,
                                "workerConfiguration": {"memory": "16 gigabytes"},
                            }
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        _, output = run(["analyze", "emr-serverless", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["unresolved"] >= 1
        assert any(
            u["reason"] == "unknown_capacity_unit" for u in payload["unresolved_at"]
        )

    def test_out_writes_the_full_list_that_judge_reads(self, repo, capsys):
        """A cadeia inteira do verbo novo, na CLI: `--out` grava a lista COMPLETA
        de facts (nao a pagina), e esse arquivo e o que `judge --facts` le. Verbo
        de analise sem `--out` seria capacidade que so existe na tela."""
        dump = repo / "application.json"
        dump.write_text(self._DUMP, encoding="utf-8")
        out = repo / "facts_emrs.json"
        code, _ = run(
            ["analyze", "emr-serverless", "--path", str(dump), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert {f["kind"] for f in facts} >= {"emrs.application", "emrs.analyzed"}
        code, judged = run(["judge", "--facts", str(out)], capsys)
        assert code == 0
        assert "total_count" in json.loads(judged)

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "emr-serverless", "--path", str(repo / "nope.json")], capsys)
        assert code == 2


class TestAnalyzeDataQuality:
    _SOURCE = (
        "def validar(vendas):\n"
        "    ruins = vendas.filter(vendas.valor < 0).count()\n"
        "    if ruins > 0:\n"
        '        raise ValueError("valor negativo")\n'
    )

    def test_prints_summary(self, repo, capsys):
        module = repo / "validacao.py"
        module.write_text(self._SOURCE, encoding="utf-8")
        _, output = run(["analyze", "data-quality", "--path", str(module)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["dq.check"] == 1
        assert payload["by_kind"]["dq.enforcement"] == 1
        assert payload["unresolved"] == 0

    def test_module_without_validation_is_analyzed_not_silent(self, repo, capsys):
        """Zero check num modulo LIDO nao pode ser o mesmo que modulo nao lido:
        `dq.module_analyzed` e o que separa os dois, e pelo verbo tambem."""
        module = repo / "sem_validacao.py"
        module.write_text("def gravar(df, dest):\n    df.write.parquet(dest)\n", encoding="utf-8")
        _, output = run(["analyze", "data-quality", "--path", str(module)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("dq.check", 0) == 0
        assert payload["by_kind"]["dq.module_analyzed"] == 1

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "data-quality", "--path", str(repo / "nope.py")], capsys)
        assert code == 2


class TestAnalyzeGraph:
    _SOURCE = (
        "from graphframes import GraphFrame\n"
        "\n"
        "def rodar(spark, vertices, arestas):\n"
        "    spark.sparkContext.setCheckpointDir"
        '("s3://bucket/ckpt")\n'
        "    g = GraphFrame(vertices.cache(), arestas.cache())\n"
        "    return g.connectedComponents()\n"
    )

    def test_prints_summary(self, repo, capsys):
        module = repo / "grafo.py"
        module.write_text(self._SOURCE, encoding="utf-8")
        _, output = run(["analyze", "graph", "--path", str(module)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["graph.import"] == 1
        assert payload["by_kind"]["graph.construction"] == 1
        assert payload["by_kind"]["graph.algorithm"] == 1
        assert payload["by_kind"]["graph.checkpoint_dir"] == 1
        assert payload["unresolved"] == 0

    def test_module_without_graph_is_analyzed_not_silent(self, repo, capsys):
        """Mesma invariante de `data-quality`: zero grafo num modulo LIDO nao
        pode ser o mesmo que modulo nao lido -- `graph.module_analyzed` e o que
        separa os dois, e pelo verbo tambem."""
        module = repo / "sem_grafo.py"
        module.write_text("def gravar(df, dest):\n    df.write.parquet(dest)\n", encoding="utf-8")
        _, output = run(["analyze", "graph", "--path", str(module)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("graph.import", 0) == 0
        assert payload["by_kind"]["graph.module_analyzed"] == 1

    def test_out_writes_the_full_list_that_judge_reads(self, repo, capsys):
        """A cadeia inteira do verbo novo, na CLI: `--out` grava a lista
        COMPLETA de facts (nao a pagina), e esse arquivo e o que `judge --facts`
        le. Nao se prova aqui que `judge` ACUSA algo -- a area `SF-GRAPH` ainda
        nao existe --, e sim que o artefato do verbo e aceito pelo motor."""
        module = repo / "grafo.py"
        module.write_text(self._SOURCE, encoding="utf-8")
        out = repo / "facts_graph.json"
        code, _ = run(["analyze", "graph", "--path", str(module), "--out", str(out)], capsys)
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert {f["kind"] for f in facts} >= {"graph.construction", "graph.module_analyzed"}
        code, judged = run(["judge", "--facts", str(out)], capsys)
        assert code == 0
        assert "total_count" in json.loads(judged)

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "graph", "--path", str(repo / "nope.py")], capsys)
        assert code == 2


class TestAnalyzeCallGraph:
    def test_derives_from_pyspark_facts(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys
        )
        _, output = run(["analyze", "call-graph", "--facts", str(facts_path)], capsys)
        payload = json.loads(output)
        assert "callgraph.summary" in payload["by_kind"]
        assert "unresolved" not in payload

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "call-graph", "--facts", str(repo / "nope.json")], capsys)
        assert code == 2


def _event_log_lines(run_ms: int) -> str:
    """Event log minimo com UM stage nomeado `scan` e duas tasks.

    `run_ms` e o `Executor Run Time` de cada task, que e o unico eixo que os
    dois lados do benchmark precisam variar: `total_task_ms` sai de
    `mean_ms * task_count` sobre `spark.stage.task_duration`.
    """
    def task(task_id: int) -> dict:
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

    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "j", "App ID": "a", "Timestamp": 1},
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Parent IDs": [],
                "Details": "",
                "Submission Time": 100,
            },
        },
        task(0),
        task(1),
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Parent IDs": [],
                "Details": "",
            },
        },
    ]
    return "".join(json.dumps(e) + "\n" for e in events)


class TestBenchmark:
    """Verbo de TOPO, nao `analyze benchmark`: ele nao extrai de artefato,
    compara dois conjuntos de facts ja extraidos -- mesma razao de `fuse`."""

    def _side(self, repo, capsys, name, run_ms):
        log = repo / f"{name}.jsonl"
        log.write_text(_event_log_lines(run_ms), encoding="utf-8")
        out = repo / f"{name}_facts.json"
        run(["analyze", "event-log", "--path", str(log), "--out", str(out)], capsys)
        return out

    def test_compares_two_facts_files(self, repo, capsys):
        before = self._side(repo, capsys, "before", 200)
        after = self._side(repo, capsys, "after", 100)
        code, output = run(
            ["benchmark", "--before", str(before), "--after", str(after)], capsys
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["by_kind"]["bench.run_delta"] == 1
        assert payload["by_kind"]["bench.analyzed"] == 1
        delta = next(f for f in payload["items"] if f["kind"] == "bench.run_delta")
        assert delta["measures"]["total_task_ms_delta_pct"] == -50.0

    def test_writes_facts_json(self, repo, capsys):
        before = self._side(repo, capsys, "before", 200)
        after = self._side(repo, capsys, "after", 100)
        out = repo / "bench.json"
        code, _ = run(
            [
                "benchmark",
                "--before", str(before),
                "--after", str(after),
                "--out", str(out),
            ],
            capsys,
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "bench.stage_delta" for f in facts)

    def test_reports_its_own_blind_spot(self, repo, capsys):
        """`bench.unresolved` tem que chegar ao relatorio como `unresolved`:
        um lado sem `spark.log_analyzed` nao pode sair como "nenhuma
        diferenca" -- ver docstring de `_core.benchmark_runs`."""
        before = self._side(repo, capsys, "before", 200)
        empty = repo / "empty_facts.json"
        empty.write_text("[]", encoding="utf-8")
        _, output = run(["benchmark", "--before", str(before), "--after", str(empty)], capsys)
        payload = json.loads(output)
        assert payload["unresolved"] == 1
        assert payload["unresolved_at"][0]["reason"] == "missing_log_analyzed"
        assert "bench.run_delta" not in payload["by_kind"]

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        before = self._side(repo, capsys, "before", 200)
        code, _ = run(
            ["benchmark", "--before", str(before), "--after", str(repo / "nope.json")], capsys
        )
        assert code == 2

    def test_the_message_names_the_side_and_the_verb_that_produces_it(self, repo, capsys):
        """`code == 2` sozinho passa com mensagem inacionavel, e passava: o
        helper cravava `analyze pyspark` para todo chamador, e a entrada do
        benchmark vem de `analyze event-log --out`. Falta o lado tambem: com dois
        arquivos na linha de comando, "arquivo nao encontrado" nao diz qual
        refazer. O precedente e `analyze terraform-diff`, que rotula o lado.
        """
        before = self._side(repo, capsys, "before", 200)
        assert (
            main(["benchmark", "--before", str(before), "--after", str(repo / "nope.json")])
            == 2
        )
        err = capsys.readouterr().err
        assert "--after" in err
        assert "--before" not in err
        assert "sparkforge analyze event-log" in err
        assert "analyze pyspark" not in err

    def test_the_message_names_the_before_side_when_it_is_the_one_missing(self, repo, capsys):
        after = self._side(repo, capsys, "after", 100)
        assert (
            main(["benchmark", "--before", str(repo / "nope.json"), "--after", str(after)]) == 2
        )
        err = capsys.readouterr().err
        assert "--before" in err
        assert "--after" not in err

    def test_the_other_callers_keep_naming_their_own_verb(self, repo, capsys):
        """A mensagem passa a depender do chamador, entao os outros dois
        caminhos precisam continuar corretos -- e nenhum deles fala de lado."""
        assert main(["analyze", "call-graph", "--facts", str(repo / "nope.json")]) == 2
        err = capsys.readouterr().err
        assert "sparkforge analyze pyspark" in err
        assert "--before" not in err and "--after" not in err

        assert main(["judge", "--facts", str(repo / "nope.json"), "--glue", "5.0"]) == 2
        assert "sparkforge analyze pyspark" in capsys.readouterr().err


_FUNCVAL_JOB = 'def gravar(df):\n    df.write.mode("overwrite").saveAsTable("db.eventos")\n'


class TestFuncvalPlan:
    """Verbo de TOPO com subacao, como `report`: nao extrai de artefato --
    deriva de facts que outro verbo ja produziu."""

    def _facts(self, repo, capsys, source=_FUNCVAL_JOB):
        job = repo / "job"
        job.mkdir(exist_ok=True)
        (job / "carga.py").write_text(source, encoding="utf-8")
        catalog = repo / "catalogo"
        catalog.mkdir(exist_ok=True)
        (catalog / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")

        pyspark_facts = repo / "pyspark_facts.json"
        catalog_facts = repo / "catalog_facts.json"
        run(["analyze", "pyspark", "--path", str(job), "--out", str(pyspark_facts)], capsys)
        run(
            [
                "analyze", "catalog-schema",
                "--path", str(catalog),
                "--out", str(catalog_facts),
            ],
            capsys,
        )
        return pyspark_facts, catalog_facts

    def test_derives_the_plan_from_two_facts_files(self, repo, capsys):
        """`--facts` e repetivel porque tem que ser: o alvo vem do
        `pyspark.write` e o schema/os agregados vem do `catalog.table_schema`,
        e nenhum verbo produz os dois no mesmo arquivo."""
        pyspark_facts, catalog_facts = self._facts(repo, capsys)
        out = repo / "plano.json"
        code, output = run(
            [
                "funcval", "plan",
                "--facts", str(pyspark_facts),
                "--facts", str(catalog_facts),
                "--out", str(out),
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["by_kind"]["funcval.plan"] == 1
        plano = next(f for f in payload["items"] if f["kind"] == "funcval.plan")
        assert plano["attrs"]["target"] == "db.eventos"
        assert set(plano["attrs"]["checks"]) == {"count", "schema", "agg:sum:cliente_id"}

    def test_the_out_file_is_the_artifact_that_compare_rereads(self, repo, capsys):
        pyspark_facts, catalog_facts = self._facts(repo, capsys)
        out = repo / "plano.json"
        run(
            [
                "funcval", "plan",
                "--facts", str(pyspark_facts),
                "--facts", str(catalog_facts),
                "--out", str(out),
            ],
            capsys,
        )
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "funcval.plan" for f in facts)

    def test_the_declared_key_carries_its_origin(self, repo, capsys):
        """Chave de negocio nao sai de fact nenhum (D-4c-1): ela entra por
        `--key`, e o check tem que dizer que a afirmacao e do operador."""
        pyspark_facts, catalog_facts = self._facts(repo, capsys)
        _, output = run(
            [
                "funcval", "plan",
                "--facts", str(pyspark_facts),
                "--facts", str(catalog_facts),
                "--key", "loja_id,pedido_id",
                "--out", str(repo / "plano.json"),
            ],
            capsys,
        )
        plano = next(
            f for f in json.loads(output)["items"] if f["kind"] == "funcval.plan"
        )
        chave = plano["attrs"]["checks"]["key:loja_id+pedido_id"]
        assert chave["origin"] == "declared"
        assert chave["derived_from"] == []
        assert plano["attrs"]["checks"]["count"]["origin"] == "derived"

    def test_without_key_the_missing_axis_is_written_not_silenced(self, repo, capsys):
        pyspark_facts, catalog_facts = self._facts(repo, capsys)
        _, output = run(
            [
                "funcval", "plan",
                "--facts", str(pyspark_facts),
                "--facts", str(catalog_facts),
                "--out", str(repo / "plano.json"),
            ],
            capsys,
        )
        plano = next(
            f for f in json.loads(output)["items"] if f["kind"] == "funcval.plan"
        )
        assert plano["attrs"]["undeclared_axes"] == ["keys"]
        assert plano["attrs"]["undeclared_axes_reason"]["keys"]

    def test_reports_its_own_blind_spot(self, repo, capsys):
        """Alvo sem catalogo casado nao vira plano de agregados adivinhado:
        vira `funcval.unresolved`, e ele tem que chegar ao relatorio."""
        pyspark_facts, _ = self._facts(repo, capsys)
        _, output = run(
            [
                "funcval", "plan",
                "--facts", str(pyspark_facts),
                "--out", str(repo / "plano.json"),
            ],
            capsys,
        )
        payload = json.loads(output)
        assert payload["unresolved"] >= 1
        assert "catalog_schema_unmatched" in {
            entry["reason"] for entry in payload["unresolved_at"]
        }

    def test_missing_facts_file_names_both_producers(self, repo, capsys):
        assert (
            main(
                [
                    "funcval", "plan",
                    "--facts", str(repo / "nope.json"),
                    "--out", str(repo / "plano.json"),
                ]
            )
            == 2
        )
        err = capsys.readouterr().err
        assert "sparkforge analyze pyspark" in err
        assert "sparkforge analyze catalog-schema" in err

    def test_out_into_a_missing_directory_is_actionable(self, repo, capsys):
        pyspark_facts, _ = self._facts(repo, capsys)
        assert (
            main(
                [
                    "funcval", "plan",
                    "--facts", str(pyspark_facts),
                    "--out", str(repo / "sem" / "plano.json"),
                ]
            )
            == 2
        )
        assert "sparkforge funcval plan" in capsys.readouterr().err


class TestFuncvalCompare:
    def _plan(self, repo, capsys, keys=()):
        helper = TestFuncvalPlan()
        pyspark_facts, catalog_facts = helper._facts(repo, capsys)
        out = repo / "plano.json"
        args = [
            "funcval", "plan",
            "--facts", str(pyspark_facts),
            "--facts", str(catalog_facts),
            "--out", str(out),
        ]
        for key in keys:
            args += ["--key", key]
        run(args, capsys)
        return out

    def _result(self, repo, name, **payload):
        path = repo / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _checks(self, count):
        return {
            "count": {"value": count},
            "schema": {"value": {"cliente_id": "bigint", "dt": "string"}},
            "agg:sum:cliente_id": {"value": 88123},
        }

    def test_compares_before_against_after(self, repo, capsys):
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        code, output = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["by_kind"]["funcval.analyzed"] == 1
        delta = next(
            f
            for f in payload["items"]
            if f["kind"] == "funcval.check_delta" and f["attrs"]["check"] == "count"
        )
        assert delta["attrs"]["diverged"] is True

    def test_the_sentinel_declares_the_proxy_limit(self, repo, capsys):
        """O limite mora na SAIDA, e nao so no spec: quem le 'os quatro proxies
        bateram' nao pode ter que ir ao spec descobrir o que isso nao prova."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(1000))
        _, output = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
            ],
            capsys,
        )
        sentinela = next(
            f for f in json.loads(output)["items"] if f["kind"] == "funcval.analyzed"
        )
        assert sentinela["attrs"]["proxies"] == ["count", "schema", "keys", "aggregates"]
        assert "NAO provam" in sentinela["attrs"]["proxy_limit"]

    def test_the_out_file_is_what_judge_reads(self, repo, capsys):
        """D-4c-26. Sem `--out`, a saida do `compare` so chegava ao `judge`
        extraida do envelope com `jq` ou `python -c` -- num fluxo cujo passo
        seguinte e obrigatorio para a area servir para alguma coisa."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        out = repo / "funcval.json"
        code, output = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
                "--out", str(out),
            ],
            capsys,
        )
        assert code == 0
        gravado = json.loads(out.read_text(encoding="utf-8"))
        # O arquivo e uma LISTA de facts, no formato que `judge --facts` le --
        # nao o envelope. E ele traz o mesmo que o stdout, sem paginacao no meio.
        assert isinstance(gravado, list)
        assert gravado == json.loads(output)["items"]
        assert {f["kind"] for f in gravado} == {"funcval.analyzed", "funcval.check_delta"}

    def test_the_out_file_carries_everything_and_not_the_page(self, repo, capsys):
        """A metade da divida que MORDE. `--limit` vale 50 por default e o
        envelope pagina; quem extrai `items` sem conferir `next_cursor` julga a
        primeira pagina e chama aquilo de comparacao -- o defeito que a
        SF-FVAL-005 acusa no dado do operador, cometido pelo fluxo do motor.

        Aqui `--limit 1` corta o stdout em UM item e o arquivo continua com
        todos. Se a escrita acontecesse depois da paginacao, este teste seria a
        unica coisa entre o motor e aquele defeito."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        out = repo / "funcval.json"
        _, output = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
                "--out", str(out),
                "--limit", "1",
            ],
            capsys,
        )
        payload = json.loads(output)
        assert len(payload["items"]) == 1
        assert payload["next_cursor"]
        gravado = json.loads(out.read_text(encoding="utf-8"))
        assert len(gravado) == payload["total_count"] > 1

    def test_the_chain_reaches_judge_without_a_step_in_between(self, repo, capsys):
        """A cadeia inteira, que e o que a divida cobrava: o arquivo do `--out`
        entra direto em `judge --facts`, sem `jq` no meio."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        out = repo / "funcval.json"
        run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
                "--out", str(out),
            ],
            capsys,
        )
        _, output = run(["judge", "--facts", str(out), "--glue", "5.0"], capsys)
        assert "SF-FVAL-001" in {f["rule_id"] for f in json.loads(output)["items"]}

    def test_without_out_nothing_is_written(self, repo, capsys):
        """`--out` e OPCIONAL, ao contrario do `--out` do `plan`: o plano e a
        entrada do proximo verbo, esta e saida terminal. Sem o argumento o verbo
        nao inventa caminho nenhum."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        antes = set(repo.iterdir())
        code, _ = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
            ],
            capsys,
        )
        assert code == 0
        assert set(repo.iterdir()) == antes

    def test_out_into_a_missing_directory_names_this_verb(self, repo, capsys):
        """A mensagem sugere o comando do verbo que FALHOU. Mandar quem errou o
        diretorio no `compare` rodar um `plan` seria o motor sugerindo o passo
        errado no unico momento em que a pessoa esta seguindo a sugestao."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1000))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(998))
        assert (
            main(
                [
                    "funcval", "compare",
                    "--plan", str(plan),
                    "--before", str(before),
                    "--after", str(after),
                    "--out", str(repo / "nao-existe" / "funcval.json"),
                ]
            )
            == 2
        )
        err = capsys.readouterr().err
        assert "sparkforge funcval compare" in err

    def test_a_plan_ref_from_another_plan_is_refused(self, repo, capsys):
        """O ponto cego que `build_comparison` nao ve: o modulo recebe o `attrs`
        do plano, nunca o Fact, entao os dois lados citando o MESMO plan_ref de
        um plano ANTIGO passariam batido e a comparacao sairia inteira, sob
        checks que ninguem pediu. Quem tem o `Fact.id` real e o chamador."""
        plan = self._plan(repo, capsys)
        before = self._result(
            repo, "antes", target="db.eventos", plan_ref="f_000000",
            checks=self._checks(1000),
        )
        after = self._result(
            repo, "depois", target="db.eventos", plan_ref="f_000000",
            checks=self._checks(998),
        )
        assert (
            main(
                [
                    "funcval", "compare",
                    "--plan", str(plan),
                    "--before", str(before),
                    "--after", str(after),
                ]
            )
            == 2
        )
        err = capsys.readouterr().err
        assert "f_000000" in err
        assert "sparkforge funcval plan" in err

    def test_the_real_plan_ref_passes(self, repo, capsys):
        """A outra metade: sem ela, a recusa acima passaria por rejeitar tudo."""
        plan = self._plan(repo, capsys)
        plan_id = next(
            f["id"]
            for f in json.loads(plan.read_text(encoding="utf-8"))
            if f["kind"] == "funcval.plan"
        )
        before = self._result(
            repo, "antes", target="db.eventos", plan_ref=plan_id, checks=self._checks(1000)
        )
        after = self._result(
            repo, "depois", target="db.eventos", plan_ref=plan_id, checks=self._checks(998)
        )
        code, _ = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
            ],
            capsys,
        )
        assert code == 0

    def test_two_sides_disagreeing_on_plan_ref_stay_with_the_module(self, repo, capsys):
        """Lados que discordam ENTRE SI sao o caso que o modulo JA bloqueia com
        `plan_ref_conflict`. Roubar esse caso apagaria a sentinela bloqueada que
        a SF-FVAL-005 precisa ver."""
        plan = self._plan(repo, capsys)
        before = self._result(
            repo, "antes", target="db.eventos", plan_ref="f_000000",
            checks=self._checks(1000),
        )
        after = self._result(
            repo, "depois", target="db.eventos", plan_ref="f_111111",
            checks=self._checks(998),
        )
        code, output = run(
            [
                "funcval", "compare",
                "--plan", str(plan),
                "--before", str(before),
                "--after", str(after),
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        sentinela = next(
            f for f in payload["items"] if f["kind"] == "funcval.analyzed"
        )
        assert sentinela["attrs"]["blocked_by"] == ["plan_ref_conflict"]
        assert "funcval.check_delta" not in payload["by_kind"]

    def test_missing_plan_file_names_the_verb_that_produces_it(self, repo, capsys):
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1))
        after = self._result(repo, "depois", target="db.eventos", checks=self._checks(1))
        assert (
            main(
                [
                    "funcval", "compare",
                    "--plan", str(repo / "nope.json"),
                    "--before", str(before),
                    "--after", str(after),
                ]
            )
            == 2
        )
        err = capsys.readouterr().err
        assert "--plan" in err
        assert "sparkforge funcval plan" in err

    def test_missing_result_file_says_who_measures(self, repo, capsys):
        """O resultado e do operador, e a mensagem tem que dizer isso: mandar
        rodar um verbo que produzisse o arquivo seria o motor afirmando medir."""
        plan = self._plan(repo, capsys)
        before = self._result(repo, "antes", target="db.eventos", checks=self._checks(1))
        assert (
            main(
                [
                    "funcval", "compare",
                    "--plan", str(plan),
                    "--before", str(before),
                    "--after", str(repo / "nope.json"),
                ]
            )
            == 2
        )
        err = capsys.readouterr().err
        assert "--after" in err
        assert "MEDIDO POR VOCE" in err


class TestCollectAthenaWorkgroup:
    def test_writes_artifact_and_registers_manifest(self, repo, capsys, monkeypatch):
        class _FakeAthenaWorkgroupClient:
            def get_work_group(self, WorkGroup):  # noqa: N803 - assinatura boto3
                return {
                    "WorkGroup": {
                        "Name": WorkGroup,
                        "State": "ENABLED",
                        "Configuration": {
                            "EngineVersion": {
                                "EffectiveEngineVersion": "Athena engine version 2",
                                "SelectedEngineVersion": "AUTO",
                            },
                            "BytesScannedCutoffPerQuery": 100,
                            "ResultConfiguration": {"OutputLocation": "s3://b/results/"},
                        },
                    }
                }

        monkeypatch.setattr(
            collect_aws,
            "require_boto3",
            lambda: _FakeBoto3(athena=_FakeAthenaWorkgroupClient()),
        )
        code, output = run(
            [
                "collect", "athena-workgroup",
                "--repo", str(repo),
                "--workgroup", "primary",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["kind"] == "athena_workgroup"
        assert payload["cache_hit"] is False
        written = json.loads((repo / payload["path"]).read_text(encoding="utf-8"))
        assert written["workgroups"][0]["engine_version"]["effective_engine_version"] == (
            "Athena engine version 2"
        )


class TestCliMcpEquivalence:
    """A garantia central da Fase 1: CLI e MCP chamam a mesma funcao de
    `_core.py`, entao para o mesmo input o payload precisa ser identico --
    nunca um subconjunto de campos, nunca uma serializacao diferente. Aqui
    comparado byte-a-byte (via round-trip JSON, para casar tipos) para pelo
    menos tres das capacidades novas desta fase."""

    def test_analyze_terraform_matches(self, repo, capsys):
        tf_path = repo / "main.tf"
        tf_path.write_text(TERRAFORM_SOURCE, encoding="utf-8")

        _, output = run(["analyze", "terraform", "--path", str(tf_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_terraform", {"path": str(tf_path)})
        assert cli_payload == mcp_payload

    def test_analyze_athena_workgroup_matches(self, repo, capsys):
        wg_path = repo / "wg.json"
        wg_path.write_text(ATHENA_WORKGROUP_DUMP, encoding="utf-8")

        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_athena_workgroup", {"path": str(wg_path)})
        assert cli_payload == mcp_payload

    def test_analyze_sql_matches(self, repo, capsys):
        sql_path = repo / "q.sql"
        sql_path.write_text(SQL_TEXT, encoding="utf-8")

        _, output = run(["analyze", "sql", "--path", str(sql_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_sql", {"path": str(sql_path)})
        assert cli_payload == mcp_payload

    def test_rules_lookup_matches(self, repo, capsys):
        _, output = run(["rules", "lookup", "--id", "SF-ENV-001"], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_rules_lookup", {"id": ["SF-ENV-001"]})
        assert cli_payload == mcp_payload
        # Trava especifica da Task 5: os dois caminhos precisam concordar tambem
        # no campo novo `knowledge_refs`, nao so no restante do payload.
        assert cli_payload["rules"][0]["knowledge_refs"]

    def test_playbook_matches(self, repo, capsys):
        """Omitir este teste ja custou uma rodada de revisao na Fase 3a --
        `playbook` e capacidade nova da Task 5 e precisa da mesma trava."""
        _, output = run(["playbook", "glue-infra-reviewer", "--repo", str(repo)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool(
            "sparkforge_playbook", {"coordinator": "glue-infra-reviewer", "repo": str(repo)}
        )
        assert cli_payload == mcp_payload
        assert cli_payload["steps"][0]["executor"] == "sf-inventory"

    def test_playbook_unknown_coordinator_matches(self, repo, capsys):
        assert main(["playbook", "nao-existe", "--repo", str(repo)]) == 2
        cli_message = capsys.readouterr().err.strip()

        mcp_payload = call_tool(
            "sparkforge_playbook", {"coordinator": "nao-existe", "repo": str(repo)}
        )
        assert "error" in mcp_payload
        assert cli_message == mcp_payload["error"]

    def test_knowledge_path_matches(self, repo, capsys):
        _, output = run(["knowledge", "path", "--file", "glue/runtime-matrix.md"], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool(
            "sparkforge_knowledge_path", {"file": "glue/runtime-matrix.md"}
        )
        assert cli_payload == mcp_payload

    def test_collect_verify_matches(self, repo, capsys):
        from sparkforge.collect.base import ArtifactEntry, register_artifact

        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_x.jsonl",
            sha256="a" * 64,
            source="s3://bucket/prefix/jr_x/",
            collect_command="sparkforge collect event-log --job-run jr_x",
            collected_at="2026-07-29T00:00:00Z",
        )
        register_artifact(entry, repo)

        _, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_collect_verify", {"repo": str(repo)})
        assert cli_payload == mcp_payload


class TestEmrFlag:
    """`--emr` nos tres verbos que aceitam runtime, e a mesma flag no MCP.

    A divida era de superficie, nao de motor: `detect_runtime` sempre soube ler
    `emr_release` de qualquer fonte, e so `emr.cluster` a alimentava. Quem sabe
    a release e nao tem dump ficava sem caminho -- e o MCP ficaria sem caminho
    mesmo com a flag na CLI, o que recriaria a assimetria um nivel acima."""

    def test_runtime_detect_derives_the_matrix_from_the_flag(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "emr-7.5.0"], capsys)
        payload = json.loads(output)
        assert payload["emr"] == "7.5.0"
        assert payload["spark"] == "3.5.2-amzn-1"
        assert payload["iceberg"] == "1.6.1-amzn-1"

    def test_the_numeric_spelling_reaches_the_same_row(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "7.5.0"], capsys)
        assert json.loads(output)["spark"] == "3.5.2-amzn-1"

    def test_judge_reports_the_runtime_the_flag_declared(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)

        _, output = run(["judge", "--facts", str(facts_path), "--emr", "emr-6.15.0"], capsys)
        assert json.loads(output)["runtime"]["emr"] == "6.15.0"

    def test_case_open_stores_the_release(self, repo, capsys):
        run(
            ["case", "open", "--repo", str(repo), "--case-id", "c-emr",
             "--now", "2026-08-01T00:00:00Z", "--emr", "emr-7.5.0"],
            capsys,
        )
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["runtime"]["emr"] == "7.5.0"

    def test_cli_and_mcp_agree(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "emr-7.5.0"], capsys)
        assert json.loads(output) == call_tool("sparkforge_runtime_detect", {"emr": "emr-7.5.0"})


class TestGlueJobRunsCommands:
    def test_analyze_cloudwatch_prints_metric_facts(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        artifact = tmp_path / "cw.json"
        artifact.write_text(
            json.dumps(
                {
                    "job_name": "my-job",
                    "job_run_id": "jr_1",
                    "start": "2026-08-01T10:00:00Z",
                    "end": "2026-08-01T10:20:00Z",
                    "period_seconds": 60,
                    "metric_data_results": [
                        {
                            "Id": "m0",
                            "Label": "glue.driver.workerUtilization",
                            "Timestamps": ["t"],
                            "Values": [0.5],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        assert main(["analyze", "cloudwatch", "--path", str(artifact)]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["by_kind"]["glue.metric"] == 1

    def test_analyze_glue_job_runs_writes_out_file(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        (runs_dir / "my-job_jr_1.json").write_text(
            json.dumps(
                {
                    "Id": "jr_1",
                    "JobName": "my-job",
                    "JobRunState": "SUCCEEDED",
                    "StartedOn": "2026-08-01T10:00:00+00:00",
                    "CompletedOn": "2026-08-01T10:20:00+00:00",
                    "ExecutionTime": 1200,
                    "GlueVersion": "5.0",
                    "WorkerType": "G.1X",
                    "NumberOfWorkers": 10,
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "facts.json"

        code = main(
            [
                "analyze",
                "glue-job-runs",
                "--path",
                str(runs_dir),
                "--job-name",
                "my-job",
                "--out",
                str(out),
            ]
        )

        assert code == 0
        kinds = {f["kind"] for f in json.loads(out.read_text(encoding="utf-8"))}
        assert "glue.job_run" in kinds
        assert "glue.job_run.distribution" in kinds
