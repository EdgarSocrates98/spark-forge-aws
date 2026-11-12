"""O recibo de execucao de testes do build: `forge/TestExecutionReceipt/v1`.

O `build_report` pode listar `receipts:` -- arquivos JSON que provam uma
execucao real: baseline, comando (argv), exit code, executor, janela e o
resultado por teste, mais o sha256 da saida capturada. O gate rehasha o
arquivo de saida (adulteracao = `receipt_stale`), exige zero falha para
servir de prova e nao aceita "zero testes vistos" como verde -- sem nenhum
teste contado, o recibo e inconclusivo e quem julga e o operador.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from sparkforge_aws.paths import resolve_within
from sparkforge_aws.receipt._hash import text_sha256

SCHEMA_ID = "forge/TestExecutionReceipt/v1"

RECEIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema", "executor", "command", "exit_code", "tests",
        "output_path", "artifact_sha256",
    ],
    "properties": {
        "schema": {"const": SCHEMA_ID},
        "executor": {"type": "string", "minLength": 1},
        "command": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        },
        "exit_code": {"type": "integer"},
        "baseline_sha": {"type": ["string", "null"]},
        "baseline_reason": {"type": "string"},
        "started_at": {"type": "string"},
        "finished_at": {"type": "string"},
        "output_path": {"type": "string", "minLength": 1},
        "artifact_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "tests": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "outcome"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "outcome": {"enum": ["passed", "failed", "skipped", "error"]},
                },
            },
        },
    },
}

# o codigo do contrato por `kind` de Finding (anotacao, nao emissao; quem
# emite e sempre o gate, com o literal no proprio chamado)
CODIGO = {
    "invalid": "schema_invalid",
    "failed": "receipt_failed",
    "inconclusive": "receipt_inconclusive",
    "output_missing": "receipt_output_missing",
    "stale": "receipt_stale",
}

_FALHOU = frozenset({"failed", "error"})


@dataclass(frozen=True)
class Finding:
    """Um problema do recibo; `kind` vira o codigo do contrato no gate."""

    kind: str  # invalid | failed | inconclusive | output_missing | stale
    detail: str


def load_receipt(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """(recibo, erro). O erro e texto legivel, nunca excecao."""
    try:
        texto = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None, "arquivo nao e UTF-8"
    except OSError:
        return None, "arquivo ilegivel"
    try:
        dado = json.loads(texto)
    except ValueError as exc:
        return None, f"JSON invalido: {exc}"
    if not isinstance(dado, dict):
        return None, "o arquivo precisa ser um objeto JSON"
    return dado, None


def validate_receipt(recibo: dict[str, Any], repo: Path | None = None) -> list[Finding]:
    """Os problemas do recibo, na ordem em que aparecem.

    Com `repo`, a saida declarada em `output_path` e rehasheada (confinada a
    `repo` por `resolve_within`); sem `repo` a integridade nao e conferida.
    """
    achados: list[Finding] = []
    erros = sorted(
        Draft202012Validator(RECEIPT_SCHEMA).iter_errors(recibo),
        key=lambda erro: [str(parte) for parte in erro.absolute_path],
    )
    for erro in erros:
        campo = "/".join(str(parte) for parte in erro.absolute_path)
        achados.append(Finding("invalid", f"{campo}: {erro.message}" if campo else erro.message))
    if erros:
        return achados
    if recibo.get("baseline_sha") is None and not str(
        recibo.get("baseline_reason") or ""
    ).strip():
        achados.append(Finding(
            "invalid",
            "baseline_sha null exige baseline_reason: diga por que a execucao "
            "nao tem base de comparacao",
        ))
    falharam = [t["name"] for t in recibo["tests"] if t["outcome"] in _FALHOU]
    passaram = [t for t in recibo["tests"] if t["outcome"] == "passed"]
    if falharam:
        achados.append(Finding(
            "failed",
            f"o recibo viu falhar: {', '.join(sorted(falharam))}; "
            "nao serve de prova de verde",
        ))
    elif not passaram or recibo["exit_code"] != 0:
        motivo = (
            "nenhum teste passou" if not passaram
            else f"exit_code {recibo['exit_code']} sem falha contada"
        )
        achados.append(Finding(
            "inconclusive",
            f"{motivo}: erro de ambiente ou de colecao nao e TDD; "
            "o operador julga se o recibo vale",
        ))
    if repo is not None:
        alvo = resolve_within(repo, recibo["output_path"])
        if alvo is None or not alvo.is_file():
            achados.append(Finding(
                "output_missing",
                f"{recibo['output_path']} nao existe; a saida que o recibo jura "
                "ter capturado nao esta no repo",
            ))
        elif text_sha256(alvo) != recibo["artifact_sha256"]:
            achados.append(Finding(
                "stale",
                f"{recibo['output_path']} tem text_sha256 {text_sha256(alvo)} e o "
                "recibo gravou outro; a saida mudou depois da execucao",
            ))
    return achados
