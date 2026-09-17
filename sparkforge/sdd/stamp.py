"""Grava `upstream.sha256` no frontmatter, sem tocar no resto do arquivo.

Existe porque sha256 calculado a mao por agente erra, e cada erro vira
`upstream_stale` falso. So a linha do hash muda; quebra de linha, BOM, ordem de
campos, comentarios e corpo ficam como estavam (`write_atomic_bytes`).

O `stamp` so escreve em artefato (`<root>/<FEATURE>/<fase>.md`) e so reescreve
a linha do hash quando ela e um escalar simples numa linha so. Qualquer outra
forma e recusada por nome em vez de virar YAML invalido.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.durable import write_atomic_bytes
from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import CERCA, FEATURE_RE, load_artifact

_CHAVE_BLOCO = "upstream:"
_CHAVE_HASH = "sha256:"
# indicadores que abrem algo que nao e escalar simples: bloco literal/dobrado,
# fluxo, ancora, alias, tag, diretiva e reservados
_INDICADORES = set("|>[]{}&*!%@`")


class StampError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _rel(repo: Path, caminho: Path) -> str:
    return caminho.relative_to(repo.resolve()).as_posix()


def _recuo(crua: str) -> int:
    return len(crua) - len(crua.lstrip())


def _e_comentario(crua: str) -> bool:
    return crua.lstrip().startswith("#")


def _linha_do_hash(path: str, linhas: list[str]) -> int | None:
    dentro = False
    for indice in range(1, len(linhas)):
        crua = linhas[indice].rstrip("\r\n")
        if crua == CERCA:
            return None
        if crua.startswith(_CHAVE_BLOCO):
            resto = crua[len(_CHAVE_BLOCO):].strip()
            if resto.startswith("{"):
                raise StampError(
                    "upstream_flow_style",
                    f"{path}: upstream em estilo fluxo ({{...}}); escreva em bloco, com "
                    "`path:` e `sha256:` em linhas proprias abaixo de `upstream:`",
                )
            dentro = True
            continue
        # comentario, mesmo na coluna zero, nao fecha o bloco
        if dentro and crua and not crua[0].isspace() and not _e_comentario(crua):
            dentro = False
        if dentro and crua.lstrip().startswith(_CHAVE_HASH):
            return indice
    return None


def _continua(linhas: list[str], indice: int, recuo: int) -> bool:
    """O valor segue na linha de baixo: proxima linha util mais recuada que a chave."""
    for seguinte in linhas[indice + 1:]:
        crua = seguinte.rstrip("\r\n")
        if crua == CERCA:
            return False
        if not crua.strip() or _e_comentario(crua):
            continue
        return _recuo(crua) > recuo
    return False


def _fim_entre_aspas(resto: str) -> int | None:
    """Indice logo depois da aspa que fecha `resto`, ou `None` se nao fecha na linha."""
    aspa = resto[0]
    posicao = 1
    while posicao < len(resto):
        caractere = resto[posicao]
        if aspa == '"' and caractere == "\\":
            posicao += 2
            continue
        if caractere == aspa:
            if aspa == "'" and resto[posicao + 1:posicao + 2] == "'":
                posicao += 2
                continue
            return posicao + 1
        posicao += 1
    return None


def _sufixo(path: str, linhas: list[str], indice: int) -> str:
    """O comentario do fim da linha do hash (com o espaco antes), a preservar.

    Recusa `sha_line_unsupported` quando o valor nao e um escalar simples inteiro
    nesta linha: reescrever ali geraria YAML invalido ou mudaria outra coisa.
    """
    crua = linhas[indice].rstrip("\r\n")
    recuo = _recuo(crua)
    depois = crua.lstrip()[len(_CHAVE_HASH):]
    resto = depois.lstrip()
    recusa = StampError(
        "sha_line_unsupported",
        f"{path}: a linha {indice + 1} nao tem o sha256 como escalar simples numa linha so; "
        'escreva `sha256: ""` e rode o stamp de novo',
    )
    if depois and not depois[0].isspace():
        raise recusa  # `sha256:x` e outra chave para o YAML, nao o hash
    if not resto or resto.startswith("#"):
        if _continua(linhas, indice, recuo):
            raise recusa
        # o primeiro espaco separa a chave do valor, e o valor novo o repoe
        return depois[1:] if resto else ""
    if resto[0] in "\"'":
        fim = _fim_entre_aspas(resto)
        if fim is None:
            raise recusa
        cauda = resto[fim:]
        if cauda.strip() and not cauda.lstrip().startswith("#"):
            raise recusa
        if cauda.strip() and not cauda[0].isspace():
            raise recusa
    else:
        if resto[0] in _INDICADORES:
            raise recusa
        marca = resto.find(" #")
        valor = resto[:marca].rstrip() if marca >= 0 else resto
        cauda = resto[len(valor):]
        if _continua(linhas, indice, recuo):
            raise recusa
    return cauda if cauda.strip() else ""


def _confere_artefato(raiz: Path, alvo: Path, path: str, root: str) -> None:
    base = resolve_within(raiz, root)
    partes: tuple[str, ...] = ()
    if base is not None:
        try:
            partes = alvo.relative_to(base).parts
        except ValueError:
            partes = ()
    if (
        len(partes) != 2
        or not FEATURE_RE.fullmatch(partes[0])
        or not partes[1].endswith(".md")
        or partes[1][: -len(".md")] not in PHASES
    ):
        raise StampError(
            "not_an_artifact",
            f"{path} nao e artefato SDD; o stamp so escreve em "
            f"{root}/<FEATURE>/<fase>.md (fases: {', '.join(PHASES)})",
        )


def stamp(repo: Path | str, path: str, root: str = DEFAULT_ROOT) -> dict[str, Any]:
    raiz = Path(repo)
    alvo = resolve_within(raiz, path)
    if alvo is None or not alvo.is_file():
        raise StampError("artifact_missing", f"{path} nao existe sob {raiz}")
    _confere_artefato(raiz, alvo, path, root)
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
    # o texto decodificado guarda o BOM como `﻿`; reencodar devolve o mesmo byte
    linhas = alvo.read_bytes().decode("utf-8").splitlines(keepends=True)
    indice = _linha_do_hash(path, linhas)
    if indice is None:
        raise StampError(
            "upstream_missing",
            f"{path}: upstream sem a linha sha256 em bloco (escreva `  sha256: \"\"` abaixo de "
            "`upstream:`)",
        )
    sufixo = _sufixo(path, linhas, indice)
    if novo != anterior:
        original = linhas[indice]
        sem_quebra = original.rstrip("\r\n")
        quebra = original[len(sem_quebra):]
        recuo = sem_quebra[: _recuo(sem_quebra)]
        linhas[indice] = f'{recuo}sha256: "{novo}"{sufixo}{quebra}'
        write_atomic_bytes(alvo, "".join(linhas).encode("utf-8"))
    return {
        "path": _rel(raiz, alvo),
        "upstream": _rel(raiz, origem),
        "sha256": novo,
        "previous": anterior,
        "changed": novo != anterior,
    }
