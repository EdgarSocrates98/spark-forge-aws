"""O coletor le o FOOTER, e nunca o dado.

Este e o unico teste do repositorio que ESCREVE Parquet de verdade e o le de
volta. A escolha e deliberada e vale o custo: um fake de footer provaria que o
extrator consome o shape que o teste inventou, nunca que pyarrow devolve aquele
shape. O par de arquivos ordenado/embaralhado so tem valor se o min/max vier do
formato, e nao de um dicionario escrito a mao.

`pytest.importorskip` guarda o arquivo inteiro: pyarrow e dependencia OPCIONAL
(`sparkforge-aws[parquet]`), e um CI sem ela precisa PULAR este arquivo, nunca
falhar. `tests/test_facts_parquet_footer.py` continua rodando em qualquer
ambiente, porque ele parte do artefato JSON.
"""

from __future__ import annotations

import json

import pytest

pq = pytest.importorskip("pyarrow.parquet")
pa = pytest.importorskip("pyarrow")

from sparkforge.collect.base import CollectorUnavailable, load_manifest  # noqa: E402
from sparkforge.collect.parquet_footer import (  # noqa: E402
    STATUS_OK,
    STATUS_PREFIXO_INEXISTENTE,
    STATUS_PREFIXO_VAZIO,
    STATUS_PYARROW_INDISPONIVEL,
    collect_parquet_footer,
    parquet_footer_path,
    require_pyarrow,
)
from sparkforge.facts.parquet_footer import extract_parquet_footer  # noqa: E402

AGORA = "2026-09-09T12:00:00Z"


def _escreve(destino, ids, *, row_group_size=1000, **kw):
    tabela = pa.table({"id": ids, "cat": [f"c{i % 5}" for i in range(len(ids))]})
    pq.write_table(tabela, destino, row_group_size=row_group_size, **kw)
    return destino


def _artefato(entrada):
    return json.loads(entrada.read_text(encoding="utf-8"))


class TestOFooterEOQueSaiDoArquivo:
    def test_le_row_groups_estatistica_e_dicionario(self, tmp_path):
        dados = tmp_path / "dados"
        dados.mkdir()
        _escreve(dados / "part-00000.parquet", list(range(3000)))

        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        payload = _artefato(tmp_path / parquet_footer_path(str(dados)))

        assert payload["status"] == STATUS_OK
        assert payload["files_read"] == 1
        arquivo = payload["files"][0]
        assert arquivo["num_rows"] == 3000
        assert arquivo["num_row_groups"] == 3
        coluna = arquivo["row_groups"][0]["columns"][0]
        assert coluna["path"] == "id"
        assert coluna["is_stats_set"] is True
        assert coluna["has_min_max"] is True
        assert coluna["has_dictionary_page"] is True
        assert coluna["compression"] == "SNAPPY"

    def test_page_index_exige_os_DOIS_indices(self, tmp_path):
        """Column index sem offset index nao permite page skipping, e o coletor
        grava os dois separados em vez de um booleano que os funde."""
        dados = tmp_path / "dados"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(2000)), write_page_index=True)
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        coluna = _artefato(tmp_path / parquet_footer_path(str(dados)))["files"][0][
            "row_groups"
        ][0]["columns"][0]
        assert coluna["has_column_index"] is True
        assert coluna["has_offset_index"] is True

    def test_sem_page_index_os_dois_saem_falsos(self, tmp_path):
        dados = tmp_path / "dados"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(2000)), write_page_index=False)
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        coluna = _artefato(tmp_path / parquet_footer_path(str(dados)))["files"][0][
            "row_groups"
        ][0]["columns"][0]
        assert coluna["has_column_index"] is False
        assert coluna["has_offset_index"] is False

    def test_estatistica_desligada_na_escrita_chega_como_ausente(self, tmp_path):
        dados = tmp_path / "dados"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(2000)), write_statistics=False)
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        coluna = _artefato(tmp_path / parquet_footer_path(str(dados)))["files"][0][
            "row_groups"
        ][0]["columns"][0]
        assert coluna["is_stats_set"] is False
        assert coluna["min"] is None and coluna["max"] is None


