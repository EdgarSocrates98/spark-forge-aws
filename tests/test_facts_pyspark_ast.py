import ast
import textwrap

from sparkforge.facts.pyspark_ast import EXTRACTOR_ID, extract_path, extract_source, extract_tree


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


class TestPartitioning:
    def test_detects_coalesce_with_literal_one(self):
        src = textwrap.dedent(
            """
            def run(df):
                df.coalesce(1).write.parquet("s3://b/p")
            """
        )
        facts = extract_source(src, "lib/loader.py")
        got = facts_of("pyspark.partitioning", facts)
        assert len(got) == 1
        fact = got[0]
        assert fact.attrs["method"] == "coalesce"
        assert fact.attrs["literal_arg"] is True
        assert fact.measures["target_count"] == 1
        assert fact.subject["file"] == "lib/loader.py"
        assert fact.subject["line"] == 3
        assert fact.subject["symbol"] == "run"
        assert "coalesce" in fact.subject["snippet"]

    def test_detects_repartition_with_literal(self):
        src = "df.repartition(200)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["method"] == "repartition"
        assert facts[0].measures["target_count"] == 200
        assert facts[0].attrs["has_partition_expr"] is False

    def test_repartition_by_column_marks_partition_expr(self):
        src = 'df.repartition(200, "cliente_id")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["has_partition_expr"] is True

    def test_non_literal_arg_is_marked_and_has_no_measure(self):
        src = "df.repartition(n_particoes)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False
        assert "target_count" not in facts[0].measures

    def test_clean_code_yields_no_partitioning_facts(self):
        src = 'df.select("a").filter("a > 1").write.parquet("s3://b/p")\n'
        assert facts_of("pyspark.partitioning", extract_source(src, "a.py")) == []

    def test_negative_literal_is_recognized(self):
        src = "df.repartition(-5)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is True
        assert facts[0].measures["target_count"] == -5
        assert facts[0].attrs["has_partition_expr"] is False

    def test_positive_unary_literal_is_recognized(self):
        src = "df.repartition(+8)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is True
        assert facts[0].measures["target_count"] == 8
        assert facts[0].attrs["has_partition_expr"] is False

    def test_coalesce_true_stays_non_literal(self):
        src = "df.coalesce(True)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False
        assert "target_count" not in facts[0].measures

    def test_double_negation_stays_non_literal(self):
        src = "df.repartition(--5)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False

    def test_negative_literal_with_column_marks_partition_expr(self):
        src = 'df.repartition(-5, "col")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["has_partition_expr"] is True

    def test_detects_repartition_by_range_with_literal(self):
        src = 'df.repartitionByRange(50, "col")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["method"] == "repartitionByRange"
        assert facts[0].measures["target_count"] == 50
        assert facts[0].attrs["has_partition_expr"] is True


class TestProvenanceAndDeterminism:
    def test_provenance_records_extractor_and_artifact(self):
        facts = extract_source("df.coalesce(1)\n", "lib/x.py")
        prov = facts[0].provenance
        assert prov["extractor"] == EXTRACTOR_ID
        assert prov["artifact"] == "lib/x.py"
        assert len(prov["artifact_sha256"]) == 64

    def test_same_input_twice_yields_identical_dicts(self):
        src = "df.coalesce(1)\ndf.repartition(10)\n"
        first = [f.to_dict() for f in extract_source(src, "a.py")]
        second = [f.to_dict() for f in extract_source(src, "a.py")]
        assert first == second


class TestUnresolved:
    def test_dynamic_dispatch_emits_unresolved_not_a_finding_candidate(self):
        src = "getattr(df, metodo)(1)\n"
        facts = extract_source(src, "a.py")
        assert facts_of("pyspark.unresolved", facts)
        assert facts_of("pyspark.partitioning", facts) == []

    def test_unresolved_records_reason_and_location(self):
        src = "getattr(df, metodo)(1)\n"
        fact = facts_of("pyspark.unresolved", extract_source(src, "a.py"))[0]
        assert fact.attrs["reason"] == "getattr"
        assert fact.subject["line"] == 1


class TestSyntaxError:
    def test_unparseable_file_yields_single_unresolved_fact(self):
        facts = extract_source("def broken(:\n", "bad.py")
        assert len(facts) == 1
        assert facts[0].kind == "pyspark.unresolved"
        assert facts[0].attrs["reason"] == "syntax_error"

    def test_parser_stack_overflow_degrades_instead_of_raising(self):
        """CPython levanta MemoryError, nao RecursionError, quando o parser
        estoura em aninhamento extremo. Para o operador as duas coisas significam
        a mesma coisa: o analisador nao conseguiu ler o arquivo. Nenhuma das duas
        pode vazar, porque quem chama so trata Fact."""
        facts = extract_source("-" * 10000 + "1\n", "deep.py")
        assert len(facts) == 1
        assert facts[0].kind == "pyspark.unresolved"
        assert facts[0].attrs["reason"] == "too_deep"

    def test_memory_error_from_parse_is_caught(self, monkeypatch):
        """Trigger deterministico, independente de interpretador: o limite exato
        que o parser aceita varia por versao, entao o teste acima poderia deixar
        de estourar num Python futuro sem que a protecao tenha sido removida."""
        import ast as ast_module

        def boom(*_args, **_kwargs):
            raise MemoryError("Parser stack overflowed")

        monkeypatch.setattr(ast_module, "parse", boom)
        facts = extract_source("df.coalesce(1)\n", "a.py")
        assert [f.attrs["reason"] for f in facts] == ["too_deep"]


