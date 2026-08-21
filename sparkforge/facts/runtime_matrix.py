"""Carrega a matriz de runtime do AWS Glue como dado, nao como constante.

Versao de Glue e fato EXTERNO -- muda por decisao da AWS, nao deste
repositorio. Antes desta entrega o valor vivia compilado em
`sparkforge/facts/runtime_detect.py` (GLUE_MATRIX) sem fonte nem data de
consulta; agora mora em `knowledge/glue/runtime-matrix.yaml`, ao lado dos
demais fatos externos vigiados por `knowledge/sources.lock.json`. Cache com
`lru_cache` porque o arquivo nao muda durante a vida do processo e varias
regras consultam a matriz por execucao.

RESOLUCAO DE CAMINHO: por que este modulo usa `sparkforge.knowledge_ref`, e
nao a sua propria conta de `parents[N]`.

A primeira versao deste arquivo (Fase SF-MIG, Task 1) computava
`ROOT = Path(__file__).resolve().parents[2]` e lia
`ROOT / "knowledge" / "glue" / "runtime-matrix.yaml"`. Isso funciona no
checkout de desenvolvimento -- `sparkforge/facts/runtime_matrix.py` fica dois
niveis abaixo da raiz do repositorio, onde `knowledge/` mora de verdade. Mas
`pyproject.toml` empacota `knowledge/` DENTRO do pacote instalado
(`[tool.hatch.build.targets.wheel.force-include]`: `"knowledge" =
"sparkforge/knowledge"`), entao no wheel instalado o arquivo esta em
`<site-packages>/sparkforge/knowledge/glue/runtime-matrix.yaml` -- um nivel
a mais de profundidade do que a conta original alcancava. `parents[2]` a
partir de `<site-packages>/sparkforge/facts/runtime_matrix.py` cai em
`<site-packages>`, nao em `<site-packages>/sparkforge`, e a leitura procurava
`knowledge/` no lugar errado.

Isso ficou latente na Task 1: nada chamava `load()` na importacao do modulo,
entao o bug so apareceria se algum consumidor chamasse a funcao rodando de
um pacote instalado. A Task 2 (`runtime_detect.py`) passou a montar
`GLUE_MATRIX` no NIVEL DE MODULO, chamando `load()` na propria importacao --
e isso transformou um bug latente em `import sparkforge.facts.runtime_detect`
quebrando incondicionalmente num wheel instalado. Reproduzido e confirmado:
build do wheel, instalacao num venv limpo, `import
sparkforge.facts.runtime_detect` -> `FileNotFoundError` em
`<site-packages>/knowledge/glue/runtime-matrix.yaml`.

`sparkforge/knowledge_ref.py` ja resolve exatamente este problema, para
exatamente este diretorio, desde a Fase 3a -- "knowledge/ passou a ser
embarcado no artefato e nenhum codigo sabia encontra-lo". A ordem de
precedencia (env var `SPARKFORGE_KNOWLEDGE` -> raiz do repo -> `parent` do
proprio modulo dentro do pacote) e a MESMA que `sparkforge/rules/loader.py`
usa para `rules/catalog`, e tem teste dedicado para o caso de pacote
instalado (`tests/test_knowledge_ref.py::
test_falls_back_to_the_package_dir_when_no_repo_root_exists`). Reimplementar
essa resolucao aqui -- como a Task 1 fez -- e reproduzir o bug que o modulo
já existe para fechar. Este modulo usa `knowledge_dir()`/`safe_knowledge_file()`
em vez disso.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file


class RuntimeMatrixError(ValueError):
    """Matriz de runtime ausente ou vazia.

    Uma matriz vazia carregaria em silencio e derrubaria toda regra com
    escopo de versao sem aviso -- o mesmo modo de falha que este motor
    recusa em qualquer outro extrator. Melhor estourar aqui do que deixar
    regra sumir por ausencia de dado que parecia presente.
    """


def _matrix_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), "glue/runtime-matrix.yaml")


def _sources_lock_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), "sources.lock.json")


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    """Retorna a matriz de versoes do Glue, indexada pela versao (ex.: "5.1")."""
    matrix_path = _matrix_path()
    with matrix_path.open("r", encoding="utf-8") as arquivo:
        conteudo = yaml.safe_load(arquivo)

    versoes = (conteudo or {}).get("versions")
    if not versoes:
        raise RuntimeMatrixError(
            f"{matrix_path}: bloco 'versions' ausente ou vazio -- "
            "toda regra com escopo de versao ficaria muda em silencio"
        )
    return versoes


@lru_cache(maxsize=1)
def watched_sources() -> frozenset[str]:
    """Retorna as URLs vigiadas em `knowledge/sources.lock.json`.

    Usado para validar que toda fonte citada na matriz e uma fonte que o
    mecanismo de procedencia do repositorio efetivamente rastreia -- uma
    URL solta na matriz, sem entrada no lock, nao teria hash nem data
    revalidados por `scripts/refresh_knowledge.py`.
    """
    with _sources_lock_path().open("r", encoding="utf-8") as arquivo:
        lock = json.load(arquivo)
    return frozenset(lock.get("sources", {}).keys())


def known_versions() -> list[str]:
    """Versoes de Glue conhecidas pela matriz, em ordem crescente."""
    return sorted(load().keys(), key=lambda v: tuple(int(p) for p in v.split(".")))
