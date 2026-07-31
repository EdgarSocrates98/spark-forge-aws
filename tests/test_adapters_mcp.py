"""O servidor MCP precisa ser CONSTRUIDO por um teste, nao so descrito.

Este modulo existe por causa de um defeito concreto: `_run_http` chamava
`StreamableHTTPServerTransport()` sem o argumento obrigatorio e depois um
metodo `asgi_app` que nunca existiu no SDK. As duas linhas estavam marcadas
`# pragma: no cover`, `parity.yaml` declarava `mcp` para `devin_desktop`, e
nenhum teste tocava o caminho -- entao a paridade com Devin Desktop era
afirmacao, e o servidor morria no primeiro segundo de quem tentasse.

A licao que estes testes fixam: construir o app ASGI nao exige porta, socket
nem processo. Tudo o que quebrou ali quebra na CONSTRUCAO, e construcao e
barata de testar. Subir uvicorn continua sem teste, de proposito -- e o que
sobra depois que a API foi verificada.

Os testes pulam se o SDK nao estiver instalado, mas `[dev]` inclui o extra
`mcp` justamente para que eles NAO pulem no CI.
"""
import pytest

pytest.importorskip("mcp", reason="SDK do MCP e extra opcional")
pytest.importorskip("starlette", reason="starlette vem com o extra `mcp`")

import anyio  # noqa: E402
import mcp.types as types  # noqa: E402

from sparkforge.adapters.mcp import build_http_app, build_server  # noqa: E402
from sparkforge.adapters.tools import TOOLS  # noqa: E402


@pytest.fixture
def server():
    return build_server()


class TestBuildServer:
    def test_registers_the_three_expected_handlers(self, server):
        registered = {k.__name__ for k in server.request_handlers}
        assert {"ListToolsRequest", "CallToolRequest"} <= registered

    def test_lists_every_tool_of_the_surface(self, server):
        handler = server.request_handlers[types.ListToolsRequest]
        result = anyio.run(lambda: handler(types.ListToolsRequest(method="tools/list")))
        assert {tool.name for tool in result.root.tools} == set(TOOLS)

    def test_every_listed_tool_carries_both_schemas(self, server):
        """Schema de entrada E de saida. Tool sem outputSchema obriga o cliente
        a adivinhar a forma do resultado, que e o oposto do contrato do pacote."""
        handler = server.request_handlers[types.ListToolsRequest]
        result = anyio.run(lambda: handler(types.ListToolsRequest(method="tools/list")))
        for tool in result.root.tools:
            assert tool.inputSchema, tool.name
            assert tool.outputSchema, tool.name


class TestBuildHttpApp:
    def test_returns_an_asgi_app_mounted_on_mcp(self, server):
        """O caminho importa: Devin Desktop aponta `serverUrl` para ele. Mudar
        `/mcp` aqui quebra a configuracao de quem ja apontou."""
        app = build_http_app(server)
        assert [route.path for route in app.routes] == ["/mcp"]

    def test_lifespan_starts_and_stops_the_session_manager(self, server):
        """A regressao real: sem entrar em `manager.run()` o app responde 500
        em toda requisicao. Entrar e sair do lifespan prova que o task group
        levanta -- e teria pego o construtor com assinatura errada."""
        app = build_http_app(server)

        async def cycle() -> None:
            async with app.router.lifespan_context(app):
                pass

        anyio.run(cycle)

    def test_json_response_mode_also_builds(self, server):
        app = build_http_app(server, json_response=True)
        assert [route.path for route in app.routes] == ["/mcp"]
