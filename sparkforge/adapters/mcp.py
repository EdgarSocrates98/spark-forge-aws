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

O extra `mcp` fixa `mcp>=2,<3`. A migracao do 1.x (2026-09-11) trocou mais do
que a API: o SDK 1.x validava `arguments` contra o `inputSchema`, validava o
resultado contra o `outputSchema` e montava `structuredContent` com o texto em
`json.dumps(indent=2)` -- tudo calado, sem que este modulo escrevesse uma
linha. O 2.x nao faz nenhuma das tres. Elas moram agora em
`sparkforge/adapters/mcp_envelope.py`, sem import do SDK, e
`fixtures/mcp_parity/` e o golden que o 1.29 produziu:
`tests/test_fixtures_golden_mcp_parity.py` cobra que o fio nao mudou.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from sparkforge.adapters.mcp_envelope import envelope_da_chamada
from sparkforge.adapters.tools import TOOLS, call_tool

_INSTALL_HINT = (
    "SDK do MCP nao instalado. Rode `pip install 'sparkforge-aws[mcp]'` para usar o "
    "servidor MCP, ou use a CLI (`sparkforge --help`) diretamente sem MCP."
)


# SPEC 71. As tools que devolvem CORPO DE FONTE do repositorio analisado.
#
# Lista literal, e nao derivacao de anotacao: nenhuma propriedade declarada
# separa "devolve trecho" de "devolve metadado", e inventar uma so para esta
# porta seria criar um segundo lugar onde a verdade pode divergir do codigo.
# `tests/test_adapters_mcp.py` cobra que a lista bate com quem de fato tem
# `snippet` no `outputSchema`.
TOOLS_COM_FONTE = ("sparkforge_code_read",)

# Carregado pelo cliente junto do handshake. Curto de proposito: aponta o mapa
# em vez de repeti-lo, porque cada byte aqui entra no contexto de TODA sessao.
_INSTRUCOES = (
    "analyze_* extrai facts de artefato; judge julga; workload, capacity, finops, tune, "
    "benchmark, funcval e arbitrate compoem sobre facts ja extraidos e nao leem artefato. "
    "Antes de ler arquivo no olho, use code_search/code_symbol/code_context. "
    "detail_level (summary|normal|full) muda o tamanho da resposta; leia "
    "economy_report antes de afirmar que reduziu."
)

# `tools/list` so muda com upgrade do pacote, e nao depende de quem pergunta.
# Uma hora e CONVENCAO, nao medida -- nenhum experimento calibrou o valor.
_TTL_TOOLS_LIST_MS = 3_600_000


def _versao_do_pacote() -> str:
    try:
        return version("sparkforge-aws")
    except PackageNotFoundError:
        return "0+unknown"


def tools_do_transporte(transport: str) -> dict[str, dict[str, Any]]:
    """O catalogo servido por `transport`. Em HTTP, sem as tools de fonte.

    SPEC 71: o Code Intelligence e `stdio-first`, e sob `transport=http` com o
    perfil `offline-strict` as tools que devolvem fonte ficam DESABILITADAS. A
    razao e de superficie, nao de confianca no cliente: stdio fala com um
    processo filho na mesma maquina; HTTP abre uma porta, e uma porta que
    devolve trecho arbitrario do repositorio e exfiltracao de codigo com
    autenticacao nenhuma -- a SPEC so cogita liberar isso atras de bind em
    127.0.0.1, validacao de Host e Origin, token efemero e rate limit, nada do
    que existe hoje.

    `offline-strict` NAO e parametro aqui porque nao existe outro perfil
    implementado neste repositorio: `_core.code_status` DERIVA o perfil da
    varredura de imports de rede, e ele so sai `offline-strict` ou `violated`.
    Aceitar um parametro de perfil seria uma manopla que hoje so tem um valor
    valido -- e uma manopla assim vira, no primeiro dia de pressa, o jeito de
    desligar a porta.
    """
    if transport != "http":
        return TOOLS
    return {n: s for n, s in TOOLS.items() if n not in TOOLS_COM_FONTE}


def build_server(transport: str = "stdio") -> Any:
    """Constroi um `mcp.server.Server` registrando `TOOLS`. Falha com mensagem
    acionavel (SystemExit) se o SDK nao estiver instalado.

    `transport` NAO liga o servidor -- quem faz isso e `main()`. Ele entra aqui
    porque o CATALOGO depende dele (SPEC 71): filtrar depois, na hora de
    atender, deixaria a tool visivel em `tools/list` e recusando em
    `tools/call`, que e a pior das duas formas -- o cliente escolheria a tool,
    montaria o pedido e so entao descobriria.
    """
    try:
        from mcp.server import Server
        from mcp.server.caching import CacheHint
        from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
    except ImportError as exc:
        raise SystemExit(_INSTALL_HINT) from exc

    catalogo = tools_do_transporte(transport)
    # O canal vai MEDIDO para o span: so a chamada que entrou por aqui recebe
    # `mcp.method.name` no export OTLP (`observability/otlp.py`).
    executar = functools.partial(call_tool, channel="mcp", transport=transport)
    ferramentas = [
        Tool(
            name=name,
            description=spec["description"],
            input_schema=spec["inputSchema"],
            output_schema=spec["outputSchema"],
        )
        for name, spec in catalogo.items()
    ]

    async def _list(_ctx: Any, _params: Any) -> Any:
        return ListToolsResult(tools=ferramentas)

    async def _call(_ctx: Any, params: Any) -> Any:
        """Converte o `Envelope` em `CallToolResult`, e nada mais.

        Toda decisao -- catalogo do transporte, validacao de entrada e de
        saida, erro de fronteira, excecao -- mora em `envelope_da_chamada`,
        onde ela e testavel sem o SDK. Este handler so troca de tipo.
        """
        env = envelope_da_chamada(params.name, params.arguments, catalogo, transport, executar)
        return CallToolResult(
            content=[TextContent(type="text", text=env.text)],
            structured_content=env.structured,
            is_error=env.is_error,
        )

    return Server(
        "sparkforge",
        # SEM `description`, de proposito. Na era 2026-07-28 o SDK carimba
        # `_meta.serverInfo` em TODA resposta (spec #3002), e a descricao
        # viajaria junto: medido em 2026-09-11, 177 bytes a mais por chamada
        # (88 so com nome e versao, 265 com a frase). `instructions` vai uma
        # vez, no handshake; a descricao iria em cada `tools/call`.
        version=_versao_do_pacote(),
        instructions=_INSTRUCOES,
        cache_hints={"tools/list": CacheHint(ttl_ms=_TTL_TOOLS_LIST_MS, scope="public")},
        on_list_tools=_list,
        on_call_tool=_call,
    )


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

    server = build_server(args.transport)

    if args.transport == "stdio":
        _run_stdio(server)
    else:
        _run_http(server, args.host, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
