# SparkForge Agentic Engineering Evolution — Design Spec

**Data:** 2026-09-03
**Status:** DRAFT
**Branch:** `audit/fakes-de-coleta`
**Prompt de origem:** `prompt_evo_comunity_spark_forge.md`

## 1. Contexto

O SparkForge é um motor determinístico de diagnóstico PySpark/Glue/EMR/Iceberg
com 147 regras, 30 extratores, 68 tools MCP, 57 skills, 38 agentes e 5
plataformas com paridade medida. A camada determinística (facts, findings,
rules, gates, validation) é robusta. A camada agêntica (debate, hipóteses,
experimentos, decisões, memória) é placeholder.

Esta spec descreve a evolução de "agent framework" para "Agentic Engineering
Runtime": especialistas independentes formam equipes, compartilham evidências,
desafiam hipóteses, debatem, realizam experimentos, validam soluções, registram
decisões e executam trabalho de forma auditável, econômica, segura e
independente do LLM/runtime.

## 2. Princípio central

> Nenhum agente é confiável apenas por ser especialista.
> Uma conclusão só é confiável quando sobrevive à evidência,
> revisão cruzada, contestação adversarial e validação.

## 3. Gap analysis (FASE 0)

### Existe (forte)

- `Fact`/`Finding`/`RuntimeContext` com evidência obrigatória
- Motor de regras determinístico com 147 regras
- Case system com 8 fases, 4 gates, skills_used tracking
- 38 agentes (8 coordenadores + 30 especialistas), 5 executores
- 57 skills com sync para 3 plataformas
- Economy system (7 tiers, context report, cache, model router)
- Code Intelligence (9 tools, graph, search, path, shape)
- Observability (TraceView, SQLiteTraceStore, ContextLedger)
- Authorization chain com path confinement
- Knowledge base versionada com 225 fontes vigiadas
- parity.yaml para 5 plataformas

### Parcial (precisa consolidar/estender)

- Agent Runtime Protocol: humano-legível, não máquina-legível; sem capability negotiation
- Agent Contract: `AgentManifest` existe mas faltam 10+ campos
- Shared Blackboard: `case.yaml` único, não árvore estruturada
- Context Engineering: funnel + progressive disclosure, mas sem L0-L5
- Token Economics: 3 classes de budget não unificadas
- Debate Engine: placeholder no supervisor, sem protocolo formal
- Hypothesis Engine: string tuples no case, sem classe
- Experiment Engine: contratos only
- Tool Risk Model: 2 taxonomias não unificadas
- Guardrails: forte em places, spotty em outros
- Agent Contract Testing: estático/lint, não runtime
- Semantic Cache: content-addressed, não semântico
- Observability: espalhado em 4 sistemas
- CLI: muitos comandos, faltam debate/evidence/decision/agents

### Missing

- Decision Engine (sem `Decision` object)
- Decision Memory / Institutional Memory
- Unknown Engine (conceito existe, classe não)
- Autonomy Levels (L0-L5)
- Adversarial Agents (contratos only, sem implementação)
- False Consensus Detection
- Agent Execution Graph (grafo tipado com node/edge types)

## 4. Arquitetura-alvo

```
USER
 ↓
CASE MANAGER
 ↓
CONTEXT ENGINE
 ↓
DOMAIN ROUTER
 ↓
SPECIALIST TEAM
 ↓
SHARED BLACKBOARD
 ↓
HYPOTHESIS ENGINE
 ↓
ADVERSARIAL REVIEW
 ↓
DEBATE ENGINE
 ↓
ARBITRATOR
 ↓
EXPERIMENT ENGINE
 ↓
VALIDATION
 ↓
DECISION ENGINE
 ↓
DECISION MEMORY
 ↓
EXECUTION
 ↓
OBSERVABILITY
 ↓
LEARNING/EVALUATION
```

Cada etapa possui: scope, budget, evidence, state, trace, stop condition.

## 5. Pacote novo: `sparkforge/agentic/`

```
sparkforge/agentic/
  __init__.py
  models.py          # Claim, Evidence, Hypothesis, Experiment, Decision, Unknown, Contradiction, Objection, Rebuttal, Risk, Assumption
  runtime.py         # AgentRuntime protocol, capability negotiation
  evidence.py        # Source Authority Engine (TIER 1-6)
  blackboard.py      # Shared Blackboard (directory-based case state)
  debate.py          # Debate Engine (Opening→Claim→Objection→Rebuttal→Verdict)
  arbitration.py     # Arbitration + false consensus detection
  experiment.py      # Experiment Designer
  decision.py        # Decision Engine + ADR automático
  memory.py          # Decision Memory (working/case/institutional)
  budget.py          # Unified token economics (AgentBudget, CaseBudget, DebateBudget)
  security.py        # Threat model + guardrails
  autonomy.py        # L0-L5 autonomy levels
  graph.py           # Agent Execution Graph (typed nodes/edges)
```

