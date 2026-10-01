"""Testes semanticos do extrator de workgroups do Athena.

`fixtures/athena/` prova o comportamento de ponta a ponta contra o catalogo;
este modulo prova as decisoes do extrator isoladamente, sobre payloads
construidos na mao -- em especial as que nunca chegam a virar Fact e por isso
nao aparecem num golden de facts: string de engine version que nao contem
inteiro, bloco ausente, tipo errado, chave ausente.

O invariante central, e a razao de o modulo existir: NENHUM caminho pode
produzir `measures.engine_version` que o dump nao afirme. SF-ATH-004 compara
esse numero com 3; um default fabricado transformaria "nao sei" em "esta
desatualizado", que e a resposta autoritativa-porem-errada que o pacote
existe para evitar.
"""
import json

import pytest

from sparkforge.facts.athena_workgroup import (
    EMITTED_KINDS,
    extract_athena_workgroup,
    extract_athena_workgroup_path,
)


def _extract(payload, path="workgroups.json"):
    return extract_athena_workgroup(payload, path)


def _kinds(facts):
    return [f.kind for f in facts]


def _workgroups(facts):
    return [f for f in facts if f.kind == "athena.workgroup"]


def _unresolved(facts):
    return [f for f in facts if f.kind == "athena.unresolved"]


def _sentinel(facts):
    return next(f for f in facts if f.kind == "athena.analyzed")


def _one(name="primary", **entry):
    base = {
        "name": name,
        "engine_version": {
            "effective_engine_version": "Athena engine version 3",
            "selected_engine_version": "AUTO",
        },
        "state": "ENABLED",
    }
    base.update(entry)
    return {"workgroups": [base]}


class TestEngineVersionParsing:
    @pytest.mark.parametrize(
        ("effective", "expected"),
        [
            ("Athena engine version 3", 3),
            ("Athena engine version 2", 2),
            ("Athena engine version 10", 10),
            # A API nao garante capitalizacao nem sufixo estaveis.
            ("ATHENA ENGINE VERSION 3", 3),
            ("Athena engine version 3 (PySpark on Athena preview)", 3),
        ],
    )
    def test_reads_the_integer_out_of_the_api_string(self, effective, expected):
        facts = _extract(
            _one(engine_version={"effective_engine_version": effective, "x": None})
        )
        assert _workgroups(facts)[0].measures["engine_version"] == expected

    @pytest.mark.parametrize(
        "effective",
        ["Athena engine version PREVIEW", "engine version", "", "3"],
    )
    def test_string_without_a_readable_integer_never_becomes_a_workgroup(self, effective):
        """`"3"` sozinho tambem nao passa: sem a palavra `version` nao ha como
        distinguir a versao da engine de qualquer outro numero na string."""
        facts = _extract(_one(engine_version={"effective_engine_version": effective}))
        assert _workgroups(facts) == []
        assert _unresolved(facts)[0].attrs["reason"] == "unparseable_engine_version"

    def test_unparseable_keeps_the_original_string_as_evidence(self):
        facts = _extract(
            _one(engine_version={"effective_engine_version": "Athena engine version PREVIEW"})
        )
        assert (
            _unresolved(facts)[0].attrs["effective_engine_version"]
            == "Athena engine version PREVIEW"
        )

    @pytest.mark.parametrize(
        "engine_version",
        [None, {}, {"selected_engine_version": "AUTO"}, "Athena engine version 3", 3, []],
    )
    def test_missing_or_wrongly_typed_block_becomes_unresolved(self, engine_version):
        """Inclusive o caso em que `engine_version` veio como string em vez de
        objeto: ler a versao dali seria adivinhar o contrato da API."""
        facts = _extract(_one(engine_version=engine_version))
        assert _workgroups(facts) == []
        assert _unresolved(facts)[0].attrs["reason"] == "missing_engine_version"

    def test_selected_engine_version_is_recorded_but_never_parsed(self):
        """`selected` e a preferencia configurada (`AUTO`), `effective` e o que
        de fato roda. Julgar pela preferencia acusaria errado todo workgroup
        em AUTO."""
        facts = _extract(
            _one(
                engine_version={
                    "effective_engine_version": "Athena engine version 3",
                    "selected_engine_version": "AUTO",
                }
            )
        )
        workgroup = _workgroups(facts)[0]
        assert workgroup.measures["engine_version"] == 3
        assert workgroup.attrs["selected_engine_version"] == "AUTO"


class TestOptionalFields:
    def test_bytes_scanned_cutoff_present_becomes_a_measure(self):
        facts = _extract(_one(bytes_scanned_cutoff=1099511627776))
        assert _workgroups(facts)[0].measures["bytes_scanned_cutoff"] == 1099511627776

    def test_bytes_scanned_cutoff_absent_is_omitted_not_zero(self):
        facts = _extract(_one())
        assert "bytes_scanned_cutoff" not in _workgroups(facts)[0].measures

    @pytest.mark.parametrize("cutoff", ["1099511627776", None, True, {}])
    def test_non_numeric_cutoff_is_dropped_instead_of_coerced(self, cutoff):
        """`True` entra na lista de proposito: em Python `isinstance(True, int)`
        e verdadeiro, e um cutoff de 1 byte inventado a partir de um booleano
        seria um limite absurdo apresentado como medida."""
        facts = _extract(_one(bytes_scanned_cutoff=cutoff))
        assert "bytes_scanned_cutoff" not in _workgroups(facts)[0].measures

    @pytest.mark.parametrize("state", [None, 3, {"a": 1}])
    def test_non_string_state_becomes_none_not_a_string(self, state):
        facts = _extract(_one(state=state))
        assert _workgroups(facts)[0].attrs["state"] is None


