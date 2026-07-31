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
streamable HTTP para Devin Desktop, que configura MCP por `serverUrl` --
`http://<host>:<port>/mcp` com os defaults de `main()`.

O extra `mcp` fixa `mcp>=1.0,<2` de proposito. O SDK 2.x removeu os
decoradores `@server.list_tools()`/`@server.call_tool()` usados em
`build_server()` em favor de `add_request_handler`, entao `mcp>=1.0` sozinho
resolveria para 2.x numa instalacao limpa e o servidor quebraria no import,
em TODAS as plataformas -- nao so no transporte HTTP. Migrar para 2.x e
trabalho proprio, com o teste de construcao abaixo como rede.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from typing import Any

from sparkforge.adapters.tools import TOOLS, call_tool

_INSTALL_HINT = (
    "SDK do MCP nao instalado. Rode `pip install 'sparkforge-aws[mcp]'` para usar o "
    "servidor MCP, ou use a CLI (`sparkforge --help`) diretamente sem MCP."
)


def build_server() -> Any:
    """Constroi um `mcp.server.Server` registrando `TOOLS`. Falha com mensagem
    acionavel (SystemExit) se o SDK nao estiver instalado."""
    try:
        from mcp.server import Server
        from mcp.types import CallToolResult, TextContent, Tool
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
    async def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
        """Devolve o dict CRU, nao `TextContent`.

        Todo tool declara `outputSchema`, e o SDK exige `structuredContent` de
        quem declara: devolvendo so texto, TODA chamada de tool falhava com
        `Output validation error: outputSchema defined but no structured
        output returned` -- em qualquer transporte, inclusive stdio. Devolver o
        dict faz o SDK preencher `structuredContent` e ainda serializar o JSON
        em `content`, entao o cliente continua recebendo o texto de antes.

        Erro de fronteira sai como `CallToolResult(isError=True)`, e nao como
        dict: `{"error": ..., "exit_code": ...}` nao casa com o `outputSchema`
        do tool, e a validacao do SDK trocaria a mensagem acionavel do adapter
        por uma queixa de schema -- o operador perderia justamente o texto que
        diz o que fazer.
        """
        result = call_tool(name, arguments)
        if isinstance(result, dict) and "error" in result and "exit_code" in result:
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                isError=True,
            )
        return result

    return server


def _run_stdio(server: Any) -> None:  # pragma: no cover -- exige o SDK do MCP
    import anyio
    from mcp.server.stdio import stdio_server

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(_run)


def build_http_app(server: Any, *, json_response: bool = False, stateless: bool = True) -> Any:
    """Monta o app ASGI do transporte streamable HTTP, sem subir servidor.

    Separado de `_run_http` para ser testavel: subir uvicorn exige porta e
    processo, montar o app nao exige nada -- e e na montagem que moram os
    erros que passaram despercebidos aqui (construtor com assinatura errada,
    metodo inexistente). `tests/test_adapters_mcp.py` chama esta funcao e
    entra no lifespan; um erro de API vira falha de teste, nao um servidor
    que morre no primeiro segundo na maquina do operador.

    `stateless=True` porque este servidor nao guarda estado de sessao: o
    estado do case vive em `.sparkforge/case.yaml`, no repositorio analisado.
    Sessao no servidor daria a impressao de continuidade que o design nao tem.
    """
    try:
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
    except ImportError as exc:
        raise SystemExit(_INSTALL_HINT) from exc

    manager = StreamableHTTPSessionManager(
        app=server, json_response=json_response, stateless=stateless
    )

    async def _handle(scope: Any, receive: Any, send: Any) -> None:
        """Atende `/mcp` E `/mcp/`, sem redirect.

        `Mount("/mcp")` do Starlette responde 307 em `/mcp` e so serve
        `/mcp/`. O serverUrl documentado e `/mcp`, e cliente HTTP que nao siga
        redirect em POST (httpx nao segue por default) nunca chega ao
        servidor: o sintoma no Devin Desktop seria "nao conecta", sem pista
        nenhuma. Desligar `redirect_slashes` no Mount troca o 307 por 404, o
        que e pior. Dai a rota ser resolvida aqui, comparando o caminho
        normalizado.
        """
        if scope.get("type") == "http" and scope.get("path", "").rstrip("/") != "/mcp":
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": b"nao encontrado; use /mcp"})
            return
        await manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def _lifespan(_app: Any) -> Any:
        # `manager.run()` levanta o task group que serve as requisicoes. Sem
        # entrar nele, o app responde 500 em toda chamada -- por isso ele e
        # amarrado ao lifespan do Starlette, e nao aberto sob demanda.
        async with manager.run():
            yield

    app = Starlette(lifespan=_lifespan)
    # Sem rota registrada, tudo cai no `default` do router -- que e onde
    # `_handle` decide entre servir e devolver 404.
    app.router.default = _handle
    return app


def _run_http(server: Any, host: str, port: int) -> None:  # pragma: no cover -- sobe servidor
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(_INSTALL_HINT) from exc

    uvicorn.run(build_http_app(server), host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> int:  # pragma: no cover -- exige o SDK do MCP
    parser = argparse.ArgumentParser(prog="sparkforge-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help=(
            "stdio para Claude Code/Devin CLI/CI; http (streamable) para Devin Desktop, "
            "que aponta serverUrl para http://<host>:<port>/mcp."
        ),
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
