"""O relatorio de contexto: o que esta execucao poe na janela.

COMPOE, nao mede. Os bytes vem do ledger que `call_tool` alimenta; a superficie
em repouso vem de `observability/surface.py`; o token de provider, quando
existe, vem do transcript do host. Este modulo soma e agrupa, e nada mais.

DUAS UNIDADES QUE NAO SE SOMAM. Byte de payload e o que o SparkForge produziu;
token de provider e o que o host gastou. Eles aparecem lado a lado e nunca no
mesmo total -- somar os dois daria um numero que nao mede nada.

O QUE ELE RECUSA: custo em dolar (chamada local nao tem tabela de preco) e
estimativa de token por divisao de bytes (o `len//4` serve de heuristica interna,
nao pode sair com o nome de token).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.collect.host_usage import read_host_usage
from sparkforge.observability.context_ledger import ContextLedger
from sparkforge.observability.surface import measure_surface


def build_context_report(
    ledger: ContextLedger,
    *,
    run_id: str,
    host_transcript: Path | str | None = None,
) -> dict[str, Any]:
    """Agrupa os spans de `run_id` e poe a superficie e o host ao lado."""
    spans = ledger.spans_of(run_id)
    lacunas: list[dict[str, Any]] = []

    por_tool: dict[str, dict[str, Any]] = {}
    efeito: dict[str, dict[str, int]] = {}
    for span in spans:
        nome = str(span["name"])
        alvo = por_tool.setdefault(nome, {"calls": 0, "payload_bytes": 0, "outcomes": {}})
        alvo["calls"] += 1
        alvo["payload_bytes"] += int(span["payload_bytes"] or 0)
        desfecho = str(span["outcome"] or "ok")
        alvo["outcomes"][desfecho] = alvo["outcomes"].get(desfecho, 0) + 1

        nivel = str(span["detail_level"] or "")
        por_nivel = efeito.setdefault(nome, {})
        por_nivel[nivel] = por_nivel.get(nivel, 0) + int(span["payload_bytes"] or 0)

    if not spans:
        lacunas.append({"reason": "run_unresolved", "count": 1})

    uso_do_host = None
    if host_transcript is not None:
        uso_do_host = read_host_usage(host_transcript)
    else:
        lacunas.append({"reason": "tokens_unresolved", "count": 1})

    return {
        "run_id": run_id,
        "by_tool": por_tool,
        # A frase "detail_level reduz" esta publicada e nunca foi medida. Aqui
        # ela vira numero: bytes por nivel pedido, por tool. O relatorio nao
        # afirma qual e menor -- ele mostra os dois.
        "detail_level_effect": efeito,
        "surface": measure_surface(),
        "host_usage": uso_do_host,
        "unresolved": lacunas,
    }
