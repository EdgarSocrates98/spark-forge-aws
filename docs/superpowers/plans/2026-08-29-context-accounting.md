# Contabilidade de contexto — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir, em byte exato, o que o SparkForge põe na janela de contexto — a resposta de cada chamada de tool, o catálogo em repouso, a tarefa inteira e o usage que o host registrou — sem inventar token nem custo.

**Architecture:** Um ponto de instrumentação em `adapters/tools.py:call_tool` (o despacho único por onde as 58 tools passam) alimentando o `SQLiteTraceStore` que já existe e está vazio; um módulo de medição estática do catálogo com lock versionado; um leitor de transcript do host no molde do `collect *`; e um verbo de topo `economy report` que compõe sobre o ledger.

**Tech Stack:** Python 3, `pytest`, `sqlite3` (stdlib). Spec: [`../specs/2026-08-29-context-accounting-design.md`](../specs/2026-08-29-context-accounting-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Lint ruff `E,F,I,UP,B,S`, linha máxima 100 (config do `pyproject.toml`). Rode `python -m ruff check <arquivos que você tocou>` antes de cada commit.
- Commit em português, Conventional Commits, via `git commit -F <arquivo>`. **Mensagem via heredoc para um arquivo**, nunca `printf` de string longa — já produziu byte NUL e o commit foi recusado.
- **Não rode a suíte inteira num processo só.** Ela leva 20 a 73 minutos, e morre quando roda como tarefa de background. Rode os módulos alvo de cada tarefa; a verificação ampla fica na Task 8, em lotes.
- Não faça `git add` dos untracked pré-existentes na raiz (`prompt_*.md`, `*.docx`, `Claude`, `bash.exe.stackdump`). **`prompt_evo_forge.md` não entra em commit nenhum.**
- Verbo de topo novo exige, no mesmo commit: `_core.py`, `cli.py`, `tools.py`, `manifest.json`, `parity.yaml` e a citação num coordenador de `agents/` — senão `test_capability_parity.py`, `test_docs_coverage.py` e `test_agent_coverage.py` reprovam separado.

**APIs reais que este plano consome** (medidas em 2026-08-29):

```
sparkforge.observability.tracer:
  TraceSpan(span_id, run_id, parent_span_id, name, component_type, start_time,
            end_time=None, input_tokens=0, output_tokens=0, cached_tokens=0,
            estimated_cost_usd=0.0, status="ok", metadata={})
    .duration_seconds() -> float
    .to_dict() -> dict            # asdict + duration_seconds
  ExecutionTrace(run_id, task_description, start_time, end_time=None,
                 profile="eco", status="running", spans=[])
    .total_tokens() / .total_cost_usd() / .to_dict()
  AgentOpsTracker.start_trace(task_description, profile="eco") -> ExecutionTrace
                 .start_span(trace, name, component_type, parent_span_id=None,
                             metadata=None) -> TraceSpan
                 .end_span(span, input_tokens=0, output_tokens=0, cached_tokens=0,
                           estimated_cost_usd=0.0, status="ok") -> None
                 .finish_trace(trace, status="completed") -> None

sparkforge.observability.store:
  SQLiteTraceStore(db_path=None)      # default: Path.cwd()/".sparkforge"/"traces.db"
    .save_trace(trace) -> None        # INSERT OR REPLACE em `traces` e `spans`
    .get_trace(run_id) -> dict | None

sparkforge.adapters.tools:
  TOOLS: dict[str, dict]              # 58 hoje
  _HANDLERS: dict[str, Callable]
  call_tool(name, arguments, *, policy=None) -> dict
    # quatro caminhos de retorno: recusa UNAUTHORIZED, CodeIndexError,
    # AdapterError, e o sucesso do handler

Resposta tipica de tool que devolve facts (medida em sparkforge_analyze_pyspark):
  chaves: by_kind, filters_applied, items, next_cursor, returned_count,
          total_count, unresolved, unresolved_at
  -> `returned_count` e declarado PELO PROPRIO payload; nao ha necessidade de
     adivinhar contagem varrendo listas.
```

**Desvio do spec, decidido antes de começar e registrado aqui.** O spec (§4.1)
diz que `estimated_cost_usd` sai de `TraceSpan`. Medido: `tests/test_observability.py:13`
e `:20` chamam `end_span(..., estimated_cost_usd=...)` para spans de **modelo**,
onde custo derivado de um tier com preço documentado é legítimo. Remover o campo
mataria junto o caso legítimo. O plano mantém o campo e o **condiciona**: só pode
ser diferente de zero quando `cost_basis` nomear a fonte do preço, e span de tool
deixa os dois vazios. Isso preserva o que o spec queria — nenhum número inventado —
sem quebrar o caso que já existe.

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/observability/context_ledger.py` | Abrir e fechar o span de uma chamada de tool; medir bytes; nunca deixar erro escapar |
| `sparkforge/observability/surface.py` | Medir o catálogo em repouso: schemas, skills, knowledge |
| `sparkforge/collect/host_usage.py` | Ler o transcript do host e extrair usage; recusar formato desconhecido |
| `sparkforge/economy/report.py` | Compor o relatório sobre o ledger |
| `docs/surface.lock.json` | Os números medidos do catálogo em repouso |
| `scripts/check_surface_lock.py` | O gate: mede e compara com o lock |
| `tests/test_context_ledger.py` | Testes do span por chamada |
| `tests/test_observability_surface.py` | Testes da medição estática |
| `tests/test_collect_host_usage.py` | Testes do leitor de transcript |
| `tests/test_economy_report.py` | Testes do relatório |
| `tests/test_surface_lock.py` | O gate como teste |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/observability/tracer.py` | `TraceSpan` ganha `payload_bytes`, `payload_basis`, `detail_level`, `item_count`, `outcome`, `cost_basis`; `end_span` ganha `cost_basis` e recusa custo sem base |
| `sparkforge/observability/store.py` | As seis colunas novas em `spans` |
| `sparkforge/adapters/tools.py` | `call_tool` abre e fecha o span nos quatro caminhos; declara a tool `sparkforge_economy_report` |
| `sparkforge/adapters/_core.py`, `cli.py` | O verbo `economy report` |
| `manifest.json`, `parity.yaml`, `agents/spark-performance-architect.md` | A tool nova |
| `tests/test_observability.py` | As duas chamadas de `end_span` passam a informar `cost_basis` |

---

## Task 1: Os campos que faltam, e o custo que passa a exigir fonte

**Files:**
- Modify: `sparkforge/observability/tracer.py`
- Modify: `sparkforge/observability/store.py`
- Modify: `tests/test_observability.py`
- Test: `tests/test_context_ledger.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_context_ledger.py`:

```python
"""Testes do span de contexto: o que o SparkForge poe na janela.

Span de tool tem BYTE. Token de provider e do host, e custo em dolar exige uma
fonte de preco -- os dois ficam vazios aqui, e vazio significa "nao se aplica",
nao "deu zero".
"""
from __future__ import annotations

import pytest

from sparkforge.observability.tracer import AgentOpsTracker, TraceSpan


class TestOsCamposNovos:
    def test_a_tool_span_carries_bytes_and_the_formula(self):
        span = TraceSpan(
            span_id="span_1",
            run_id="run_1",
            parent_span_id=None,
            name="sparkforge_analyze_pyspark",
            component_type="tool",
            start_time=0.0,
            payload_bytes=1234,
            payload_basis='len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))',
        )

        assert span.payload_bytes == 1234
        assert "json.dumps" in span.payload_basis
        assert span.to_dict()["payload_bytes"] == 1234

    def test_the_new_fields_default_to_absent_not_zero(self):
        """`detail_level` e `item_count` vazios dizem "a tool nao declarou",
        e nao "veio vazio"."""
        span = TraceSpan(
            span_id="span_1",
            run_id="run_1",
            parent_span_id=None,
            name="sparkforge_case_get",
            component_type="tool",
            start_time=0.0,
        )

        assert span.detail_level == ""
        assert span.item_count is None
        assert span.outcome == "ok"


class TestCustoExigeFonte:
    def test_cost_without_a_basis_is_refused(self):
        """Custo sem fonte e o numero inventado que o subprojeto E recusou."""
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")

        with pytest.raises(ValueError, match="cost_basis"):
            tracker.end_span(span, estimated_cost_usd=0.05)

    def test_cost_with_a_named_basis_is_accepted(self):
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "modelo", "model")

        tracker.end_span(
            span, estimated_cost_usd=0.05, cost_basis="TIER_PRICING:tier_3"
        )

        assert span.estimated_cost_usd == 0.05
        assert span.cost_basis == "TIER_PRICING:tier_3"

    def test_zero_cost_needs_no_basis(self):
        """Zero nao afirma preco nenhum, entao nao precisa de fonte."""
        tracker = AgentOpsTracker()
        trace = tracker.start_trace("t")
        span = tracker.start_span(trace, "tool", "tool")

        tracker.end_span(span)

        assert span.estimated_cost_usd == 0.0
        assert span.cost_basis == ""
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_context_ledger.py -v`
Expected: FAIL com `TypeError: TraceSpan.__init__() got an unexpected keyword argument 'payload_bytes'`

- [ ] **Step 3: Implementar**

Em `sparkforge/observability/tracer.py`, o dataclass `TraceSpan` ganha seis campos
depois de `metadata` (ordem importa: todos têm default, então vão depois dos que já
têm default):

```python
@dataclass
class TraceSpan:
    span_id: str
    run_id: str
    parent_span_id: str | None
    name: str
    component_type: str  # task, routing, context, agent, model, tool, eval, gate
    start_time: float
    end_time: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "ok"  # ok, error
    metadata: dict[str, Any] = field(default_factory=dict)
    # Bytes que ESTE span poe na janela de contexto, e a formula que os produziu.
    # Nao e "o que o modelo viu": o host reserializa com espacamento proprio, e
    # afirmar que sao o mesmo numero seria a mentira confortavel desta fase.
    payload_bytes: int = 0
    payload_basis: str = ""
    # O que a chamada PEDIU. Vazio quando a tool nao aceita o parametro -- vazio
    # aqui significa "nao se aplica", e nao "pediu full".
    detail_level: str = ""
    # `None` e nao `0`: zero item e uma resposta vazia de verdade, e ausencia e a
    # tool que nao declara `returned_count`.
    item_count: int | None = None
    outcome: str = "ok"  # ok, unauthorized, error
    # Custo so pode existir com a fonte do preco nomeada. Ver `end_span`.
    cost_basis: str = ""
```

E `end_span` passa a exigir a base quando há custo:

```python
    def end_span(
        self,
        span: TraceSpan,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        status: str = "ok",
        cost_basis: str = "",
    ) -> None:
        """Fecha o span. Custo diferente de zero EXIGE `cost_basis`.

        Preco sem fonte e o numero inventado que o subprojeto E recusou por
        escrito, e um span de tool nao tem preco nenhum: chamada local nao tem
        tabela publicada. Zero nao afirma preco, entao dispensa a fonte.
        """
        if estimated_cost_usd and not cost_basis:
            raise ValueError(
                f"custo {estimated_cost_usd} sem `cost_basis`: preco sem fonte e "
                f"numero inventado. Nomeie de onde o preco veio (ex.: "
                f"'TIER_PRICING:tier_3') ou deixe o custo em zero."
            )
        span.end_time = time.time()
        span.input_tokens = input_tokens
        span.output_tokens = output_tokens
        span.cached_tokens = cached_tokens
        span.estimated_cost_usd = estimated_cost_usd
        span.cost_basis = cost_basis
        span.status = status
```

Em `sparkforge/observability/store.py`, a tabela `spans` ganha as seis colunas
(no `CREATE TABLE`, depois de `metadata_json` e antes do `FOREIGN KEY`):

```python
                    metadata_json TEXT,
                    payload_bytes INTEGER,
                    payload_basis TEXT,
                    detail_level TEXT,
                    item_count INTEGER,
                    outcome TEXT,
                    cost_basis TEXT,
                    FOREIGN KEY(run_id) REFERENCES traces(run_id)
```

E o `INSERT` de span passa a gravá-las:

```python
                conn.execute(
                    """
                    INSERT OR REPLACE INTO spans (
                        span_id, run_id, parent_span_id, name, component_type,
                        start_time, end_time, duration_seconds, input_tokens, output_tokens,
                        cached_tokens, estimated_cost_usd, status, metadata_json,
                        payload_bytes, payload_basis, detail_level, item_count,
                        outcome, cost_basis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        span.span_id,
                        span.run_id,
                        span.parent_span_id,
                        span.name,
                        span.component_type,
                        span.start_time,
                        span.end_time,
                        span.duration_seconds(),
                        span.input_tokens,
                        span.output_tokens,
                        span.cached_tokens,
                        span.estimated_cost_usd,
                        span.status,
                        json.dumps(span.metadata, default=str),
                        span.payload_bytes,
                        span.payload_basis,
                        span.detail_level,
                        span.item_count,
                        span.outcome,
                        span.cost_basis,
                    ),
                )
```

Em `tests/test_observability.py`, as duas chamadas de `end_span` que informam
custo passam a informar a fonte. Linha 12-13 e 19-20:

```python
    tracker.end_span(
        span1,
        input_tokens=500,
        output_tokens=100,
        cached_tokens=0,
        estimated_cost_usd=0.0002,
        cost_basis="TIER_PRICING:tier_1",
    )
```

```python
    tracker.end_span(
        span2,
        input_tokens=1200,
        output_tokens=300,
        cached_tokens=500,
        estimated_cost_usd=0.0008,
        cost_basis="TIER_PRICING:tier_2",
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_context_ledger.py tests/test_observability.py tests/test_model_and_observability.py -q`
Expected: PASS. Reporte a contagem real.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/observability tests/test_context_ledger.py tests/test_observability.py
git add sparkforge/observability tests/test_context_ledger.py tests/test_observability.py
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(observability): o span ganha byte, e o custo passa a exigir fonte`

---

## Task 2: O span por chamada de tool

**Files:**
- Create: `sparkforge/observability/context_ledger.py`
- Modify: `sparkforge/adapters/tools.py` (`call_tool`)
- Test: `tests/test_context_ledger.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_context_ledger.py`:

```python
class TestOSpanDaChamada:
    def _facts_file(self, tmp_path):
        import json

        destino = tmp_path / "facts.json"
        destino.write_text(json.dumps([]), encoding="utf-8")
        return destino

    def test_a_successful_call_records_the_exact_bytes(self, tmp_path, monkeypatch):
        import json

        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        spans = ledger.spans_of("run_teste")
        assert len(spans) == 1
        esperado = len(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
        assert spans[0]["payload_bytes"] == esperado
        assert spans[0]["name"] == "sparkforge_analyze_pyspark"
        assert spans[0]["component_type"] == "tool"
        assert spans[0]["outcome"] == "ok"

    def test_the_declared_item_count_is_carried_not_guessed(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        span = ledger.spans_of("run_teste")[0]
        assert span["item_count"] == resultado["returned_count"]

    def test_the_requested_detail_level_is_recorded(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        tools.call_tool(
            "sparkforge_analyze_pyspark",
            {"path": str(origem), "detail_level": "summary"},
        )

        assert ledger.spans_of("run_teste")[0]["detail_level"] == "summary"

    def test_a_tool_span_never_carries_provider_tokens_or_cost(
        self, tmp_path, monkeypatch
    ):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        span = ledger.spans_of("run_teste")[0]
        assert span["input_tokens"] == 0
        assert span["output_tokens"] == 0
        assert span["estimated_cost_usd"] == 0.0
        assert span["cost_basis"] == ""


class TestOsTresCaminhosDeErro:
    """Recusa tambem ocupa contexto. Uma investigacao cheia de recusa pareceria
    barata se elas nao fossem contadas."""

    def test_an_adapter_error_records_a_span(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        resultado = tools.call_tool(
            "sparkforge_analyze_pyspark", {"path": str(tmp_path / "nao_existe")}
        )

        assert "error" in resultado
        span = ledger.spans_of("run_teste")[0]
        assert span["outcome"] == "error"
        assert span["payload_bytes"] > 0

    def test_an_unauthorized_call_records_a_span(self, tmp_path, monkeypatch):
        from sparkforge.adapters import tools
        from sparkforge.agents.autonomy import CallPolicy
        from sparkforge.observability.context_ledger import ContextLedger
        from sparkforge.registry.models import ExecutionProfile

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        politica = CallPolicy(
            agent="sf-runtime-specialist",
            allowed_tools=["sparkforge_case_get"],
            profile=ExecutionProfile.ECO,
            root=tmp_path,
        )
        resultado = tools.call_tool(
            "sparkforge_analyze_pyspark", {"path": str(tmp_path)}, policy=politica
        )

        assert resultado.get("error_code") == "UNAUTHORIZED"
        assert ledger.spans_of("run_teste")[0]["outcome"] == "unauthorized"

    def test_an_unknown_tool_records_nothing(self, tmp_path, monkeypatch):
        """`KeyError` de nome desconhecido e contrato de CATALOGO, e acontece
        ANTES do despacho: nao houve payload nenhum para medir."""
        import pytest

        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        with pytest.raises(KeyError):
            tools.call_tool("sparkforge_inexistente", {})

        assert ledger.spans_of("run_teste") == []


class TestLedgerQuebradoNaoQuebraATool:
    """O teste que mais importa: instrumentacao que derruba o produto e
    defeito, nao observabilidade."""

    def test_an_unwritable_ledger_does_not_change_the_result(
        self, tmp_path, monkeypatch
    ):
        from sparkforge.adapters import tools
        from sparkforge.observability.context_ledger import ContextLedger

        impossivel = tmp_path / "arquivo_no_lugar_do_diretorio"
        impossivel.write_text("nao sou diretorio", encoding="utf-8")
        ledger = ContextLedger(db_path=impossivel / "traces.db", run_id="run_teste")
        monkeypatch.setattr(tools, "_LEDGER", ledger)

        origem = tmp_path / "job"
        origem.mkdir()
        (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
        resultado = tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})

        assert "items" in resultado
        assert "error" not in resultado
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_context_ledger.py -k "OSpanDaChamada or Erro or Quebrado" -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.observability.context_ledger'`

- [ ] **Step 3: Implementar**

Crie `sparkforge/observability/context_ledger.py`:

```python
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
jeito. Instrumentacao que quebra o produto e defeito.
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
        self._store = SQLiteTraceStore(db_path=db_path)
        self.run_id = run_id or os.environ.get(_ENV_RUN_ID) or f"run_{uuid.uuid4().hex[:12]}"

    def record(
        self,
        *,
        name: str,
        resultado: dict[str, Any],
        detail_level: str,
        outcome: str,
        start_time: float,
    ) -> None:
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
        try:
            trace = self._store.get_trace(run_id)
        except Exception:  # noqa: BLE001 -- leitura de ledger e best-effort igual
            return []
        return list(trace["spans"]) if trace else []
```

Em `sparkforge/adapters/tools.py`, no topo do módulo (junto dos outros imports):

```python
from sparkforge.observability.context_ledger import ContextLedger
```

e, logo depois de `_HANDLERS`, o ledger do processo:

```python
# Um ledger por processo. E modulo-level de proposito: `call_tool` e chamado de
# lugares que nao tem como carregar estado (a CLI, o servidor MCP, um teste), e
# passar o ledger por parametro obrigaria todos eles a saber que ele existe.
# Teste que queira inspecionar substitui este nome.
_LEDGER = ContextLedger()
```

E `call_tool` passa a medir os quatro caminhos. O corpo inteiro depois do
`KeyError`:

```python
    argumentos = arguments or {}
    detail_level = str(argumentos.get("detail_level") or "")
    inicio = time.time()

    if policy is not None:
        decisao = policy.decide(name, argumentos)
        if not decisao.authorized:
            recusa: dict[str, Any] = {
                "error": f"chamada recusada pela cadeia de autorizacao: {decisao.reason}",
                "exit_code": 2,
                "error_code": "UNAUTHORIZED",
            }
            if decisao.required_approval is not None:
                recusa["required_approval"] = decisao.required_approval.value
            _LEDGER.record(
                name=name,
                resultado=recusa,
                detail_level=detail_level,
                outcome="unauthorized",
                start_time=inicio,
            )
            return recusa

    try:
        resultado = handler(argumentos)
        desfecho = "ok"
    except _core.CodeIndexError as exc:
        resultado = {"error": exc.message, "exit_code": exc.exit_code, **exc.detalhes}
        desfecho = "error"
    except _core.AdapterError as exc:
        resultado = {"error": exc.message, "exit_code": exc.exit_code}
        desfecho = "error"

    _LEDGER.record(
        name=name,
        resultado=resultado,
        detail_level=detail_level,
        outcome=desfecho,
        start_time=inicio,
    )
    return resultado
```

Se `time` ainda não estiver importado em `tools.py`, acrescente `import time`
junto dos outros imports da stdlib.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_context_ledger.py -q`
Expected: PASS.

Depois, a suíte que mais toca `call_tool`:

Run: `python -m pytest tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_harness_authorization.py -q`
Expected: PASS. Se alguma reprovar por causa do ledger, o defeito é do ledger — a
regra é que ele nunca muda o resultado.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/observability sparkforge/adapters/tools.py tests/test_context_ledger.py
git add sparkforge/observability sparkforge/adapters/tools.py tests/test_context_ledger.py
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(observability): um span por chamada de tool, nos quatro caminhos`

---

## Task 3: O catálogo em repouso

**Files:**
- Create: `sparkforge/observability/surface.py`
- Test: `tests/test_observability_surface.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_observability_surface.py`:

```python
"""Testes da medicao estatica: quanto pesa a superficie ANTES de qualquer chamada.

Nao executa tool nenhuma. Le o catalogo, os arquivos de skill e os de knowledge,
e conta byte.
"""
from __future__ import annotations

from sparkforge.observability.surface import measure_surface


class TestAMedidaEstatica:
    def test_the_tool_catalogue_is_measured_per_tool(self):
        medida = measure_surface()
        por_tool = medida["tools"]["by_name"]

        assert "sparkforge_analyze_pyspark" in por_tool
        assert por_tool["sparkforge_analyze_pyspark"] > 0

    def test_the_catalogue_total_is_the_sum_of_its_tools(self):
        medida = measure_surface()

        assert medida["tools"]["total_bytes"] == sum(medida["tools"]["by_name"].values())

    def test_every_skill_on_disk_is_measured(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "skills"
        no_disco = {p.name for p in raiz.iterdir() if p.is_dir()}
        medida = measure_surface()

        assert set(medida["skills"]["by_name"]) == no_disco

    def test_knowledge_is_measured_by_document(self):
        medida = measure_surface()

        assert medida["knowledge"]["document_count"] > 0
        assert medida["knowledge"]["total_bytes"] > 0

    def test_nothing_is_executed(self):
        """A medida le disco. Se ela chamasse uma tool, um `path` inexistente
        derrubaria a medicao -- e o teste abaixo prova que ela nao chama."""
        from sparkforge.adapters import tools

        chamadas = []
        original = tools.call_tool
        try:
            tools.call_tool = lambda *a, **k: chamadas.append(a)  # type: ignore[assignment]
            measure_surface()
        finally:
            tools.call_tool = original  # type: ignore[assignment]

        assert chamadas == []


class TestRecusa:
    def test_an_unreadable_document_is_named_not_skipped(self, tmp_path):
        from sparkforge.observability.surface import measure_directory

        (tmp_path / "bom.md").write_text("conteudo", encoding="utf-8")
        (tmp_path / "ruim.md").write_bytes(b"\xff\xfe invalido \x00")

        medida = measure_directory(tmp_path, "*.md")

        assert medida["by_name"]["bom.md"] == len("conteudo".encode())
        assert "ruim.md" in medida["unresolved"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_observability_surface.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.observability.surface'`

- [ ] **Step 3: Implementar**

Crie `sparkforge/observability/surface.py`:

```python
"""Quanto pesa a superficie do SparkForge ANTES de qualquer chamada.

Tres superficies, e todas sao bytes de disco ou de serializacao -- nada aqui
executa tool, roda suite ou chama modelo. E por isso que esta medida cabe num CI
que hoje nao consegue rodar a suite inteira.

  tools     -- o que `tools/list` devolve, por tool
  skills    -- cada `SKILL.md`
  knowledge -- cada documento de `knowledge/`

O numero de cada uma e o que `docs/surface.lock.json` trava: crescer a superficie
passa a exigir declarar o crescimento, que e o que este repositorio ja faz com
toda alegacao publicada.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SERIALIZATION_BASIS = 'len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))'


def _bytes_of(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))


def measure_directory(root: Path, pattern: str) -> dict[str, Any]:
    """Bytes de cada arquivo que casa `pattern`, e o que nao deu para ler.

    Arquivo ilegivel entra em `unresolved` com o nome: pular em silencio faria a
    superficie parecer menor do que e, que e o erro que esta medida existe para
    nao cometer.
    """
    por_nome: dict[str, int] = {}
    nao_resolvidos: list[str] = []
    for caminho in sorted(root.rglob(pattern)):
        if not caminho.is_file():
            continue
        try:
            por_nome[caminho.name] = len(caminho.read_text(encoding="utf-8").encode("utf-8"))
        except (UnicodeDecodeError, OSError):
            nao_resolvidos.append(caminho.name)
    return {
        "by_name": por_nome,
        "total_bytes": sum(por_nome.values()),
        "document_count": len(por_nome),
        "unresolved": nao_resolvidos,
    }


def measure_tool_catalogue() -> dict[str, Any]:
    """Bytes do que `tools/list` devolve, por tool.

    Le `TOOLS` direto -- e o mesmo objeto que o servidor serializa, e medir a
    partir dele nao exige subir servidor nenhum.
    """
    from sparkforge.adapters.tools import TOOLS

    por_nome = {nome: _bytes_of(declaracao) for nome, declaracao in TOOLS.items()}
    return {
        "by_name": por_nome,
        "total_bytes": sum(por_nome.values()),
        "tool_count": len(por_nome),
        "basis": SERIALIZATION_BASIS,
    }


def measure_skills(root: Path) -> dict[str, Any]:
    """Bytes de cada `SKILL.md`, indexados pelo nome do DIRETORIO.

    `measure_directory` indexaria todos por `SKILL.md`, e um dicionario com a
    mesma chave 44 vezes guardaria uma skill so.
    """
    por_nome: dict[str, int] = {}
    nao_resolvidos: list[str] = []
    for caminho in sorted(root.rglob("SKILL.md")):
        try:
            por_nome[caminho.parent.name] = len(
                caminho.read_text(encoding="utf-8").encode("utf-8")
            )
        except (UnicodeDecodeError, OSError):
            nao_resolvidos.append(caminho.parent.name)
    return {
        "by_name": por_nome,
        "total_bytes": sum(por_nome.values()),
        "document_count": len(por_nome),
        "unresolved": nao_resolvidos,
    }


def measure_surface(root: Path | None = None) -> dict[str, Any]:
    """As tres superficies, medidas sem executar nada."""
    raiz = root or ROOT
    return {
        "tools": measure_tool_catalogue(),
        "skills": measure_skills(raiz / "skills"),
        "knowledge": measure_directory(raiz / "knowledge", "*.md"),
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_observability_surface.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/observability/surface.py tests/test_observability_surface.py
git add sparkforge/observability/surface.py tests/test_observability_surface.py
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(observability): a superficie em repouso, medida sem executar nada`

---

## Task 4: O lock e o gate

**Files:**
- Create: `docs/surface.lock.json`, `scripts/check_surface_lock.py`, `tests/test_surface_lock.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_surface_lock.py`:

```python
"""O gate da superficie: lock, e nao limiar.

Nao existe "20% e demais" que fonte nenhuma publique. O que existe e o numero
medido de hoje: crescer a superficie passa a exigir DECLARAR o crescimento,
igual a `docs/claims.lock.json` ja faz com alegacao publicada.
"""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.observability.surface import measure_surface

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "surface.lock.json"


def _lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


class TestOLockBateComAMedida:
    def test_the_lock_exists_and_declares_its_basis(self):
        lock = _lock()

        assert lock["schema_version"] == 1
        assert "json.dumps" in lock["basis"]

    def test_the_tool_catalogue_matches(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["tools"]["tool_count"] == lock["tools"]["tool_count"]
        assert medida["tools"]["total_bytes"] == lock["tools"]["total_bytes"]

    def test_the_skills_match(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["skills"]["document_count"] == lock["skills"]["document_count"]
        assert medida["skills"]["total_bytes"] == lock["skills"]["total_bytes"]

    def test_the_knowledge_matches(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["knowledge"]["document_count"] == lock["knowledge"]["document_count"]
        assert medida["knowledge"]["total_bytes"] == lock["knowledge"]["total_bytes"]

    def test_nothing_is_unresolved(self):
        """Arquivo ilegivel na superficie e defeito, nao ruido."""
        medida = measure_surface()

        assert medida["skills"]["unresolved"] == []
        assert medida["knowledge"]["unresolved"] == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_surface_lock.py -v`
Expected: FAIL com `FileNotFoundError` em `docs/surface.lock.json`

- [ ] **Step 3: Implementar**

Crie `scripts/check_surface_lock.py`:

```python
#!/usr/bin/env python3
"""Gate da superficie do SparkForge: o que ela pesa antes de qualquer chamada.

Fonte da verdade: `docs/surface.lock.json`. O lock nao e limiar -- ele e o
numero medido de hoje, e crescer a superficie passa a exigir declarar o
crescimento, no mesmo mecanismo de `docs/claims.lock.json`.

Ele mede SEM EXECUTAR NADA, e isso e o ponto: a suite inteira nao cabe num job
de CI (o runner mata com SIGXCPU), entao um gate que dependesse dela nao teria
onde rodar.

Uso:
    python scripts/check_surface_lock.py            # audita; sai 1 se divergir
    python scripts/check_surface_lock.py --update   # regrava o lock medido
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sparkforge.observability.surface import (  # noqa: E402 -- depois do sys.path
    SERIALIZATION_BASIS,
    measure_surface,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "surface.lock.json"

_CAMPOS = (
    ("tools", "tool_count"),
    ("tools", "total_bytes"),
    ("skills", "document_count"),
    ("skills", "total_bytes"),
    ("knowledge", "document_count"),
    ("knowledge", "total_bytes"),
)


def _payload() -> dict:
    medida = measure_surface()
    return {
        "schema_version": 1,
        "basis": SERIALIZATION_BASIS,
        "tools": {
            "tool_count": medida["tools"]["tool_count"],
            "total_bytes": medida["tools"]["total_bytes"],
        },
        "skills": {
            "document_count": medida["skills"]["document_count"],
            "total_bytes": medida["skills"]["total_bytes"],
        },
        "knowledge": {
            "document_count": medida["knowledge"]["document_count"],
            "total_bytes": medida["knowledge"]["total_bytes"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--update", action="store_true", help="Regrava o lock medido.")
    args = parser.parse_args(argv)

    atual = _payload()

    if args.update:
        LOCK.write_text(
            json.dumps(atual, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"lock atualizado: {LOCK.relative_to(ROOT)}")
        return 0

    if not LOCK.is_file():
        print(f"{LOCK.relative_to(ROOT)} nao existe. Rode com --update.", file=sys.stderr)
        return 1

    travado = json.loads(LOCK.read_text(encoding="utf-8"))
    divergencias = [
        f"{secao}.{campo}: lock {travado[secao][campo]}, medido {atual[secao][campo]}"
        for secao, campo in _CAMPOS
        if travado.get(secao, {}).get(campo) != atual[secao][campo]
    ]

    for linha in divergencias:
        print(linha)
    if divergencias:
        print(
            f"{len(divergencias)} divergencia(s). A superficie mudou: rode "
            f"`python scripts/check_surface_lock.py --update` e DECLARE o "
            f"crescimento na mensagem do commit.",
            file=sys.stderr,
        )
        return 1
    print("0 divergencia(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Gere o lock:

```bash
python scripts/check_surface_lock.py --update
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_surface_lock.py -q && python scripts/check_surface_lock.py`
Expected: PASS e `0 divergencia(s).`

Acrescente o passo ao CI, em `.github/workflows/ci.yml`, junto dos outros gates
(depois do passo `vNext claims lastro`):

```yaml
      - name: Surface lock
        run: python scripts/check_surface_lock.py
```

- [ ] **Step 5: Commit**

```bash
python -m ruff check scripts/check_surface_lock.py tests/test_surface_lock.py
git add docs/surface.lock.json scripts/check_surface_lock.py tests/test_surface_lock.py .github/workflows/ci.yml
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(gate): a superficie travada por lock, e nao por limiar`

---

## Task 5: O usage que o host registrou

**Files:**
- Create: `sparkforge/collect/host_usage.py`
- Test: `tests/test_collect_host_usage.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_collect_host_usage.py`:

```python
"""Testes do leitor de usage do host.

E o unico nivel desta fase que le artefato que o SparkForge NAO produz e cujo
formato ele nao controla -- e por isso entra pela porta do `collect *`, com a
mesma disciplina: le o que sabe ler, e recusa por nome o resto.
"""
from __future__ import annotations

import json

from sparkforge.collect.host_usage import read_host_usage


def _transcript(tmp_path, linhas):
    destino = tmp_path / "sessao.jsonl"
    destino.write_text(
        "\n".join(json.dumps(linha) for linha in linhas) + "\n", encoding="utf-8"
    )
    return destino


class TestOFormatoConhecido:
    def test_usage_of_each_assistant_message_is_summed(self, tmp_path):
        caminho = _transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "cache_read_input_tokens": 40,
                        }
                    },
                },
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 200,
                            "output_tokens": 30,
                            "cache_read_input_tokens": 60,
                        }
                    },
                },
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 300
        assert leitura["output_tokens"] == 50
        assert leitura["cached_tokens"] == 100
        assert leitura["message_count"] == 2
        assert leitura["source"] == "claude_code_transcript"

    def test_a_message_without_usage_is_counted_as_a_gap(self, tmp_path):
        caminho = _transcript(
            tmp_path,
            [
                {"type": "assistant", "message": {"usage": {"input_tokens": 10}}},
                {"type": "assistant", "message": {}},
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 10
        assert leitura["unresolved"] == [{"reason": "usage_field_absent", "count": 1}]

    def test_non_assistant_lines_are_ignored_without_a_gap(self, tmp_path):
        """Linha de usuario nao tem usage por natureza -- ignorar nao e lacuna."""
        caminho = _transcript(
            tmp_path,
            [
                {"type": "user", "message": {"content": "oi"}},
                {"type": "assistant", "message": {"usage": {"input_tokens": 10}}},
            ],
        )
        leitura = read_host_usage(caminho)

        assert leitura["message_count"] == 1
        assert leitura["unresolved"] == []


class TestRecusas:
    def test_an_unknown_format_is_refused_by_name(self, tmp_path):
        caminho = tmp_path / "outro_host.json"
        caminho.write_text(json.dumps({"tokens": 123}), encoding="utf-8")

        leitura = read_host_usage(caminho)

        assert leitura["input_tokens"] == 0
        assert leitura["unresolved"] == [
            {"reason": "host_format_unknown", "count": 1}
        ]

    def test_a_missing_file_is_refused_by_name(self, tmp_path):
        leitura = read_host_usage(tmp_path / "nao_existe.jsonl")

        assert leitura["unresolved"] == [{"reason": "transcript_not_found", "count": 1}]

    def test_a_malformed_line_does_not_abort_the_read(self, tmp_path):
        destino = tmp_path / "sessao.jsonl"
        destino.write_text(
            '{"nao valido\n'
            + json.dumps(
                {"type": "assistant", "message": {"usage": {"input_tokens": 7}}}
            )
            + "\n",
            encoding="utf-8",
        )
        leitura = read_host_usage(destino)

        assert leitura["input_tokens"] == 7
        assert {"reason": "malformed_line", "count": 1} in leitura["unresolved"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_collect_host_usage.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.collect.host_usage'`

- [ ] **Step 3: Implementar**

Crie `sparkforge/collect/host_usage.py`:

```python
"""O usage que o HOST registrou -- o unico token de provider que existe aqui.

O SparkForge nao chama provider nenhum: medido, `sparkforge/` nao importa
`anthropic`, `openai`, `bedrock` nem `litellm`. Quem gasta token e o host
executando os agents. Este modulo le o que o host gravou, e por isso entra pela
porta do `collect *` -- a unica parte do projeto que ja le artefato de fora.

A DISCIPLINA E A MESMA DOS COLETORES: le o formato que conhece, e recusa por
NOME o que nao conhece. Um parser adivinhado sobre transcript de outro host
produziria numero com cara de medida.

Formato conhecido: o transcript JSONL do Claude Code, uma mensagem por linha,
com `usage` dentro de `message` nas linhas de assistente.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_CLAUDE_CODE = "claude_code_transcript"


def _vazio(fonte: str, razao: str) -> dict[str, Any]:
    return {
        "source": fonte,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "message_count": 0,
        "unresolved": [{"reason": razao, "count": 1}],
    }


def read_host_usage(path: Path | str) -> dict[str, Any]:
    """Soma o usage das mensagens de assistente de um transcript."""
    caminho = Path(path)
    if not caminho.is_file():
        return _vazio("", "transcript_not_found")

    texto = caminho.read_text(encoding="utf-8", errors="replace")
    entrada = saida = cache = mensagens = 0
    lacunas: Counter[str] = Counter()
    reconheceu = False

    for linha in texto.splitlines():
        limpa = linha.strip()
        if not limpa:
            continue
        try:
            evento = json.loads(limpa)
        except json.JSONDecodeError:
            lacunas["malformed_line"] += 1
            continue
        if not isinstance(evento, dict) or "type" not in evento:
            lacunas["host_format_unknown"] += 1
            continue
        reconheceu = True
        if evento.get("type") != "assistant":
            continue
        uso = (evento.get("message") or {}).get("usage")
        if not isinstance(uso, dict):
            lacunas["usage_field_absent"] += 1
            continue
        entrada += int(uso.get("input_tokens") or 0)
        saida += int(uso.get("output_tokens") or 0)
        cache += int(uso.get("cache_read_input_tokens") or 0)
        mensagens += 1

    return {
        "source": SOURCE_CLAUDE_CODE if reconheceu else "",
        "input_tokens": entrada,
        "output_tokens": saida,
        "cached_tokens": cache,
        "message_count": mensagens,
        "unresolved": [
            {"reason": razao, "count": quantas} for razao, quantas in sorted(lacunas.items())
        ],
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_collect_host_usage.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/collect/host_usage.py tests/test_collect_host_usage.py
git add sparkforge/collect/host_usage.py tests/test_collect_host_usage.py
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(collect): o usage do host, lido do formato que existe e recusado nos outros`

---

## Task 6: O relatório

**Files:**
- Create: `sparkforge/economy/report.py`
- Test: `tests/test_economy_report.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_economy_report.py`:

```python
"""Testes do relatorio de contexto.

Ele compoe sobre o ledger; nao le artefato e nao mede nada por conta propria. O
usage do host, quando existe, aparece AO LADO do byte -- nunca somado a ele,
porque byte de payload e token de provider nao sao a mesma unidade.
"""
from __future__ import annotations

from sparkforge.economy.report import build_context_report
from sparkforge.observability.context_ledger import ContextLedger


def _ledger_com_chamadas(tmp_path, monkeypatch):
    from sparkforge.adapters import tools

    ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste")
    monkeypatch.setattr(tools, "_LEDGER", ledger)
    origem = tmp_path / "job"
    origem.mkdir()
    (origem / "job.py").write_text("df.collect()\n", encoding="utf-8")
    tools.call_tool("sparkforge_analyze_pyspark", {"path": str(origem)})
    tools.call_tool(
        "sparkforge_analyze_pyspark",
        {"path": str(origem), "detail_level": "summary"},
    )
    return ledger


class TestORelatorio:
    def test_payload_is_grouped_by_tool(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        por_tool = relatorio["by_tool"]["sparkforge_analyze_pyspark"]
        assert por_tool["calls"] == 2
        assert por_tool["payload_bytes"] > 0

    def test_the_detail_level_effect_is_reported_whatever_it_is(
        self, tmp_path, monkeypatch
    ):
        """A frase "detail_level reduz" esta publicada e nunca foi medida.

        Este bloco a MEDE. Ele nao afirma que `summary` e menor -- ele reporta
        os dois numeros, e quem le conclui.
        """
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        efeito = relatorio["detail_level_effect"]["sparkforge_analyze_pyspark"]
        assert "" in efeito
        assert "summary" in efeito
        assert all(isinstance(v, int) for v in efeito.values())

    def test_the_surface_at_rest_is_included(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        assert relatorio["surface"]["tools"]["tool_count"] > 0

    def test_host_usage_sits_beside_bytes_never_summed(self, tmp_path, monkeypatch):
        import json

        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        transcript = tmp_path / "sessao.jsonl"
        transcript.write_text(
            json.dumps(
                {"type": "assistant", "message": {"usage": {"input_tokens": 500}}}
            )
            + "\n",
            encoding="utf-8",
        )
        relatorio = build_context_report(
            ledger, run_id="run_teste", host_transcript=transcript
        )

        assert relatorio["host_usage"]["input_tokens"] == 500
        assert "input_tokens" not in relatorio["by_tool"]["sparkforge_analyze_pyspark"]


class TestRecusas:
    def test_a_run_without_spans_is_refused_by_name(self, tmp_path):
        ledger = ContextLedger(db_path=tmp_path / "traces.db", run_id="run_vazio")
        relatorio = build_context_report(ledger, run_id="run_inexistente")

        assert relatorio["by_tool"] == {}
        assert {"reason": "run_unresolved", "count": 1} in relatorio["unresolved"]

    def test_without_a_transcript_there_is_no_host_usage(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        relatorio = build_context_report(ledger, run_id="run_teste")

        assert relatorio["host_usage"] is None
        assert {"reason": "tokens_unresolved", "count": 1} in relatorio["unresolved"]

    def test_nothing_reports_a_dollar_cost(self, tmp_path, monkeypatch):
        ledger = _ledger_com_chamadas(tmp_path, monkeypatch)
        blob = str(build_context_report(ledger, run_id="run_teste")).lower()

        for palavra in ("usd", "cost", "custo"):
            assert palavra not in blob
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_economy_report.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.economy.report'`

- [ ] **Step 3: Implementar**

Crie `sparkforge/economy/report.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_economy_report.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/economy/report.py tests/test_economy_report.py
git add sparkforge/economy/report.py tests/test_economy_report.py
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(economy): o relatorio de contexto, com byte e token lado a lado`

---

## Task 7: A superfície — verbo e tool

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, `manifest.json`, `parity.yaml`, `agents/spark-performance-architect.md`
- Test: `tests/test_adapters_cli.py`, `tests/test_adapters_tools.py`

- [ ] **Step 1: Escrever o teste que falha**

Em `tests/test_adapters_tools.py`, acrescente `"sparkforge_economy_report"` ao
conjunto de `test_the_full_tool_surface_is_declared` (junto de
`"sparkforge_tune"`), e o construtor de argumentos reais em
`_real_output_for` (antes do bloco `if name == "sparkforge_glue_dependency_audit":`):

```python
    if name == "sparkforge_economy_report":
        result = call_tool("sparkforge_economy_report", {"run_id": "run_inexistente"})
        assert result["unresolved"], "a amostra precisa render ao menos uma lacuna"
        return result
```

Em `tests/test_adapters_cli.py`, acrescente ao final:

```python
class TestEconomyReportCommand:
    """`economy report` e verbo de TOPO: compoe sobre o ledger, nao le artefato."""

    def test_an_unknown_run_refuses_by_name(self, capsys):
        from sparkforge.adapters.cli import main

        code = main(["economy", "report", "--run-id", "run_inexistente"])

        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["by_tool"] == {}
        assert {"reason": "run_unresolved", "count": 1} in payload["unresolved"]

    def test_the_surface_at_rest_comes_in_the_payload(self, capsys):
        from sparkforge.adapters.cli import main

        main(["economy", "report", "--run-id", "run_inexistente"])
        payload = json.loads(capsys.readouterr().out)

        assert payload["surface"]["tools"]["tool_count"] > 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_adapters_cli.py -k EconomyReport tests/test_adapters_tools.py -k "surface or economy" -v`
Expected: FAIL — `argument {analyze,...}: invalid choice: 'economy'` e a lista de tools divergindo.

- [ ] **Step 3: Implementar**

Em `sparkforge/adapters/_core.py`, junto do import de `build_conf_advice`:

```python
from sparkforge.economy.report import build_context_report
from sparkforge.observability.context_ledger import ContextLedger
```

e a função, antes do bloco `# funcval`:

```python
# --------------------------------------------------------------------------- #
# economy
# --------------------------------------------------------------------------- #


def economy_report(run_id: str, host_transcript: str = "") -> dict[str, Any]:
    """O que esta execucao poe na janela de contexto.

    Verbo de TOPO pela mesma razao de `capacity`, `finops` e `tune`: compoe
    sobre o ledger e nao le artefato nenhum.

    `host_transcript` e opcional porque o token de provider e do HOST: sem ele,
    o relatorio traz byte medido e `tokens_unresolved` -- nunca uma estimativa
    com nome de token.
    """
    ledger = ContextLedger()
    return build_context_report(
        ledger,
        run_id=run_id,
        host_transcript=host_transcript or None,
    )
```

Em `sparkforge/adapters/cli.py`, o parser (junto dos outros verbos de topo,
antes do bloco `# funcval`):

```python
    # economy ------------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `capacity`, `finops` e `tune`: compoe
    # sobre o ledger e nao le artefato nenhum.
    economy_p = sub.add_parser(
        "economy",
        help="O que a execucao poe na janela de contexto: byte medido, nunca token estimado.",
    )
    economy_sub = economy_p.add_subparsers(dest="subcommand", required=True)
    economy_report_p = economy_sub.add_parser(
        "report", help="Agrupa os spans de um run e poe a superficie ao lado."
    )
    economy_report_p.add_argument("--run-id", required=True)
    economy_report_p.add_argument(
        "--host-transcript",
        default="",
        help=(
            "Transcript JSONL do host, quando houver. Sem ele o relatorio traz "
            "`tokens_unresolved` -- token de provider e do host, nao deste processo."
        ),
    )
    economy_report_p.add_argument("--out", help="Escreve o relatorio (JSON) neste arquivo.")
```

o handler (junto de `_cmd_tune`):

```python
def _cmd_economy_report(args: argparse.Namespace) -> int:
    payload = _core.economy_report(args.run_id, host_transcript=args.host_transcript)
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0
```

e o despacho, junto de `("tune", None)`:

```python
    ("economy", "report"): _cmd_economy_report,
```

Em `sparkforge/adapters/tools.py`, a declaração (antes de
`"sparkforge_funcval_plan"`):

```python
    "sparkforge_economy_report": {
        "description": (
            "O que a execucao poe na janela de contexto: bytes MEDIDOS por tool, o "
            "efeito medido do `detail_level`, o peso do catalogo em repouso e -- "
            "quando houver transcript do host -- o token de provider AO LADO, nunca "
            "somado ao byte. Verbo de topo, nao um `analyze`: compoe sobre o ledger "
            "que `call_tool` alimenta e nao le artefato nenhum. "
            "O QUE ELE RECUSA: (1) custo em dolar -- chamada de tool local nao tem "
            "tabela de preco publicada; (2) estimativa de token por divisao de bytes "
            "-- `len//4` e heuristica interna e nao pode sair com o nome de token, "
            "entao sem transcript sai `tokens_unresolved`; (3) somar byte com token, "
            "que sao unidades diferentes. `payload_bytes` e a serializacao canonica "
            "da resposta do despacho, e NAO 'o que o modelo viu': o host reserializa "
            "com espacamento proprio."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["run_id"],
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": (
                        "O run cujos spans agregar. Sem spans correlacionados sai "
                        "`run_unresolved` -- agregar spans de outra investigacao "
                        "seria pior que numero nenhum."
                    ),
                },
                "host_transcript": {
                    "type": "string",
                    "description": (
                        "Caminho do transcript JSONL do host, quando houver. E a "
                        "unica fonte de token de provider que existe aqui."
                    ),
                },
            },
        },
        "outputSchema": _may_fail(
            _ECONOMY_REPORT_SUCCESS_SCHEMA,
            "Relatorio de contexto, ou erro se o ledger nao puder ser lido.",
        ),
        "annotations": _READ_ONLY,
    },
