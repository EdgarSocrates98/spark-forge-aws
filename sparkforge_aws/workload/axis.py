"""O eixo do fingerprint: o valor, de onde ele veio, e quanto vale confiar.

Um eixo com valor e sem procedencia e a forma mais cara de errar neste
projeto, porque parece resposta. Por isso as invariantes abaixo sao impostas na
CONSTRUCAO, e nao conferidas depois: um eixo invalido nunca chega a existir.

  - `measured` exige `basis` e `evidence`. Classe sem lastro nao e classe.
  - valor diferente de `unknown` exige confianca diferente de `unknown`.
  - `unknown` nao carrega evidencia: se ha evidencia, o eixo nao e desconhecido.

`declared` e um valor de confianca DISTINTO de `measured`, e nunca e promovido.
Quem le `sla = critical` precisa saber, sem procurar, que alguem escreveu isso
e nada mediu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALORES = ("extreme", "high", "medium", "low", "critical", "unknown")
CONFIANCAS = ("measured", "declared", "unknown")


@dataclass(frozen=True)
class Axis:
    value: str
    confidence: str
    basis: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)
    missing: str = ""
    collect_command: str = ""

    def __post_init__(self) -> None:
        if self.value not in VALORES:
            raise ValueError(f"valor de eixo desconhecido: {self.value!r}")
        if self.confidence not in CONFIANCAS:
            raise ValueError(f"confidence desconhecida: {self.confidence!r}")
        if self.value != "unknown" and self.confidence == "unknown":
            raise ValueError(
                f"eixo com valor {self.value!r} nao pode ter confidence 'unknown': "
                f"valor sem procedencia parece resposta."
            )
        if self.value == "unknown" and self.evidence:
            raise ValueError(
                "eixo 'unknown' nao carrega evidence: se ha evidencia, ele nao e desconhecido."
            )
        if self.confidence == "measured":
            if not self.basis:
                raise ValueError("eixo 'measured' exige basis: classe sem base nao e classe.")
            if not self.evidence:
                raise ValueError(
                    "eixo 'measured' exige evidence: classe sem lastro parece medicao."
                )

    def to_dict(self) -> dict[str, Any]:
        saida: dict[str, Any] = {
            "value": self.value,
            "confidence": self.confidence,
            "basis": self.basis,
            "evidence": list(self.evidence),
        }
        if self.missing:
            saida["missing"] = self.missing
        if self.collect_command:
            saida["collect_command"] = self.collect_command
        return saida


def unknown_axis(missing: str, collect_command: str = "") -> Axis:
    """Eixo sem lastro, com o que falta e -- quando existe -- o comando que resolve."""
    return Axis(
        value="unknown",
        confidence="unknown",
        missing=missing,
        collect_command=collect_command,
    )
