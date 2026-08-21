"""Carrega a matriz de runtime do AWS Glue como dado, nao como constante.

Versao de Glue e fato EXTERNO -- muda por decisao da AWS, nao deste
repositorio. Antes desta entrega o valor vivia compilado em
`sparkforge/facts/runtime_detect.py` (GLUE_MATRIX) sem fonte nem data de
consulta; agora mora em `knowledge/glue/runtime-matrix.yaml`, ao lado dos
demais fatos externos vigiados por `knowledge/sources.lock.json`. Cache com
`lru_cache` porque o arquivo nao muda durante a vida do processo e varias
regras consultam a matriz por execucao.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "knowledge" / "glue" / "runtime-matrix.yaml"
SOURCES_LOCK_PATH = ROOT / "knowledge" / "sources.lock.json"


class RuntimeMatrixError(ValueError):
    """Matriz de runtime ausente ou vazia.

    Uma matriz vazia carregaria em silencio e derrubaria toda regra com
    escopo de versao sem aviso -- o mesmo modo de falha que este motor
    recusa em qualquer outro extrator. Melhor estourar aqui do que deixar
    regra sumir por ausencia de dado que parecia presente.
    """


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    """Retorna a matriz de versoes do Glue, indexada pela versao (ex.: "5.1")."""
    with MATRIX_PATH.open("r", encoding="utf-8") as arquivo:
        conteudo = yaml.safe_load(arquivo)

    versoes = (conteudo or {}).get("versions")
    if not versoes:
        raise RuntimeMatrixError(
            f"{MATRIX_PATH}: bloco 'versions' ausente ou vazio -- "
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
    with SOURCES_LOCK_PATH.open("r", encoding="utf-8") as arquivo:
        lock = json.load(arquivo)
    return frozenset(lock.get("sources", {}).keys())


def known_versions() -> list[str]:
    """Versoes de Glue conhecidas pela matriz, em ordem crescente."""
    return sorted(load().keys(), key=lambda v: tuple(int(p) for p in v.split(".")))
