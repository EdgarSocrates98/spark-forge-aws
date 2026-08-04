"""Validacao de saida contra JSON Schema.

Gate de saida, rigido. Nao trava investigacao; trava alucinacao. A regra que
mais importa nao e expressavel em JSON Schema puro: efeito quantificado sem
benchmark_ref e rejeitado por _reject_unbacked_gain.

Desde a Fase 4a `benchmark_ref` nao e mais texto livre: ele cita o `fact_id` de
um `bench.run_delta` -- o fato que `sparkforge benchmark --before X --after Y`
emite ao comparar dois conjuntos de facts de event log. Ate a Fase 4a o gate
nao tinha produtor, e um campo preenchivel com qualquer string e um gate que se
contorna digitando qualquer coisa. A validacao acontece em DUAS camadas:

- **forma, sempre**: `^f_[0-9a-f]{6}$`, a forma de `Fact.id`. Vale em qualquer
  chamada, porque nao depende de nada alem do proprio achado.
- **pertinencia, quando der**: `validate_finding(payload, fact_ids)` recebe so
  o achado na assinatura padrao -- nao tem o conjunto de facts, entao "o
  `fact_id` existe" nao e verificavel ali. Quem tiver o conjunto passa
  `fact_ids` e ganha a segunda camada; quem nao tiver (golden, motor) mantem a
  primeira.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# "40%", "40 %", "2x", "2 vezes" -- numero seguido de unidade de ganho.
# Lookbehind negativo evita casar o "2x" embutido em "v2x" (ex.: caminho
# s3://bucket/v2x/) ou em qualquer token alfanumerico -- o digito precisa
# comecar isolado, nao ser sufixo de uma palavra.
_QUANTIFIED = re.compile(
    r"(?<![a-zA-Z0-9_])\d+(?:[.,]\d+)?\s*(?:%|x\b|vezes\b)", re.IGNORECASE
)

# A forma de `Fact.id` (`sparkforge/findings/models.py`): "f_" + sha1[:6].
# Duplicar o padrao aqui, em vez de importar, mantem `validate` sem dependencia
# do modulo de modelos -- ele valida PAYLOAD, dict cru vindo de JSON, nunca
# objeto. O acoplamento que importa esta coberto por teste.
#
# `\Z` e nao `$`: `$` casa TAMBEM antes de um `\n` final, e `"f_abc123\n"`
# passava por bem formado. Um `benchmark_ref` lido de arquivo, de stdin ou de
# campo colado carrega o terminador de linha, e a camada de pertinencia compara
# a string CRUA contra o conjunto de `fact_id` -- a forma que passava com `\n`
# era a mesma que depois nao casava com fact nenhum, trocando uma rejeicao clara
# por uma confusa. `\Z` so casa no fim absoluto da string.
_BENCH_REF = re.compile(r"^f_[0-9a-f]{6}\Z")


class ValidationFailed(ValueError):
    """Payload rejeitado pelo schema ou pela regra de ganho sem benchmark."""


@lru_cache(maxsize=8)
def _schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    if not path.is_file():
        raise ValidationFailed(f"schema ausente: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _check(payload: dict[str, Any], schema_name: str) -> None:
    try:
        jsonschema.validate(payload, _schema(schema_name))
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "<raiz>"
        raise ValidationFailed(f"{location}: {exc.message}") from exc


def validate_fact(payload: dict[str, Any]) -> None:
    _check(payload, "fact.schema.json")


def _reject_unbacked_gain(
    payload: dict[str, Any], fact_ids: set[str] | None = None
) -> None:
    effect = payload.get("expected_effect") or ""
    if not effect or not _QUANTIFIED.search(effect):
        return

    ref = payload.get("benchmark_ref")
    if not ref:
        raise ValidationFailed(
            f"expected_effect quantifica ganho ({effect!r}) sem benchmark_ref. "
            "Ganho previsto sem benchmark e invencao."
        )
    if not _BENCH_REF.match(str(ref)):
        raise ValidationFailed(
            f"benchmark_ref {ref!r} nao e um fact_id. Desde a Fase 4a o campo cita o "
            "`fact_id` de um fact `bench.run_delta` -- forma `f_` + 6 digitos hex, "
            "produzido por `sparkforge benchmark --before <facts> --after <facts>`. "
            "Texto livre nao prova medicao nenhuma: era o que permitia satisfazer "
            "este gate digitando qualquer coisa no campo."
        )
    if fact_ids is not None and str(ref) not in fact_ids:
        raise ValidationFailed(
            f"benchmark_ref {ref!r} nao esta no conjunto de facts informado. "
            "O achado cita uma medicao que nao acompanha a evidencia."
        )


def validate_finding(payload: dict[str, Any], fact_ids: set[str] | None = None) -> None:
    """Valida o achado contra o schema e contra a regra de ganho sem benchmark.

    `fact_ids` e OPCIONAL de proposito: golden e motor chamam esta funcao sem
    ter o conjunto de facts a mao. Sem ele valem o schema e a forma do
    `benchmark_ref`; com ele vale tambem a pertinencia -- o `fact_id` citado
    precisa estar no conjunto.
    """
    _check(payload, "finding.schema.json")
    _reject_unbacked_gain(payload, fact_ids)
