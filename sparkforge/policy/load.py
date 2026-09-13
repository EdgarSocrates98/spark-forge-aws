"""Carga da policy: sem arquivo e `None` (comportamento de hoje); invalida
levanta `PolicyError`, porque quem a escreveu acredita que ela morde."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.paths import resolve_within
from sparkforge.policy.schema import validar

POLICY_RELATIVE = Path(".sparkforge") / "policy.yaml"


class PolicyError(ValueError):
    """Policy ilegivel ou fora do schema."""


@dataclass(frozen=True)
class Regra:
    rule: str
    decision: str
    reason: str = ""


@dataclass(frozen=True)
class Politica:
    denied: tuple[str, ...] = ()
    approvals: tuple[str, ...] = ()
    ask_classes: tuple[str, ...] = ()
    ask_names: tuple[str, ...] = ()
    extra_roots: tuple[str, ...] = ()
    bash: tuple[Regra, ...] = ()
    paths: tuple[Regra, ...] = ()


def construir(dados: dict[str, Any]) -> Politica:
    """A `Politica` de um mapa ja validado."""
    tools = dados.get("tools") or {}
    ask = tools.get("ask") or {}

    def regras(chave: str) -> tuple[Regra, ...]:
        return tuple(
            Regra(r["rule"], r["decision"], str(r.get("reason") or ""))
            for r in dados.get(chave) or []
        )

    return Politica(
        denied=tuple(tools.get("denied") or []),
        approvals=tuple(tools.get("approvals") or []),
        ask_classes=tuple(ask.get("classes") or []),
        ask_names=tuple(ask.get("names") or []),
        extra_roots=tuple(dados.get("extra_roots") or []),
        bash=regras("bash"),
        paths=regras("paths"),
    )


def raiz_do_projeto(valor: Path | str) -> Path:
    """A raiz declarada (`CLAUDE_PROJECT_DIR`, o `cwd` do hook, o diretorio
    corrente), resolvida. Ela vem de fora do processo, entao so vale se for um
    diretorio que existe; o arquivo lido embaixo dela e confinado por
    `resolve_within`, o mesmo algoritmo do catalogo e do knowledge."""
    raiz = Path(valor).expanduser().resolve()
    if not raiz.is_dir():
        raise PolicyError(f"raiz do projeto nao e um diretorio existente: {valor}")
    return raiz


def caminho(raiz: Path | str) -> Path:
    """`<raiz>/.sparkforge/policy.yaml`, confinado a raiz; um symlink que
    escape dela e recusado em vez de lido."""
    alvo = resolve_within(raiz_do_projeto(raiz), POLICY_RELATIVE)
    if alvo is None:
        raise PolicyError(f"{POLICY_RELATIVE.as_posix()} resolve para fora da raiz do projeto")
    return alvo


def carregar(raiz: Path | str) -> Politica | None:
    """A policy de `<raiz>/.sparkforge/policy.yaml`, ou `None` sem arquivo."""
    alvo = caminho(raiz)
    if not alvo.is_file():
        return None
    try:
        dados = yaml.safe_load(alvo.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"{POLICY_RELATIVE.as_posix()}: ilegivel: {exc}") from exc
    erros = validar(dados)
    if erros:
        raise PolicyError(f"{POLICY_RELATIVE.as_posix()}: " + "; ".join(erros))
    return construir(dados)
