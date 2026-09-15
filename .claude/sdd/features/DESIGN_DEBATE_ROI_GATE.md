# DESIGN: Debate ROI Gate (§11)

> Technical design for implementing Debate ROI Gate (§11)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_ROI_GATE |
| **Date** | 2026-09-14 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_DEBATE_ROI_GATE.md](./DEFINE_DEBATE_ROI_GATE.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
findings + UNIAO dos facts + runtime + budget
            │
   run.py::_arbitra_pares  (caminho unico de run_executor e open_debate_plans)
   ├─ arbitrate(par) ── fecha ──> Decision (como hoje; sem gate)
   └─ nao fecha ──> entrada = {rules, recommendation, reason, plan, debate_gate}
                                                                   ▲
                    executor/gate.py::avaliar(par, resultado, findings, lacunas,
                                              diretas, plano, kinds, politica)
                    ├─ signals: severity, reversible, arbitration, evidence_gap,
                    │           complexity, contradiction_count
                    ├─ refused: expected_information_gain
                    └─ verdict: experimentar_antes | debater | nao_debater | unresolved
            │
   run_executor ──> trace `kind: debate_gate` (id proprio) no blackboard
            │
   debate_run.start ── entrada.debate_gate.verdict != debater ──> recusa nomeada, nada gravado
                    └─ debater ──> budget, plano congelado (IGUAL a hoje: `plan` nao muda)

politicas lidas do catalogo:
   rules/catalog/debate_gate.yaml    debate_severities: [P0, P1]
   rules/catalog/action_kinds.yaml   kinds.<kind>.reversible: true|false (70)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/agentic/executor/gate.py` | Avaliação pura do par: sinais, recusa do sinal sem fonte, veredito ordenado; carga das duas políticas | stdlib + `yaml`, `safe_catalog_file` |
| `run.py::_arbitra_pares` | Anexa `debate_gate` a cada entrada que vira plano | chamada ao gate |
| `run.py::run_executor` | Grava um trace `debate_gate` por plano | `_persistir` existente |
| `debate_run.start` | Três recusas novas antes do budget | constantes + `_recusa` |
| `rules/catalog/debate_gate.yaml` | Limiar de severidade declarado | YAML de política |
| `rules/catalog/action_kinds.yaml` | `reversible` nos 70 `kind`, com o critério no cabeçalho | YAML de vocabulário |
| `sparkforge/adapters/tools.py` | Enum de recusa do debate e descrições de `arbitrate`/`debate start` | schema existente |

---

## Key Decisions

### Decision 1: O gate é vizinho de `plan`, calculado em `_arbitra_pares`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** `_arbitra_pares` é o caminho único de `run_executor` e `open_debate_plans`, e o plano congelado do debate copia `entrada["plan"]`; o `debate_id` é o hash desse documento, e o `brief.json` de `retomada` é golden byte a byte.

**Choice:** `avaliar(...)` é chamado quando o par não fecha, e o resultado entra como `entrada["debate_gate"]`, ao lado de `plan`, `recommendation` e `reason`. Nada é acrescentado dentro de `plan`. As duas políticas são carregadas uma vez por processo (cache de módulo, como `agent_for_area` em `plan.py`), e o teste passa a sua pelo parâmetro.

**Rationale:** Uma leitura só de "este par vira debate?" — a mesma razão que criou `open_debate_plans`. E o plano congelado não muda, então os 13 goldens de debate e os ids ficam onde estão.

**Alternatives Rejected:**
1. Dentro de `debate_plan()` — `plan.py` teria de receber findings, lacunas e o resultado da arbitragem, e o bloco entraria no plano congelado, movendo o `debate_id`.
2. Só no `debate start` — o `arbitrate` não mostraria o veredito.

**Consequences:**
- O schema de `debate_plans` (itens `{"type": "object"}`) não muda.
- O `arbitrate` passa a carregar as duas políticas; `load_catalog` não entra (as severidades vêm do finding).

---

### Decision 2: Sinais e ordem do veredito

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O operador validou a ordem `experimentar_antes` → `debater` → `nao_debater`, com `unresolved` para sinal ausente. Condição suficiente de `debater` presente não pode ser anulada por outro sinal ausente.

**Choice:**

| Sinal | Fonte | Ausente quando |
|-------|-------|----------------|
| `severity` | pior `finding.severity` de cada regra do par (P0 < P1 < P2 < P3) | regra sem finding com `severity` em P0–P3 |
| `reversible` | `kinds[finding.action.kind].reversible` | finding sem `action.kind`, `kind` fora do vocabulário, ou sem `reversible` booleano |
| `arbitration` | `escalate`, `experiment` ou `sem_vencedor` (sem `winning_claim_id`) | nunca |
| `evidence_gap` | `Unknown` com `blocking` que `_fala_de` qualquer regra do par, com o `Experiment` de `experiments_from` (ligado por `unknown_question`) | nunca (lista vazia é valor) |
| `complexity` | participantes do plano + `participants_unresolved` | nunca; informativo |
| `contradiction_count` | `len(direct_conflicts(findings))` do case | nunca; informativo |

Regras, a primeira que casa vence:
1. `evidence_gap` não vazio → `experimentar_antes` (motivo `lacuna_mensuravel`).
2. Qualquer lado com severidade conhecida em `debate_severities` (`severidade`), ou `reversible` conhecido `false` (`irreversivel`), ou `arbitration == escalate` (`sem_lastro`) → `debater`, com todos os motivos que casaram.
3. Todos os sinais de decisão conhecidos e nenhum acima → `nao_debater` (`barato_e_reversivel`).
4. Senão → `unresolved`, com `missing` nomeando cada sinal e regra.

`refused.expected_information_gain` sai sempre, com o motivo: sem modelo de probabilidade não há fonte, e a regra 23 põe modelo no host.

**Rationale:** Debate não cria a medida que falta, então a lacuna vem primeiro. Condição suficiente conhecida decide sem esperar o sinal que falta; só `nao_debater` exige tudo conhecido, porque dispensar debate com sinal ausente seria decidir por falta de dado.

**Alternatives Rejected:**
1. Nota ponderada — pesos seriam convenção sem calibração.
2. `unresolved` sempre que algum sinal falta — um P0 conhecido deixaria de abrir debate por causa de um `kind` sem declaração do outro lado.

**Consequences:**
- O par real: P0 e P1 conhecidos, sem lacuna → `debater` só por `severidade`. `irreversivel` não entra: `dependency.remove_library` e `dependency.declare_in_iac` mudam arquivo do repositório e são reversíveis pelo critério da Decision 4.

---

### Decision 3: Recusas do `debate start`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** Recusa tem nome (regra 20) e não grava nada; o enum é literal em `tools.py` e `tests/test_cli_debate.py:345` confere que ele é o conjunto das constantes.

**Choice:** Constantes `GATE_EXPERIMENTAR_ANTES = "gate_experimentar_antes"`, `GATE_NAO_DEBATER = "gate_nao_debater"`, `GATE_UNRESOLVED = "gate_unresolved"` em `debate_run.py`. `start` confere o gate logo depois de achar a entrada do par e ANTES do budget (budget não importa para par que não será debatido). O `detail` nomeia a saída: o experimento e a lacuna; as duas ações com o `rollback` de cada regra; os sinais em `missing`. Entrada sem `debate_gate` (caller antigo) é tratada como `unresolved`. Os três valores entram no fim de `_DEBATE_REFUSAL_REASONS`, e a paridade MCP ganha `REESCRITAS_DEPOIS_DO_GOLDEN[("sparkforge_debate_start", "outputSchema.oneOf[1].properties.reason.enum")]` e as descrições alteradas de `sparkforge_debate_start` e `sparkforge_arbitrate`.

**Rationale:** O host decide pelo nome; a ordem antes do budget evita pedir `max_rounds` para um debate que não vai existir.

**Alternatives Rejected:**
1. Aviso sem recusa — o gate viraria anotação.
2. `--force` — cortado no brainstorm.

**Consequences:**
- Os goldens `sem_budget` e `sem_max_rounds` continuam recusando `budget_undeclared`: o par real sai `debater`.

---

### Decision 4: Políticas no catálogo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A-005 decidida com o operador: mudança só em arquivo do repositório é reversível (o `rollback.patch` desfaz); o que destrói ou reescreve estado fora dele não é.

**Choice:** `action_kinds.yaml` ganha o critério no cabeçalho e `reversible` em cada `kind`: `false` para `maintenance.expire_snapshots`, `storage.change_storage_format`, `storage.change_partition_scheme` e `schema.align_types`; `true` nos outros 66. `rules/catalog/debate_gate.yaml`:

```yaml
policy_version: 1
# Severidades que, sozinhas, justificam debate. Politica declarada, nao medida.
debate_severities: [P0, P1]
```

Carga por `safe_catalog_file`, forma validada (`policy_version` inteiro, `debate_severities` lista não vazia dentro de P0–P3); política ausente ou inválida vira `verdict: unresolved` com a mensagem, sem derrubar o plano (regra 27). O arquivo entra em `NAO_SAO_AREA` de `tests/test_rules_loader.py` (o `load_catalog` só lê a chave `rules:`).

**Rationale:** Política revisável num lugar, no molde de `proof_axes.yaml`.

**Alternatives Rejected:**
1. Derivar reversibilidade da `direction` — `replace` de valor de configuração é reversível.
2. Constante no código — o operador escolheu manter configurável.

**Consequences:**
- Teste novo trava `reversible` booleano nos 70 e fixa o conjunto dos 4 `false` (mudança nele exige mexer no teste, à vista).

---

### Decision 5: Trace próprio

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** O trace `arbitration` tem id content-addressed sobre o corpo; acrescentar campo moveria o id de todo trace já gravado.

**Choice:** `run_executor` acrescenta, por plano, `{"kind": "debate_gate", "rules": [a, b], "verdict", "reasons", "missing", "decided_by": AGENTE}` com id `trace_` + sha1[:8] do corpo canônico, na mesma lista `traces` que vai a `_persistir`. `open_debate_plans` continua puro.

**Rationale:** O revisor acha no blackboard por que houve ou não debate, sem mudar o que já foi gravado.

**Alternatives Rejected:**
1. Campo no trace `arbitration` — move ids.
2. Entidade nova no blackboard — tipo novo para um evento.

**Consequences:**
- `persistence` conta um trace a mais por plano.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `rules/catalog/action_kinds.yaml` | Modify | Critério e `reversible` nos 70 `kind` | (general) | None |
| 2 | `rules/catalog/debate_gate.yaml` | Create | Limiar de severidade | (general) | None |
| 3 | `sparkforge/agentic/executor/gate.py` | Create | Sinais, veredito, carga das políticas | @python-developer | 1, 2 |
| 4 | `sparkforge/agentic/executor/run.py` | Modify | `debate_gate` na entrada; trace | @python-developer | 3 |
| 5 | `sparkforge/agentic/executor/debate_run.py` | Modify | Três recusas no `start` | @python-developer | 4 |
| 6 | `sparkforge/adapters/tools.py` | Modify | Enum e descrições | @python-developer | 5 |
| 7 | `tests/test_agentic_executor_gate.py` | Create | Os quatro vereditos, sinais, política inválida, varredura de texto | @test-generator | 3 |
| 8 | `fixtures/debate/gate_{experimentar_antes,nao_debater,unresolved}/` + `tests/test_fixtures_golden_debate.py` | Create/Modify | Goldens com `input/findings.json` e `input/facts.json` sintéticos (o harness passa a aceitar a união do próprio caso) | @test-generator | 5 |
| 9 | `tests/test_rules_action_field.py`, `tests/test_rules_loader.py`, `tests/test_fixtures_golden_mcp_parity.py`, `tests/test_agentic_executor_run.py` | Modify | Trava de `reversible`, `NAO_SAO_AREA`, exceções de paridade, trace novo | (general) | 1-6 |
| 10 | `docs/guia/usos/` (página do debate), `CLAUDE.md` (regra 29), `docs/superpowers/STATUS.md`, referência gerada, `docs/claims.lock.json` | Modify | Manual e números | (general) | 1-9 |

**Total Files:** 10 grupos

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 3-6 | Python puro no molde do executor |
| @test-generator | 7, 8 | Unidade e goldens sintéticos |
| (general) | 1, 2, 9, 10 | Política declarada e registros literais do repositório |

**Agent Discovery:**
- Scanned: `agents/**/*.md` do agentspec
- Matched by: tipo de arquivo; o build constrói direto, como nas frentes anteriores

---

## Code Patterns

### Pattern 1: Veredito ordenado

```python
def _veredito(sinais: dict[str, Any], politica: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    if sinais["evidence_gap"]:
        return "experimentar_antes", ["lacuna_mensuravel"], []
    motivos: list[str] = []
    faltando: list[str] = []
    for regra, severidade in sinais["severity"].items():
        if severidade is None:
            faltando.append(f"severity:{regra}")
        elif severidade in politica["debate_severities"]:
            motivos.append(f"severidade:{regra}={severidade}")
    for regra, reversivel in sinais["reversible"].items():
        if reversivel is None:
            faltando.append(f"reversible:{regra}")
        elif reversivel is False:
            motivos.append(f"irreversivel:{regra}")
    if sinais["arbitration"] == "escalate":
        motivos.append("sem_lastro")
    if motivos:
        return "debater", motivos, faltando
    if faltando:
        return "unresolved", [], faltando
    return "nao_debater", ["barato_e_reversivel"], []
```

### Pattern 2: Recusa no `start`, antes do budget

```python
gate = entrada.get("debate_gate") or {"verdict": "unresolved", "missing": ["debate_gate"]}
recusa = _RECUSA_DO_GATE.get(gate.get("verdict"))
if recusa is not None:
    return _recusa(recusa, _detalhe_do_gate(gate, par, findings))
```

### Pattern 3: Trava do vocabulário

```python
def test_todo_kind_declara_reversible(self):
    kinds = _vocabulary()["kinds"]
    faltando = sorted(n for n, c in kinds.items() if not isinstance(c.get("reversible"), bool))
    assert faltando == [], f"kind sem `reversible` booleano: {faltando}"

def test_irreversiveis_sao_os_declarados(self):
    kinds = _vocabulary()["kinds"]
    assert sorted(n for n, c in kinds.items() if c.get("reversible") is False) == [
        "maintenance.expire_snapshots", "schema.align_types",
        "storage.change_partition_scheme", "storage.change_storage_format",
    ]
```

---

## Data Flow

```text
1. arbitrate --findings --facts (uniao) --repo .
   │
   ▼
2. _arbitra_pares: par nao fecha -> plano + debate_gate ; run_executor grava trace debate_gate
   │
   ▼
3. host le debate_plans[].debate_gate.verdict
   │
   ├─ debater ............ debate start -> budget -> plano congelado (como hoje)
   ├─ experimentar_antes . mede o experimento nomeado; start recusa gate_experimentar_antes
   ├─ nao_debater ........ decisao humana; start recusa gate_nao_debater
   └─ unresolved ......... declarar o sinal que falta; start recusa gate_unresolved
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Host de debate (`run-debate`, `scripts/run_debate.py`) | Lê o veredito no plano; recebe a recusa do `start` | N/A |
| Paridade MCP (golden 1.29) | Exceções declaradas | N/A |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Quatro vereditos, precedência, sinais, `refused`, política ausente/inválida, varredura sem frase de ganho | `tests/test_agentic_executor_gate.py` | pytest | AT-001 a AT-008, AT-011 |
| Golden | Três recusas do `start` com findings sintéticos; estado do case byte a byte igual | `fixtures/debate/gate_*`, `tests/test_fixtures_golden_debate.py` | pytest | AT-002, AT-003, AT-006 |
| Golden existente | 13 casos de debate sem regravação; `brief.json` de `retomada` igual | `tests/test_fixtures_golden_debate.py` | pytest | AT-001 |
| Vocabulário | `reversible` nos 70 e os 4 `false` | `tests/test_rules_action_field.py` | pytest | AT-009 |
| Trace | Trace `debate_gate` com id próprio; id do `arbitration` igual | `tests/test_agentic_executor_run.py` | pytest | AT-010 |
| Enum e paridade | Constantes = enum; exceções declaradas | `tests/test_cli_debate.py`, `tests/test_fixtures_golden_mcp_parity.py` | pytest | AT-012 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `debate_gate.yaml` ausente ou inválido | `verdict: unresolved`, `missing: ["policy"]`, mensagem em `reason`; plano emitido | No |
| `action_kinds.yaml` sem `reversible` para o `kind` | Sinal ausente daquela regra; decide só se outro sinal for suficiente | No |
| Entrada sem `debate_gate` no `start` | `gate_unresolved` | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `debate_severities` | lista de P0–P3 | `[P0, P1]` | Severidades que justificam debate sozinhas |
| `kinds.<kind>.reversible` | bool | obrigatório | Reversibilidade declarada da ação |

---

## Security Considerations

- Leitura das políticas por `safe_catalog_file` (a mesma fronteira do catálogo).
- Nada chama provider (regra 23); o gate não grava nada fora do trace do blackboard.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A |
| Metrics | Span das tools `arbitrate` e `debate start` pelo `call_tool` |
| Tracing | Trace `debate_gate` por plano no blackboard do case |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | design-agent | Initial version |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_DEBATE_ROI_GATE.md`
