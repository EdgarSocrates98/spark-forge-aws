from __future__ import annotations

from sparkforge_aws.adapters.mcp import tools_do_transporte
from sparkforge_aws.adapters.tools import TOOLS, call_tool


def test_full_and_compact_surfaces_have_declared_sizes() -> None:
    # 141 -> 143 em 2026-10-05: `agentops_timeline` e `agentops_critical_path`
    # (FASE 10 do prompt_evo_runtime) -- aditivo, compact continua 7.
    # 143 -> 145 em 2026-10-08 (`d33d5c74`, Graph Studio): `graph_view` e
    # `graph_status` projetam o indice de codigo; o commit nao atualizou este
    # lock nem `docs/surface.lock.json` -- drift achado pela suite, nao
    # decisao de esconder tool. HTTP/full fica em 144: `code_read` continua
    # fora por depender do indice local.
    # 145 -> 146 em 2026-10-16 (FASE 1 §1.2): `sparkforge_aws_ai` observa o
    # estado do host (detect/versao/auth/integracao); read-only, nunca lanca
    # processo. HTTP/full sobe para 145 na mesma medida.
    # 146 -> 148 em 2026-10-20: `knowledge_list` e `knowledge_search` leem o
    # conhecimento versionado na raiz resolvida; read-only. HTTP/full 147.
    assert len(tools_do_transporte("stdio", "full")) == 148
    assert len(tools_do_transporte("stdio", "compact")) == 7
    assert len(tools_do_transporte("http", "compact")) == 7


def test_gateway_envelope_is_shared_and_provider_tokens_remain_separate() -> None:
    payload = call_tool(
        "sparkforge_aws_context_start",
        {"intent": "Glue FGAC", "profile": "economy", "max_bytes": 6000},
    )
    assert payload["schema_version"] == 1
    assert "execution_plan" in payload
    assert "context_tree" in payload
    assert payload["context_tree"]["tokens"]["status"] == "unresolved"
    assert payload["provider_tokens"] is None
    assert "sparkforge_aws_context_start" in TOOLS
