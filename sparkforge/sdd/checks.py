"""Os gates do SDD: cada falha e uma recusa com nome e o que a destrava."""

from __future__ import annotations

import ast
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import Artifact, discover, load_artifact

_AQUI = Path(__file__).resolve().parent


@cache
def schema_for(phase: str) -> dict[str, Any]:
    """Schema da fase = campos comuns + campos proprios, sem campo extra."""
    comum = json.loads((_AQUI / "schema" / "common.json").read_text(encoding="utf-8"))
    propria = json.loads((_AQUI / "schema" / f"{phase}.json").read_text(encoding="utf-8"))
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": [*comum["required"], *propria.get("required", [])],
        "properties": {**comum["properties"], **propria["properties"]},
    }
    if "$defs" in propria:
        schema["$defs"] = propria["$defs"]
    return schema


@cache
def change_kinds() -> dict[str, dict[str, Any]]:
    return yaml.safe_load((_AQUI / "change_kinds.yaml").read_text(encoding="utf-8"))


PREDECESSOR: dict[str, str] = {
    "design": "define",
    "plan": "design",
    "build_report": "plan",
    "ship": "build_report",
}
PRONTO = ("ready", "done")


@dataclass
class _Contexto:
    repo: Path
    feature: str
    caminhos: dict[str, Path]
    artefatos: dict[str, Artifact] = field(default_factory=dict)
    refused: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)

    def rel(self, caminho: Path) -> str:
        try:
            return caminho.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return str(caminho)

    def recusa(self, code: str, caminho: Path, campo: str | None, unlock: str) -> None:
        self.refused.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho),
             "field": campo, "unlock": unlock}
        )

    def lacuna(self, code: str, caminho: Path, unlock: str) -> None:
        self.unresolved.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho), "unlock": unlock}
        )


Gate = Callable[[_Contexto, str, Artifact], None]


def _carrega(ctx: _Contexto) -> None:
    for fase in PHASES:
        caminho = ctx.caminhos.get(fase)
        if caminho is None:
            continue
        artefato = load_artifact(caminho)
        if artefato.error is not None:
            ctx.recusa("schema_invalid", caminho, None, artefato.error)
            continue
        erros = sorted(
            Draft202012Validator(schema_for(fase)).iter_errors(artefato.meta),
            key=lambda erro: [str(parte) for parte in erro.absolute_path],
        )
        if erros:
            for erro in erros:
                campo = "/".join(str(parte) for parte in erro.absolute_path) or None
                ctx.recusa("schema_invalid", caminho, campo, erro.message)
            continue
        if artefato.meta["phase"] != fase:
            ctx.recusa("schema_invalid", caminho, "phase",
                       f"o arquivo {fase}.md declara phase {artefato.meta['phase']}")
            continue
        if artefato.meta["feature"] != ctx.feature:
            ctx.recusa("schema_invalid", caminho, "feature",
                       f"o arquivo mora em {ctx.feature}/ e declara feature "
                       f"{artefato.meta['feature']}")
            continue
        ctx.artefatos[fase] = artefato