class TestExtractTree:
    def test_deterministic_order_across_two_runs(self, tmp_path):
        (tmp_path / "b.py").write_text("df.repartition(10)\n", encoding="utf-8")
        nested = tmp_path / "lib"
        nested.mkdir()
        (nested / "a.py").write_text("df.coalesce(1)\n", encoding="utf-8")

        first = [f.to_dict() for f in extract_tree(tmp_path, repo_root=tmp_path)]
        second = [f.to_dict() for f in extract_tree(tmp_path, repo_root=tmp_path)]
        assert first == second
        assert len(first) == 2

    def test_pycache_is_skipped(self, tmp_path):
        (tmp_path / "a.py").write_text("df.coalesce(1)\n", encoding="utf-8")
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "a.cpython-310.py").write_text("df.coalesce(2)\n", encoding="utf-8")

        facts = extract_tree(tmp_path, repo_root=tmp_path)
        assert len(facts) == 1
        assert facts[0].measures["target_count"] == 1

    def test_posix_style_anchor_with_repo_root(self, tmp_path):
        nested = tmp_path / "lib" / "sub"
        nested.mkdir(parents=True)
        (nested / "a.py").write_text("df.coalesce(1)\n", encoding="utf-8")

        facts = extract_tree(tmp_path, repo_root=tmp_path)
        assert facts[0].subject["file"] == "lib/sub/a.py"
        assert "\\" not in facts[0].subject["file"]

    def test_posix_style_anchor_without_repo_root(self, tmp_path):
        (tmp_path / "a.py").write_text("df.coalesce(1)\n", encoding="utf-8")

        facts = extract_tree(tmp_path)
        assert "\\" not in facts[0].subject["file"]

    def test_syntax_error_file_does_not_erase_others(self, tmp_path):
        (tmp_path / "good_a.py").write_text("df.coalesce(1)\n", encoding="utf-8")
        (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        (tmp_path / "good_b.py").write_text("df.repartition(10)\n", encoding="utf-8")

        facts = extract_tree(tmp_path, repo_root=tmp_path)
        unresolved = facts_of("pyspark.unresolved", facts)
        partitioning = facts_of("pyspark.partitioning", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "syntax_error"
        assert len(partitioning) == 2

    def test_over_deep_file_does_not_erase_others(self, tmp_path, monkeypatch):
        """Regression guard for Defect 1.

        A real interpreter stack exhaustion is not a reliable test trigger:
        which exception it raises (RecursionError vs. MemoryError) depends
        on the Python version and on whether the depth comes from a fluent
        chain (fixed by the explicit-stack `_Context`) or from `ast.parse`
        itself. `ast.parse` is monkeypatched to simulate a RecursionError
        deterministically, so this test exercises the `except RecursionError`
        path in `extract_source` and confirms `extract_tree` does not lose
        the other files' facts because of it.
        """
        (tmp_path / "good_a.py").write_text("df.coalesce(1)\n", encoding="utf-8")
        (tmp_path / "deep.py").write_text("__SENTINEL_TOO_DEEP__\n", encoding="utf-8")
        (tmp_path / "good_b.py").write_text("df.repartition(10)\n", encoding="utf-8")

        real_parse = ast.parse

        def fake_parse(source, *args, **kwargs):
            if source == "__SENTINEL_TOO_DEEP__\n":
                raise RecursionError("simulated stack exhaustion")
            return real_parse(source, *args, **kwargs)

        monkeypatch.setattr(ast, "parse", fake_parse)

        facts = extract_tree(tmp_path, repo_root=tmp_path)
        unresolved = facts_of("pyspark.unresolved", facts)
        partitioning = facts_of("pyspark.partitioning", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "too_deep"
        assert len(partitioning) == 2

    def test_bom_and_non_bom_twins_produce_identical_facts(self, tmp_path):
        code = "df.coalesce(1)\n"
        plain_root = tmp_path / "plain"
        bom_root = tmp_path / "bom"
        plain_root.mkdir()
        bom_root.mkdir()
        (plain_root / "twin.py").write_bytes(code.encode("utf-8"))
        (bom_root / "twin.py").write_bytes(code.encode("utf-8-sig"))

        plain_facts = extract_path(plain_root / "twin.py", repo_root=plain_root)
        bom_facts = extract_path(bom_root / "twin.py", repo_root=bom_root)

        assert len(plain_facts) == len(bom_facts) == 1
        assert plain_facts[0].kind == "pyspark.partitioning"
        assert plain_facts[0].id == bom_facts[0].id
        assert [f.to_dict() for f in plain_facts] == [f.to_dict() for f in bom_facts]
