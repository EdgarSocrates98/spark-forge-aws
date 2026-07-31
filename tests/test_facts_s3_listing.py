"""Testes semanticos do extrator de listagem S3.

`fixtures/s3/` prova o comportamento de ponta a ponta contra o catalogo; este
modulo prova as decisoes do extrator isoladamente. Duas delas carregam quase
todo o risco, e as duas so aparecem aqui:

**O que NAO e arquivo de dados.** `_SUCCESS` tem 0 byte. Um prefixo com 200
arquivos de 300 MB e um `_SUCCESS` tem media de 298 MB se o marcador for
excluido, e 296 MB se for contado -- irrelevante. Mas um prefixo com 3
arquivos e 3 marcadores tem a media cortada pela metade, e SF-PQ-001 e um
limiar sobre media. O erro so aparece nos casos pequenos, que sao os que
ninguem testa a mao.

**O que a listagem nao respondeu.** `IsTruncated` e um booleano facil de
ignorar, e ignora-lo produz numeros que parecem certos: `file_count: 1000` e
uma contagem plausivel, nao um erro visivel. Por isso a fixture de truncamento
e o teste abaixo existem os dois.
"""
import json

import pytest

from sparkforge.facts.s3_listing import (
    EMITTED_KINDS,
    extract_s3_listing,
    extract_s3_listing_path,
    extract_s3_listing_tree,
)


def _extract(payload, path="listing.json"):
    return extract_s3_listing(payload, path)


def _summaries(facts):
    return [f for f in facts if f.kind == "s3.prefix_summary"]


def _unresolved(facts):
    return [f for f in facts if f.kind == "s3.unresolved"]


def _sentinel(facts):
    return next(f for f in facts if f.kind == "s3.analyzed")


def _listing(*objects, truncated=False, bucket="lake", prefix="analytics/pedidos/"):
    return {
        "Name": bucket,
        "Prefix": prefix,
        "IsTruncated": truncated,
        "Contents": [{"Key": key, "Size": size} for key, size in objects],
    }


class TestGrouping:
    def test_format_and_compression_come_from_the_suffix(self):
        facts = _extract(
            _listing(
                ("a/part-0.snappy.parquet", 1000),
                ("a/eventos.json.gz", 2000),
                ("a/dados.csv", 3000),
            )
        )
        groups = {(f.attrs["format"], f.attrs["compression"]) for f in _summaries(facts)}
        assert groups == {("parquet", "snappy"), ("text", "gzip"), ("text", "none")}

    def test_each_group_gets_its_own_summary(self):
        """Um sumario unico por prefixo diluiria o `.gz` gigante na media do
        Parquet, e SF-PQ-003 -- que exige `format: text` -- nunca casaria."""
        facts = _extract(
            _listing(("a/part-0.snappy.parquet", 1000), ("a/carga.csv.gz", 4_000_000_000))
        )
        by_format = {f.attrs["format"]: f.measures["max_file_bytes"] for f in _summaries(facts)}
        assert by_format == {"parquet": 1000, "text": 4_000_000_000}

    def test_unknown_suffix_is_not_guessed_as_parquet(self):
        """`format: unknown` faz SF-PQ-003 nao avaliar o grupo. Chutar
        `parquet` faria a regra de compressao nao splitavel calar sobre um
        arquivo que pode muito bem ser texto."""
        facts = _extract(_listing(("a/dados.bin", 1000)))
        summary = _summaries(facts)[0]
        assert (summary.attrs["format"], summary.attrs["compression"]) == ("unknown", "unknown")

    def test_longer_suffix_wins_over_the_shorter_one(self):
        """`.json.gz` tem que casar antes de `.json`, senao um arquivo
        comprimido seria classificado como texto puro e SF-PQ-003 o ignoraria."""
        facts = _extract(_listing(("a/eventos.json.gz", 1000)))
        assert _summaries(facts)[0].attrs["compression"] == "gzip"

    def test_classification_is_case_insensitive(self):
        facts = _extract(_listing(("a/PART-0.SNAPPY.PARQUET", 1000)))
        assert _summaries(facts)[0].attrs["format"] == "parquet"

    def test_the_subject_tells_the_groups_apart(self):
        facts = _extract(
            _listing(("a/part-0.snappy.parquet", 1000), ("a/carga.csv.gz", 2000))
        )
        symbols = {f.subject["symbol"] for f in _summaries(facts)}
        assert len(symbols) == 2
        assert all(s.startswith("s3://lake/analytics/pedidos/") for s in symbols)


