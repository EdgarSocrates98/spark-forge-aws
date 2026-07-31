"""Testes semanticos do extrator do inventario de consumidores.

O inventario e o unico artefato do pacote escrito por uma pessoa, e isso muda
a natureza dos erros: nao ha ferramenta gerando o formato, entao grafia,
maiuscula e campo faltando sao a regra, nao a excecao. Duas decisoes seguram o
peso disso:

**Normalizacao minima e previsivel.** `service` vira minusculas sem espaco nas
bordas, e nada alem. SF-ENV-002 casa por `attrs.service: athena`, entao
`"Athena "` precisa casar -- mas inventar sinonimos ("athena-sql" -> "athena")
faria a regra depender de um dicionario que ninguem le, e uma grafia nao
prevista viraria silencio em vez de fact visivel.

**Silencio explicito.** Tabela ausente do inventario nao produz fact, e a
regra nao dispara para ela. Isso e correto e perigoso ao mesmo tempo: correto
porque ausencia de declaracao nao e declaracao de ausencia; perigoso porque o
operador pode ler "nenhum achado" como "nenhum consumidor afetado". Dai a
sentinela com `table_count`, que distingue inventario vazio de inventario que
nunca foi lido.
"""
import pytest

from sparkforge.facts.consumers import (
    EMITTED_KINDS,
    KNOWN_SERVICES,
    extract_consumers,
    extract_consumers_path,
    extract_consumers_tree,
)


def _extract(payload, path="consumers.yaml"):
    return extract_consumers(payload, path)


def _consumers(facts):
    return [f for f in facts if f.kind == "env.consumer"]


def _unresolved(facts):
    return [f for f in facts if f.kind == "env.unresolved"]


def _sentinel(facts):
    return next(f for f in facts if f.kind == "env.consumers_analyzed")


def _inventory(*entries):
    return {"consumers": list(entries)}


class TestNormalization:
    @pytest.mark.parametrize("raw", ["athena", "Athena", "ATHENA", "  athena  "])
    def test_service_is_lowercased_and_stripped(self, raw):
        """SF-ENV-002 casa por `attrs.service: athena`. Sem normalizar, um
        `Athena` maiusculo faria a regra calar sobre um consumidor real."""
        facts = _extract(_inventory({"table": "db.t", "service": raw}))
        assert _consumers(facts)[0].attrs["service"] == "athena"

    def test_unknown_service_is_kept_not_rejected(self):
        """Servico fora da lista conhecida vira fact com o texto que a pessoa
        escreveu. Rejeitar transformaria um erro de grafia em silencio."""
        facts = _extract(_inventory({"table": "db.t", "service": "hive-metastore"}))
        consumer = _consumers(facts)[0]
        assert consumer.attrs["service"] == "hive-metastore"
        assert consumer.attrs["known_service"] is False

    def test_known_service_is_flagged(self):
        facts = _extract(_inventory({"table": "db.t", "service": "quicksight"}))
        assert _consumers(facts)[0].attrs["known_service"] is True

    def test_athena_is_in_the_known_list(self):
        """Se `athena` sair da lista, SF-ENV-002 continua funcionando -- mas o
        sinal de grafia errada some. Este assert e o alarme."""
        assert "athena" in KNOWN_SERVICES

    def test_table_keeps_its_case(self):
        """Nome de tabela e identificador do catalogo, e o casamento com o
        fact Iceberg e por igualdade: normalizar aqui quebraria a juncao."""
        facts = _extract(_inventory({"table": "glue_catalog.Curated.Pedidos", "service": "athena"}))
        assert _consumers(facts)[0].attrs["table"] == "glue_catalog.Curated.Pedidos"


class TestOptionalFields:
    def test_owner_and_note_are_carried_when_present(self):
        facts = _extract(
            _inventory({"table": "db.t", "service": "athena", "owner": "squad-x", "note": "diario"})
        )
        attrs = _consumers(facts)[0].attrs
        assert attrs["owner"] == "squad-x"
        assert attrs["note"] == "diario"

    def test_absent_optional_fields_are_omitted_not_empty(self):
        facts = _extract(_inventory({"table": "db.t", "service": "athena"}))
        attrs = _consumers(facts)[0].attrs
        assert "owner" not in attrs
        assert "note" not in attrs

    @pytest.mark.parametrize("value", ["", "   ", 3, None])
    def test_blank_or_wrongly_typed_optional_is_dropped(self, value):
        facts = _extract(_inventory({"table": "db.t", "service": "athena", "owner": value}))
        assert "owner" not in _consumers(facts)[0].attrs


class TestDeduplication:
    def test_the_same_pair_declared_twice_yields_one_fact(self):
        facts = _extract(
            _inventory(
                {"table": "db.t", "service": "athena"},
                {"table": "db.t", "service": "athena", "owner": "outro-squad"},
            )
        )
        assert len(_consumers(facts)) == 1

    def test_the_same_table_with_two_services_yields_two_facts(self):
        facts = _extract(
            _inventory(
                {"table": "db.t", "service": "athena"},
                {"table": "db.t", "service": "redshift"},
            )
        )
        assert len(_consumers(facts)) == 2

    def test_case_differences_deduplicate_too(self):
        facts = _extract(
            _inventory(
                {"table": "db.t", "service": "athena"},
                {"table": "db.t", "service": "ATHENA"},
            )
        )
        assert len(_consumers(facts)) == 1