## 6. Entidades de primeira classe (FASE C)

### Claim

```python
@dataclass(frozen=True)
class Claim:
    id: str
    type: Literal["observation", "inference", "hypothesis", "recommendation"]
    statement: str
    claimant: str  # agent_id
    evidence_refs: list[str]  # fact_id ou evidence_id
    assumptions: list[str]
    confidence: Literal["high", "medium", "low"]
    falsifiable: bool
    created_at: str  # ISO 8601
```

### Evidence

```python
@dataclass(frozen=True)
class Evidence:
    id: str
    source: str  # fact_id, url, doc path
    authority: Literal["T1", "T2", "T3", "T4", "T5", "T6"]
    freshness: str  # ISO date
    version: str | None
    scope: str
    applicability: str
    supports: list[str]  # claim_ids
    contradicts: list[str]  # claim_ids
```

### Hypothesis

```python
@dataclass(frozen=True)
class Hypothesis:
    id: str
    statement: str
    supporting_evidence: list[str]  # evidence_ids
    contradicting_evidence: list[str]
    assumptions: list[str]
    expected_outcome: str
    failure_modes: list[str]
    confidence: Literal["high", "medium", "low"]
    falsification_method: str
    status: Literal["open", "confirmed", "refuted", "abandoned"]
```

### Experiment

```python
@dataclass(frozen=True)
class Experiment:
    id: str
    hypothesis_id: str
    variable: str  # single variable changed
    baseline: str
    controls: list[str]
    expected_results: str
    success_criteria: str
    failure_criteria: str
    rollback: str
    cost_estimate: str
    time_estimate: str
    status: Literal["proposed", "running", "succeeded", "failed", "abandoned"]
    result: str | None
```

### Decision

```python
@dataclass(frozen=True)
class Decision:
    id: str
    problem: str
    options: list[str]
    selected_option: str
    rejected_options: list[str]
    evidence_refs: list[str]
    debate_id: str | None
    experiment_ids: list[str]
    risks: list[str]
    assumptions: list[str]
    unknowns: list[str]
    confidence: Literal["high", "medium", "low"]
    runtime: str  # RuntimeContext snapshot
    validation: str
    rollback: str
    falsification_condition: str
    created_at: str
```

### Unknown

```python
@dataclass(frozen=True)
class Unknown:
    id: str
    question: str
    impact: str
    blocking: bool
    owner: str | None
    evidence_needed: list[str]
    resolution_method: str | None
    status: Literal["open", "resolved", "accepted"]
```

### Contradiction, Objection, Rebuttal

```python
@dataclass(frozen=True)
class Contradiction:
    id: str
    claim_a: str  # claim_id
    claim_b: str  # claim_id
    description: str
    detected_by: str  # agent_id
    resolution: str | None  # "debate", "experiment", "arbitration", "unresolved"

@dataclass(frozen=True)
class Objection:
    id: str
    target_claim: str  # claim_id
    objector: str  # agent_id
    statement: str
    evidence_refs: list[str]
    created_at: str

@dataclass(frozen=True)
class Rebuttal:
    id: str
    target_objection: str  # objection_id
    rebuttal_by: str  # agent_id
    statement: str
    evidence_refs: list[str]
    created_at: str
```

## 7. Agent Contract estendido (FASE C)

Estender `AgentManifest` com:

```python
responsibilities: list[str]
non_responsibilities: list[str]
allowed_actions: list[str]
forbidden_actions: list[str]
inputs: list[str]
outputs: list[str]
evidence_requirements: str
confidence_policy: str
escalation_policy: str
time_budget: str | None
compatible_runtimes: list[str]
evaluation_profile: str | None
```

## 8. AgentRuntime protocol (FASE D)