class TestControlObjects:
    @pytest.mark.parametrize(
        "key", ["a/_SUCCESS", "a/_committed", "a/_started", "a/.DS_Store", "a/dt=1/"]
    )
    def test_control_objects_never_count_as_data(self, key):
        facts = _extract(_listing((key, 0), ("a/part-0.snappy.parquet", 300_000_000)))
        summary = _summaries(facts)[0]
        assert summary.measures["file_count"] == 1
        assert summary.measures["avg_file_bytes"] == 300_000_000

    def test_control_objects_are_still_counted_in_the_sentinel(self):
        """Excluir do sumario nao e esconder: a sentinela mostra que existiam,
        para que a diferenca entre `object_count` e a soma dos grupos tenha
        explicacao."""
        facts = _extract(_listing(("a/_SUCCESS", 0), ("a/part-0.snappy.parquet", 100)))
        sentinel = _sentinel(facts)
        assert sentinel.measures["object_count"] == 2
        assert sentinel.measures["control_object_count"] == 1

    def test_a_directory_marker_with_bytes_is_not_a_control_object(self):
        """Chave terminada em `/` com tamanho > 0 nao e marcador do console:
        e um objeto de verdade com nome estranho, e some-lo importa."""
        facts = _extract(_listing(("a/estranho/", 500),))
        assert _summaries(facts)[0].measures["file_count"] == 1


class TestTruncation:
    def test_truncated_listing_emits_no_summary(self):
        objects = [(f"a/part-{i}.snappy.parquet", 1_000_000) for i in range(50)]
        facts = _extract(_listing(*objects, truncated=True))
        assert _summaries(facts) == []
        assert _unresolved(facts)[0].attrs["reason"] == "truncated_listing"

    def test_the_blind_spot_records_how_much_was_seen(self):
        """`listed_object_count` deixa o operador saber que a pagina existe --
        so nao vale como total."""
        facts = _extract(_listing(("a/part-0.snappy.parquet", 10), truncated=True))
        assert _unresolved(facts)[0].attrs["listed_object_count"] == 1

    def test_the_sentinel_marks_the_listing_as_truncated(self):
        facts = _extract(_listing(("a/part-0.snappy.parquet", 10), truncated=True))
        sentinel = _sentinel(facts)
        assert sentinel.attrs["truncated"] is True
        assert sentinel.measures["group_count"] == 0

    def test_a_complete_listing_is_not_marked_truncated(self):
        facts = _extract(_listing(("a/part-0.snappy.parquet", 10)))
        assert _sentinel(facts).attrs["truncated"] is False


class TestMeasures:
    def test_percentiles_are_real_file_sizes_not_interpolations(self):
        """Um p95 interpolado seria um numero que nenhum arquivo tem, e o
        operador nao conseguiria ir olhar 'o arquivo do p95'."""
        sizes = [10, 20, 30, 40, 50]
        facts = _extract(_listing(*[(f"a/p{i}.parquet", s) for i, s in enumerate(sizes)]))
        summary = _summaries(facts)[0]
        assert summary.measures["p50_file_bytes"] in sizes
        assert summary.measures["p95_file_bytes"] in sizes
        assert summary.measures["min_file_bytes"] == 10
        assert summary.measures["max_file_bytes"] == 50

    def test_total_and_average_agree(self):
        facts = _extract(_listing(("a/x.parquet", 100), ("a/y.parquet", 300)))
        summary = _summaries(facts)[0]
        assert summary.measures["total_bytes"] == 400
        assert summary.measures["avg_file_bytes"] == 200

    def test_a_single_file_still_produces_every_measure(self):
        facts = _extract(_listing(("a/x.parquet", 42)))
        measures = _summaries(facts)[0].measures
        assert measures["file_count"] == 1
        assert measures["min_file_bytes"] == measures["max_file_bytes"] == 42


