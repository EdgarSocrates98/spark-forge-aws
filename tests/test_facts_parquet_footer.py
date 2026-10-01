"""O footer do Parquet vira fact, e a sobreposicao de min/max vira numero.

`knowledge/storage/parquet-layout.md` §2 ja afirma que estatistica min/max so
serve se os valores estiverem AGRUPADOS -- dado espalhado faz cada row group
cobrir quase todo o dominio, e nenhum pode ser descartado. Este modulo e onde
essa frase vira medida.

## O par que sustenta peso

`TestSobreposicaoDeMinMax` tem duas fixtures com o MESMO numero de row groups,
o MESMO numero de linhas e o MESMO tamanho: uma ordenada, outra embaralhada. Se
a medida reagisse a tamanho ou a contagem, as duas dariam igual. Elas dao
`1/3` contra `~1`, e e isso que prova que ela mede ORDENACAO.
"""

from __future__ import annotations

import pytest

from sparkforge.facts.parquet_footer import EMITTED_KINDS, extract_parquet_footer


def _coluna(nome, tipo="INT64", **kw):
    base = {
        "path": nome,
        "physical_type": tipo,
        "compression": "SNAPPY",
        "encodings": ["PLAIN", "RLE_DICTIONARY"],
        "has_dictionary_page": True,
        "is_stats_set": True,
        "has_min_max": True,
        "min": 0,
        "max": 100,
        "null_count": 0,
        "num_values": 1000,
        "total_compressed_size": 4000,
        "total_uncompressed_size": 12000,
        "has_column_index": False,
        "has_offset_index": False,
        "bloom_filter_offset": None,
    }
    base.update(kw)
    return base


def _artefato(row_groups, *, prefix="s3://lake/curated/pedidos/", **kw):
    arquivo = {
        "path": "part-00000.parquet",
        "file_bytes": 268435456,
        "num_rows": sum(rg["num_rows"] for rg in row_groups),
        "num_row_groups": len(row_groups),
        "num_columns": len(row_groups[0]["columns"]) if row_groups else 0,
        "created_by": "parquet-mr version 1.13.1",
        "format_version": "2.6",
        "row_groups": row_groups,
    }
    base = {
        "prefix": prefix,
        "files_seen": 1,
        "files_read": 1,
        "sampling": "first_n",
        "max_files": 20,
        "status": "ok",
        "files": [arquivo],
    }
    base.update(kw)
    return base


def _rg(indice, faixas, *, num_rows=1000, total_byte_size=134217728, **kwcol):
    """Um row group com uma coluna por faixa `(nome, min, max)`."""
    return {
        "index": indice,
        "num_rows": num_rows,
        "total_byte_size": total_byte_size,
        "columns": [
            _coluna(nome, min=mn, max=mx, num_values=num_rows, **kwcol)
            for nome, mn, mx in faixas
        ],
    }


def _por_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


class TestCensoDoFooter:
    def test_o_arquivo_vira_fact(self):
        facts = extract_parquet_footer(_artefato([_rg(0, [("id", 0, 999)])]), "dump.json")
        arquivo = _por_kind(facts, "parquet.file")
        assert len(arquivo) == 1
        assert arquivo[0].measures["num_row_groups"] == 1
        assert arquivo[0].attrs["created_by"] == "parquet-mr version 1.13.1"
        assert arquivo[0].attrs["format_version"] == "2.6"

    def test_cada_row_group_vira_fact(self):
        facts = extract_parquet_footer(
            _artefato([_rg(i, [("id", i * 100, i * 100 + 99)]) for i in range(3)]),
            "dump.json",
        )
        grupos = _por_kind(facts, "parquet.row_group")
        assert len(grupos) == 3
        assert grupos[0].measures["total_byte_size"] == 134217728

    def test_a_amostragem_sai_declarada_no_censo(self):
        """`files_read < files_seen` precisa CHEGAR ao fact: um censo parcial que
        nao se anuncia como parcial e pior que censo nenhum."""
        facts = extract_parquet_footer(
            _artefato([_rg(0, [("id", 0, 99)])], files_seen=1240, files_read=1),
            "dump.json",
        )
        censo = _por_kind(facts, "parquet.footer_analyzed")[0]
        assert censo.measures["files_seen"] == 1240
        assert censo.measures["files_read"] == 1
        assert censo.attrs["sampling"] == "first_n"
        assert censo.attrs["partial"] is True

    def test_censo_completo_nao_se_declara_parcial(self):
        facts = extract_parquet_footer(
            _artefato([_rg(0, [("id", 0, 99)])], files_seen=1, files_read=1), "dump.json"
        )
        assert _por_kind(facts, "parquet.footer_analyzed")[0].attrs["partial"] is False

    def test_nenhum_column_chunk_e_emitido(self):
        """A ausencia e DECISAO: 100 row groups x 50 colunas seriam 5000 facts
        que nao decidem nada sozinhos, e `facts.json` e committado."""
        facts = extract_parquet_footer(
            _artefato([_rg(i, [("id", 0, 9)]) for i in range(4)]), "dump.json"
        )
        assert not [f for f in facts if f.kind == "parquet.column_chunk"]
        assert "parquet.column_chunk" not in EMITTED_KINDS


