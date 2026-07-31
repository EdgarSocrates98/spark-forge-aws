# tests/test_knowledge_ref.py
"""Resolucao da raiz de knowledge, com a mesma disciplina do catalogo.

`knowledge_dir()` espelha `catalog_dir()` de proposito: mesma ordem de
precedencia, mesma recusa de caminho que escapa. Duas resolucoes com regras
diferentes no mesmo pacote seria a origem do proximo bug de path.
"""
from pathlib import Path

import pytest

from sparkforge.knowledge_ref import KnowledgeError, knowledge_dir, safe_knowledge_file

ROOT = Path(__file__).resolve().parents[1]


class TestResolution:
    def test_finds_the_repo_root_knowledge(self):
        assert knowledge_dir() == ROOT / "knowledge"

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(tmp_path))
        assert knowledge_dir() == tmp_path.resolve()

    def test_env_var_pointing_at_a_file_is_rejected(self, tmp_path, monkeypatch):
        target = tmp_path / "nao-e-diretorio.md"
        target.write_text("x", encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(target))
        with pytest.raises(KnowledgeError, match="diretorio"):
            knowledge_dir()

    def test_env_var_pointing_nowhere_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(tmp_path / "ausente"))
        with pytest.raises(KnowledgeError, match="diretorio"):
            knowledge_dir()


class TestContainment:
    """`base` vem de variavel de ambiente e `name` pode vir de uma citacao no
    catalogo, que e dado editavel. Mesma superficie que obriga o avaliador de
    `expr` a ter whitelist."""

    def test_resolves_a_file_inside_the_root(self):
        target = safe_knowledge_file(ROOT / "knowledge", "glue/runtime-matrix.md")
        assert target.is_file()

    def test_rejects_parent_traversal(self):
        with pytest.raises(KnowledgeError, match="fora do diretorio"):
            safe_knowledge_file(ROOT / "knowledge", "../pyproject.toml")

    def test_rejects_absolute_path(self):
        with pytest.raises(KnowledgeError, match="fora do diretorio"):
            safe_knowledge_file(ROOT / "knowledge", str(ROOT / "pyproject.toml"))

    def test_missing_file_is_an_actionable_error(self):
        """Erro generico obriga o operador a adivinhar. A secao 7.3 da Fase 0
        exige causa, o que falta e o que resolve."""
        with pytest.raises(KnowledgeError, match="nao existe"):
            safe_knowledge_file(ROOT / "knowledge", "glue/arquivo-que-nao-existe.md")
