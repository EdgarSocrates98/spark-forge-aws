"""O que o cliente MCP recebe de um `tools/call`, decidido sem o SDK.

Ate o SDK `mcp` 1.x, quatro regras moravam DENTRO do SDK, e `adapters/mcp.py`
dependia delas sem declarar:

1. `arguments` validado contra o `inputSchema` -- falha vira
   `Input validation error: <mensagem do jsonschema>`;
2. o dict devolvido vira `structuredContent`, e o texto e
   `json.dumps(dict, indent=2)`;
3. com `outputSchema`, resultado que nao e dict vira
   `Output validation error: outputSchema defined but no structured output
   returned`, e dict fora do schema vira `Output validation error: <mensagem>`;
4. excecao do handler vira `isError` com `str(excecao)`.

O SDK 2.x nao faz nenhuma das quatro: o `on_call_tool` devolve um
`CallToolResult` pronto, e o servidor nao importa `jsonschema`. Trocar so a API
deixaria as 86 tools respondendo e a validacao perdida em silencio. Por isso as
regras moram aqui, como funcoes puras sobre dicts, com as mensagens copiadas
literalmente do 1.29 -- `fixtures/mcp_parity/` e o golden que o 1.29 produziu, e
`tests/test_fixtures_golden_mcp_parity.py` cobra que nada mudou.

Este modulo NAO importa `mcp`, de proposito: a validacao passa a ter teste que
roda sem o extra opcional, coisa que ela nunca teve enquanto morava no SDK.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import jsonschema

ERRO_SEM_ESTRUTURA = (
    "Output validation error: outputSchema defined but no structured output returned"
)


@dataclass(frozen=True)
class Envelope:
    """O resultado de uma chamada antes de virar tipo do SDK.

    `structured` e `None` em todo erro: o 1.x nunca mandava `structuredContent`
    num `isError`, e um dict de erro nao casa com o `outputSchema` da tool.
    """

    text: str
    structured: dict[str, Any] | None
    is_error: bool


def _erro(texto: str) -> Envelope:
    return Envelope(text=texto, structured=None, is_error=True)


def _erro_compacto(payload: Mapping[str, Any]) -> Envelope:
    """Erro de fronteira do adapter, em JSON sem espacos.

    `separators=(",", ":")` porque o texto e transporte, nao leitura humana; a
    mensagem acionavel dentro do dict fica identica, so o envelope encolhe.
    """
    return _erro(json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")))


def validar_entrada(arguments: Mapping[str, Any], schema: Mapping[str, Any]) -> str | None:
    """Mensagem de erro do 1.x se `arguments` fere o `inputSchema`, senao `None`."""
    try:
        jsonschema.validate(instance=dict(arguments), schema=dict(schema))
    except jsonschema.ValidationError as exc:
        return f"Input validation error: {exc.message}"
    return None


def validar_saida(resultado: Any, schema: Mapping[str, Any] | None) -> str | None:
    """Mensagem de erro do 1.x se `resultado` fere o `outputSchema`, senao `None`.

    Sem `outputSchema` nao ha o que validar, como no 1.x. Toda tool deste
    repositorio declara um, entao na pratica o ramo `None` so existe para que a
    funcao nao invente exigencia que o schema nao faz.
    """
    if schema is None:
        return None
    if not isinstance(resultado, dict):
        return ERRO_SEM_ESTRUTURA
    try:
        jsonschema.validate(instance=resultado, schema=dict(schema))
    except jsonschema.ValidationError as exc:
        return f"Output validation error: {exc.message}"
    return None


def envelope_da_chamada(
    name: str,
    arguments: Mapping[str, Any] | None,
    catalogo: Mapping[str, Mapping[str, Any]],
    transport: str,
    executar: Callable[[str, dict[str, Any]], Any],
) -> Envelope:
    """Decide o que o cliente recebe, na ordem em que o 1.x decidia.

    A porta do catalogo vem PRIMEIRO, antes de validar ou executar: uma tool
    escondida de `tools/list` (SPEC 71) que ainda atendesse `tools/call` para
    quem soubesse o nome seria "escondida", nao "desabilitada". A mensagem e a
    que `adapters/mcp.py` ja produzia, nao a do SDK.

    `executar` e `tools.call_tool` em producao; entra como parametro para que
    este modulo nao importe o despacho inteiro e para que o teste injete o
    resultado que quiser.
    """
    if name not in catalogo:
        return _erro_compacto(
            {
                "error": (
                    f"ferramenta indisponivel no transporte {transport!r}: {name}. "
                    "Use --transport stdio."
                ),
                "exit_code": 2,
            }
        )
    spec = catalogo[name]
    argumentos = dict(arguments or {})

    falha = validar_entrada(argumentos, spec["inputSchema"])
    if falha is not None:
        return _erro(falha)

    try:
        resultado = executar(name, argumentos)
    except Exception as exc:  # noqa: BLE001 -- o 1.x convertia QUALQUER excecao em isError
        return _erro(str(exc))

    if isinstance(resultado, dict) and "error" in resultado and "exit_code" in resultado:
        return _erro_compacto(resultado)

    falha = validar_saida(resultado, spec.get("outputSchema"))
    if falha is not None:
        return _erro(falha)

    return Envelope(text=json.dumps(resultado, indent=2), structured=resultado, is_error=False)
