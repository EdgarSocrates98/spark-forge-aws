"""Grava `upstream.sha256` no frontmatter, sem tocar no resto do arquivo.

Existe porque sha256 calculado a mao por agente erra, e cada erro vira
`upstream_stale` falso. So a linha do hash muda; quebra de linha, ordem de
campos e corpo ficam como estavam (`write_atomic_bytes`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.durable import write_atomic_bytes
from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd.load import CERCA, load_artifact


class StampError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _rel(repo: Path, caminho: Path) -> str:
    return caminho.relative_to(repo.resolve()).as_posix()


def _linha_do_hash(linhas: list[str]) -> int | None:
    dentro = False
    for indice in range(1, len(linhas)):
        crua = linhas[indice].rstrip("\r\n")
        if crua == CERCA:
            return None
        if crua.startswith("upstream:"):
            dentro = True
            continue
        if dentro and crua and not crua[0].isspace():
            dentro = False
        if dentro and crua.lstrip().startswith("sha256:"):
            return indice
    return None


def stamp(repo: Path | str, path: str) -> dict[str, Any]:
    raiz = Path(repo)
    alvo = resolve_within(raiz, path)
    if alvo is None or not alvo.is_file():
        raise StampError("artifact_missing", f"{path} nao existe sob {raiz}")
    artefato = load_artifact(alvo)
    if artefato.error is not None:
        raise StampError("schema_invalid", f"{path}: {artefato.error}")
    upstream = artefato.meta.get("upstream")
    if not isinstance(upstream, dict) or not upstream.get("path"):
        raise StampError("upstream_missing", f"{path} nao declara upstream.path")
    origem = resolve_within(raiz, str(upstream["path"]))
    if origem is None or not origem.is_file():
        raise StampError("upstream_missing", f"{upstream['path']} nao existe sob {raiz}")
    novo = text_sha256(origem)
    anterior = str(upstream.get("sha256") or "")
    linhas = alvo.read_bytes().decode("utf-8").splitlines(keepends=True)
    indice = _linha_do_hash(linhas)
    if indice is None:
        raise StampError(
            "upstream_missing",
            f"{path}: upstream sem a linha sha256 em bloco (escreva `  sha256: \"\"` abaixo de "
            "`upstream:`)",
        )
    if novo != anterior:
        original = linhas[indice]
        sem_quebra = original.rstrip("\r\n")
        quebra = original[len(sem_quebra):]
        recuo = sem_quebra[: len(sem_quebra) - len(sem_quebra.lstrip())]
        linhas[indice] = f'{recuo}sha256: "{novo}"{quebra}'
        write_atomic_bytes(alvo, "".join(linhas).encode("utf-8"))
    return {
        "path": _rel(raiz, alvo),
        "upstream": _rel(raiz, origem),
        "sha256": novo,
        "previous": anterior,
        "changed": novo != anterior,
    }