class TestPerfilPorColuna:
    def test_cobertura_de_estatistica_e_fracao_dos_row_groups(self):
        rgs = [_rg(0, [("id", 0, 9)]), _rg(1, [("id", 10, 19)], is_stats_set=False)]
        perfil = _por_kind(
            extract_parquet_footer(_artefato(rgs), "dump.json"), "parquet.column_profile"
        )[0]
        assert perfil.measures["stats_coverage"] == 0.5

    def test_cobertura_de_dicionario_page_index_e_bloom(self):
        rgs = [
            _rg(0, [("id", 0, 9)], has_column_index=True, has_offset_index=True),
            _rg(1, [("id", 10, 19)], has_dictionary_page=False, bloom_filter_offset=4),
        ]
        perfil = _por_kind(
            extract_parquet_footer(_artefato(rgs), "dump.json"), "parquet.column_profile"
        )[0]
        assert perfil.measures["dictionary_coverage"] == 0.5
        assert perfil.measures["page_index_coverage"] == 0.5
        assert perfil.measures["bloom_coverage"] == 0.5

    def test_razao_de_compressao_e_descomprimido_sobre_comprimido(self):
        perfil = _por_kind(
            extract_parquet_footer(_artefato([_rg(0, [("id", 0, 9)])]), "dump.json"),
            "parquet.column_profile",
        )[0]
        assert perfil.measures["compression_ratio"] == pytest.approx(3.0)

    def test_codec_divergente_entre_row_groups_sai_na_lista(self):
        """Mais de um codec na mesma coluna e sinal proprio, e por isso `codecs`
        e lista e nao string."""
        rgs = [_rg(0, [("id", 0, 9)]), _rg(1, [("id", 10, 19)], compression="GZIP")]
        perfil = _por_kind(
            extract_parquet_footer(_artefato(rgs), "dump.json"), "parquet.column_profile"
        )[0]
        assert perfil.attrs["codecs"] == ["GZIP", "SNAPPY"]


class TestSobreposicaoDeMinMax:
    """O §2 do `knowledge/storage/parquet-layout.md` virando numero."""

    def test_dado_ordenado_da_cobertura_de_um_sobre_n(self):
        rgs = [_rg(i, [("id", i * 100, i * 100 + 99)]) for i in range(3)]
        perfil = _por_kind(
            extract_parquet_footer(_artefato(rgs), "dump.json"), "parquet.column_profile"
        )[0]
        # dominio 0..299; cada rg cobre 99/299
        assert perfil.measures["avg_range_coverage"] == pytest.approx(99 / 299, rel=1e-6)
        assert perfil.measures["expected_row_groups_scanned"] == pytest.approx(
            3 * 99 / 299, rel=1e-6
        )

    def test_dado_espalhado_da_cobertura_perto_de_um(self):
        """MESMO numero de row groups, MESMO tamanho, MESMA contagem de linhas --
        so a distribuicao muda. Se a medida reagisse a tamanho, as duas dariam
        igual."""
        rgs = [_rg(i, [("id", 0, 299)]) for i in range(3)]
        perfil = _por_kind(
            extract_parquet_footer(_artefato(rgs), "dump.json"), "parquet.column_profile"
        )[0]
        assert perfil.measures["avg_range_coverage"] == pytest.approx(1.0)
        assert perfil.measures["expected_row_groups_scanned"] == pytest.approx(3.0)

    def test_o_par_prova_que_a_medida_e_de_ORDENACAO(self):
        ordenado = _por_kind(
            extract_parquet_footer(
                _artefato([_rg(i, [("id", i * 100, i * 100 + 99)]) for i in range(3)]),
                "dump.json",
            ),
            "parquet.column_profile",
        )[0]
        espalhado = _por_kind(
            extract_parquet_footer(
                _artefato([_rg(i, [("id", 0, 299)]) for i in range(3)]), "dump.json"
            ),
            "parquet.column_profile",
        )[0]
        assert ordenado.measures["num_row_groups"] == espalhado.measures["num_row_groups"]
        assert ordenado.measures["total_byte_size"] == espalhado.measures["total_byte_size"]
        assert ordenado.measures["avg_range_coverage"] < espalhado.measures[
            "avg_range_coverage"
        ]


