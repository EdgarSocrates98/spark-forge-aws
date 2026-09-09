"""`spark.exception` -- a excecao que `spark.stage.failure` ja carrega.

Derivacao pura sobre a uniao dos facts, no molde de `bridge.py`. Nao le
artefato: `attrs.reason` do `spark.stage.failure` E o campo `Failure Reason` do
event log, que num job Spark e a excecao com a pilha, ja redigida por
`secrets.redact` em `event_log.py`.

A redacao vem ANTES do parse, e o parse nao a desfaz. Texto redigido vira
recusa nomeada, nunca excecao inventada.

## O que este parser cobre, e o que ele recusa -- medido

Medido em 2026-09-08 sobre `fixtures/`: existe **um** `spark.stage.failure` no
corpus inteiro (`broadcast_timeout_stage_failure`), e o `reason` dele e uma
linha so, sem pilha:

    org.apache.spark.SparkException: Could not execute broadcast in 300 secs. [...]

`_CABECA` casa essa forma, `_FRAME` nao acha frame nenhum, e o fact sai com
`is_chained=False` e zero `spark.exception.frame` -- que e a leitura certa: nao
havia pilha para estruturar.

A LACUNA que essa medida deixa aberta, e ela e nomeada aqui de proposito: o
corpus nao tem nenhum `Failure Reason` no formato

    Job aborted due to stage failure: Task 3 in stage 5.0 failed 4 times [...]
        at ...   (frame indentado por TAB no artefato real)

em que a classe da excecao aparece no MEIO da primeira linha, depois do prefixo
do `DAGScheduler`. `_CABECA` e ancorada em inicio de linha de proposito -- sem a
ancora, qualquer `chave.pontuada: valor` de mensagem livre viraria classe de
excecao que ninguem lancou --, entao esse formato sai hoje como
`spark.exception.unresolved: sem_forma_de_stacktrace`. E recusa NOMEADA, nao
silencio; alargar a ancora exige a fixture que prove a forma, e ela nao existe
ainda.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "exception@0.1.0"

EMITTED_KINDS = frozenset(
    {"spark.exception", "spark.exception.frame", "spark.exception.unresolved"}
)

# `com.pacote.Classe: mensagem` no inicio de linha. O `:` e obrigatorio -- sem
# ele o texto e mensagem livre, nao excecao, e forcar o parse produziria uma
# classe que ninguem lancou.
_CABECA = re.compile(r"^([\w$]+(?:\.[\w$]+)+)\s*:\s*(.*)$", re.MULTILINE)
_CAUSED = re.compile(r"^Caused by:\s*([\w$]+(?:\.[\w$]+)+)", re.MULTILINE)
_FRAME = re.compile(r"^\s+at\s+([\w$.]+)\.([\w$<>]+)\(([^:)]+):(\d+)\)", re.MULTILINE)

_TOPO = 5


def build_exceptions(facts: Sequence[Fact], top_n: int = _TOPO) -> list[Fact]:
    """Estrutura o `reason` de cada `spark.stage.failure`, ou recusa com nome.

    Funcao PURA sobre Facts: nunca reparseia event log.

    Lista vazia so acontece quando NAO HA falha nenhuma no case. Havendo falha,
    sai `spark.exception` ou sai `spark.exception.unresolved` -- e a diferenca
    entre "esta falha nao trouxe excecao" e "ninguem perguntou" e exatamente o
    que a recusa nomeada guarda, no molde de `spark.stage.callsite`.
    """
    saida: list[Fact] = []
    for fact in facts:
        if fact.kind != "spark.stage.failure":
            continue
        subject = dict(fact.subject)
        attrs = fact.attrs or {}
        reason = str(attrs.get("reason") or "")
        provenance = _provenance(fact)

        if attrs.get("redacted"):
            saida.append(_unresolved(subject, "reason_redigida", provenance))
            continue

        cabeca = _CABECA.search(reason)
        if not cabeca:
            saida.append(_unresolved(subject, "sem_forma_de_stacktrace", provenance))
            continue

        causas = _CAUSED.findall(reason)
        saida.append(
            Fact(
                kind="spark.exception",
                subject=subject,
                measures={},
                attrs={
                    "exception_class": cabeca.group(1),
                    "message_head": cabeca.group(2).strip()[:200],
                    "is_chained": bool(causas),
                    "caused_by": causas,
                },
                provenance=provenance,
            )
        )
        for ordem, (cls, metodo, arquivo, linha) in enumerate(
            _FRAME.findall(reason)[:top_n]
        ):
            saida.append(
                Fact(
                    kind="spark.exception.frame",
                    subject={**subject, "frame": ordem},
                    measures={},
                    attrs={
                        "class": cls,
                        "method": metodo,
                        "file": arquivo,
                        "line": int(linha),
                    },
                    provenance=provenance,
                )
            )
    return sort_facts(saida)


def _provenance(fact: Fact) -> dict[str, Any]:
    """Herda o artefato do fact de origem, e assina com ESTE extrator.

    O `artifact_sha256` tambem vem de la: o texto parseado e byte a byte o que
    aquele event log carregava, e trocar o hash por vazio apagaria a unica
    ancora que liga a excecao ao arquivo que a produziu.
    """
    origem = fact.provenance or {}
    return {
        "artifact": origem.get("artifact", "facts"),
        "artifact_sha256": origem.get("artifact_sha256", ""),
        "extractor": EXTRACTOR_ID,
    }


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any]
) -> Fact:
    return Fact(
        kind="spark.exception.unresolved",
        subject=subject,
        measures={},
        attrs={"reason": reason},
        provenance=provenance,
    )


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_exceptions"]
