# DEFINE: Debate Executor

> Conduzir até o fim, sem chamar provider dentro de `sparkforge/`, o debate que a arbitragem determinística hoje só planeja — por uma máquina de estados pura e dois drivers de host — e medir o desfecho contra um gabarito.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_EXECUTOR |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

**Input:** `.claude/sdd/features/BRAINSTORM_DEBATE_EXECUTOR.md` (tipo `brainstorm_document`, Abordagem A confirmada em 2026-09-11).

---

## Problem Statement

Quando a arbitragem não fecha uma contradição, `sparkforge arbitrate` emite um `DebatePlan` e para em `debate.unresolved`. Nada gera as rodadas, e o `debate referee`, que já verifica o protocolo, só tem o que verificar se um humano preencher o debate à mão. Isso vale tanto numa sessão de host quanto em lote, onde a contradição fica aberta de vez.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador numa sessão de host (Claude Code, Devin) | Investiga um case e recebe `debate.unresolved` | Conduz o debate à mão, sem estado persistido nem retomada |
| Execução em lote/CI | Roda o pipeline de diagnóstico sem humano | Não tem caminho para resolver contradição |
| Frentes futuras (router, reputation, benchmark da regra 30) | Consomem debates medidos | Não existe nenhum debate executado sobre o qual medir |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1 — Máquina de estados pura em `sparkforge/agentic/executor/`: `start` (a partir de um `DebatePlan` do case), `next` (o brief do próximo lado, ou `done`/`budget_exhausted`) e `submit` (valida, grava `Claim`/`Objection`/`Rebuttal` no blackboard, avança) |
| **MUST** | G2 — `submit` recusa por nome e não avança o estado: `dangling_evidence_ref`, claim sem `evidence_refs`, `hypothesis` fechando causa raiz, lado ou rodada fora de vez, schema inválido |
| **MUST** | G3 — Fechamento sempre pelo `referee_over_blackboard`, que já existe. `upheld: true` grava `Decision` com a claim vencedora; `upheld: false` grava `Decision` `unresolved`; nunca vencedor por maioria |
| **MUST** | G4 — Parada por consenso (uma rodada inteira sem objeção nova) ou pelo `DebateBudget` declarado no `case.yaml`; sem bloco `budget:`, `start` recusa com `budget_undeclared` |
| **MUST** | G5 — Estado só no blackboard e no diretório do debate no case; `next` recalcula tudo dele, então o driver pode morrer e recomeçar |
| **MUST** | G6 — Regra 23 intacta: 0 SDK de provider e 0 `subprocess` em `sparkforge/`, conferido por `tests/test_evals_invariants.py`, estendido aos módulos novos |
| **MUST** | G7 — Driver headless `scripts/run_debate.py`: um `claude -p` por vez de lado, no workspace de prova, com transcripts gravados fora do repositório |
| **MUST** | G8 — Suíte `evals/agentic/debate/` com ≥ 3 casos sintéticos e gabarito (`winner: <rule_id>` ou `unresolved`), e grader `sparkforge/evals/debate_grade.py` |
| **SHOULD** | G9 — `debate start/next/submit` como tools MCP `LOCAL_MUTATION`, com os sete registros manuais e o `surface.lock` atualizados, e o crescimento declarado no commit |
| **SHOULD** | G10 — Skill `run-debate` que conduz os subagentes do host pelo mesmo `next`/`submit` |
| **COULD** | G11 — Baseline da suíte de debate (Haiku, N ≥ 3) em `evals/agentic/debate/baselines/<data>/` |

---

## Success Criteria

