"""O `--set`: parse e alteracao dos facts de configuracao.

`--set <camada>:<chave>=<valor>`. A camada vai ate o primeiro `:`, a chave ate o
primeiro `=` depois dela, e o resto e o valor -- que pode ter `:` (classe Java,
caminho S3).

A alteracao so toca fact que JA existe: `attrs.value` recebe o texto, e
`measures.value`, quando o fact o tinha, recebe o numero. Medido em
2026-09-12: em `tf.attribute` o valor numerico mora TAMBEM em `measures.value`,
e `SF-GLUE-003` le ali. Sem atualizar a medida, o `--set` no
`max_concurrent_runs` nao moveria a regra.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sparkforge.findings.models import Fact
from sparkforge.simulate.layers import CAMADAS


class SimulateError(ValueError):
    """Entrada que nao pode ser simulada; `reason` nomeia o motivo."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class Mudanca:
    camada: str
    chave: str
    valor: str


def parse_sets(sets: Sequence[str]) -> list[Mudanca]:
    if not sets:
        raise SimulateError("sem_set", "informe ao menos um --set camada:chave=valor")
    mudancas: list[Mudanca] = []
    for bruto in sets:
        camada, sep, resto = str(bruto).partition(":")
        chave, igual, valor = resto.partition("=")
        if not sep or camada not in CAMADAS:
            raise SimulateError(
                "camada_invalida",
                f"--set {bruto!r}: comece pela camada ({', '.join(sorted(CAMADAS))}), "
                "por exemplo --set tf:max_concurrent_runs=1",
            )
        if not chave or not igual:
            raise SimulateError("set_malformado", f"--set {bruto!r}: use camada:chave=valor")
        mudancas.append(Mudanca(camada, chave, valor))
    return mudancas


def _numero(valor: str) -> int | float | None:
    try:
        return float(valor) if "." in valor else int(valor)
    except ValueError:
        return None


def patch_fact(fact: Fact, valor: str) -> Fact:
    measures: dict[str, Any] = dict(fact.measures)
    if "value" in measures:
        numero = _numero(valor)
        if numero is None:
            raise SimulateError(
                "valor_nao_numerico_para_medida",
                f"{fact.attrs.get('key')}: {valor!r} nao e numero, e o fact guarda o valor "
                "como medida numerica",
            )
        measures["value"] = numero
    return Fact(
        kind=fact.kind,
        subject=fact.subject,
        measures=measures,
        attrs={**fact.attrs, "value": valor},
        provenance=fact.provenance,
    )


def apply_sets(
    facts: Sequence[Fact], mudancas: Sequence[Mudanca]
) -> tuple[list[Fact], list[dict[str, Any]]]:
    """Os facts com todas as mudancas aplicadas, e o que cada uma alterou."""
    atuais = list(facts)
    changes: list[dict[str, Any]] = []
    for mudanca in mudancas:
        kinds = CAMADAS[mudanca.camada]
        alvos = [i for i, f in enumerate(atuais) if f.kind in kinds
                 and f.attrs.get("key") == mudanca.chave]
        if not alvos:
            raise SimulateError(
                "chave_ausente_na_camada",
                f"--set {mudanca.camada}:{mudanca.chave}: nenhum fact da camada "
                f"{mudanca.camada!r} declara essa chave; o simulate so altera o que existe",
            )
        antigos = sorted({str(atuais[i].attrs.get("value")) for i in alvos})
        for indice in alvos:
            atuais[indice] = patch_fact(atuais[indice], mudanca.valor)
        changes.append(
            {
                "layer": mudanca.camada,
                "key": mudanca.chave,
                "old_values": antigos,
                "new_value": mudanca.valor,
                "facts_changed": len(alvos),
            }
        )
    return atuais, changes
