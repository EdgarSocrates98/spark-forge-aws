"""`lakeformation.missing_grant` -- a permissao que a operacao exigia e o grant
medido nao tinha, cruzada com a falha observada.

Derivacao pura sobre a UNIAO dos facts, no molde de `lakeformation.py` e
`timeout_diagnosis.py`: nao le artefato, e e chamada por `fuse()`.

## Por que ele existe

`ERR-LF-001` (`Insufficient Lake Formation permission(s) on`) declara
`lakeformation.missing_grant` em `evidence_required` desde antes de o motor ler
Lake Formation. A mensagem nomeia o RECURSO e nao a permissao; a permissao sai da
OPERACAO que o codigo faz, lida da tabela citada em
`knowledge/glue/lakeformation-permissions.yaml`. "Permissao exigida fora do
conjunto concedido" nao cabe nos seis comparadores de `rules/expr.py`, e por isso
e fact (regra 33 do CLAUDE.md).

## O modelo decide o lado (regras 31 e 32)

Sob FTA, a credencial do Lake Formation le e escreve: cobra-se o grant. Sob FGAC,
a leitura cobra o grant e a escrita cobra o IAM do runtime role. Escrita em alvo
REGISTRADO sob FGAC e o conflito declarado da secao 6 de
`knowledge/glue/lakeformation-fgac.md`, e sai recusa nomeada, sem lado escolhido.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.knowledge_ref import knowledge_dir, safe_knowledge_file

EXTRACTOR_ID = "lakeformation_missing_grant@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "lakeformation.missing_grant",
        "lakeformation.missing_grant.unresolved",
    }
)

# As operacoes que `_operacoes` produz. A tabela precisa ter ao menos uma linha
# para cada uma; `test_tabela_de_operacao_cita_fonte_e_cobre_o_extrator` cobra.
OPERACOES_MAPEADAS = ("read", "write", "overwrite", "create")

_RELATIVE = "glue/lakeformation-permissions.yaml"
_CAMPOS = ("operation", "model", "side", "resource_level", "requires", "source", "quote")


def _path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


@lru_cache(maxsize=1)
def load_table() -> dict[str, Any]:
    """A tabela inteira, validada. Linha sem campo, ou com fonte fora de `fontes`,
    levanta `ValueError` -- a mesma guarda de `lakeformation_matrix.load`."""
    with _path().open("r", encoding="utf-8") as arquivo:
        documento = yaml.safe_load(arquivo) or {}
    fontes = documento.get("fontes") or {}
    problemas: list[str] = []
    for linha in documento.get("operacoes") or []:
        rotulo = f"{linha.get('operation')}/{linha.get('model')}"
        for campo in _CAMPOS:
            if not linha.get(campo):
                problemas.append(f"{rotulo}: sem `{campo}`")
        if linha.get("source") and linha["source"] not in fontes:
            problemas.append(f"{rotulo}: `source` {linha['source']!r} fora de `fontes`")
    if problemas:
        raise ValueError(
            "knowledge/glue/lakeformation-permissions.yaml invalido:\n  "
            + "\n  ".join(problemas)
        )
    return documento


def requirement(operation: str, model: str) -> dict[str, Any] | None:
    """A linha da tabela para (operacao, modelo), ou `None` quando a fonte nao a declara."""
    for linha in load_table().get("operacoes") or []:
        if linha["operation"] == operation and linha["model"] == model:
            return dict(linha)
    return None


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "OPERACOES_MAPEADAS",
    "load_table",
    "requirement",
]