```python
@dataclass(frozen=True)
class RuntimeCapabilities:
    spawn_agent: bool
    parallel_agents: bool
    nested_agents: bool
    structured_output: bool
    tool_calling: bool
    streaming: bool
    checkpointing: bool

class AgentRuntime(Protocol):
    @property
    def capabilities(self) -> RuntimeCapabilities: ...
    def spawn_agent(self, agent_id: str, task: str) -> str: ...
    def send_message(self, agent_id: str, message: str) -> None: ...
    def receive_message(self, agent_id: str) -> str | None: ...
    def tool_call(self, tool: str, args: dict) -> dict: ...
    def checkpoint(self, state: dict) -> str: ...
    def resume(self, checkpoint_id: str) -> dict: ...
```

## 9. Shared Blackboard (FASE F)

Evoluir de `case.yaml` único para árvore estruturada:

```
.sparkforge/
  case.yaml           # metadata + phase + gates (existente)
  blackboard/
    facts.jsonl       # facts extraídos (existente via facts_index)
    claims.jsonl      # claims feitas por agentes
    hypotheses.jsonl  # hipóteses geradas
    objections.jsonl  # objeções levantadas
    contradictions.jsonl
    evidence.jsonl    # evidência classificada
    experiments.jsonl
    decisions.jsonl
    unknowns.jsonl
    traces.jsonl      # trace events
```

Cada arquivo é append-only JSONL. Agentes leem apenas o que precisam.

## 10. Debate Engine (FASE G)

Protocolo formal:

```
Opening → Claim → Objection → Rebuttal → Revision → Final Position → Verdict
```

Debate triggers (não automático para tarefas simples):
- contradictory findings
- confidence below threshold
- high-risk action
- production-impacting change
- destructive action
- evidence conflict
- cross-domain conflict

Debate budget: max rounds, max tokens, stop condition.

## 11. Arbitration (FASE G)

Não é votação majoritária. Avalia:
- evidence quality
- source authority
- independence (false consensus detection)
- specificity
- runtime applicability
- version applicability
- counterexamples
- risk, cost, performance, correctness

`independence_score`: 5 agents independentes > 5 agents derivados do mesmo contexto.

## 12. Autonomy Levels (FASE L)

| Level | Nome | Allowed | Approval |
|---|---|---|---|
| L0 | deterministic | extraction, judging | none |
| L1 | specialist | single-domain analysis | none |
| L2 | cooperative | cross-domain analysis | none |
| L3 | debate | multi-agent debate | post-hoc review |
| L4 | experimental | run experiments | pre-approval |
| L5 | autonomous engineering | self-modify | pre-approval + eval |

## 13. CLI commands (FASE K)

```
sparkforge agents list
sparkforge agents inspect <id>
sparkforge case graph
sparkforge case explain
sparkforge debate start
sparkforge debate status
sparkforge evidence list
sparkforge evidence verify
sparkforge decisions list
sparkforge decision explain <id>
sparkforge budget show
sparkforge tokens report
```

## 14. Não faz

- Não criar agentes apenas para aumentar número
- Não criar debate para tarefas simples
- Não transmitir transcript completo sem necessidade
- Não usar consenso majoritário ingênuo
- Não confiar em confidence declarada
- Não tratar LLM knowledge como evidence
- Não criar loops sem stop condition
- Não permitir budget infinito
- Não quebrar arquitetura existente sem justificativa

## 15. Compatibilidade

- Tudo que funciona hoje deve continuar funcionando
- `case.yaml` existente continua válido
- APIs existentes não quebram sem migration path
- Gates existentes continuam passando
- 9486 testes existentes continuam passando

## 16. Entregáveis

1. `sparkforge/agentic/` pacote com 12 módulos
2. `AgentManifest` estendido
3. CLI commands novos
4. Testes (contract, contamination, debate, regression)
5. Documentação (AGENTS.md, CLAUDE.md, payload Devin)
6. Spec de evolução (este arquivo)
7. Relatório final (`docs/agentic-evolution-report.md`)

---

## 17. Desvios registrados (2026-09-03, auditoria da entrega)

Convenção deste repositório: spec é **registro histórico**. O que está acima
não é reescrito quando a medição derruba parte dele — o desvio entra aqui, com
o que caiu e o que sobrou. `docs/superpowers/STATUS.md` e
`docs/agentic-evolution-report.md` são a fonte da verdade do estado atual.

### D-1 — "9486 testes existentes" (seção 15) não é o número de base

A spec publicou 9486, o relatório de entrega publicou 9881 e a mensagem de
commit publicou 9897: **três números para a mesma base**, e nenhum deles bate
com a medição. Medido em 2026-09-03 com a suíte inteira coletada:
`pytest tests/ --collect-only` → **9 952 testes**, dos quais **252** são da
camada agêntica. O que sobrou da frase: a suíte continua passando, e nenhuma
regressão foi introduzida. O que caiu: o número.