```

o schema, junto dos outros `_*_SUCCESS_SCHEMA` (antes de `TOOLS`):

```python
_ECONOMY_REPORT_SUCCESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["run_id", "by_tool", "detail_level_effect", "surface", "unresolved"],
    "properties": {
        "run_id": {"type": "string"},
        "by_tool": {
            "type": "object",
            "description": "Por tool: chamadas, bytes de payload e desfechos.",
        },
        "detail_level_effect": {
            "type": "object",
            "description": (
                "Bytes por nivel pedido, por tool. O relatorio NAO afirma qual e "
                "menor -- mostra os dois, e quem le conclui."
            ),
        },
        "surface": {
            "type": "object",
            "description": "O catalogo em repouso: tools, skills e knowledge em bytes.",
        },
        "host_usage": {
            "type": ["object", "null"],
            "description": "Token do provider, quando houve transcript. `null` quando nao.",
        },
        "unresolved": {"type": "array", "items": {"type": "object"}},
    },
}
```

e o handler, junto de `_h_tune`:

```python
def _h_economy_report(args: dict[str, Any]) -> dict[str, Any]:
    return _core.economy_report(
        args["run_id"], host_transcript=args.get("host_transcript", "")
    )
```

com o registro em `_HANDLERS`, junto de `"sparkforge_tune"`:

```python
    "sparkforge_economy_report": _h_economy_report,