class TestRecusaNomeada:
    def test_tipo_sem_dominio_numerico(self):
        """Min/max lexicografico de string produziria um numero com cara de
        medida e sem significado de distancia."""
        rgs = [
            _rg(i, [("nome", "a", "z")], tipo="BYTE_ARRAY") for i in range(3)
        ]
        facts = extract_parquet_footer(_artefato(rgs), "dump.json")
        recusa = _por_kind(facts, "parquet.unresolved")
        assert recusa and recusa[0].attrs["reason"] == "tipo_sem_dominio_numerico"
        perfil = _por_kind(facts, "parquet.column_profile")[0]
        assert "avg_range_coverage" not in perfil.measures

    def test_estatistica_incompleta(self):
        rgs = [_rg(0, [("id", 0, 9)]), _rg(1, [("id", 10, 19)], has_min_max=False)]
        facts = extract_parquet_footer(_artefato(rgs), "dump.json")
        recusa = _por_kind(facts, "parquet.unresolved")
        assert recusa and recusa[0].attrs["reason"] == "estatistica_incompleta"

    def test_row_group_unico(self):
        """Com um row group so nao ha o que descartar, e a razao precisa ser
        distinguivel de dado espalhado -- as duas dariam cobertura 1.0."""
        facts = extract_parquet_footer(_artefato([_rg(0, [("id", 0, 99)])]), "dump.json")
        recusa = _por_kind(facts, "parquet.unresolved")
        assert recusa and recusa[0].attrs["reason"] == "row_group_unico"

    def test_dominio_degenerado(self):
        rgs = [_rg(i, [("const", 7, 7)]) for i in range(3)]
        facts = extract_parquet_footer(_artefato(rgs), "dump.json")
        recusa = _por_kind(facts, "parquet.unresolved")
        assert recusa and recusa[0].attrs["reason"] == "dominio_degenerado"

    def test_as_quatro_recusas_sao_distinguiveis_entre_si(self):
        """As quatro produzem a MESMA ausencia de `avg_range_coverage`, e duas
        colapsadas na mesma razao seriam uma recusa que nao nomeia nada."""
        casos = {
            "tipo_sem_dominio_numerico": [
                _rg(i, [("nome", "a", "z")], tipo="BYTE_ARRAY") for i in range(3)
            ],
            "estatistica_incompleta": [
                _rg(0, [("id", 0, 9)]),
                _rg(1, [("id", 10, 19)], has_min_max=False),
            ],
            "row_group_unico": [_rg(0, [("id", 0, 99)])],
            "dominio_degenerado": [_rg(i, [("id", 7, 7)]) for i in range(3)],
        }
        vistas = set()
        for esperada, rgs in casos.items():
            facts = extract_parquet_footer(_artefato(rgs), "dump.json")
            razoes = {f.attrs["reason"] for f in _por_kind(facts, "parquet.unresolved")}
            assert esperada in razoes, esperada
            vistas |= razoes
        assert len(vistas) == 4

    def test_status_de_recusa_do_coletor_chega_ao_fact(self):
        """Prefixo vazio, sem permissao ou sem pyarrow produzem a MESMA lista
        vazia de arquivos, e so a razao os separa."""
        facts = extract_parquet_footer(
            {
                "prefix": "s3://lake/vazio/",
                "files_seen": 0,
                "files_read": 0,
                "sampling": "first_n",
                "max_files": 20,
                "status": "prefixo_vazio",
                "files": [],
            },
            "dump.json",
        )
        recusa = _por_kind(facts, "parquet.unresolved")
        assert recusa and recusa[0].attrs["reason"] == "prefixo_vazio"
        assert not _por_kind(facts, "parquet.file")

    def test_artefato_sem_arquivo_nao_inventa_censo_positivo(self):
        facts = extract_parquet_footer(
            {"prefix": "s3://x/", "status": "sem_permissao", "files": []}, "dump.json"
        )
        censo = _por_kind(facts, "parquet.footer_analyzed")[0]
        assert censo.measures["files_read"] == 0