### D-2 — "12 módulos" (seção 16) é 13

`sparkforge/agentic/` tem 13 módulos mais `__init__.py`. `AGENTS.md` chegou a
publicar "12 módulos" sobre uma tabela que listava 13. Corrigido nos dois.

### D-3 — a arquitetura-alvo da seção 4 não está ligada

A seção 4 desenha `CASE MANAGER → CONTEXT ENGINE → ... → DECISION MEMORY`. O
que foi entregue são as **peças**: nenhum extrator, regra, tool MCP ou
coordenador escreve `Claim`/`Evidence`/`Decision`, e não existe executor de
debate. A camada é biblioteca com verbos de leitura. O desenho continua sendo o
alvo; ele não é o estado. Status por componente:
`docs/agentic-evolution-report.md`.

Consequência que decorre disso, e que a spec não previu: **as Fases 51-53 do
prompt de origem (benchmark da arquitetura nova contra a antiga) não têm como
ser executadas**, porque só existe um lado para medir. Nenhuma afirmação de
ganho foi publicada.

### D-4 — a seção 14 ("Não faz") foi violada em cinco pontos pela própria entrega

Medido na auditoria, com teste de regressão para cada um:

| "Não faz" da seção 14 | O que a entrega fez | Onde |
|---|---|---|
| Não confiar em confidence declarada | `budget show` devolvia `CaseBudget()` de fábrica como estado do case | `cli.py::_cmd_budget_show` |
| Não permitir budget infinito | `max_time_seconds`, `max_retries`, `max_total_tool_calls` e `max_total_time_seconds` eram declarados e nunca lidos | `budget.py` |
| Não usar consenso majoritário ingênuo | com uma claim só, a arbitragem recomendava experimento para diferenciar a claim dela mesma; e `evidence_weight` era o mesmo para toda claim da rodada | `arbitration.py` |
| Não tratar LLM knowledge como evidence | `has_sufficient_authority` e `has_fresh_in_scope` eram a mesma expressão, então a distinção entre "tem autoridade" e "sustenta a claim" não existia | `evidence.py` |
| (implícito em "não permitir budget infinito") | guardrail de L5 lia a exigência do próprio perfil estático e nunca disparava | `autonomy.py` |

Mais sete defeitos mecânicos na mesma auditoria (custo e tempo de experimento
fixos, guardrails de injeção e de segredo com falso positivo sobre o
vocabulário do próprio produto, edge de grafo colando na claim errada,
`detect_waste` com parâmetro morto, `agents inspect` aceitando caminho,
`RuntimeCapabilities` duplicando `parity.yaml` sem teste que amarrasse). A
tabela completa está em `docs/agentic-evolution-report.md`, seção "Auditoria de
2026-09-03".

### D-5 — as duas decisões de projeto, tomadas

Elas foram levantadas como "vistas e não corrigidas" e resolvidas na mesma
auditoria, depois de decididas. Ficam aqui porque **mudam contrato**, e contrato
mudado sem registro é o que esta seção existe para impedir:

1. **Falso consenso passou a medir linhagem.** A seção 11 promete detectar
   "same source, same hypothesis lineage", e `compute_independence_score` media
   a média entre diversidade de agente e de fonte: dois agentes citando a mesma
   fonte única davam 0,75 contra limiar 0,3, e nada disparava. Hoje o score é o
   **elo fraco** (`min`) das duas dimensões, a fonte conta por ligação
   `supports` (evidência solta na lista não sustenta claim nenhuma), e
   `detect_false_consensus` tem um segundo sinal independente do score: duas ou
   mais claims com conjunto de fontes IDÊNTICO. Ausência de fonte não entra
   nesse sinal — ausência não é fonte compartilhada.
2. **`Claim.id` cobre o que define a claim.** Era hash de
   `claimant + tipo + statement`, e a consequência era medida: revisar uma
   claim — a mesma frase, agora sustentada por evidência nova — colidia com a
   versão anterior e `append_claim` a recusava como duplicata. Não havia como
   registrar revisão nenhuma. Hoje `evidence_refs`, `assumptions` e
   `confidence` entram no hash, e o campo opcional `supersedes` liga a revisão
   à versão anterior, conferido contra o blackboard. Claims idênticas em tudo
   continuam com o mesmo id — o que mudou é o que conta como "idêntica".