```

Em `manifest.json`, `"sparkforge_economy_report"` na lista `tools`, em ordem
alfabética (fica logo depois de `"sparkforge_collect_verify"`).

Em `parity.yaml`, uma capability própria, depois da de `tune`:

```yaml
  - name: measure what the run puts in the context window
    tools: [sparkforge_economy_report]
    cli: [economy report]
    knowledge: []
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]
```

Em `agents/spark-performance-architect.md`, antes da seção
`## Configuração derivada da medida, e não do costume`:

```markdown
## Quanto contexto a investigação custou

`sparkforge_economy_report` responde com byte medido, e não com token estimado. Leia
`by_tool` para saber qual verbo pesa, e `detail_level_effect` antes de afirmar que
`summary` reduz — essa frase está publicada há muito tempo e só agora tem número.

`host_usage` vem `null` quando não há transcript do host: token de provider é do host, e
este processo não chama modelo nenhum. Nunca converta byte em token dividindo por quatro
para preencher o vazio — o relatório traz `tokens_unresolved` exatamente para isso não
acontecer.

```

Rode `python scripts/sync_skills.py` para re-renderizar os três espelhos do
coordenador.

- [ ] **Step 4: Rodar e ver passar**

```bash
python -m pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_capability_parity.py tests/test_canonical_registry.py tests/test_docs_coverage.py tests/test_agent_coverage.py tests/test_agents_parity.py tests/test_arvore_versionada.py tests/test_harness_authorization.py -q
```