class TestOParQueProvaQueAMedidaEDeOrdenacao:
    """O ponto da frente inteira, exercitado sobre Parquet REAL.

    Os dois arquivos tem o MESMO numero de linhas, o MESMO row_group_size e o
    MESMO conjunto de valores. So a ORDEM muda. Se a medida reagisse a tamanho
    ou a contagem, os dois dariam igual.
    """

    def _cobertura(self, tmp_path, nome, ids):
        dados = tmp_path / nome
        dados.mkdir()
        _escreve(dados / "a.parquet", ids, row_group_size=1000)
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        payload = _artefato(tmp_path / parquet_footer_path(str(dados)))
        facts = extract_parquet_footer(payload, "dump.json")
        perfis = [
            f
            for f in facts
            if f.kind == "parquet.column_profile" and f.attrs["column"] == "id"
        ]
        assert perfis, "a coluna `id` precisa render perfil"
        return perfis[0]

    def test_ordenado_contra_embaralhado(self, tmp_path):
        n = 3000
        ordenado = self._cobertura(tmp_path, "ord", list(range(n)))
        # Espalhado: cada row group recebe uma amostra que atravessa TODO o
        # dominio, entao min e max de cada um sao quase os globais. Nao e
        # aleatorio de proposito -- aleatorio faria o teste depender de semente,
        # e uma semente ruim o faria piscar.
        espalhado = self._cobertura(
            tmp_path, "esp", [(i % 1000) * 3 + (i // 1000) for i in range(n)]
        )

        assert ordenado.measures["num_row_groups"] == espalhado.measures["num_row_groups"]
        assert ordenado.measures["avg_range_coverage"] < 0.4
        assert espalhado.measures["avg_range_coverage"] > 0.9
        assert (
            ordenado.measures["expected_row_groups_scanned"]
            < espalhado.measures["expected_row_groups_scanned"]
        )

    def test_a_coluna_string_recusa_com_nome(self, tmp_path):
        """`cat` e BYTE_ARRAY: min/max ordenam e nao MEDEM distancia."""
        dados = tmp_path / "s"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(3000)))
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        facts = extract_parquet_footer(
            _artefato(tmp_path / parquet_footer_path(str(dados))), "dump.json"
        )
        recusas = [
            f
            for f in facts
            if f.kind == "parquet.unresolved" and f.attrs.get("column") == "cat"
        ]
        assert recusas and recusas[0].attrs["reason"] == "tipo_sem_dominio_numerico"


class TestAmostragemDeclarada:
    def test_max_files_corta_e_o_artefato_declara_o_corte(self, tmp_path):
        dados = tmp_path / "muitos"
        dados.mkdir()
        for i in range(5):
            _escreve(dados / f"part-{i:05d}.parquet", list(range(100)), row_group_size=50)

        collect_parquet_footer(str(dados), tmp_path, now=AGORA, max_files=2)
        payload = _artefato(tmp_path / parquet_footer_path(str(dados)))
        assert payload["files_seen"] == 5
        assert payload["files_read"] == 2
        assert payload["sampling"] == "first_n_by_name"

        censo = [
            f
            for f in extract_parquet_footer(payload, "dump.json")
            if f.kind == "parquet.footer_analyzed"
        ][0]
        assert censo.attrs["partial"] is True

    def test_a_amostra_e_reproduzivel_pelo_NOME(self, tmp_path):
        """Duas coletas do mesmo prefixo precisam ler os MESMOS arquivos, ou
        dois `facts.json` do mesmo lugar deixam de ser comparaveis."""
        dados = tmp_path / "estavel"
        dados.mkdir()
        for i in range(4):
            _escreve(dados / f"part-{i:05d}.parquet", list(range(100)), row_group_size=50)

        collect_parquet_footer(str(dados), tmp_path, now=AGORA, max_files=2)
        primeiro = [
            f["path"] for f in _artefato(tmp_path / parquet_footer_path(str(dados)))["files"]
        ]
        (tmp_path / parquet_footer_path(str(dados))).unlink()
        collect_parquet_footer(str(dados), tmp_path, now=AGORA, max_files=2)
        segundo = [
            f["path"] for f in _artefato(tmp_path / parquet_footer_path(str(dados)))["files"]
        ]
        assert primeiro == segundo
        assert all("part-00000" in p or "part-00001" in p for p in primeiro)

    def test_teto_duro_recusa_antes_de_ler(self, tmp_path):
        with pytest.raises(ValueError, match="teto"):
            collect_parquet_footer(str(tmp_path), tmp_path, now=AGORA, max_files=10_000)

    def test_max_files_zero_e_recusado(self, tmp_path):
        with pytest.raises(ValueError, match=">= 1"):
            collect_parquet_footer(str(tmp_path), tmp_path, now=AGORA, max_files=0)