class TestMalformedInventory:
    @pytest.mark.parametrize("payload", [[], "texto", 3])
    def test_payload_that_is_not_a_mapping_is_unresolved(self, payload):
        facts = _extract(payload)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_inventory"

    def test_empty_file_is_not_an_error(self):
        """YAML vazio carrega como `None`. E um inventario legitimo -- vazio,
        nao quebrado."""
        facts = _extract(None)
        assert _unresolved(facts) == []
        assert _sentinel(facts).measures["table_count"] == 0

    def test_consumers_of_the_wrong_type_reports_the_section(self):
        facts = _extract({"consumers": {"db.t": "athena"}})
        assert _unresolved(facts)[0].attrs["section"] == "consumers"

    @pytest.mark.parametrize("table", [None, "", "   ", 3])
    def test_entry_without_a_usable_table_is_unresolved(self, table):
        facts = _extract(_inventory({"table": table, "service": "athena"}))
        assert _unresolved(facts)[0].attrs["reason"] == "missing_table"

    @pytest.mark.parametrize("service", [None, "", "   ", 3])
    def test_entry_without_a_usable_service_keeps_the_table_as_evidence(self, service):
        facts = _extract(_inventory({"table": "db.t", "service": service}))
        unresolved = _unresolved(facts)[0]
        assert unresolved.attrs["reason"] == "missing_service"
        assert unresolved.attrs["table"] == "db.t"

    def test_one_bad_entry_never_discards_the_good_ones(self):
        facts = _extract(_inventory("lixo", {"table": "db.t", "service": "athena"}))
        assert len(_consumers(facts)) == 1
        assert len(_unresolved(facts)) == 1


class TestSentinel:
    def test_counts_tables_consumers_and_unresolved(self):
        facts = _extract(
            _inventory(
                {"table": "db.a", "service": "athena"},
                {"table": "db.a", "service": "redshift"},
                {"table": "db.b", "service": "athena"},
                {"service": "emr"},
            )
        )
        assert _sentinel(facts).measures == {
            "table_count": 2,
            "consumer_count": 3,
            "unresolved_count": 1,
        }

    def test_a_table_with_only_broken_entries_is_not_counted_as_covered(self):
        """`table_count` conta tabela COBERTA, nao tabela mencionada. Uma
        entrada sem `service` nao diz quem consome, entao contar a tabela ali
        faria o inventario parecer mais completo do que e -- e cobertura
        inflada e o unico jeito de este extrator mentir. A menção nao se perde:
        ela vira `env.unresolved` com o nome da tabela em `attrs`."""
        facts = _extract(_inventory({"table": "db.t"}))
        assert _sentinel(facts).measures["table_count"] == 0
        assert _sentinel(facts).measures["consumer_count"] == 0
        assert _unresolved(facts)[0].attrs["table"] == "db.t"


class TestContract:
    def test_no_fact_escapes_the_declared_namespace(self):
        facts = _extract(_inventory({"table": "db.t", "service": "athena"})) + _extract("texto")
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_consumer_is_anchored_to_the_table(self):
        """Ancorar no arquivo faria o achado dizer "o inventario esta errado"
        quando ele e sobre uma tabela especifica."""
        facts = _extract(_inventory({"table": "db.t", "service": "athena"}))
        assert _consumers(facts)[0].subject == {"type": "table", "symbol": "db.t"}

    def test_extraction_is_deterministic(self):
        payload = _inventory(
            {"table": "db.b", "service": "athena"}, {"table": "db.a", "service": "emr"}
        )
        assert [f.to_dict() for f in _extract(payload)] == [f.to_dict() for f in _extract(payload)]


class TestPathEntryPoints:
    def test_reads_yaml_and_anchors_relative_to_the_repo_root(self, tmp_path):
        inventory = tmp_path / ".sparkforge" / "consumers.yaml"
        inventory.parent.mkdir()
        inventory.write_text(
            "consumers:\n  - table: db.t\n    service: athena\n", encoding="utf-8"
        )

        facts = extract_consumers_path(inventory, repo_root=tmp_path)
        assert _consumers(facts)[0].attrs["table"] == "db.t"
        assert _sentinel(facts).provenance["artifact"] == ".sparkforge/consumers.yaml"

    def test_invalid_yaml_becomes_unresolved_with_a_sentinel(self, tmp_path):
        inventory = tmp_path / "consumers.yaml"
        inventory.write_text("consumers: [\n  - table: db.t\n", encoding="utf-8")

        facts = extract_consumers_path(inventory, repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "malformed_inventory"
        assert _sentinel(facts).measures["unresolved_count"] == 1

    def test_unreadable_path_becomes_unresolved(self, tmp_path):
        facts = extract_consumers_path(tmp_path / "nao-existe.yaml", repo_root=tmp_path)
        assert _unresolved(facts)[0].attrs["reason"] == "read_error"

    def test_tree_unions_inventories_split_by_domain(self, tmp_path):
        (tmp_path / "vendas.yaml").write_text(
            "consumers:\n  - table: db.pedidos\n    service: athena\n", encoding="utf-8"
        )
        (tmp_path / "logistica.yml").write_text(
            "consumers:\n  - table: db.entregas\n    service: redshift\n", encoding="utf-8"
        )

        facts = extract_consumers_tree(tmp_path, repo_root=tmp_path)
        assert {f.attrs["table"] for f in _consumers(facts)} == {"db.pedidos", "db.entregas"}
