"""Intake de evidencia estrangeira: o documento `sparkforge_aws/upstream-facts/v1`.

Quando um orquestrador (The Forge) encadeia um diagnostico de outro motor neste
analisador, o handoff chega traduzido para este contrato: uma lista de facts no
shape nativo (`id`, `schema_version`, `kind`, `subject`, `measures`, `attrs`,
`provenance`) cuja identidade e ESTRANGEIRA e tem que continuar visivel:

- `id` vive no namespace `upstream:` e nunca e recomputado: o `f_<sha>` nativo
  deriva de (kind, subject, measures), e reaplicar a derivacao faria a observacao
  estrangeira parecer observada localmente — o mesmo defeito que
  `apiforge/upstream-facts/v1` recusa com `AF-UPSTREAM-UNMARKED`.
- `kind` vive no namespace `upstream.`: nenhuma regra do catalogo casa com esses
  kinds, entao nenhum juizo nativo dispara sobre claim de outro motor.
- `provenance.extractor` e `theforge/handoff`, o canal de intake — nunca um
  extrator nativo (`pyspark_ast`, ...), que lavaria a origem. Na admissao o
  intake grava `artifact`/`artifact_sha256` do arquivo consumido, sobrepondo o
  que o documento declarar: a procedencia registra o que ESTE motor leu.
- `attrs.upstream` carrega a procedencia do lado de la: `provider`, `run_id`,
  `node`, `item` (strings nao vazias), mais `plan_run`, `epistemic`, `claim` e
  `evidence_ids` quando o orquestrador os tem.

Intake e transporte de evidencia, nunca de instrucao: chaves imperativas
(`_FORBIDDEN_KEYS`) sao recusadas em qualquer profundidade dos campos de
payload — um documento upstream nao pode carregar prompt, rota ou diretiva para
este motor. Bounds sao enforcement duro: 256 KiB por documento, 128 facts.

Erros sao `UpstreamError`: a borda (`_core`) os transforma em `AdapterError`
com exit 2, o mesmo envelope de qualquer input invalido.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

UPSTREAM_SCHEMA = "sparkforge_aws/upstream-facts/v1"
UPSTREAM_EXTRACTOR = "theforge/handoff"
UPSTREAM_ID_PREFIX = "upstream:"
UPSTREAM_KIND_PREFIX = "upstream."
MAX_UPSTREAM_BYTES = 256 * 1024
MAX_UPSTREAM_FACTS = 128

_UPSTREAM_KEYS = ("provider", "run_id", "node", "item")
# Mesmo vocabulario fechado de `apiforge.application.analyze._FORBIDDEN_KEYS`: o
# que transformaria transporte de evidencia em transporte de instrucao. Match e
# exato apos normalizacao (lowercase, `-`/` ` -> `_`), entao `plan_run` segue
# sendo chave de procedencia enquanto `plan` e recusado.
_FORBIDDEN_KEYS = frozenset(
    {
        "action",
        "actions",
        "agent",
        "command",
        "commands",
        "directive",
        "directives",
        "execute",
        "goal",
        "instruction",
        "instructions",
        "message",
        "messages",
        "objective",
        "persona",
        "plan",
        "prompt",
        "prompts",
        "request",
        "role",
        "route",
        "routes",
        "routing",
        "system",
        "task",
        "tasks",
        "tool_call",
        "workflow",
    }
)
_FACT_MAP_FIELDS = ("subject", "measures", "attrs", "provenance")


class UpstreamError(Exception):
    """O documento de upstream nao e `sparkforge_aws/upstream-facts/v1` valido."""


def _normalized_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def _forbidden_key(value: object) -> str | None:
    """Primeira chave proibida numa arvore JSON, ou None. Iterativo: a
    profundidade do payload e controlada por quem escreve o documento."""
    stack = [value]
    while stack:
        node = stack.pop()
        if isinstance(node, Mapping):
            for key, item in node.items():
                if _normalized_key(key) in _FORBIDDEN_KEYS:
                    return str(key)
                stack.append(item)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)
    return None


def _check_fact(index: int, fact: object, document: Path) -> dict[str, Any]:
    """Um fact validado: o dict de entrada com `artifact`/`artifact_sha256` do
    arquivo que o intake leu (a procedencia que este motor observou)."""
    if not isinstance(fact, Mapping):
        raise UpstreamError(f"{document.name}: upstream fact {index} nao e um objeto")
    fact_id = fact.get("id")
    kind = fact.get("kind")
    provenance = fact.get("provenance")
    upstream_attrs = fact.get("attrs")
    marked = (
        isinstance(fact_id, str)
        and fact_id.startswith(UPSTREAM_ID_PREFIX)
        and isinstance(kind, str)
        and kind.startswith(UPSTREAM_KIND_PREFIX)
        and isinstance(provenance, Mapping)
        and provenance.get("extractor") == UPSTREAM_EXTRACTOR
        and isinstance(upstream_attrs, Mapping)
        and isinstance(upstream_attrs.get("upstream"), Mapping)
    )
    if not marked:
        raise UpstreamError(
            f"{document.name}: upstream fact {index} ({fact_id!r}) nao esta marcado: "
            "precisa de id em `upstream:`, kind em `upstream.`, "
            f"provenance.extractor == {UPSTREAM_EXTRACTOR!r} e attrs.upstream "
            "com a procedencia do motor de origem"
        )
    origin = cast(Mapping[str, Any], upstream_attrs)["upstream"]
    missing = [
        key for key in _UPSTREAM_KEYS if not isinstance(origin.get(key), str) or not origin[key]
    ]
    if missing:
        raise UpstreamError(
            f"{document.name}: upstream fact {index} ({fact_id!r}): attrs.upstream "
            f"sem as chaves {missing} (provider, run_id, node, item nao vazias)"
        )
    for field_name in _FACT_MAP_FIELDS:
        payload = fact.get(field_name)
        if not isinstance(payload, Mapping):
            raise UpstreamError(
                f"{document.name}: upstream fact {index} ({fact_id!r}): "
                f"{field_name!r} precisa ser um objeto"
            )
        bad = _forbidden_key(payload)
        if bad is not None:
            raise UpstreamError(
                f"{document.name}: upstream fact {index} ({fact_id!r}): {field_name} "
                f"carrega a chave {bad!r}, que transporta instrucao — o intake de "
                "upstream aceita evidencia, nunca comandos"
            )
    return dict(fact)


def read_upstream_facts(path: str | Path) -> list[dict[str, Any]]:
    """Facts de um documento `sparkforge_aws/upstream-facts/v1`, validados e com a
    procedencia do intake gravada. Ordem do documento preservada (ja e a ordem
    do handoff, que e deterministica)."""
    document = Path(path)
    if not document.is_file():
        raise UpstreamError(f"upstream: arquivo nao encontrado: {document}")
    raw = document.read_bytes()
    if len(raw) > MAX_UPSTREAM_BYTES:
        raise UpstreamError(
            f"upstream: {document.name} excede 256 KiB "
            f"({MAX_UPSTREAM_BYTES} bytes; {len(raw)} recebidos)"
        )
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise UpstreamError(f"upstream: {document.name}: JSON invalido: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("schema") != UPSTREAM_SCHEMA:
        raise UpstreamError(f"upstream: {document.name}: schema precisa ser {UPSTREAM_SCHEMA!r}")
    facts = data.get("facts")
    if not isinstance(facts, list):
        raise UpstreamError(f"upstream: {document.name}: 'facts' precisa ser uma lista")
    if len(facts) > MAX_UPSTREAM_FACTS:
        raise UpstreamError(
            f"upstream: {document.name}: {len(facts)} facts excede o limite de {MAX_UPSTREAM_FACTS}"
        )
    digest = hashlib.sha256(raw).hexdigest()
    stamped: list[dict[str, Any]] = []
    for index, fact in enumerate(facts):
        checked = _check_fact(index, fact, document)
        checked["provenance"] = {
            **checked["provenance"],
            "artifact": document.name,
            "artifact_sha256": digest,
        }
        stamped.append(checked)
    return stamped
