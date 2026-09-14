# DESIGN: Tune com timeouts e speculation (frente 2b)

> Technical design for implementing Tune com timeouts e speculation

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_TIMEOUTS_SPECULATION |
| **Date** | 2026-09-14 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_TUNE_TIMEOUTS_SPECULATION.md](./DEFINE_TUNE_TIMEOUTS_SPECULATION.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
event log ──> facts/event_log.py
               ├─ _StageAccumulator: (duração, executor, input) por task bem-sucedida
               ├─ critério de speculation da versão (+ valor configurado em Spark Properties)
               ├─ spark.stage.slow_tasks      (um por stage com task medida)
               └─ spark.executor.slow_node    (um por executor lento em >= 2 stages, input <= mediana)

facts fundidos (fuse) ──> tuning/spark_conf.py: build_conf_advice(facts, runtime, headroom)
               ├─ spark.speculation        <- spark.executor.slow_node (+ slow_tasks para nomear a recusa)
               ├─ spark.network.timeout    <- spark.timeout.relation quebrada: heartbeat_s × 12
               └─ spark.sql.broadcastTimeout <- spark.timeout.diagnosis(broadcast, sem also_seen, sem sintoma)
                                              + spark.sql.broadcast_exchange (collect+build+broadcast)
                                              limiares de sintoma lidos de rules/catalog/timeout.yaml (SF-TIMEOUT-001)

rules/catalog
   ├─ spark-ui.yaml:  SF-UI-007 sobre spark.executor.slow_node
   ├─ timeout.yaml:   SF-TIMEOUT-002 action -> spark.network.timeout, increase
   └─ action_kinds.yaml: capacity.investigate_slow_executor

CLAUDE.md / AGENTS.md: regras 15 e 16 reescritas
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Critério de task lenta | `duração > max(multiplier × mediana, tempo mínimo)` com o `quantile` satisfeito, por versão | Python puro no extrator |
| `spark.stage.slow_tasks` | Contagem de lentas, limiar, mediana de duração e de input, e por executor as lentas e o maior input delas | Fact por stage |
| `spark.executor.slow_node` | Executor lento em dois ou mais stages sem partição maior | Fact derivado no fim da extração (regra 33) |
| Derivações do `tune` | Três propriedades novas, recusas nomeadas, `--headroom` também no `broadcastTimeout` | `sparkforge/tuning/spark_conf.py` |
| `SF-UI-007` | Achado de nó lento (P2) | Catálogo YAML |
| Paridade MCP | Exceção declarada para a chamada gravada que devolve a `SF-TIMEOUT-002` | `tests/test_fixtures_golden_mcp_parity.py` |

---

## Key Decisions

### Decision 1: Critério de task lenta = o do scheduler do Spark, por versão

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O operador escolheu o critério do próprio Spark. A fórmula é a mesma em `TaskSetManager` v3.1.1, v3.5.4 e v4.1.1 (`threshold = max(multiplier × mediana, tempo mínimo)`, só depois de `max(floor(quantile × numTasks), 1)` tasks concluídas), mas os defaults mudam no Spark 4.0.0: multiplier 1.5 e quantile 0.75 antes; 3 e 0.9 depois. O tempo mínimo é 100 ms em todas (constante `MIN_TIME_TO_SPECULATION` na 3.1.1, `spark.speculation.minTaskRuntime` desde 3.2.0).

**Choice:** O extrator lê a versão de `SparkListenerLogStart` (já lida para `spark.runtime_version`) e escolhe a linha da tabela; valor configurado de `spark.speculation.multiplier`, `.quantile` e `.minTaskRuntime` em `Spark Properties` vence o default. A mediana é das tasks bem-sucedidas (`Failed` e `Killed` fora; cópia especulativa que terminou entra, como no `successfulTaskDurations`). Stage com menos tasks concluídas do que o `quantile` pede sai com `slow_count: 0` e `quantile_met: false`. Sem versão e sem os três valores configurados, o stage não ganha `slow_tasks` e sai um `spark.unresolved` com razão `speculation_criterion_unknown`, uma vez por log.

**Rationale:** Compara com o que o motor compara, o mesmo princípio do threshold de broadcast da 2a; a versão muda o critério, e a regra 18 pede que isso seja explícito.

**Alternatives Rejected:**
1. p95 do stage — marca 5% das tasks como lentas em todo stage.
2. Fator declarado pelo operador — empurra a decisão para quem nem sempre sabe o número.

**Consequences:**
- A tabela de versões vive no extrator, ao lado da de AQE no `tune`.
- Log sem `SparkListenerLogStart` nem configuração perde a análise, com lacuna nomeada.

---

### Decision 2: `spark.executor.slow_node` separa nó de partição pelo input da task

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A recusa antiga da speculation dizia que nenhuma fonte separava lentidão do NÓ da lentidão da PARTIÇÃO. Contar "o mesmo executor em dois ou mais stages" é agregação entre facts, e o `where` do motor não alcança (regra 33).

**Choice:** No fim da extração, para cada executor, conta os stages em que ele tem task lenta E todas as suas tasks lentas naquele stage leram no máximo a mediana de input do stage (`Input Metrics.Bytes Read`). Com dois ou mais stages assim, emite `spark.executor.slow_node` (`measures`: `stages_slow`, `slow_tasks`; `attrs`: `executor_id`, `host`, `stage_ids`). Stage sem input medido não conta como prova de nó (input desconhecido não é input pequeno).

**Rationale:** Uma task lenta que leu mais que a mediana é explicada pela partição; uma que leu igual ou menos, repetida no mesmo executor em stages diferentes, aponta o nó.

**Alternatives Rejected:**
1. Regra contando stages por `expr` — o motor não tem agregação.
2. Um fact por task — volume sem decisão.

**Consequences:**
- O `tune` e a `SF-UI-007` leem o mesmo fact.
- O host viaja como atributo, sem agrupamento por host (fora do escopo).

---

### Decision 3: `tune` lê os limiares de sintoma só do `timeout.yaml`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O `broadcastTimeout` só é proposto sem sintoma acima dos limiares da `SF-TIMEOUT-001`. Copiar os números no `tune` criaria duas fontes; `load_catalog()` custa ~810 ms e carrega tudo.

**Choice:** `_limiares_de_sintoma()` lê `safe_catalog_file(catalog_dir(), "timeout.yaml")`, acha a regra `SF-TIMEOUT-001` e devolve o bloco de limiar, com `functools.lru_cache`. Catálogo ilegível vira recusa `limiar_indisponivel`, nunca default. Comparação: `skew_p95_over_p50`, `spill_over_input`, `gc_ratio`, `executor_lost_count` do `spark.timeout.diagnosis` contra `skew_ratio`, `spill_ratio`, `gc_ratio`, `executor_lost_min`.

**Rationale:** Limiar é regra (regra 11); o `tune` consulta, não decide.

**Alternatives Rejected:**
1. Constantes no `tune` — divergem na primeira mudança do catálogo.
2. `load_catalog()` inteiro — custo sem necessidade.

**Consequences:**
- O `tune` passa a depender do diretório do catálogo, o mesmo que o `judge` usa.

---

### Decision 4: Valores e recusas das três propriedades

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** Decisões do brainstorm, com as unidades de cada chave (`network.timeout` e `broadcastTimeout` em segundos; `speculation` booleano).

**Choice:**
- `spark.speculation`: valor `true` (string, para o `change plan` escrever o literal) só com `spark.executor.slow_node`. Recusas: `sem_tasks_por_executor` (nenhum `slow_tasks`), `sem_tasks_lentas` (nenhuma lenta), `lentidao_da_particao` (executor repetido, mas com input acima da mediana), `lentidao_espalhada` (lentas sem executor repetido), `speculation_ja_ligada` (`spark.speculation` pedido como `true`).
- `spark.network.timeout`: `ceil(heartbeat_s × 12)` s, com `heartbeat_s >= network_timeout_s` em `spark.timeout.relation`. Recusas: `sem_relacao_observada`, `relacao_ok`.
- `spark.sql.broadcastTimeout`: `ceil(max(collect_ms + build_ms + broadcast_ms) × (1 + headroom) / 1000)` s. Recusas: `sem_diagnostico_de_broadcast` (nenhum diagnóstico ou categoria diferente de `broadcast`), `broadcast_com_outra_categoria` (`also_seen` não vazio), `sintoma_ao_lado`, `limiar_indisponivel`, `sem_broadcast_medido`, `ja_cabe_no_timeout` (valor efetivo, default 300 s, já no piso ou acima).

**Rationale:** Piso medido com folga declarada, como o overhead da 2a; a razão 12 é a dos defaults documentados (120 s / 10 s).

**Alternatives Rejected:**
1. Dobrar o limite — número mágico.
2. Baixar o heartbeat — o operador escolheu manter o heartbeat pedido.

**Consequences:**
- `--headroom` passa a valer para overhead e `broadcastTimeout`; a descrição da CLI e da tool muda.
- 13 nomes de recusa novos no enum do `outputSchema` (e três saem de `no_measured_basis`).

---

### Decision 5: `SF-TIMEOUT-002` muda de alvo, e a paridade MCP declara a chamada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A ação da regra manda baixar o heartbeat; o `tune` passa a subir o `network.timeout`. O golden congelado do SDK 1.29 (`fixtures/mcp_parity/calls.json`) grava a chamada `sucesso_verbo_lookup`, que devolve a `SF-TIMEOUT-002` inteira, texto e `structuredContent`.

**Choice:** `action.target: spark.network.timeout`, `direction: increase`, `kind` inalterado; o `proposed_change` passa a citar o valor que o `tune` deriva. No teste de paridade, `CHAMADAS_ALTERADAS_DEPOIS_DO_GOLDEN = {"sucesso_verbo_lookup": motivo}`: para essa chamada a comparação troca, antes de comparar, só os campos declarados da regra (`action.target`, `action.direction`, `proposed_change`) nos dois lados (texto JSON e `structuredContent`) e confere que todo o resto bate byte a byte; a contagem de campos trocados é travada. O golden não se regrava.

**Rationale:** Mantém a garantia do golden (a migração de SDK não mexeu em nada) e declara, com motivo, a única mudança de conteúdo que o catálogo fez.

**Alternatives Rejected:**
1. Deixar a ação antiga — catálogo e `tune` diriam coisas opostas.
2. Regravar o golden — apagaria a referência do SDK 1.29.

**Consequences:**
- Segunda exceção declarada no teste de paridade; qualquer outra mudança continua derrubando.

---

### Decision 6: `SF-UI-007` com ação nova de investigação

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O achado de nó lento existe mesmo sem quem rode o `tune`. O vocabulário de ação é fechado e nenhum `kind` fala de executor lento.

**Choice:** `SF-UI-007` (P2, `status: confirmed`, `runtime_scope` vazio), `requires_facts: [spark.executor.slow_node]`, `when` com `measures.stages_slow >= threshold.min_stages` (2). Ação `capacity.investigate_slow_executor` (novo, eixo `capacidade`), `target: spark.speculation`, `direction: investigate`, `moves: [skew.task_duration_ratio]`. `proposed_change`: investigar o worker (disco, rede, vizinho barulhento) e só então ligar speculation como mitigação, com o risco de duplicar trabalho e I/O. Fontes: `TaskSetManager.scala` (critério) e a página de configuração do Spark.

**Rationale:** `runtime.wall_clock` é o maior grupo de eixo e o teste de ordenação trava o tamanho dele; `skew.task_duration_ratio` é o eixo que a lentidão do nó move.

**Alternatives Rejected:**
1. Reusar `skew.apply_treatment` — skew é da partição, o oposto do que a regra diz.

**Consequences:**
- Registros de regra nova: rota da área já existe; `test_fixtures_kind_coverage` exige o golden positivo.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/event_log.py` | Modify | Critério por versão, `slow_tasks`, `slow_node`, lacuna | @python-developer | None |
| 2 | `sparkforge/tuning/spark_conf.py` | Modify | Três derivações, limiares do catálogo, recusas | @python-developer | 1 |
| 3 | `sparkforge/adapters/{tools,cli}.py` | Modify | Enum de recusa, descrição, `--headroom` também no broadcast | @python-developer | 2 |
| 4 | `rules/catalog/{spark-ui,timeout,action_kinds}.yaml` | Modify | `SF-UI-007`, ação da `SF-TIMEOUT-002`, `kind` novo | (general) | 1 |
| 5 | `fixtures/eventlog/{no_lento_em_dois_stages,lentidao_da_particao,lentidao_espalhada,criterio_spark4}/` | Create | Goldens do extrator e da `SF-UI-007` | @test-generator | 1, 4 |
| 6 | `fixtures/tuning/{speculation_*,network_*,broadcast_timeout_*}/` | Create | Goldens das propostas e recusas | @test-generator | 2 |
| 7 | `fixtures/change/do_tune_network/` | Create | AT-014 | @test-generator | 2 |
| 8 | `tests/test_facts_event_log.py`, `tests/test_tuning_spark_conf.py`, `tests/test_fixtures_golden_{eventlog,tuning}.py`, `tests/test_fixtures_golden_mcp_parity.py`, listas de kind | Modify | Unidade, golden e registros | @test-generator | 1-7 |
| 9 | `CLAUDE.md`, `AGENTS.md`, `agents/spark-performance-architect.md`, `docs/guia/usos/job-lento.md`, `docs/superpowers/STATUS.md` | Modify | Regras 15/16 e manuais | (general) | 1-8 |

**Total Files:** 9 grupos

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1, 2, 3 | Extração e composição em Python puro |
| @test-generator | 5, 6, 7, 8 | Goldens sintéticos e testes de unidade |
| (general) | 4, 9 | Catálogo YAML e texto; o build segue os registros do repositório direto |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do agentspec
- Matched by: tipo de arquivo e propósito; como nas frentes anteriores, o build constrói direto por causa dos registros literais do repositório

---

## Code Patterns

### Pattern 1: Critério por versão no extrator

```python
_ESPECULACAO_ANTES_DO_4 = {"multiplier": 1.5, "quantile": 0.75, "min_ms": 100.0}
_ESPECULACAO_DESDE_O_4 = {"multiplier": 3.0, "quantile": 0.9, "min_ms": 100.0}


def _criterio_de_especulacao(spark_version: str, propriedades: dict[str, str]) -> dict[str, float] | None:
    try:
        maior = int(spark_version.split(".")[0])
    except (ValueError, IndexError):
        maior = None
    base = None if maior is None else (_ESPECULACAO_DESDE_O_4 if maior >= 4 else _ESPECULACAO_ANTES_DO_4)
    configurado = {
        "multiplier": propriedades.get("spark.speculation.multiplier"),
        "quantile": propriedades.get("spark.speculation.quantile"),
        "min_ms": propriedades.get("spark.speculation.minTaskRuntime"),
    }
    if base is None and not all(configurado.values()):
        return None
    criterio = dict(base or {})
    for chave, valor in configurado.items():
        lido = _numero_ou_ms(valor) if valor else None
        if lido is not None:
            criterio[chave] = lido
    return criterio
```

### Pattern 2: Lentas de um stage

```python
def _lentas(tasks: list[tuple[int, str, int | None]], criterio: dict[str, float]) -> tuple[float, list]:
    duracoes = sorted(d for d, _, _ in tasks)
    mediana = statistics.median(duracoes)
    limiar = max(criterio["multiplier"] * mediana, criterio["min_ms"])
    return limiar, [t for t in tasks if t[0] > limiar]
```

### Pattern 3: Recusa com limiar do catálogo

```python
@functools.lru_cache(maxsize=1)
def _limiares_de_sintoma() -> dict[str, float] | None:
    try:
        caminho = safe_catalog_file(catalog_dir(), "timeout.yaml")
        documento = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
    except (OSError, yaml.YAMLError, CatalogError):
        return None
    regra = next((r for r in documento.get("rules") or [] if r.get("id") == "SF-TIMEOUT-001"), None)
    return dict(regra["threshold"]) if regra and regra.get("threshold") else None
```

---

## Data Flow

```text
1. analyze event-log: TaskEnd guarda (duração, executor, host, input); StageCompleted fecha o stage
   │
   ▼
2. fim da extração: critério por versão -> slow_tasks por stage -> slow_node por executor
   │
   ▼
3. fuse: une facts de runs (o que falhou traz o diagnóstico; o que completou, o broadcast medido)
   │
   ▼
4. judge: SF-UI-007 sobre slow_node; SF-TIMEOUT-002 com a ação nova
   │
   ▼
5. tune: três propostas ou recusas nomeadas; change plan --from-tune leva ao --conf
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Event log do Spark | Arquivo JSON lines | N/A |
| Catálogo de regras (`rules/catalog/timeout.yaml`) | Leitura local contida | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Critério por versão, override configurado, `quantile` não satisfeito, `Killed` fora, input desconhecido | `tests/test_facts_event_log.py` | pytest | AT-001, AT-002 |
| Unit | Três derivações e as 13 recusas, `headroom` no broadcast, limiar do catálogo | `tests/test_tuning_spark_conf.py` | pytest | AT-003 a AT-011 |
| Golden (event log) | 4 casos, com `SF-UI-007` dispara e cala | `tests/test_fixtures_golden_eventlog.py` | pytest | AT-001 a AT-005 |
| Golden (tuning) | Casos novos; os 14 atuais só mudam em `refused` | `tests/test_fixtures_golden_tuning.py` | pytest | AT-003 a AT-011 |
| Golden (change) | `do_tune_network` | `tests/test_fixtures_golden_change.py` | pytest | AT-014 |
| Golden (timeout) e paridade | `heartbeat_maior_que_network` com a ação nova; chamada declarada | `tests/test_fixtures_golden_timeout.py`, `tests/test_fixtures_golden_mcp_parity.py` | pytest | AT-012 |
| Documento | Regras 15/16 | leitura + `check_status_numbers.py` | revisão | AT-013 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Log sem versão e sem critério configurado | `spark.unresolved` `speculation_criterion_unknown`, sem `slow_tasks` | No |
| Task sem `Executor ID` | Entra na mediana, fora da contagem por executor | No |
| Catálogo ilegível no `tune` | Recusa `limiar_indisponivel` | No |
| `headroom` negativo | `AdapterError` exit 2 (já existe) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--headroom` | float | ausente | Folga sobre o piso de overhead e de `broadcastTimeout` |
| `spark.speculation.multiplier` / `.quantile` / `.minTaskRuntime` (lidos do log) | número | tabela por versão | Critério de task lenta |

---

## Security Considerations

- Leitura do catálogo pelo `safe_catalog_file`, contida no diretório resolvido.
- Nada aplica configuração; `REVIEW` em toda proposta.
- Fixtures sintéticos; nenhum dado de produção.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A (biblioteca determinística) |
| Metrics | `threshold_ms`, `median_ms` e o critério usado viajam no fact |
| Tracing | Spans de tool já gravados por `call_tool` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | design-agent | Initial version |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_TUNE_TIMEOUTS_SPECULATION.md`
