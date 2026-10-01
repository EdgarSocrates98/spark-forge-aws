"""O manifesto de um pack (`pack.yaml`) e a faixa de versao do core.

`packaging` nao e dependencia declarada deste projeto (`pyproject.toml` so tem
PyYAML e jsonschema), e a faixa `core:` precisa de cinco operadores sobre
versao de inteiros. O comparador abaixo cobre exatamente isso; pre-release
(`1.0.0rc1`) e recusada no manifesto em vez de comparada pela metade.
"""
from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.paths import resolve_within

PACKAGE = "sparkforge-aws"
MANIFEST_FILE = "pack.yaml"
RESERVED_PREFIX = "SF"

_ID = re.compile(r"^[a-z][a-z0-9-]*$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9]*$")
_VERSION = re.compile(r"^\d+(?:\.\d+)*$")
_CLAUSULA = re.compile(r"^(>=|<=|==|>|<)(\d+(?:\.\d+)*)$")


class PackRefused(Exception):
    """Pack recusado inteiro; `reason` e o motivo nomeado."""

    def __init__(self, reason: str, detail: str, pack_id: str | None = None) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.pack_id = pack_id


@dataclass(frozen=True)
class Manifest:
    id: str
    version: str
    prefix: str
    core: str
    description: str


def _versao(texto: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in texto.split("."))


def _comparar(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    largura = max(len(a), len(b))
    a = a + (0,) * (largura - len(a))
    b = b + (0,) * (largura - len(b))
    return (a > b) - (a < b)


def _clausulas(faixa: str) -> list[tuple[str, tuple[int, ...]]]:
    saida = []
    for bruto in faixa.split(","):
        casou = _CLAUSULA.match(bruto.strip())
        if casou is None:
            raise ValueError(f"clausula invalida em `core`: {bruto.strip()!r}")
        saida.append((casou.group(1), _versao(casou.group(2))))
    return saida


def dentro_da_faixa(instalada: str, faixa: str) -> bool:
    atual = _versao(instalada)
    for operador, alvo in _clausulas(faixa):
        c = _comparar(atual, alvo)
        ok = {">=": c >= 0, "<=": c <= 0, "==": c == 0, ">": c > 0, "<": c < 0}[operador]
        if not ok:
            return False
    return True


_PYPROJECT_VERSION = re.compile(
    r'^\[project\]\s*$.*?^version\s*=\s*"([^"]+)"', re.MULTILINE | re.DOTALL
)


def installed_version() -> str | None:
    """A versao do core QUE ESTA RODANDO: raiz do repo -> metadata do pacote.

    A mesma precedencia de `catalog_dir()` e `knowledge_dir()`. So
    `importlib.metadata` nao basta, e isto e medido (2026-09-12): com o codigo
    carregado do repositorio, a metadata respondeu `0.4.0` de uma dist-info
    antiga em site-packages, enquanto o `pyproject.toml` do mesmo codigo diz
    `0.5.0` -- e so a `egg-info` da raiz, achada quando o diretorio corrente e o
    repo, dava a versao certa. Checar compatibilidade contra outra versao que
    nao a do codigo carregado recusaria pack bom, ou aceitaria pack incompativel.
    `tomllib` nao existe no Python 3.10 do CI; o regex le so o `version` da
    secao `[project]`.
    """
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.is_file():
        texto = pyproject.read_text(encoding="utf-8")
        casou = _PYPROJECT_VERSION.search(texto)
        if casou and f'name = "{PACKAGE}"' in texto:
            return casou.group(1)
    try:
        return importlib.metadata.version(PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        return None


def read_manifest(root: Path) -> Manifest:
    """Le `<root>/pack.yaml`. Levanta `PackRefused` com `manifesto_invalido` ou
    `prefixo_reservado`."""
    caminho = resolve_within(root, MANIFEST_FILE)
    if caminho is None or not caminho.is_file():
        raise PackRefused("manifesto_invalido", f"{MANIFEST_FILE} ausente em {root}")
    try:
        documento: Any = yaml.safe_load(caminho.read_text(encoding="utf-8-sig"))
    except yaml.YAMLError as exc:
        raise PackRefused("manifesto_invalido", f"{MANIFEST_FILE}: YAML invalido: {exc}") from exc
    bloco = documento.get("pack") if isinstance(documento, dict) else None
    if not isinstance(bloco, dict):
        raise PackRefused("manifesto_invalido", f"{MANIFEST_FILE} sem o mapa `pack:`")

    nomes = ("id", "version", "prefix", "core")
    campos = {nome: str(bloco.get(nome) or "").strip() for nome in nomes}
    faltando = [nome for nome, valor in campos.items() if not valor]
    pack_id = campos["id"] or None
    if faltando:
        raise PackRefused(
            "manifesto_invalido", f"campos ausentes em `pack`: {', '.join(faltando)}", pack_id
        )
    if not _ID.match(campos["id"]):
        raise PackRefused("manifesto_invalido", f"`id` {campos['id']!r} fora de ^[a-z][a-z0-9-]*$")
    if not _VERSION.match(campos["version"]):
        raise PackRefused(
            "manifesto_invalido", f"`version` {campos['version']!r} nao e versao numerica", pack_id
        )
    if not _PREFIX.match(campos["prefix"]):
        raise PackRefused(
            "manifesto_invalido", f"`prefix` {campos['prefix']!r} fora de ^[A-Z][A-Z0-9]*$", pack_id
        )
    try:
        _clausulas(campos["core"])
    except ValueError as exc:
        raise PackRefused("manifesto_invalido", str(exc), pack_id) from exc
    if campos["prefix"] == RESERVED_PREFIX:
        raise PackRefused(
            "prefixo_reservado", f"o prefixo {RESERVED_PREFIX} e do core", pack_id
        )
    return Manifest(
        id=campos["id"],
        version=campos["version"],
        prefix=campos["prefix"],
        core=campos["core"],
        description=str(bloco.get("description") or "").strip(),
    )


def check_core(manifest: Manifest, instalada: str | None) -> None:
    if instalada is None or not dentro_da_faixa(instalada, manifest.core):
        raise PackRefused(
            "core_incompativel",
            f"`core: {manifest.core}` nao aceita a versao instalada "
            f"{instalada or 'desconhecida'}",
            manifest.id,
        )
