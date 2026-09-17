"""Le um artefato SDD: frontmatter YAML conferivel, corpo livre."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.scan import iter_source_files
from sparkforge.sdd import PHASES

CERCA = "---"


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


def discover(root: Path) -> dict[str, dict[str, Path]]:
    """`{feature: {fase: caminho}}` para `root/<FEATURE>/<fase>.md`, e nada mais fundo."""
    features: dict[str, dict[str, Path]] = {}
    for arquivo in iter_source_files(root, "*.md"):
        partes = arquivo.relative_to(root).parts
        if len(partes) != 2 or arquivo.stem not in PHASES:
            continue
        features.setdefault(partes[0], {})[arquivo.stem] = arquivo
    return features