class TestMalformedPayload:
    @pytest.mark.parametrize("payload", [[], "texto", 3, None])
    def test_payload_that_is_not_an_object_is_unresolved(self, payload):
        facts = _extract(payload)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_json"

    def test_workgroups_of_the_wrong_type_reports_the_section(self):
        facts = _extract({"workgroups": {"primary": {}}})
        unresolved = _unresolved(facts)[0]
        assert unresolved.attrs["reason"] == "malformed_json"
        assert unresolved.attrs["section"] == "workgroups"

    def test_entry_that_is_not_an_object_reports_the_indexed_section(self):
        facts = _extract({"workgroups": ["primary"]})
        assert _unresolved(facts)[0].attrs["section"] == "workgroups[]"

    @pytest.mark.parametrize("name", [None, "", "   ", 3])
    def test_entry_without_a_usable_name_is_unresolved(self, name):
        facts = _extract({"workgroups": [{"name": name}]})
        assert _unresolved(facts)[0].attrs["reason"] == "missing_workgroup_name"

    def test_missing_workgroups_key_is_not_an_error(self):
        """Dump valido que simplesmente nao coletou workgroup nenhum. Marcar
        isso como erro faria o operador cacar um defeito inexistente."""
        facts = _extract({})
        assert _unresolved(facts) == []
        assert _sentinel(facts).measures == {"workgroup_count": 0, "unresolved_count": 0}

    def test_one_bad_entry_never_discards_the_good_ones(self):
        facts = _extract(
            {
                "workgroups": [
                    "lixo",
                    {
                        "name": "primary",
                        "engine_version": {
                            "effective_engine_version": "Athena engine version 3"
                        },
                    },
                ]
            }
        )
        assert [f.attrs["name"] for f in _workgroups(facts)] == ["primary"]
        assert len(_unresolved(facts)) == 1


class TestSentinel:
    def test_counts_workgroups_and_unresolved(self):
        facts = _extract(
            {
                "workgroups": [
                    {"name": "a", "engine_version": {"effective_engine_version": "version 3"}},
                    {"name": "b"},
                    {"name": "c", "engine_version": {"effective_engine_version": "sem numero"}},
                ]
            }
        )
        assert _sentinel(facts).measures == {"workgroup_count": 3, "unresolved_count": 2}

    def test_workgroup_count_counts_named_entries_not_emitted_facts(self):
        """`workgroup_count` conta o que o dump descreveu; `unresolved_count`
        conta o que nao deu para ler. Se os dois contassem a mesma coisa, um
        dump inteiramente ilegivel pareceria um dump vazio."""
        facts = _extract({"workgroups": [{"name": "so-o-nome"}]})
        assert _sentinel(facts).measures == {"workgroup_count": 1, "unresolved_count": 1}

    def test_sentinel_exists_even_for_a_completely_malformed_payload(self):
        facts = _extract("texto")
        assert _sentinel(facts).measures["workgroup_count"] == 0


class TestContract:
    def test_no_fact_escapes_the_declared_namespace(self):
        facts = _extract(_one()) + _extract("texto") + _extract({"workgroups": [{}]})
        assert set(_kinds(facts)) <= EMITTED_KINDS

    def test_workgroup_is_anchored_to_the_workgroup_not_to_the_file(self):
        """Ancorar no arquivo faria o operador ler 'o dump esta errado' quando
        o achado e sobre um workgroup especifico dentro dele."""
        subject = _workgroups(_extract(_one(name="legacy-etl")))[0].subject
        assert subject == {"type": "job_run", "symbol": "legacy-etl"}

    def test_extraction_is_deterministic(self):
        payload = _one()
        assert [f.to_dict() for f in _extract(payload)] == [f.to_dict() for f in _extract(payload)]

    def test_facts_come_back_sorted_by_kind(self):
        facts = _extract({"workgroups": [{"name": "b"}, {"name": "a"}]})
        assert _kinds(facts) == sorted(_kinds(facts))


class TestPathEntryPoint:
    def test_reads_a_file_and_anchors_relative_to_the_repo_root(self, tmp_path):
        dump = tmp_path / "sub" / "workgroups.json"
        dump.parent.mkdir()
        dump.write_text(json.dumps(_one()), encoding="utf-8")

        facts = extract_athena_workgroup_path(dump, repo_root=tmp_path)
        assert _sentinel(facts).provenance["artifact"] == "sub/workgroups.json"
        assert _sentinel(facts).provenance["artifact_sha256"]

    def test_invalid_json_becomes_unresolved_instead_of_raising(self, tmp_path):
        dump = tmp_path / "workgroups.json"
        dump.write_text("{ nao e json", encoding="utf-8")

        facts = extract_athena_workgroup_path(dump, repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_json"

    def test_unreadable_path_becomes_unresolved_instead_of_raising(self, tmp_path):
        facts = extract_athena_workgroup_path(tmp_path / "nao-existe.json", repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "read_error"

    def test_bom_prefixed_file_still_parses(self, tmp_path):
        """Dump salvo por PowerShell no Windows vem com BOM. Sem
        `utf-8-sig` isso viraria `malformed_json` num arquivo perfeito."""
        dump = tmp_path / "workgroups.json"
        dump.write_text(json.dumps(_one()), encoding="utf-8-sig")

        facts = extract_athena_workgroup_path(dump, repo_root=tmp_path)
        assert len(_workgroups(facts)) == 1