Expected: PASS. A contagem fixa de tools em
`tests/test_harness_authorization.py::TestOCatalogoContinuaCabendoNaVerificacao`
sobe de 57 para 58 — atualize e reporte.

- [ ] **Step 5: Commit**

```bash
python -m ruff check sparkforge/adapters tests/test_adapters_cli.py tests/test_adapters_tools.py
git add sparkforge/adapters manifest.json parity.yaml agents .claude .agents .github tests
git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(cli): o verbo economy report e a tool da contabilidade de contexto`

---

## Task 8: Documentação e gates

- [ ] **Step 1: Os gates dirigidos**

```bash
python scripts/check_surface_lock.py
python scripts/check_vnext_claims.py
python -m pytest tests/test_docs_coverage.py -q
```

O `check_vnext_claims.py` leva de 10 a 20 minutos e reexecuta as provas. Se
divergir, remedeie **por lista de ids tirada da saída dele**, nunca por
varredura genérica: a varredura já reescreveu quatro alegações erradas porque o
`pattern` do proof extrai um grupo diferente do texto publicado.

- [ ] **Step 2: README**

Acrescente `economy report` à tabela dos verbos que compõem, junto de `tune`:

```markdown
| Contexto que a execução consumiu | `economy report` | os spans do ledger que `call_tool` alimenta, mais a superfície em repouso e o transcript do host quando houver |
```