def _gate_order(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    anterior = PREDECESSOR[fase]
    if anterior in ctx.caminhos and anterior not in ctx.artefatos:
        return  # o anterior existe e ja foi recusado por schema; nao repete a causa
    previo = ctx.artefatos.get(anterior)
    if previo is None or previo.meta["status"] not in PRONTO:
        ctx.recusa("phase_out_of_order", artefato.path, "phase",
                   f"{fase} exige {anterior}.md com status ready ou done")


def _upstream_esperado(ctx: _Contexto, fase: str) -> str | None:
    if fase in PREDECESSOR:
        return PREDECESSOR[fase]
    if fase == "define" and "explore" in ctx.caminhos:
        return "explore"
    return None


def _gate_upstream(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    esperado = _upstream_esperado(ctx, fase)
    declarado = artefato.meta.get("upstream")
    if esperado is None:
        return
    esperado_rel = f"{ctx.rel(ctx.caminhos[esperado])}" if esperado in ctx.caminhos else (
        f"{ctx.rel(artefato.path.parent)}/{esperado}.md"
    )
    if declarado is None:
        ctx.recusa("upstream_missing", artefato.path, "upstream",
                   f"declare upstream.path: {esperado_rel} e rode `sparkforge sdd stamp`")
        return
    alvo = resolve_within(ctx.repo, declarado["path"])
    if alvo is None or not alvo.is_file():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao existe; o upstream de {fase} e {esperado_rel}")
        return
    if esperado in ctx.caminhos and alvo != ctx.caminhos[esperado].resolve():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao e o upstream de {fase}; use {esperado_rel}")
        return
    if declarado["sha256"] != text_sha256(alvo):
        ctx.recusa("upstream_stale", artefato.path, "upstream/sha256",
                   f"{declarado['path']} mudou; revise {fase} e rode "
                   f"`sparkforge sdd stamp --repo . {ctx.rel(artefato.path)}`")


def _nomes_de_teste(arvore: ast.Module) -> set[str]:
    nomes: set[str] = set()
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.ClassDef):
            for membro in no.body:
                if isinstance(membro, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nomes.add(f"{no.name}::{membro.name}")
    return nomes


def _teste_existe(repo: Path, referencia: str) -> bool:
    caminho, _, nome = referencia.partition("::")
    alvo = resolve_within(repo, caminho) if caminho else None
    if alvo is None or not alvo.is_file() or not nome:
        return False
    try:
        arvore = ast.parse(alvo.read_bytes())
    except (SyntaxError, ValueError):
        return False
    return nome in _nomes_de_teste(arvore)


def _conferir_teste(
    ctx: _Contexto, artefato: Artifact, campo: str, referencia: str, dono: str
) -> None:
    if _teste_existe(ctx.repo, referencia):
        return
    if "build_report" in ctx.artefatos:
        ctx.recusa("verified_by_dangling", artefato.path, campo,
                   f"{referencia} nao existe depois do build; escreva o teste ou corrija a "
                   "referencia")
    else:
        ctx.lacuna("test_not_written", artefato.path,
                   f"{referencia} ainda nao existe; o build escreve o teste de {dono} antes do "
                   "codigo")


def _ids_de_fact(arquivo: Path) -> set[str]:
    try:
        dado = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    itens = dado.get("items", []) if isinstance(dado, dict) else dado
    if not isinstance(itens, list):
        return set()
    return {str(item.get("id")) for item in itens if isinstance(item, dict)}


def _gate_success_source(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["success"]):
        if not str(item.get("source") or "").strip():
            ctx.recusa("success_without_source", artefato.path, f"success/{indice}/source",
                       f"diga de onde vem o numero de {item['id']} (regra 24)")


def _gate_change_kinds(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    conhecidos = change_kinds()
    for indice, chave in enumerate(artefato.meta["change_kinds"]):
        if chave not in conhecidos:
            ctx.recusa("schema_invalid", artefato.path, f"change_kinds/{indice}",
                       f"'{chave}' nao existe em sparkforge/sdd/change_kinds.yaml; use uma de: "
                       + ", ".join(sorted(conhecidos)))


def _gate_verified_by(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["acceptance"]):
        prova = item["verified_by"]
        campo = f"acceptance/{indice}/verified_by"
        referencia = prova["ref"]
        if prova["kind"] == "test":
            _conferir_teste(ctx, artefato, campo, referencia, item["id"])
        elif prova["kind"] == "fact":
            caminho, _, fact_id = referencia.partition("#")
            alvo = resolve_within(ctx.repo, caminho) if caminho else None
            if alvo is None or not alvo.is_file() or fact_id not in _ids_de_fact(alvo):
                ctx.lacuna("fact_not_collected", artefato.path,
                           f"{fact_id or referencia} nao esta em {caminho}; colete o artefato e "
                           "rode o `sparkforge analyze` que o extrai")
        elif prova["kind"] == "funcval":
            alvo = resolve_within(ctx.repo, referencia)
            if alvo is None or not alvo.is_file():
                ctx.lacuna("funcval_not_run", artefato.path,
                           f"rode `sparkforge funcval compare --out {referencia}` para "
                           f"{item['id']}")


_GATES: dict[str, tuple[Gate, ...]] = {
    "explore": (),
    "define": (_gate_upstream, _gate_success_source, _gate_change_kinds, _gate_verified_by),
    "design": (_gate_order, _gate_upstream),
    "plan": (_gate_order, _gate_upstream),
    "build_report": (_gate_order, _gate_upstream),
    "ship": (_gate_order, _gate_upstream),
}


def check_feature(repo: Path, feature: str, caminhos: dict[str, Path]) -> _Contexto:
    ctx = _Contexto(repo=repo, feature=feature, caminhos=caminhos)
    _carrega(ctx)
    for fase in PHASES:
        artefato = ctx.artefatos.get(fase)
        if artefato is None:
            continue
        for gate in _GATES[fase]:
            gate(ctx, fase, artefato)
    return ctx


def check(repo: Path | str, root: str = DEFAULT_ROOT, feature: str | None = None) -> dict[str, Any]:
    """`{ok, root, features, refused, unresolved}` sobre `repo/root`."""
    raiz_repo = Path(repo)
    raiz = resolve_within(raiz_repo, root)
    if raiz is None or not raiz.is_dir():
        return {
            "ok": False,
            "root": root,
            "features": [],
            "refused": [],
            "unresolved": [{
                "code": "root_missing", "feature": None, "path": root,
                "unlock": f"crie {root}/<FEATURE>/ ou passe --root para a pasta dos artefatos",
            }],
        }
    todas = discover(raiz)
    nomes = sorted(todas) if feature is None else [n for n in sorted(todas) if n == feature]
    refused: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for nome in nomes:
        ctx = check_feature(raiz_repo, nome, todas[nome])
        refused.extend(ctx.refused)
        unresolved.extend(ctx.unresolved)
    return {
        "ok": not refused and not unresolved,
        "root": root,
        "features": nomes,
        "refused": refused,
        "unresolved": unresolved,
    }
