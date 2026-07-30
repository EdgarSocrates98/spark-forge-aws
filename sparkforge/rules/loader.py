"""Descoberta, parsing e validacao estrutural do catalogo de regras.

Resolucao de path, em ordem: env var SPARKFORGE_CATALOG -> raiz do repo
(rules/catalog) -> fallback relativo ao pacote. Desvio deliberado da spec secao
14: o catalogo e dado consultavel e e o terceiro degrau da escada de
portabilidade, entao fica na raiz e nao enterrado no pacote.

routing.yaml tem schema proprio e e carregado por sparkforge.case.router.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from sparkforge.rules.expr import ExprError, evaluate

ROUTING_FILE = "routing.yaml"

_REQUIRED = (
    "id",
    "category",
    "title",
    "requires_facts",
    "when",
    "status",
    "runtime_scope",
    "sources",
)


class CatalogError(ValueError):
    """Catalogo malformado. Falha na carga, nunca em producao."""


def catalog_dir() -> Path:
    override = os.environ.get("SPARKFORGE_CATALOG")
    if override:
        return Path(override)

    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "rules" / "catalog"
    if candidate.is_dir():
        return candidate

    return Path(__file__).resolve().parent / "catalog"


def _validate_expr(rule_id: str, expr: str) -> None:
    probe: dict[str, Any] = {"measures": {}, "attrs": {}, "threshold": {}}
    try:
        evaluate(expr, probe)
    except ExprError as exc:
        message = str(exc)
        # Caminho ausente e esperado com contexto vazio; o que importa e a forma.
        if "ausente" not in message:
            raise CatalogError(
                f"{rule_id}: expressao rejeitada pelo avaliador: {message}"
            ) from exc


def _validate_conditions(rule_id: str, rule: dict[str, Any]) -> None:
    """Toda condicao precisa de `fact` ou `absent`.

    Sem esta checagem, um typo na chave (`facts:` em vez de `fact:`) faz a regra
    nunca disparar, em silencio: o motor nao acha candidato, nao ha erro, e o
    relatorio sai limpo. Falso negativo mudo e o pior modo de falha de um
    analisador, entao a regra malformada morre na carga.
    """
    when = rule.get("when") or {}
    if not isinstance(when, dict):
        raise CatalogError(f"{rule_id}: `when` precisa ser um mapa com `all` ou `any`")

    groups = [g for g in ("all", "any") if g in when]
    if not groups:
        raise CatalogError(f"{rule_id}: `when` sem grupo `all` nem `any`")

    for group in groups:
        conditions = when.get(group) or []
        if not isinstance(conditions, list):
            raise CatalogError(f"{rule_id}: `when.{group}` precisa ser uma lista")
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                raise CatalogError(
                    f"{rule_id}: `when.{group}[{index}]` precisa ser um mapa"
                )
            if "fact" not in condition and "absent" not in condition:
                raise CatalogError(
                    f"{rule_id}: `when.{group}[{index}]` sem `fact` nem `absent` "
                    f"(chaves presentes: {', '.join(sorted(condition)) or 'nenhuma'})"
                )


def _collect_exprs(rule: dict[str, Any]) -> list[str]:
    found: list[str] = []
    when = rule.get("when") or {}
    for group in ("all", "any"):
        for condition in when.get(group) or []:
            if isinstance(condition, dict) and "expr" in condition:
                found.append(condition["expr"])
    for entry in rule.get("severity_by") or []:
        if isinstance(entry, dict) and "when" in entry:
            found.append(entry["when"])
    return found


def load_catalog(
    directory: Path | None = None, validate_exprs: bool = False
) -> list[dict[str, Any]]:
    """Carrega todas as regras exceto routing. Levanta CatalogError se invalido."""
    base = directory or catalog_dir()
    if not base.is_dir():
        raise CatalogError(f"diretorio de catalogo inexistente: {base}")

    rules: list[dict[str, Any]] = []
    seen: dict[str, str] = {}

    for path in sorted(base.glob("*.yaml")):
        if path.name == ROUTING_FILE:
            continue

        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
        except yaml.YAMLError as exc:
            raise CatalogError(f"{path.name}: YAML invalido: {exc}") from exc

        version = document.get("catalog_version", 1)

        for rule in document.get("rules") or []:
            rule_id = rule.get("id", "<sem id>")

            missing = [key for key in _REQUIRED if key not in rule]
            if missing:
                raise CatalogError(
                    f"{rule_id}: campos obrigatorios ausentes: {', '.join(missing)}"
                )
            if "severity_default" not in rule and "severity_by" not in rule:
                raise CatalogError(f"{rule_id}: precisa de severity_default ou severity_by")
            for source in rule["sources"]:
                if "url" not in source and "origin" not in source:
                    raise CatalogError(f"{rule_id}: source sem url nem origin")
            if rule_id in seen:
                raise CatalogError(
                    f"id duplicado: {rule_id} em {seen[rule_id]} e {path.name}"
                )

            # Sempre, nao so sob validate_exprs: condicao malformada e defeito
            # estrutural, da mesma classe de campo obrigatorio ausente.
            _validate_conditions(rule_id, rule)

            if validate_exprs:
                for expr in _collect_exprs(rule):
                    _validate_expr(rule_id, expr)

            seen[rule_id] = path.name
            rule["catalog_version"] = version
            rule["_source_file"] = path.name
            rules.append(rule)

    return sorted(rules, key=lambda r: r["id"])