- [ ] SC1 — Sobre o caso da regra 29 (`fixtures/graph/import_sem_jar_no_iac` ∪ `fixtures/infra_code/fgac_com_jar_extra`, 1 contradição não resolvida), o fluxo `start → next/submit → referee` termina com exatamente 1 `Decision` gravada, a partir de submissões gravadas em fixture, sem nenhum modelo.
- [ ] SC2 — Matar o processo entre dois `submit` e chamar `next` de novo devolve o mesmo brief: golden byte a byte do brief antes e depois.
- [ ] SC3 — 100% das razões de recusa do G2 têm golden próprio, e em todas o estado do debate fica byte-idêntico ao anterior.
- [ ] SC4 — `referee` com `upheld: false` produz `Decision` `unresolved` em 100% dos casos de fixture montados para isso (objeção sem réplica, hipótese sobrando, budget esgotado sem consenso).
- [ ] SC5 — `start` sem bloco `budget:` no `case.yaml` sai com `budget_undeclared`, sem gravar nada.
- [ ] SC6 — A suíte de debate tem ≥ 3 casos, e cada caso tem um teste que prova que ele é decidível **só** com o fact que o lado precisa coletar: sem o fact, o gabarito é `unresolved`.
- [ ] SC7 — `tests/test_evals_invariants.py` e `tests/test_harness_boundary.py` verdes, com os módulos novos na lista conferida.
- [ ] SC8 — O gate de lastro e o gate de números passam, e o `surface.lock` foi atualizado com o crescimento declarado (se G9 entrar).

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Início | Case com `DebatePlan` de 2 regras e `budget:` declarado | `debate start` | Estado criado; `next` devolve o brief do lado A com claim, `fact_id`s citáveis, schema e budget restante |
| AT-002 | Sem budget | Case sem bloco `budget:` | `debate start` | Recusa `budget_undeclared`; nada gravado |
| AT-003 | Submissão válida | Brief do lado A | `submit` de claim com `evidence_refs` existentes | Claim gravada; `next` devolve o brief do lado B |
| AT-004 | Referência pendurada | — | `submit` citando `f_000000` inexistente | Recusa `dangling_evidence_ref`; estado inalterado |
| AT-005 | Claim sem evidência | — | `submit` com `evidence_refs: []` | Recusa nomeada; estado inalterado |
| AT-006 | Fora de vez | `next` aponta o lado B | `submit` como lado A | Recusa `out_of_turn`; estado inalterado |
| AT-007 | Hipótese fechando | — | Claim `hypothesis` como vencedora no fechamento | `referee` `upheld: false`; `Decision` `unresolved` |
| AT-008 | Consenso | Uma rodada inteira sem objeção nova | `next` | `referee` roda; `upheld: true`; `Decision` com a claim vencedora |
| AT-009 | Budget esgotado | `max_rounds` atingido com objeção sem réplica | `next` | `referee` `upheld: false`; `Decision` `unresolved` |
| AT-010 | Retomada | Estado após 2 submissões; processo morto | `next` numa chamada nova | Mesmo brief de antes, byte a byte |
| AT-011 | Evidência nova | O lado coleta um fact novo com tool do SparkForge | `submit` citando o novo `fact_id` | Aceito somente se o fact está na união de facts do case |
| AT-012 | Headless | Caso sintético da suíte | `scripts/run_debate.py` | Transcripts por lado fora do repositório; `Decision` gravada; workspace sem gabarito |
| AT-013 | Grader | `Decision` e gabarito do caso | `debate_grade` | `winner` correto / errado / `unresolved` correto, com custo dos transcripts em colunas separadas |
| AT-014 | Regra 23 | Módulos novos | Testes de invariante | 0 SDK de provider, 0 `subprocess` em `sparkforge/` |

---

## Out of Scope

