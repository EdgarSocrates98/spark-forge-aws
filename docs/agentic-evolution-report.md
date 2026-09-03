# SparkForge Agentic Evolution Report

**Data:** 2026-09-03
**Branch:** `audit/fakes-de-coleta`
**Spec:** `docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`

## Resumo executivo

O SparkForge evoluiu de "repositório de skills determinísticas" para **Agentic
Engineering Runtime**: uma camada agêntica com 13 módulos, 9 entidades de
primeira classe, protocolo de debate formal, arbitragem independente com
detecção de falso consenso, experimentos controlados, decisões auditáveis com
ADR automático, memória institucional跨-case, budget unificado, threat model
com 12 threat types, níveis de autonomia L0-L5, e Agent Execution Graph.

A camada determinística existente (Fact, Finding, Rule, Case, Gates) **não foi
substituída** — foi estendida. Os 9881 testes existentes continuam passando.
206 testes novos foram adicionados para a camada agêntica.

## O que foi implementado

### `sparkforge/agentic/` — 13 módulos

| Módulo | Linhas | Testes | Status |
|---|---|---|---|
| `models.py` | 470 | 35 | IMPLEMENTED |
| `runtime.py` | 180 | 14 | IMPLEMENTED |
| `evidence.py` | 230 | 16 | IMPLEMENTED |
| `blackboard.py` | 280 | 19 | IMPLEMENTED |
| `debate.py` | 250 | 16 | IMPLEMENTED |
| `arbitration.py` | 280 | 14 | IMPLEMENTED |
| `experiment.py` | 150 | 10 | IMPLEMENTED |
| `decision.py` | 200 | 14 | IMPLEMENTED |
| `memory.py` | 180 | 10 | IMPLEMENTED |
| `budget.py` | 280 | 14 | IMPLEMENTED |
| `security.py` | 300 | 16 | IMPLEMENTED |
| `autonomy.py` | 200 | 10 | IMPLEMENTED |
| `graph.py` | 320 | 10 | IMPLEMENTED |

### Entidades de primeira classe

9 dataclasses frozen com id determinístico (content-addressed sha1):

- `Claim` — afirmação feita por um agente (observation/inference/hypothesis/recommendation)
- `Evidence` — evidência classificada por authority tier (T1-T6)
- `Hypothesis` — explicação proposta, falsificável
- `Experiment` — teste de hipótese com variável controlada
- `Decision` — decisão auditável com rollback e falsification condition
- `Unknown` — incerteza explícita (nunca vira fact sem evidência)
- `Contradiction` — conflito entre claims detectado
- `Objection` — contestação de uma claim com evidência própria
- `Rebuttal` — resposta a uma objeção com evidência própria

### AgentManifest estendido

12 campos novos adicionados ao `AgentManifest`:
`responsibilities`, `non_responsibilities`, `allowed_actions`,
`forbidden_actions`, `inputs`, `outputs`, `evidence_requirements`,
`confidence_policy`, `escalation_policy`, `time_budget`,
`compatible_runtimes`, `evaluation_profile`.

### CLI commands

8 comandos novos:
- `sparkforge agents list` / `agents inspect <id>`
- `sparkforge blackboard summary` / `blackboard list --type <tipo>`
- `sparkforge decisions list` / `decisions explain <id>`
- `sparkforge budget show`
- `sparkforge autonomy show --level <L0-L5>`

## O que NÃO foi implementado (declarado honestamente)

- **NOT IMPLEMENTED**: Semantic cache (embedding-based). O cache existente é
  content-addressed (SHA-256), não semântico.
- **NOT IMPLEMENTED**: L5 autonomous self-modification. O nível L5 está
  definido com guardrails, mas a execução automática de auto-modificação
  não está implementada.
- **NOT IMPLEMENTED**: Cross-case memory retrieval automático. A memória
  institucional existe (`find_similar_decisions`), mas a consulta automática
  durante novo case não está wired.
- **PARTIALLY IMPLEMENTED**: CLI commands são leitura-only. Escrita no
  blackboard é via API Python, não CLI.
- **EXPERIMENTAL**: Debate execution real. O protocolo está definido, mas
  a execução depende do runtime spawn capability (Claude/Devin despacham
  subagentes; Copilot/Codex usam playbook como floor).

## Testes

- 206 testes novos (todos passando)
- 9881 testes existentes (todos passando, 0 regressões)
- Gates: `sync_skills.py --check` OK, `check_surface_lock.py` 0 divergências,
  `check_status_numbers.py --strict` 0 divergências

## Arquitetura

```
USER
 ↓
CASE MANAGER (existente: sparkforge.case.store)
 ↓
CONTEXT ENGINE (existente: sparkforge.context.funnel/progressive)
 ↓
DOMAIN ROUTER (existente: sparkforge.case.router + routing.yaml)
 ↓
SPECIALIST TEAM (novo: sparkforge.agentic.runtime)
 ↓
SHARED BLACKBOARD (novo: sparkforge.agentic.blackboard)
 ↓
HYPOTHESIS ENGINE (novo: sparkforge.agentic.models.Hypothesis)
 ↓
ADVERSARIAL REVIEW (novo: sparkforge.agentic.arbitration)
 ↓
DEBATE ENGINE (novo: sparkforge.agentic.debate)
 ↓
ARBITRATOR (novo: sparkforge.agentic.arbitration)
 ↓
EXPERIMENT ENGINE (novo: sparkforge.agentic.experiment)
 ↓
VALIDATION (existente: sparkforge.adapters._core.validate_output)
 ↓
DECISION ENGINE (novo: sparkforge.agentic.decision)
 ↓
DECISION MEMORY (novo: sparkforge.agentic.memory)
 ↓
EXECUTION (existente: CLI/MCP adapters)
 ↓
OBSERVABILITY (existente: sparkforge.observability + novo: blackboard traces)
 ↓
LEARNING/EVALUATION (novo: sparkforge.agentic.memory + budget waste detection)
```

## Princípios preservados

- Nenhum agente é confiável apenas por ser especialista.
- Uma conclusão só é confiável quando sobrevive à evidência, revisão cruzada,
  contestação adversarial e validação.
- Unknown nunca vira fact por conveniência — retorna `UNRESOLVED`.
- Toda decisão é auditável e reversível (ou declara irreversível).
- Budget é finito e enforced — não aumenta infinitamente.
- Runtime-independente: Claude, Devin, Copilot, Codex executam o mesmo protocolo.
- Correctness, safety, evidence, auditability > token savings.

## Compatibilidade

- `case.yaml` existente continua válido e não modificado.
- APIs existentes não quebram.
- Gates existentes continuam passando.
- 9881 testes existentes continuam passando.
- `AgentManifest` estendido é backward-compatible (campos novos são opcionais).
