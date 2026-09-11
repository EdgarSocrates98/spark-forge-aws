"""O envelope do `tools/call`, testado SEM o SDK do MCP.

Enquanto a validacao de entrada e de saida morava no SDK 1.x, ela so existia
quando o extra `mcp` estava instalado, e nenhum teste deste repositorio a
cobrava. Estes testes nao usam `importorskip`: eles rodam em qualquer
ambiente, e um deles confere por AST que `mcp_envelope.py` nao importa `mcp`.

As mensagens esperadas sao as do SDK 1.29, as mesmas que
`fixtures/mcp_parity/calls.json` registrou.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from sparkforge.adapters.mcp_envelope import (
    ERRO_SEM_ESTRUTURA,
    Envelope,
    envelope_da_chamada,
    validar_entrada,
    validar_saida,
)

MODULO = Path(__file__).resolve().parents[1] / "sparkforge" / "adapters" / "mcp_envelope.py"

CATALOGO: dict[str, dict[str, Any]] = {
    "t_ok": {
        "inputSchema": {
            "type": "object",
            "properties": {"n": {"type": "integer"}, "ids": {"type": "array"}},
            "required": ["n"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {"dobro": {"type": "integer"}},
            "required": ["dobro"],
        },
    },
}


def _executar_dobro(name: str, arguments: dict[str, Any]) -> Any:
    return {"dobro": arguments["n"] * 2}


def _chamar(executar: Any, arguments: dict[str, Any] | None = None, name: str = "t_ok") -> Envelope:
    return envelope_da_chamada(name, arguments, CATALOGO, "stdio", executar)


class TestSucesso:
    def test_structured_e_o_dict_e_o_texto_e_indent_2(self):
        env = _chamar(_executar_dobro, {"n": 21})
        assert env == Envelope(
            text=json.dumps({"dobro": 42}, indent=2), structured={"dobro": 42}, is_error=False
        )

    def test_texto_escapa_nao_ascii_como_o_1x(self):
        env = _chamar(lambda n, a: {"dobro": 1, "nota": "ação"}, {"n": 1})
        assert "\\u00e7" in env.text
        assert env.structured == {"dobro": 1, "nota": "ação"}


class TestEntrada:
    def test_obrigatorio_ausente_nao_executa(self):
        chamadas: list[str] = []

        def executar(name: str, arguments: dict[str, Any]) -> Any:
            chamadas.append(name)
            return {"dobro": 0}

        env = _chamar(executar, {})
        assert env == Envelope(
            text="Input validation error: 'n' is a required property",
            structured=None,
            is_error=True,
        )
        assert chamadas == []

    def test_tipo_errado(self):
        env = _chamar(_executar_dobro, {"n": 1, "ids": "x"})
        assert env.is_error
        assert env.text == "Input validation error: 'x' is not of type 'array'"

    def test_arguments_none_vale_como_vazio(self):
        assert _chamar(_executar_dobro, None).text.startswith("Input validation error:")

    def test_validar_entrada_devolve_none_quando_casa(self):
        assert validar_entrada({"n": 1}, CATALOGO["t_ok"]["inputSchema"]) is None


class TestSaida:
    def test_dict_fora_do_schema(self):
        env = _chamar(lambda n, a: {"dobro": "dois"}, {"n": 1})
        assert env == Envelope(
            text="Output validation error: 'dois' is not of type 'integer'",
            structured=None,
            is_error=True,
        )

    def test_resultado_que_nao_e_dict(self):
        env = _chamar(lambda n, a: ["lista"], {"n": 1})
        assert env == Envelope(text=ERRO_SEM_ESTRUTURA, structured=None, is_error=True)

    def test_sem_output_schema_nao_valida(self):
        assert validar_saida(["qualquer"], None) is None


class TestErros:
    def test_erro_de_fronteira_sai_compacto(self):
        payload = {"error": "Caminho nao encontrado: ç", "exit_code": 2}
        env = _chamar(lambda n, a: payload, {"n": 1})
        assert env == Envelope(
            text='{"error":"Caminho nao encontrado: ç","exit_code":2}',
            structured=None,
            is_error=True,
        )

    def test_erro_de_fronteira_nao_passa_pela_validacao_de_saida(self):
        recusa = {"error": "x", "exit_code": 3, "error_code": "UNAUTHORIZED"}
        env = _chamar(lambda n, a: recusa, {"n": 1})
        assert json.loads(env.text) == {"error": "x", "exit_code": 3, "error_code": "UNAUTHORIZED"}

    def test_excecao_vira_str(self):
        def executar(name: str, arguments: dict[str, Any]) -> Any:
            raise KeyError("ferramenta desconhecida")

        env = _chamar(executar, {"n": 1})
        assert env == Envelope(text="'ferramenta desconhecida'", structured=None, is_error=True)

    def test_fora_do_catalogo_recusa_antes_de_validar(self):
        env = envelope_da_chamada("t_escondida", {"lixo": 1}, CATALOGO, "http", _executar_dobro)
        assert env.is_error and env.structured is None
        assert json.loads(env.text) == {
            "error": (
                "ferramenta indisponivel no transporte 'http': t_escondida. "
                "Use --transport stdio."
            ),
            "exit_code": 2,
        }


def test_modulo_nao_importa_o_sdk():
    arvore = ast.parse(MODULO.read_text(encoding="utf-8"))
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])
    assert "mcp" not in importados
