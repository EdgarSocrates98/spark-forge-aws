"""Resolucao de `SPARKFORGE_PACKS` e carga das regras de cada pack.

Um pack e SO DADO: regras YAML, knowledge e fixtures. Nada dele e importado --
so `yaml.safe_load` e leitura de texto --, e todo caminho passa por
`resolve_within`, o mesmo confinamento de `safe_catalog_file`.

Pack com defeito sai INTEIRO, com o motivo nomeado (regra 20): carregar as
regras boas de um pack meio quebrado daria resultado que ninguem explica. E o
core nunca cai por causa de pack. A unica excecao que levanta e diretorio de
`SPARKFORGE_PACKS` que nao existe: e erro de configuracao do operador, no molde
de `SPARKFORGE_CATALOG`.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.scan import iter_source_files
from sparkforge.packs.manifest import (
    Manifest,
    PackRefused,
    check_core,
    installed_version,
    read_manifest,
)
from sparkforge.paths import resolve_within
from sparkforge.rules.loader import CatalogError, _json_safe, validate_rule

ENV = "SPARKFORGE_PACKS"


@dataclass(frozen=True)
class Pack:
    root: Path
    manifest: Manifest
    rules: tuple[dict[str, Any], ...]

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def prefix(self) -> str:
        return self.manifest.prefix

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge"


@dataclass(frozen=True)
class PackSet:
    active: tuple[Pack, ...] = ()
    refused: tuple[dict[str, Any], ...] = field(default=())

    def rules(self) -> list[dict[str, Any]]:
        return [dict(regra) for pack in self.active for regra in pack.rules]

    def prefixes(self) -> dict[str, str]:
        return {pack.prefix: pack.id for pack in self.active}

    def pack_of(self, rule_id: str) -> Pack | None:
        prefixo = str(rule_id).split("-", 1)[0]
        return next((p for p in self.active if p.prefix == prefixo), None)


def pack_dirs() -> list[Path]:
    """Os diretorios de `SPARKFORGE_PACKS`, resolvidos e exigidos existentes."""
    bruto = os.environ.get(ENV, "")
    dirs: list[Path] = []
    for parte in bruto.split(os.pathsep):
        if not parte.strip():
            continue
        resolvido = Path(parte.strip()).expanduser().resolve()
        if not resolvido.is_dir():
            raise CatalogError(f"{ENV} aponta para {resolvido}, que nao e um diretorio existente")
        dirs.append(resolvido)
    return dirs


def _rule_files(root: Path) -> list[tuple[str, Path]]:
    """Os YAML de `rules/` como `(relativo, caminho)`.

    O diretorio do pack vem de variavel do operador. Antes de QUALQUER varredura,
    `rules/` e resolvido e exigido dentro do pack: um `rules` que seja symlink
    para fora vira recusa, e a varredura nunca anda fora do pack. Depois, cada
    arquivo passa pela porta de leitura da casa (`iter_source_files`, com
    denylist e teto de tamanho -- `glob` cru e proibido por
    `tests/test_facts_scan.py`) e e confinado de novo por `resolve_within`.
    """
    raiz = root.resolve()
    base = (raiz / "rules").resolve()
    if not base.is_relative_to(raiz):
        raise PackRefused("regra_invalida", "rules/ aponta para fora do pack")
    if not base.is_dir():
        return []
    arquivos = []
    for entrada in sorted(iter_source_files(base, "*.yaml")):
        relativo = entrada.relative_to(base).as_posix()
        caminho = resolve_within(base, relativo)
        if caminho is None:
            raise PackRefused("regra_invalida", f"rules/{relativo} aponta para fora do pack")
        arquivos.append((relativo, caminho))
    return arquivos


def _load_rules(root: Path, manifest: Manifest) -> tuple[dict[str, Any], ...]:
    padrao = re.compile(rf"^{re.escape(manifest.prefix)}-[A-Z][A-Z0-9]*-[0-9]{{3}}$")
    vistos: dict[str, str] = {}
    regras: list[dict[str, Any]] = []
    for relativo, caminho in _rule_files(root):
        origem = f"rules/{relativo}"
        try:
            documento = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
        except yaml.YAMLError as exc:
            detalhe = f"{origem}: YAML invalido: {exc}"
            raise PackRefused("regra_invalida", detalhe, manifest.id) from exc
        documento = _json_safe(documento)
        if not isinstance(documento, dict):
            detalhe = f"{origem}: esperado um mapa com `rules:`"
            raise PackRefused("regra_invalida", detalhe, manifest.id)
        versao = documento.get("catalog_version", 1)
        for regra in documento.get("rules") or []:
            if not isinstance(regra, dict):
                raise PackRefused("regra_invalida", f"{origem}: regra que nao e mapa", manifest.id)
            try:
                validate_rule(regra, validate_exprs=True)
            except CatalogError as exc:
                raise PackRefused("regra_invalida", f"{origem}: {exc}", manifest.id) from exc
            rule_id = str(regra["id"])
            if not padrao.match(rule_id):
                raise PackRefused(
                    "id_fora_do_prefixo",
                    f"{rule_id} em {origem} nao casa {manifest.prefix}-<AREA>-NNN",
                    manifest.id,
                )
            if rule_id in vistos:
                raise PackRefused(
                    "id_duplicado", f"{rule_id} em {vistos[rule_id]} e {origem}", manifest.id
                )
            vistos[rule_id] = origem
            regra["catalog_version"] = versao
            regra["_source_file"] = f"packs/{manifest.id}/{origem}"
            regra["_pack"] = manifest.id
            regras.append(regra)
    return tuple(regras)


def load_pack(
    root: Path,
    taken_ids: frozenset[str] = frozenset(),
    taken_prefixes: frozenset[str] = frozenset(),
) -> Pack:
    """Carrega um pack. Levanta `PackRefused` no primeiro motivo, nesta ordem:
    manifesto, prefixo reservado, pack duplicado, core, regras."""
    manifest = read_manifest(root)
    if manifest.id in taken_ids:
        raise PackRefused("pack_duplicado", f"id {manifest.id} ja ativo", manifest.id)
    if manifest.prefix in taken_prefixes:
        raise PackRefused(
            "pack_duplicado",
            f"prefixo {manifest.prefix} ja e de outro pack ativo: "
            "o prefixo diz a origem do finding",
            manifest.id,
        )
    check_core(manifest, installed_version())
    return Pack(root=root, manifest=manifest, rules=_load_rules(root, manifest))


def resolve(dirs: list[Path] | None = None) -> PackSet:
    """Os packs de `dirs` (padrao: `SPARKFORGE_PACKS`), ativos e recusados."""
    alvos = pack_dirs() if dirs is None else dirs
    ativos: list[Pack] = []
    recusados: list[dict[str, Any]] = []
    for root in alvos:
        try:
            pack = load_pack(
                root,
                frozenset(p.id for p in ativos),
                frozenset(p.prefix for p in ativos),
            )
        except PackRefused as exc:
            recusados.append(
                {"dir": str(root), "id": exc.pack_id, "reason": exc.reason, "detail": exc.detail}
            )
            continue
        ativos.append(pack)
    return PackSet(active=tuple(ativos), refused=tuple(recusados))
