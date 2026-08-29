"""O span de uma chamada de tool: quantos bytes ela poe na janela de contexto.

POR QUE AQUI. `adapters/tools.py:call_tool` e o despacho unico -- as 58 tools
passam por ele, `adapters/mcp.py` entra por ele, e e onde a cadeia de
autorizacao ja morde. Um ponto de instrumentacao, e nao um por handler.

O QUE ELE MEDE, E O QUE NAO. `payload_bytes` sao os bytes da serializacao
canonica do dicionario que o despacho devolveu -- provavel e reproduzivel. NAO
sao "o que o modelo viu": o host reserializa com espacamento proprio, e afirmar
que sao o mesmo numero seria a mentira confortavel desta fase. Por isso a
formula viaja no proprio span, em `payload_basis`.

TOKEN E CUSTO FICAM VAZIOS. Resposta de tool tem byte; token de provider e do
host, e chamada local nao tem tabela de preco. Vazio aqui significa "nao se
aplica", e nao "deu zero".

NUNCA DERRUBA A CHAMADA. Ledger indisponivel -- disco cheio, SQLite travado,
diretorio sem permissao -- e a tool devolve o resultado do handler do mesmo
jeito. Instrumentacao que quebra o produto e defeito. Isso vale tambem para a
CONSTRUCAO do proprio store: `SQLiteTraceStore.__init__` chama `mkdir` no
diretorio pai, e se esse caminho ja existe como ARQUIVO (nao diretorio), o
`mkdir` levanta ali mesmo, antes de qualquer escrita. Por isso o try/except
cobre a construcao, e nao so `save_trace`.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from sparkforge.observability.store import SQLiteTraceStore
from sparkforge.observability.tracer import ExecutionTrace, TraceSpan

PAYLOAD_BASIS = 'len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))'

# O host define este nome quando quer que os spans de varias chamadas caiam na
# mesma tarefa. Sem ele, cada processo tem o seu -- e a agregacao por tarefa
# recusa por nome, em vez de somar spans de investigacoes diferentes.
_ENV_RUN_ID = "SPARKFORGE_RUN_ID"


def payload_bytes(resultado: dict[str, Any]) -> int:
    """Os bytes da serializacao canonica. A formula esta em `PAYLOAD_BASIS`."""
    return len(json.dumps(resultado, ensure_ascii=False, default=str).encode("utf-8"))


def declared_item_count(resultado: dict[str, Any]) -> int | None:
    """A contagem que o PROPRIO payload declara, nunca uma varredura.

    Varrer as listas do dicionario para adivinhar "quantos itens" mediria o que
    a adivinhacao acertou: a resposta de `analyze` tem `items` E `unresolved_at`,
    e as duas sao listas. `returned_count` e declarado pelo produtor.
    """
    valor = resultado.get("returned_count")
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


class ContextLedger:
    """Grava um span por chamada de tool. Falha de escrita nao propaga."""

    def __init__(self, db_path: Path | None = None, run_id: str | None = None) -> None:
        self.run_id = run_id or os.environ.get(_ENV_RUN_ID) or f"run_{uuid.uuid4().hex[:12]}"
        try:
            self._store: SQLiteTraceStore | None = SQLiteTraceStore(db_path=db_path)
        except Exception:  # noqa: BLE001,S110 -- medicao nunca derruba a chamada
            self._store = None

    def record(
        self,
        *,
        name: str,
        resultado: dict[str, Any],
        detail_level: str,
        outcome: str,
        start_time: float,
    ) -> None:
        if self._store is None:
            return
        span = TraceSpan(
            span_id=f"span_{uuid.uuid4().hex[:8]}",
            run_id=self.run_id,
            parent_span_id=None,
            name=name,
            component_type="tool",
            start_time=start_time,
            end_time=time.time(),
            status="ok" if outcome == "ok" else "error",
            payload_bytes=payload_bytes(resultado),
            payload_basis=PAYLOAD_BASIS,
            detail_level=detail_level,
            item_count=declared_item_count(resultado),
            outcome=outcome,
        )
        trace = ExecutionTrace(
            run_id=self.run_id,
            task_description="tool calls",
            start_time=start_time,
            spans=[span],
        )
        try:
            self._store.save_trace(trace)
        except Exception:  # noqa: BLE001,S110 -- medicao nunca derruba a chamada
            pass

    def spans_of(self, run_id: str) -> list[dict[str, Any]]:
        """Os spans de um run, para leitura. `[]` quando nao ha nada gravado."""
        if self._store is None:
            return []
        try:
            trace = self._store.get_trace(run_id)
        except Exception:  # noqa: BLE001 -- leitura de ledger e best-effort igual
            return []
        return list(trace["spans"]) if trace else []