class TestRecusaNomeada:
    def test_prefixo_inexistente(self, tmp_path):
        collect_parquet_footer(str(tmp_path / "nao_existe"), tmp_path, now=AGORA)
        payload = _artefato(tmp_path / parquet_footer_path(str(tmp_path / "nao_existe")))
        assert payload["status"] == STATUS_PREFIXO_INEXISTENTE
        assert payload["files"] == []

    def test_prefixo_vazio_nao_e_prefixo_inexistente(self, tmp_path):
        """Os dois produzem a MESMA lista vazia, e so a razao os separa."""
        vazio = tmp_path / "vazio"
        vazio.mkdir()
        collect_parquet_footer(str(vazio), tmp_path, now=AGORA)
        assert _artefato(tmp_path / parquet_footer_path(str(vazio)))["status"] == (
            STATUS_PREFIXO_VAZIO
        )

    def test_pyarrow_ausente_vira_status_e_nao_excecao(self, tmp_path, monkeypatch):
        """Sem a dependencia opcional, a coleta grava a RAZAO -- excecao mataria
        o artefato, e sem artefato a recusa vira silencio."""
        import sparkforge.collect.parquet_footer as modulo

        def sem_pyarrow():
            raise CollectorUnavailable("pyarrow nao disponivel")

        monkeypatch.setattr(modulo, "require_pyarrow", sem_pyarrow)
        collect_parquet_footer(str(tmp_path), tmp_path, now=AGORA)
        assert _artefato(tmp_path / parquet_footer_path(str(tmp_path)))["status"] == (
            STATUS_PYARROW_INDISPONIVEL
        )

    def test_as_razoes_sao_distinguiveis_entre_si(self, tmp_path):
        vazio = tmp_path / "v"
        vazio.mkdir()
        collect_parquet_footer(str(vazio), tmp_path, now=AGORA)
        collect_parquet_footer(str(tmp_path / "x"), tmp_path, now=AGORA)
        razoes = {
            _artefato(tmp_path / parquet_footer_path(str(p)))["status"]
            for p in (vazio, tmp_path / "x")
        }
        assert len(razoes) == 2


class TestManifestoEOffline:
    def test_registra_no_manifesto(self, tmp_path):
        dados = tmp_path / "d"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(100)), row_group_size=50)
        entrada = collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        assert entrada.kind == "parquet_footer"
        assert entrada.collect_command.startswith("sparkforge collect parquet-footer")
        registrados = {e["path"] for e in load_manifest(tmp_path)}
        assert parquet_footer_path(str(dados)) in registrados

    def test_segunda_coleta_e_no_op_offline(self, tmp_path, monkeypatch):
        """Artefato presente e integro nao toca pyarrow -- mesma politica
        offline-first do resto de `sparkforge/collect/`."""
        dados = tmp_path / "d"
        dados.mkdir()
        _escreve(dados / "a.parquet", list(range(100)), row_group_size=50)
        collect_parquet_footer(str(dados), tmp_path, now=AGORA)

        import sparkforge.collect.parquet_footer as modulo

        def explode():
            raise AssertionError("offline hit nao deveria importar pyarrow")

        monkeypatch.setattr(modulo, "require_pyarrow", explode)
        entrada = collect_parquet_footer(str(dados), tmp_path, now=AGORA)
        assert entrada.kind == "parquet_footer"


def test_require_pyarrow_devolve_o_modulo():
    assert require_pyarrow() is not None
