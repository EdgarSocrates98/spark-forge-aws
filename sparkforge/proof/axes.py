"""A politica do Change Proof: `rules/catalog/proof_axes.yaml`.

Ela mora no diretorio do catalogo, e nao em `knowledge/`, porque viaja com as
regras que ela interpreta: o `force-include` do wheel copia `rules/catalog`
inteiro, e o `load_catalog` so pega regra da chave `rules:`, que este arquivo
nao tem. A leitura passa por `safe_catalog_file`, a mesma fronteira de contencao
do catalogo.

A forma e validada na carga e recusada com o campo nomeado: uma politica que
aceitasse `source: benchmark` em vez de `bench` faria todo eixo sair
`unproven` sem que nada dissesse por que.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sparkforge.rules.loader import catalog_dir, safe_catalog_file

POLICY_FILE = "proof_axes.yaml"
SOURCES = frozenset({"funcval", "bench", "none"})
IMPROVES_WHEN = frozenset({"decreases"})


class PolicyError(ValueError):
    """A politica nao pode ser usada; a mensagem nomeia o campo."""


def _lista_de_texto(valor: Any) -> bool:
    return isinstance(valor, list) and all(isinstance(item, str) and item for item in valor)


def _validar_eixo(nome: str, eixo: Any) -> None:
    if not isinstance(eixo, dict):
        raise PolicyError(f"{POLICY_FILE}: axes.{nome} precisa ser um mapa")
    fonte = eixo.get("source")
    if fonte not in SOURCES:
        raise PolicyError(
            f"{POLICY_FILE}: axes.{nome}.source {fonte!r} fora de {sorted(SOURCES)}"
        )
    if fonte == "bench":
        if not isinstance(eixo.get("measure"), str) or not eixo["measure"]:
            raise PolicyError(f"{POLICY_FILE}: axes.{nome} de bench precisa de `measure`")
        if eixo.get("improves_when") not in IMPROVES_WHEN:
            raise PolicyError(
                f"{POLICY_FILE}: axes.{nome}.improves_when fora de {sorted(IMPROVES_WHEN)}"
            )
    if fonte == "none" and not str(eixo.get("unlock") or "").strip():
        raise PolicyError(
            f"{POLICY_FILE}: axes.{nome} sem comparador precisa de `unlock` (regra 20)"
        )
    for campo in ("refuted_by", "confounded_by"):
        if campo in eixo and not _lista_de_texto(eixo[campo]):
            raise PolicyError(f"{POLICY_FILE}: axes.{nome}.{campo} precisa ser lista de rule_id")


def validate_policy(doc: Any) -> None:
    """Recusa a politica malformada, nomeando o campo."""
    if not isinstance(doc, dict):
        raise PolicyError(f"{POLICY_FILE}: esperado um mapa no topo")
    if not isinstance(doc.get("policy_version"), int):
        raise PolicyError(f"{POLICY_FILE}: `policy_version` inteiro e obrigatorio")
    chaves = doc.get("stable_keys")
    if not isinstance(chaves, dict) or not all(_lista_de_texto(v) for v in chaves.values()):
        raise PolicyError(f"{POLICY_FILE}: `stable_keys` precisa mapear tipo -> lista de campos")
    convencao = doc.get("delta_sign_convention")
    if not isinstance(convencao, dict) or not convencao.get("refutes_when") or not str(
        convencao.get("reason") or ""
    ).strip():
        raise PolicyError(
            f"{POLICY_FILE}: `delta_sign_convention` precisa de `refutes_when` e `reason`"
        )
    eixos = doc.get("axes")
    if not isinstance(eixos, dict) or not eixos:
        raise PolicyError(f"{POLICY_FILE}: `axes` precisa ser um mapa nao vazio")
    for nome, eixo in eixos.items():
        _validar_eixo(str(nome), eixo)


def load_policy(directory: Path | None = None) -> dict[str, Any]:
    """Carrega e valida a politica do diretorio do catalogo."""
    base = directory or catalog_dir()
    caminho = safe_catalog_file(base, POLICY_FILE)
    try:
        doc = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"{POLICY_FILE}: nao pode ser lido ({exc})") from exc
    validate_policy(doc)
    return doc
