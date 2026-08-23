"""SparkForge Migration Package.

O pacote exporta o motor de regras -- `version_path` expande o par de versoes em
degraus, `collect` compoe os artefatos do job num unico `list[Fact]` e
`assessment` julga cada degrau com o catalogo versionado. Ele nao
exporta mais `GlueMigrationAnalyzer`: aquele analisador casava substring de
codigo contra uma lista fixa de pares 4.0->5.1, sem fonte, sem `runtime_scope` e
sem degrau intermediario, e por isso nao conseguia dizer QUANDO um breaking
change entrou nem se ele ainda vale depois do proximo salto.
"""
from __future__ import annotations

from sparkforge.migration import assessment, collect, version_path

__all__ = [
    "assessment",
    "collect",
    "version_path",
]
