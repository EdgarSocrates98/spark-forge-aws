"""Le um artefato SDD: frontmatter YAML conferivel, corpo livre."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.scan import Pulo, varrer_source_files
from sparkforge.sdd import PHASES

CERCA = "---"
# o mesmo padrao de `feature` em schema/common.json
FEATURE_RE = re.compile(r"[A-Z0-9_]+")


@dataclass(frozen=True)
class Artifact:
    path: Path
    meta: dict[str, Any] | None
    body: str
    error: str | None = None


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """(bloco YAML, corpo); `None` no bloco quando a cerca nao abre ou nao fecha."""
    linhas = text.splitlines(keepends=True)
    if not linhas or linhas[0].rstrip("\r\n") != CERCA:
        return None, text
    for indice in range(1, len(linhas)):
        if linhas[indice].rstrip("\r\n") == CERCA:
            return "".join(linhas[1:indice]), "".join(linhas[indice + 1 :])
    return None, text


def load_artifact(path: Path) -> Artifact:
    try:
        texto = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return Artifact(path, None, "", "arquivo nao e UTF-8")
    bloco, corpo = split_frontmatter(texto)
    if bloco is None:
        return Artifact(
            path,
            None,
            texto,
            "frontmatter ausente: a primeira linha precisa ser '---' e o bloco fecha com '---'",
        )
    try:
        meta = yaml.safe_load(bloco)
    except yaml.YAMLError as exc:
        marca = getattr(exc, "problem_mark", None)
        # +1 porque a marca e 0-based, +1 pela cerca de abertura
        onde = f" na linha {marca.line + 2}" if marca is not None else ""
        problema = getattr(exc, "problem", None) or str(exc)
        return Artifact(path, None, corpo, f"YAML invalido{onde}: {problema}")
    if not isinstance(meta, dict):
        return Artifact(path, None, corpo, "frontmatter precisa ser um mapeamento YAML")
    return Artifact(path, meta, corpo)


@dataclass(frozen=True)
class Descoberta:
    """As features achadas E o que a varredura deixou de fora sob a raiz.

    Juntos de proposito: uma feature chamada `BUILD` e podada pela varredura, e
    devolver so `features` faria ela sumir calada.
    """

    features: dict[str, dict[str, Path]]
    pulos: tuple[Pulo, ...]


def discover(root: Path) -> Descoberta:
    """`root/<FEATURE>/<fase>.md`, com FEATURE no padrao do schema, e nada mais fundo."""
    varredura = varrer_source_files(root, "*.md")
    features: dict[str, dict[str, Path]] = {}
    for arquivo in varredura.arquivos:
        partes = arquivo.relative_to(root).parts
        if len(partes) != 2 or arquivo.stem not in PHASES:
            continue
        if not FEATURE_RE.fullmatch(partes[0]):
            continue
        features.setdefault(partes[0], {})[arquivo.stem] = arquivo
    return Descoberta(features=features, pulos=varredura.pulos)
