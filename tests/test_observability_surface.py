"""Testes da medicao estatica: quanto pesa a superficie ANTES de qualquer chamada.

Nao executa tool nenhuma. Le o catalogo, os arquivos de skill e os de knowledge,
e conta byte.
"""
from __future__ import annotations

from sparkforge.observability.surface import measure_surface


class TestAMedidaEstatica:
    def test_the_tool_catalogue_is_measured_per_tool(self):
        medida = measure_surface()
        por_tool = medida["tools"]["by_name"]

        assert "sparkforge_analyze_pyspark" in por_tool
        assert por_tool["sparkforge_analyze_pyspark"] > 0

    def test_the_catalogue_total_is_the_sum_of_its_tools(self):
        medida = measure_surface()

        assert medida["tools"]["total_bytes"] == sum(medida["tools"]["by_name"].values())

    def test_every_skill_on_disk_is_measured(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "skills"
        no_disco = {p.name for p in raiz.iterdir() if p.is_dir()}
        medida = measure_surface()

        assert set(medida["skills"]["by_name"]) == no_disco

    def test_knowledge_is_measured_by_document(self):
        medida = measure_surface()

        assert medida["knowledge"]["document_count"] > 0
        assert medida["knowledge"]["total_bytes"] > 0

    def test_nothing_is_executed(self):
        """A medida le disco. Se ela chamasse uma tool, um `path` inexistente
        derrubaria a medicao -- e o teste abaixo prova que ela nao chama."""
        from sparkforge.adapters import tools

        chamadas = []
        original = tools.call_tool
        try:
            tools.call_tool = lambda *a, **k: chamadas.append(a)  # type: ignore[assignment]
            measure_surface()
        finally:
            tools.call_tool = original  # type: ignore[assignment]

        assert chamadas == []


class TestRecusa:
    def test_an_unreadable_document_is_named_not_skipped(self, tmp_path):
        from sparkforge.observability.surface import measure_directory

        (tmp_path / "bom.md").write_text("conteudo", encoding="utf-8")
        (tmp_path / "ruim.md").write_bytes(b"\xff\xfe invalido \x00")

        medida = measure_directory(tmp_path, "*.md")

        assert medida["by_name"]["bom.md"] == len(b"conteudo")
        assert "ruim.md" in medida["unresolved"]

    def test_same_name_in_different_subdirs_does_not_collide(self, tmp_path):
        """`runtime-matrix.md` existe em emr/, emr-serverless/ e glue/ dentro de
        `knowledge/` -- indexar por nome de arquivo faria um pisar no outro e a
        medida ficar menor do que a superficie real."""
        from sparkforge.observability.surface import measure_directory

        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "nota.md").write_text("um", encoding="utf-8")
        (tmp_path / "b" / "nota.md").write_text("dois-bytes", encoding="utf-8")

        medida = measure_directory(tmp_path, "*.md")

        assert medida["document_count"] == 2
        assert medida["total_bytes"] == len(b"um") + len(b"dois-bytes")
        assert set(medida["by_name"]) == {"a/nota.md", "b/nota.md"}
