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
from pathlib import Path

import pytest

pytest.importorskip("mcp", reason="SDK do MCP e extra opcional")
pytest.importorskip("starlette", reason="starlette vem com o extra `mcp`")

import anyio  # noqa: E402
import mcp.types as types  # noqa: E402

from sparkforge.adapters.mcp import build_http_app, build_server  # noqa: E402
from sparkforge.adapters.tools import TOOLS  # noqa: E402

ROOT = str(Path(__file__).resolve().parents[1])


@pytest.fixture
def server():
    return build_server()


def _call(server, name: str, arguments: dict):
    """Chama o tool ATRAVES do handler do SDK, nao de `tools.call_tool`.

    A diferenca e o ponto do teste: `tools.call_tool` sempre funcionou; o que
    estava quebrado era a camada do SDK entre ele e o cliente.
    """
    handler = server.request_handlers[types.CallToolRequest]
    request = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    return anyio.run(lambda: handler(request)).root


def _status(app, path: str) -> int:
    """Dirige o app ASGI direto e devolve o status, sem subir servidor.

    Um POST vazio nao completa handshake de MCP nenhum -- e nem precisa: o que
    este helper distingue e "a rota chegou no transporte" (qualquer status que
    o proprio MCP produza) de "a rota nao existe" (404 do roteador).
    """
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 80),
        "scheme": "http",
    }
    captured: dict = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]

    async def drive():
        async with app.router.lifespan_context(app):
            await app(scope, receive, send)

    anyio.run(drive)
    return captured["status"]


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


class TestCallTool:
    """O defeito que estes testes fixam derrubava TODA chamada de tool.

    Todo tool declara `outputSchema`, e o SDK exige `structuredContent` de quem
    declara. O handler devolvia so `TextContent`, entao qualquer `tools/call`
    -- em stdio e em HTTP, no Claude Code e no Devin -- respondia
    `Output validation error: outputSchema defined but no structured output
    returned`. Nenhum teste chamava o tool ATRAVES do SDK: `tools.call_tool`
    era exercitado direto, e ele nunca esteve quebrado.
    """

    def test_a_successful_call_returns_structured_content(self, server):
        # `{"repo": ROOT}` ate a fase da superficie de codigo, e era ARGUMENTO
        # INVENTADO: `sparkforge_runtime_detect` nunca declarou `repo` no
        # `inputSchema` e `_h_runtime_detect` nunca o leu -- ele era descartado
        # em silencio e o teste passava por acaso, exercitando a tool com zero
        # entrada. Fechar o schema (SPEC 68, `additionalProperties: false`) fez
        # o SDK recusar, que e o gate funcionando: o argumento errado agora
        # aparece em vez de sumir. `glue` e declarado, e lido, e deriva a versao
        # de Spark que a asercao abaixo confere.
        result = _call(server, "sparkforge_runtime_detect", {"glue": "5.0"})
        assert result.isError is not True
        assert result.structuredContent is not None
        assert "spark" in result.structuredContent

    def test_structured_content_validates_against_the_declared_output_schema(self, server):
        """O SDK valida `structuredContent` contra o `outputSchema` do tool.
        Passar aqui e a prova de que os dois nao divergiram."""
        result = _call(server, "sparkforge_rules_lookup", {"id": ["SF-PQ-002"]})
        assert result.isError is not True
        assert [r["id"] for r in result.structuredContent["rules"]] == ["SF-PQ-002"]

    def test_text_content_still_carries_the_json(self, server):
        """O cliente que so le texto nao pode regredir: o JSON continua em
        `content`, alem de `structuredContent`."""
        result = _call(server, "sparkforge_runtime_detect", {"glue": "5.0"})
        assert result.content
        assert '"spark"' in result.content[0].text

    def test_adapter_error_keeps_its_actionable_message(self, server):
        """Erro de fronteira sai como `isError`, com o texto do adapter. Se
        fosse devolvido como dict, ele nao casaria com o `outputSchema` e a
        validacao do SDK trocaria a mensagem util por uma queixa de schema."""
        result = _call(server, "sparkforge_analyze_plan", {"path": "/nao/existe.txt"})
        assert result.isError is True
        assert "nao encontrado" in result.content[0].text

    def test_unknown_tool_is_an_error_not_a_crash(self, server):
        result = _call(server, "sparkforge_nao_existe", {})
        assert result.isError is True


