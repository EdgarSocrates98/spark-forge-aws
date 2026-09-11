"""A era `2026-07-28` do protocolo MCP, negociada por um cliente 2.x.

O SDK 2.x atende dois handshakes: o legado (`initialize`) e o novo, em que o
cliente pergunta `server/discover` e manda o envelope por requisicao. Este
teste prova que o servidor fala o novo, e que o que ele declara nele e o que
foi escolhido -- `instructions` curto, versao do pacote, e NENHUMA
`description`, porque na era nova ela viajaria no carimbo `_meta.serverInfo`
de toda resposta (177 bytes por chamada, medido em 2026-09-11).
"""
from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="SDK do MCP e extra opcional")

from importlib.metadata import version  # noqa: E402

import anyio  # noqa: E402

from sparkforge.adapters.mcp import _INSTRUCOES, _versao_do_pacote, build_server  # noqa: E402
from sparkforge.adapters.tools import TOOLS  # noqa: E402

if int(version("mcp").split(".")[0]) < 2:
    pytest.skip("era 2026-07-28 so existe no SDK 2.x", allow_module_level=True)


def _conectar(modo: str) -> dict:
    from mcp import Client

    async def _ir() -> dict:
        async with Client(build_server("stdio"), mode=modo) as cliente:
            lista = await cliente.list_tools()
            return {
                "protocolo": cliente.protocol_version,
                "discover": cliente.session.discover_result,
                "server_info": cliente.server_info,
                "instructions": cliente.instructions,
                "tools": len(lista.tools),
            }

    return anyio.run(_ir)


def test_negocia_2026_07_28_por_discover():
    sessao = _conectar("auto")
    assert sessao["protocolo"] == "2026-07-28"
    assert sessao["discover"] is not None
    assert sessao["tools"] == len(TOOLS)


def test_handshake_legado_continua_atendido():
    sessao = _conectar("legacy")
    assert sessao["protocolo"] != "2026-07-28"
    assert sessao["discover"] is None
    assert sessao["tools"] == len(TOOLS)


@pytest.mark.parametrize("modo", ["auto", "legacy"])
def test_identidade_declarada(modo):
    sessao = _conectar(modo)
    assert sessao["server_info"].name == "sparkforge"
    assert sessao["server_info"].version == _versao_do_pacote()
    assert sessao["server_info"].description is None
    assert sessao["instructions"] == _INSTRUCOES
