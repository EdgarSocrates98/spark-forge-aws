"""Servidor MCP. Casca fina sobre `tools.py` -- nenhuma logica de dominio aqui.

O SDK do MCP e uma dependencia extra opcional (`pip install 'sparkforge-aws[mcp]'`)
e provavelmente nao esta instalado no ambiente de testes. Por isso todo import do
SDK e tardio, dentro de `build_server()`/`main()`, nunca no topo do modulo: o
resto do pacote (inclusive `tools.py`) precisa funcionar sem ele.

Sem estado de sessao no servidor: o estado do case vive em
`.sparkforge/case.yaml`, no repositorio analisado. E isso que permite retomar
em outra ferramenta (Devin Desktop, Claude Code, CI) sem carregar contexto de
sessao nenhum -- so o commit.

Dois transportes, mesmo nucleo: stdio para Claude Code, Devin CLI e CI;
streamable HTTP para Devin Desktop, que configura MCP por `serverUrl`.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from sparkforge.adapters.tools import TOOLS, call_tool

_INSTALL_HINT = (
    "SDK do MCP nao instalado. Rode `pip install 'sparkforge-aws[mcp]'` para usar o "
    "servidor MCP, ou use a CLI (`sparkforge --help`) diretamente sem MCP."
)


def build_server() -> Any:  # pragma: no cover -- exige o SDK do MCP, ausente em CI
    """Constroi um `mcp.server.Server` registrando `TOOLS`. Falha com mensagem
    acionavel (SystemExit) se o SDK nao estiver instalado."""
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise SystemExit(_INSTALL_HINT) from exc

    server = Server("sparkforge")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=spec["description"],
                inputSchema=spec["inputSchema"],
                outputSchema=spec["outputSchema"],
            )
            for name, spec in TOOLS.items()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        result = call_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return server


def _run_stdio(server: Any) -> None:  # pragma: no cover -- exige o SDK do MCP
    import anyio
    from mcp.server.stdio import stdio_server

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(_run)


def _run_http(server: Any, host: str, port: int) -> None:  # pragma: no cover -- exige o SDK do MCP
    import anyio
    import uvicorn
    from mcp.server.streamable_http import StreamableHTTPServerTransport

    async def _run() -> None:
        transport = StreamableHTTPServerTransport()
        app = transport.asgi_app(server)
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        await uvicorn.Server(config).serve()

    anyio.run(_run)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover -- exige o SDK do MCP
    parser = argparse.ArgumentParser(prog="sparkforge-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio para Claude Code/Devin CLI/CI; http (streamable) para Devin Desktop.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    server = build_server()

    if args.transport == "stdio":
        _run_stdio(server)
    else:
        _run_http(server, args.host, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