E atualize os números medidos de tools nos lugares que os citam — meça, não
copie:

```bash
python -c "from sparkforge.adapters import tools; print(len(tools.TOOLS))"
```

- [ ] **Step 3: STATUS**

Uma seção para a fase em `docs/superpowers/STATUS.md`, antes de
`## Dívidas abertas`, registrando:

- a premissa que mudou: o SparkForge nunca chama provider, medido pela ausência
  de import de `anthropic`/`openai`/`bedrock`/`litellm`;
- o ledger que já existia vazio, e os dois campos que mentiriam;
- o desvio do spec sobre `estimated_cost_usd` (mantido e condicionado a
  `cost_basis`, em vez de removido, porque span de modelo tem caso legítimo);
- o que ficou de fora: gate por execução, tokenizer embarcado, custo em dólar.

Atualize também os contadores do topo do arquivo (tools) com o número medido.

- [ ] **Step 4: Gate de números**

```bash
python scripts/check_vnext_claims.py
```

Itere até `0 divergencia(s).`

- [ ] **Step 5: Verificação ampla, em lotes**

A suíte inteira num processo só não sobrevive: leva de 20 a 73 minutos e morre
quando roda como tarefa de background. Gere os lotes e rode um por vez:

```bash
python - <<'PY'
import pathlib
arquivos = sorted(p.name for p in pathlib.Path("tests").glob("test_*.py"))
tamanho = -(-len(arquivos) // 6)
for i in range(6):
    grupo = arquivos[i * tamanho : (i + 1) * tamanho]
    if grupo:
        pathlib.Path(f"lote{i + 1}.txt").write_text(
            "\n".join("tests/" + n for n in grupo), encoding="utf-8", newline="\n"
        )
        print(f"lote{i + 1}: {len(grupo)} arquivos")
PY

for i in 1 2 3 4 5 6; do
  python -m pytest -q $(cat lote$i.txt | tr '\n' ' ') 2>&1 | tail -3
done
```