class TestBuildHttpApp:
    @pytest.mark.parametrize(
        ("path", "expected_404"),
        [("/mcp", False), ("/mcp/", False), ("/", True), ("/outra", True)],
    )
    def test_serves_mcp_with_and_without_the_trailing_slash(self, server, path, expected_404):
        """Devin Desktop aponta `serverUrl` para `/mcp`. Com `Mount`, esse
        caminho respondia 307 para `/mcp/` -- e httpx nao segue redirect por
        default, entao o sintoma seria "nao conecta", sem pista nenhuma.
        Desligar `redirect_slashes` no Mount trocava o 307 por 404, pior
        ainda. As duas formas tem que servir, e o resto tem que dar 404."""
        app = build_http_app(server)
        assert (_status(app, path) == 404) is expected_404

    def test_lifespan_starts_and_stops_the_session_manager(self, server):
        """A regressao real: sem entrar em `manager.run()` o app responde 500
        em toda requisicao. Entrar e sair do lifespan prova que o task group
        levanta -- e teria pego o construtor com assinatura errada."""
        app = build_http_app(server)

        async def cycle() -> None:
            async with app.router.lifespan_context(app):
                pass

        anyio.run(cycle)

    def test_json_response_mode_also_serves(self, server):
        app = build_http_app(server, json_response=True)
        assert _status(app, "/mcp") != 404


class TestSpec71OTransporteHttpNaoServeFonte:
    """SPEC 71: `stdio-first`. Sob HTTP, tool que devolve fonte fica de fora.

    A porta e de SUPERFICIE e nao de confianca no cliente: stdio fala com um
    processo filho na mesma maquina, HTTP abre uma porta. Uma porta que devolve
    trecho arbitrario do repositorio e exfiltracao de codigo sem autenticacao
    nenhuma -- e a SPEC so cogita liberar isso atras de bind em 127.0.0.1,
    validacao de Host e Origin, token efemero e rate limit, nada do que existe
    hoje.
    """

    def test_stdio_serve_o_catalogo_inteiro(self):
        from sparkforge.adapters.mcp import tools_do_transporte

        assert tools_do_transporte("stdio") == TOOLS

    def test_http_nao_serve_a_tool_de_leitura_de_fonte(self):
        from sparkforge.adapters.mcp import TOOLS_COM_FONTE, tools_do_transporte

        servidas = tools_do_transporte("http")
        assert set(TOOLS) - set(servidas) == set(TOOLS_COM_FONTE)
        assert "sparkforge_code_read" not in servidas

    def test_a_lista_literal_bate_com_quem_declara_snippet(self):
        """A metade que impede a lista de envelhecer.

        `TOOLS_COM_FONTE` e literal porque nenhuma anotacao declarada separa
        "devolve trecho" de "devolve metadado". Uma tool nova que passasse a
        devolver `snippet` sem entrar na lista continuaria servindo fonte por
        HTTP, em silencio -- e e isso que este teste pega, derivando a mesma
        resposta pelo outputSchema.
        """
        from sparkforge.adapters.mcp import TOOLS_COM_FONTE

        def _tem_snippet(schema):
            if "oneOf" in schema:
                return any(_tem_snippet(ramo) for ramo in schema["oneOf"])
            return "snippet" in (schema.get("properties") or {})

        derivada = {n for n, s in TOOLS.items() if _tem_snippet(s["outputSchema"])}
        assert derivada == set(TOOLS_COM_FONTE)

    def test_a_tool_escondida_tambem_recusa_a_chamada(self):
        """Escondida de `tools/list` nao e desabilitada.

        Sem a porta no `call_tool`, quem soubesse o nome continuaria sendo
        atendido -- e saber o nome e trivial: ele esta na documentacao.
        """
        servidor = build_server("http")
        resultado = _call(servidor, "sparkforge_code_read", {"repo": "."})
        assert resultado.isError is True
        assert "--transport stdio" in resultado.content[0].text