- Papéis Evidence Collector, Experiment Designer, Risk Reviewer e Verifier
- Debate ROI gate com métricas novas (fica o `should_trigger_debate` existente)
- Adapters Strands, OpenAI Agents, LangGraph, AgentCore e A2A; driver headless para Devin
- Model router, reputation e tournament
- Executor de experimento
- OTel GenAI e Execution Receipt
- Benchmark debate × arbitragem determinística (e, com ele, qualquer afirmação de ganho — regra 30)
- SDK de provider em extra ou em pacote irmão
- Mudar a semântica de `arbitrate` ou do `referee`

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 23: nenhuma chamada de modelo em `sparkforge/` | A geração só por host disparado de fora do pacote |
| Technical | Regra 29: o executor é L0 (`applied_changes: false`) | O debate decide e grava `Decision`; não aplica mudança |
| Technical | Regra 30: nenhum ganho afirmado | O baseline da suíte é o primeiro lado, e mais nada |
| Technical | `tests/test_harness_boundary.py` | O grader fica em `sparkforge/evals/`; a máquina de estados, em `sparkforge/agentic/executor/`; runtime não importa avaliação |
| Technical | `debate_plan` sem `budget:` sai `unresolved` | `start` herda a recusa, sem default de código |
| Technical | Três tools MCP novas | Os sete registros manuais, `surface.lock --update` e alegações em `docs/harness/` |
| Security / Privacy | Workspace de prova no driver headless; caso real nunca entra em arquivo | Casos sintéticos; transcripts fora do repositório |
| Resource | Execução real gasta token | O driver headless nunca roda no CI |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/agentic/executor/` (máquina de estados), `sparkforge/adapters/{cli,_core,tools}.py` (verbos, ao lado de `debate referee`), `sparkforge/evals/debate_grade.py`, `scripts/run_debate.py`, `skills/run-debate/`, `evals/agentic/debate/`, `fixtures/debate/` | Segue o padrão `arbitrate`/`referee` |
| **KB Domains** | agentspec: `genai`, `testing`, `python`, `pydantic`. Repo: `sparkforge/agentic/{debate,referee,blackboard,budget}.py`, `sparkforge/agentic/executor/{plan,run,conflict}.py`, `docs/agentic-evolution-report.md`, spec de 2026-09-03 | O protocolo concreto é o do repositório |
| **IaC Impact** | None | — |

---

## Data Contract (if applicable)

N/A.

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `debate_plan` sem `budget:` sai `unresolved`, e o critério de parada vem só dos tetos declarados | O `start` precisaria de outra fonte de budget | [x] Lido em `sparkforge/agentic/executor/plan.py::_limites`/`_criterio_de_parada` |
| A-002 | Os participantes do `DebatePlan` são agentes por área de regra, e a contradição é binária (regra A × regra B); "proponente/cético" vira "cada lado defende a sua regra e objeta a outra" | Contradição de 3+ regras exigiria rodízio de lados | [ ] Contar, no Design, os tamanhos de contradição que `conflict.py` produz sobre o corpus |
| A-003 | `referee_over_blackboard` trata a `Decision` gravada como fechamento e aplica as quatro recusas | Seria preciso um fechamento próprio | [x] Lido em `sparkforge/agentic/referee.py:317` |
| A-004 | Uma sessão `claude -p` no workspace de prova recebe o brief, usa tools do SparkForge e termina com um bloco JSON parseável | O driver precisaria de pós-processamento ou de outro formato | [ ] Smoke no build (como o B1 do eval harness) |
| A-005 | Dá para construir casos sintéticos em que a resolução depende de um fact que o lado precisa coletar | SC6 não fecha | [ ] Design lista os candidatos entre os `*.unresolved` do corpus |
| A-006 | O subagente do host segue a skill `run-debate` até o fim | Driver interativo pouco confiável | [ ] Verificação manual no build |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Lacuna declarada no próprio repositório (`debate.unresolved`, "MISSING — executor de debate") |
| Users | 2 | Três personas concretas, todas internas |
| Goals | 3 | 11 metas com MoSCoW, cada uma com artefato |
| Success | 3 | 8 critérios verificáveis por golden ou gate; 14 testes de aceitação |
| Scope | 3 | 9 exclusões explícitas, herdadas do YAGNI |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma bloqueia o Design. A-002, A-004 e A-005 são validações dentro dele e do build.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versão inicial, derivada de `BRAINSTORM_DEBATE_EXECUTOR.md`; A-001 e A-003 validadas lendo o código |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_DEBATE_EXECUTOR.md`