class TestMalformedPayload:
    @pytest.mark.parametrize("payload", [[], "texto", 3])
    def test_payload_that_is_not_an_object_is_unresolved(self, payload):
        facts = _extract(payload)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_json"

    def test_contents_of_the_wrong_type_reports_the_section(self):
        facts = _extract({"Name": "lake", "Prefix": "p/", "Contents": {"Key": "a"}})
        assert _unresolved(facts)[0].attrs["section"] == "Contents"

    def test_entry_without_key_is_unresolved(self):
        facts = _extract({"Name": "lake", "Prefix": "p/", "Contents": [{"Size": 10}]})
        assert _unresolved(facts)[0].attrs["reason"] == "missing_key"

    @pytest.mark.parametrize("size", [None, "1024", True, {}])
    def test_non_numeric_size_is_unresolved_not_zero(self, size):
        """Tamanho ausente virando 0 derrubaria a media e faria SF-PQ-001
        disparar sobre dado que ninguem mediu. `True` entra na lista porque em
        Python `isinstance(True, int)` e verdadeiro."""
        facts = _extract({"Name": "lake", "Prefix": "p/", "Contents": [{"Key": "a", "Size": size}]})
        assert _unresolved(facts)[0].attrs["reason"] == "missing_size"
        assert _summaries(facts) == []

    def test_missing_contents_is_not_an_error(self):
        """Prefixo vazio e uma resposta valida: o comando rodou e nao achou
        objeto nenhum."""
        facts = _extract({"Name": "lake", "Prefix": "p/"})
        assert _unresolved(facts) == []
        assert _sentinel(facts).measures["object_count"] == 0

    def test_one_bad_entry_never_discards_the_good_ones(self):
        facts = _extract(
            {
                "Name": "lake",
                "Prefix": "p/",
                "Contents": ["lixo", {"Key": "p/x.parquet", "Size": 100}],
            }
        )
        assert _summaries(facts)[0].measures["file_count"] == 1
        assert len(_unresolved(facts)) == 1

    def test_missing_bucket_name_does_not_invent_one(self):
        facts = _extract({"Contents": [{"Key": "p/x.parquet", "Size": 100}]})
        assert "desconhecido" in _summaries(facts)[0].attrs["prefix"]


class TestContract:
    def test_no_fact_escapes_the_declared_namespace(self):
        facts = _extract(_listing(("a/x.parquet", 1))) + _extract("texto")
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_extraction_is_deterministic(self):
        payload = _listing(("a/x.parquet", 1), ("a/y.csv.gz", 2))
        assert [f.to_dict() for f in _extract(payload)] == [f.to_dict() for f in _extract(payload)]

    def test_the_sentinel_counts_the_unresolved(self):
        facts = _extract({"Name": "lake", "Prefix": "p/", "Contents": [{"Size": 1}, "lixo"]})
        assert _sentinel(facts).measures["unresolved_count"] == len(_unresolved(facts))


class TestPathEntryPoints:
    def test_reads_a_file_and_anchors_relative_to_the_repo_root(self, tmp_path):
        listing = tmp_path / "sub" / "listing.json"
        listing.parent.mkdir()
        listing.write_text(json.dumps(_listing(("a/x.parquet", 1))), encoding="utf-8")

        facts = extract_s3_listing_path(listing, repo_root=tmp_path)
        assert _sentinel(facts).provenance["artifact"] == "sub/listing.json"
        assert _sentinel(facts).provenance["artifact_sha256"]

    def test_invalid_json_becomes_unresolved_with_a_sentinel(self, tmp_path):
        listing = tmp_path / "listing.json"
        listing.write_text("{ nao e json", encoding="utf-8")

        facts = extract_s3_listing_path(listing, repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_json"
        assert _sentinel(facts).measures["unresolved_count"] == 1

    def test_unreadable_path_becomes_unresolved(self, tmp_path):
        facts = extract_s3_listing_path(tmp_path / "nao-existe.json", repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "read_error"

    def test_tree_reads_every_page_of_a_paginated_listing(self, tmp_path):
        """Listagem paginada chega como varios arquivos, e cada um e um dump
        valido por si so."""
        for page in range(3):
            (tmp_path / f"page-{page}.json").write_text(
                json.dumps(_listing((f"a/part-{page}.parquet", 100))), encoding="utf-8"
            )

        facts = extract_s3_listing_tree(tmp_path, repo_root=tmp_path)
        assert len([f for f in facts if f.kind == "s3.analyzed"]) == 3
