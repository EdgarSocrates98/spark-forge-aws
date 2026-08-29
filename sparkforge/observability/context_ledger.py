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

BUFFER EM MEMORIA, NAO ESCRITA POR CHAMADA. Medido com store real: gravar um
span por chamada custa ~6ms, dominado pelo fsync do commit do SQLite (nao pela
abertura de conexao -- reusar a conexao so baixa para ~4.4ms). Numa sessao MCP
de centenas de chamadas isso vira segundos de latencia sincrona no caminho
quente, e pagar fsync so para medir contexto nao e aceitavel. Por isso
`record()` so monta o span e guarda na lista em memoria; quem grava e
`flush()`, uma vez, no fim do processo (`atexit`).

O QUE SE PERDE. Processo morto por `SIGKILL` (ou `os._exit`, ou queda de
energia) nao chama `atexit`, e os spans ainda no buffer somem -- telemetria
perdida, e nao chamada de tool quebrada. Essa e a troca deliberada: perder a
MEDICAO de um processo morto abruptamente e aceitavel; atrasar toda chamada de
tool com fsync sincrono para nao perde-la, nao. Quem quiser garantia mais
forte pode chamar `flush()` manualmente em pontos de checkpoint -- o metodo e
publico e idempotente com buffer vazio.

NUNCA DERRUBA A CHAMADA. Ledger indisponivel -- disco cheio, SQLite travado,
diretorio sem permissao, ou o proprio `resultado` carregando um valor que
`json.dumps` recusa -- e a tool devolve o resultado do handler do mesmo jeito.
Instrumentacao que quebra o produto e defeito. Por isso `record()` protege a
MONTAGEM do span (que chama `payload_bytes`, que pode levantar `TypeError`
sobre um payload nao serializavel) com o MESMO try/except que protegeria uma
escrita -- falhar ao MEDIR se comporta como falhar ao GRAVAR: as duas sao
"perdi o dado", nunca "quebrei a tool". A construcao do `SQLiteTraceStore`
recebe o mesmo tratamento dentro de `flush()`, porque ela faz `mkdir` no
diretorio pai e levanta ali mesmo se esse caminho ja existe como ARQUIVO.
"""
from __future__ import annotations

import atexit
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
    """Os bytes da serializacao canonica. A formula esta em `PAYLOAD_BASIS`.

    SEM `default=str`, DE PROPOSITO. `payload_basis` existe para que quem
    reproduza a conta pelo texto chegue no mesmo numero -- e o texto nao
    menciona `default=str`. Adicionar o parametro sem atualizar a constante
    faria a base declarada mentir sobre a formula real; a base so pode dizer
    a verdade se o codigo daqui bater com ela.

    Handler que devolve `Path`/`datetime`/`Decimal` e defeito de handler, e
    `default=str` esconderia isso atras de `"<Path object at 0x...>"` dentro
    do numero em vez de deixar o `TypeError` apontar para a causa. Este
    `TypeError`, quando acontece, NAO derruba a chamada de tool: quem chama
    esta funcao (`ContextLedger.record`) o contem no mesmo try/except que
    protege a escrita, porque falhar ao medir e "perdi o dado", nunca
    "quebrei a tool".
    """
    return len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))


def declared_item_count(resultado: dict[str, Any]) -> int | None:
    """A contagem que o PROPRIO payload declara, nunca uma varredura.

    Varrer as listas do dicionario para adivinhar "quantos itens" mediria o que
    a adivinhacao acertou: a resposta de `analyze` tem `items` E `unresolved_at`,
    e as duas sao listas. `returned_count` e declarado pelo produtor.
    """
    valor = resultado.get("returned_count")
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


class ContextLedger:
    """Acumula spans em memoria e descarrega tudo de uma vez em `flush()`.

    `record()` nunca toca disco -- so monta o `TraceSpan` e anexa a lista.
    Isso e o que torna a instrumentacao barata o bastante para viver no
    caminho quente de `call_tool`. Ver a docstring do modulo para a medicao
    que motivou a troca e o que se perde num `SIGKILL`.
    """

    def __init__(self, db_path: Path | None = None, run_id: str | None = None) -> None:
        self.run_id = run_id or os.environ.get(_ENV_RUN_ID) or f"run_{uuid.uuid4().hex[:12]}"
        self._db_path = db_path
        self._store: SQLiteTraceStore | None = None
        self._buffer: list[TraceSpan] = []
        # `atexit` e o gatilho do flush automatico -- ver docstring do modulo
        # para o que se perde quando o processo nao chega a rodar isto
        # (SIGKILL, queda de energia). Registrar aqui, e nao so na primeira
        # `record()`, garante que um ledger criado e nunca usado ainda assim
        # tenta descarregar o que acumulou (buffer vazio e um `flush()` que
        # nao faz nada).
        atexit.register(self.flush)

    def record(
        self,
        *,
        name: str,
        resultado: dict[str, Any],
        detail_level: str,
        outcome: str,
        start_time: float,
    ) -> None:
        """Monta o span e guarda em memoria. Nunca toca disco, nunca derruba a chamada.

        A MONTAGEM do span entra no try/except, e nao so uma escrita que nao
        existe mais aqui: `payload_bytes(resultado)` roda dentro do
        `TraceSpan(...)`, e um `resultado` com valor nao serializavel (um
        handler devolvendo `Path`/`datetime` seria defeito, mas defeito de
        handler nao pode virar defeito de instrumentacao) faz isso levantar
        `TypeError` ANTES de qualquer escrita. Falhar ao MONTAR o span se
        comporta como falhar ao GRAVAR: as duas sao "perdi a medicao", nunca
        "quebrei a chamada de tool".
        """
        try:
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
            self._buffer.append(span)
        except Exception:  # noqa: BLE001,S110 -- medir nunca derruba a chamada
            pass

    def flush(self) -> None:
        """Descarrega o buffer inteiro numa transacao so.

        Chamado por `atexit` no fim do processo, e pode ser chamado a mao em
        pontos de checkpoint por quem quiser garantia mais forte que "no fim
        do processo". `start_time` da trace e o do PRIMEIRO span do buffer
        (a ordem de chegada, nao a ultima chamada): antes do buffer, cada
        `record()` fazia `INSERT OR REPLACE` na mesma linha de `traces`, e a
        linha sobrevivente ficava com o `start_time` da ULTIMA chamada,
        `end_time` sempre `NULL` e `status` sempre `"running"` -- descrevendo
        errado quando o run comecou e nunca registrando que ele terminou.
        Com um `flush()` por processo isso deixa de ser possivel: ha uma
        trace so, com o inicio verdadeiro e o desfecho `"completed"`.

        Idempotente com buffer vazio -- um ledger criado e nunca usado no
        `atexit` so retorna.
        """
        if not self._buffer:
            return
        spans = self._buffer
        self._buffer = []
        try:
            store = self._ensure_store()
            trace = ExecutionTrace(
                run_id=self.run_id,
                task_description="tool calls",
                start_time=spans[0].start_time,
                end_time=time.time(),
                status="completed",
                spans=spans,
            )
            store.save_trace(trace)
        except Exception:  # noqa: BLE001,S110 -- medicao nunca derruba a chamada
            pass

    def _ensure_store(self) -> SQLiteTraceStore:
        """Constroi o store preguicosamente, so quando ha algo para gravar.

        `SQLiteTraceStore.__init__` faz `mkdir` no diretorio pai -- e se esse
        caminho ja existe como ARQUIVO (nao diretorio), o `mkdir` levanta ali
        mesmo, antes de qualquer escrita. Por isso esta construcao tambem
        entra no try/except de quem chama, e nao so `save_trace`.
        """
        if self._store is None:
            self._store = SQLiteTraceStore(db_path=self._db_path)
        return self._store

    def spans_of(self, run_id: str) -> list[dict[str, Any]]:
        """Os spans de um run: os que ainda estao no BUFFER mais os que ja
        foram para o disco. Sem as duas fontes, um teste que grava e le antes
        do `flush()` veria lista vazia -- e `record()` de proposito nao
        grava mais nada sincronamente."""
        em_buffer = [s.to_dict() for s in self._buffer if s.run_id == run_id]
        em_disco: list[dict[str, Any]] = []
        if self._store is not None:
            try:
                trace = self._store.get_trace(run_id)
            except Exception:  # noqa: BLE001 -- leitura de ledger e best-effort igual
                trace = None
            if trace:
                em_disco = list(trace["spans"])
        return em_disco + em_buffer
