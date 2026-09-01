"""SparkForge Migration Package.

O pacote exporta o motor de regras -- `version_path` expande o par de versoes em
degraus, `collect` compoe os artefatos do job num unico `list[Fact]` e
`assessment` julga cada degrau com o catalogo versionado. Ele nao
exporta mais `GlueMigrationAnalyzer`: aquele analisador casava substring de
codigo contra uma lista fixa de pares 4.0->5.1, sem fonte, sem `runtime_scope` e
sem degrau intermediario, e por isso nao conseguia dizer QUANDO um breaking
change entrou nem se ele ainda vale depois do proximo salto.

O par `release_descriptor`/`release_diff` mora aqui, e nao em
`sparkforge/facts/`, porque nao extrai de artefato nenhum: compoe sobre o dado
que `sparkforge.facts.runtime_matrix` ja carregou de `knowledge/`, respondendo a
pergunta de migracao -- a mesma que `version_path` ja responde para o Glue, e a
que o `MigrationAssessment` de EMR vai consumir.
"""
from __future__ import annotations

from sparkforge.migration import (
    assessment,
    collect,
    release_descriptor,
    release_diff,
    version_path,
)

__all__ = [
    "assessment",
    "collect",
    "release_descriptor",
    "release_diff",
    "version_path",
]
