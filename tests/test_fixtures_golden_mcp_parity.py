"""O servidor MCP sob o SDK 2.x contra o golden que o SDK 1.29 produziu.

`fixtures/mcp_parity/` (o `FIXTURES` abaixo) foi gravado UMA vez, com o 1.29 instalado, por
`scripts/mcp_parity.py snapshot` (ver `meta.json`). Este teste liga o servidor
de hoje em processo e compara:

* no handshake LEGADO, o JSON cru do fio -- o mesmo que um cliente da era
  1.x recebe. A unica diferenca aceita e `outputSchema.type = "object"` nas
  tools cujo schema e `oneOf` de objetos: o spec `2025-06-18` exige o campo, o
  SDK 2.x confere, e sem ele o `tools/list` inteiro falhava. O conteudo de
  toda chamada da amostra -- texto, `structuredContent`, `isError` -- tem de
  bater byte a byte;
* na era `2026-07-28`, o mesmo conteudo, com o envelope da era separado e
  conferido a parte: `resultType`, o carimbo `_meta.serverInfo` e as dicas de
  cache de `tools/list`.

A allowlist e fechada. Campo novo que o SDK passar a mandar, e que nao esteja
aqui, derruba o teste -- e quem o aceitar escreve o motivo.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp", reason="SDK do MCP e extra opcional")

from sparkforge.adapters.mcp import _TTL_TOOLS_LIST_MS, _versao_do_pacote  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "mcp_parity"


def _carregar_script() -> Any:
    """`scripts/mcp_parity.py` pelo caminho, sem por a raiz no `sys.path`.

    Este modulo tambem roda no gate de wheel (`verify_wheel.py` coleta todo
    `test_fixtures_*.py`), onde a raiz do repositorio no `sys.path` faria o
    `sparkforge` do repositorio vencer o instalado. La o extra `mcp` nao e
    instalado e o `importorskip` acima pula antes de chegar aqui.
    """
    spec = importlib.util.spec_from_file_location("mcp_parity", ROOT / "scripts" / "mcp_parity.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


mcp_parity = _carregar_script()

if mcp_parity.mcp_major() < 2:
    pytest.skip("paridade e cobrada contra o SDK 2.x", allow_module_level=True)

# Caminho -> motivo. Unico diff aceito contra o golden do 1.29.
_OUTPUT_TYPE = re.compile(r"^\$\.tools_list\.(stdio|http)\.tools\[\d+\]\.outputSchema\.type$")
ALLOWLIST_MOTIVO = {
    _OUTPUT_TYPE.pattern: (
        "spec 2025-06-18 exige outputSchema.type; o SDK 2.x confere no handshake legado. "
        "Os ramos do oneOf ja eram objeto, entao o conjunto aceito nao muda."
    ),
}

# Envelope da era 2026-07-28, conferido a parte e nunca comparado ao golden.
ENVELOPE_DA_ERA = ("_meta", "resultType", "ttlMs", "cacheScope")

# Tools que entraram DEPOIS do golden (gravado sob o 1.29 com 86 tools). O golden
# prova a migracao de SDK e fica congelado; regrava-lo sob o 2.x apagaria a
# referencia. Tool nova entra aqui com data e motivo, e a comparacao do golden
# cobre so as tools que ele conhece. Uma tool nova FORA desta lista derruba
# `test_toda_tool_nova_esta_declarada`.
NOVAS_DEPOIS_DO_GOLDEN = {
    "sparkforge_report_github": "2026-09-11: projecao de findings para SARIF e resumo de PR",
    "sparkforge_telemetry_export": "2026-09-11: spans de tool e transcript do host em OTLP/JSON",
}


def _nomes(lista: dict[str, Any]) -> list[str]:
    return [tool["name"] for tool in lista["tools"]]


def _so_do_golden(coleta: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    """A coleta com `tools/list` restrito as tools que o golden conhece."""
    listas = {}
    for transporte, lista in coleta["tools_list"].items():
        conhecidas = set(_nomes(golden["tools_list"][transporte]))
        listas[transporte] = {
            **lista,
            "tools": [t for t in lista["tools"] if t["name"] in conhecidas],
        }
    return {**coleta, "tools_list": listas}


def _fora_da_allowlist(difs: list[tuple[str, Any, Any]]) -> list[tuple[str, Any, Any]]:
    return [
        (caminho, antes, agora)
        for caminho, antes, agora in difs
        if not (_OUTPUT_TYPE.match(caminho) and antes == "<ausente>" and agora == "object")
    ]


def _sem_envelope(resultado: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in resultado.items() if k not in ENVELOPE_DA_ERA}


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    return mcp_parity.carregar_golden()


@pytest.fixture(scope="module")
def legado() -> dict[str, Any]:
    return mcp_parity.coletar("legacy")


@pytest.fixture(scope="module")
def moderno() -> dict[str, Any]:
    return mcp_parity.coletar("auto")


def test_golden_foi_gerado_pelo_1x(golden):
    assert golden["meta"]["mcp"].startswith("1.")
    assert golden["meta"]["regenerado_sob_2x"] is False
    assert golden["meta"]["amostra"] == [item["id"] for item in mcp_parity.AMOSTRA]


def test_contagem_do_catalogo(legado, golden):
    novas = len(NOVAS_DEPOIS_DO_GOLDEN)
    assert len(golden["tools_list"]["stdio"]["tools"]) == 86
    assert len(golden["tools_list"]["http"]["tools"]) == 85
    assert len(legado["tools_list"]["stdio"]["tools"]) == 86 + novas
    assert len(legado["tools_list"]["http"]["tools"]) == 85 + novas


def test_toda_tool_nova_esta_declarada(legado, golden):
    for transporte in ("stdio", "http"):
        novas = set(_nomes(legado["tools_list"][transporte])) - set(
            _nomes(golden["tools_list"][transporte])
        )
        assert novas == set(NOVAS_DEPOIS_DO_GOLDEN), transporte
    assert all(motivo.strip() for motivo in NOVAS_DEPOIS_DO_GOLDEN.values())


class TestHandshakeLegado:
    def test_so_o_type_do_output_schema_difere(self, legado, golden):
        difs = mcp_parity.diff_contra_golden(_so_do_golden(legado, golden))
        assert _fora_da_allowlist(difs) == []

    def test_o_diff_aceito_tem_o_tamanho_medido(self, legado, golden):
        difs = mcp_parity.diff_contra_golden(_so_do_golden(legado, golden))
        por_transporte = {t: sum(f".{t}." in c for c, _, _ in difs) for t in ("stdio", "http")}
        assert por_transporte == {"stdio": 77, "http": 76}

    def test_toda_chamada_bate_byte_a_byte(self, legado, golden):
        for chave, esperado in golden["calls"].items():
            assert legado["calls"][chave]["result"] == esperado["result"], chave

    def test_o_fio_legado_nao_carrega_envelope_novo(self, legado):
        for transporte in ("stdio", "http"):
            assert set(legado["tools_list"][transporte]) == {"tools"}
        for chamada in legado["calls"].values():
            assert not set(chamada["result"]) & set(ENVELOPE_DA_ERA)


class TestEra2026:
    def test_conteudo_igual_ao_legado(self, moderno, legado):
        for transporte in ("stdio", "http"):
            lista = moderno["tools_list"][transporte]
            assert _sem_envelope(lista) == legado["tools_list"][transporte]
        for chave, chamada in legado["calls"].items():
            assert _sem_envelope(moderno["calls"][chave]["result"]) == chamada["result"], chave

    def test_carimbo_so_com_nome_e_versao(self, moderno):
        esperado = {"name": "sparkforge", "version": _versao_do_pacote()}
        for chamada in moderno["calls"].values():
            carimbo = chamada["result"]["_meta"]["io.modelcontextprotocol/serverInfo"]
            assert carimbo == esperado

    def test_tools_list_leva_a_dica_de_cache(self, moderno):
        for transporte in ("stdio", "http"):
            lista = moderno["tools_list"][transporte]
            assert lista["ttlMs"] == _TTL_TOOLS_LIST_MS
            assert lista["cacheScope"] == "public"
            assert lista["resultType"] == "complete"


def test_allowlist_tem_motivo():
    assert all(motivo.strip() for motivo in ALLOWLIST_MOTIVO.values())