O lote que contém os `test_fixtures_golden_*` estoura dez minutos e precisa ser
quebrado outra vez, em grupos de quatro a cinco módulos: cada golden reextrai o
corpus inteiro e sozinho leva de 2 a 15 minutos.

Apague os `lote*.txt` antes de commitar — eles são andaime, não artefato.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/superpowers/STATUS.md docs/claims.lock.json docs/harness docs/surface.lock.json
git commit -F <arquivo com a mensagem>
```

Mensagem: `docs: a contabilidade de contexto, e a premissa que nao tinha produtor`

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §1.2 os dois campos que mentem | 1 |
| §3.1 um ponto de instrumentação | 2 |
| §3.2 `payload_bytes` e a base junto | 1, 2 |
| §3.3 byte sempre, token só com fonte | 1, 5, 6 |
| §3.4 não é Fact | 2 (ledger próprio) |
| §3.5 reusar o ledger | 1, 2 |
| §3.6 correlação por `run_id`, e a recusa | 2, 6 |
| §3.7 lock e não limiar | 4 |
| §4.1 campos novos e corrigidos | 1 |
| §4.2 nível 1 | 2 |
| §4.2 nível 2 | 3 |
| §4.2 nível 3 | 6 |
| §4.2 nível 4 / §4.3 | 5 |
| §5 superfície | 7 |
| §6 as cinco recusas nomeadas | 2, 5, 6 |
| §7.1 byte exato | 2 |
| §7.2 os três caminhos de erro | 2 |
| §7.3 ledger quebrado não quebra a tool | 2 |
| §7.4 efeito do `detail_level` medido | 6 |
| §7.5 garantias do subsistema | 2, 6 |
| §7.6 o lock bate | 4 |
| §8 documentação | 8 |
| §9 critérios de aceite 1–7 | 1–7 |
