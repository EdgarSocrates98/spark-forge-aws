# DESIGN: Debate Executor

> Technical design for implementing Debate Executor

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_EXECUTOR |
| **Date** | 2026-09-11 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_DEBATE_EXECUTOR.md](./DEFINE_DEBATE_EXECUTOR.md) |
| **Status** | ✅ Complete (Built) |

**Design confidence: 0.80.** O padrão vem do codebase: executor determinístico → plano → verificação (`arbitrate`, `debate_plan`, `referee_over_blackboard`), mais o runner de eval como precedente de geração fora do pacote. O KB do agentspec (`genai`) só traz orquestração genérica.

**Premissas do DEFINE resolvidas nesta fase:**

| ID | Resultado | Como |
|----|-----------|------|
| A-002 | Confirmada: contradição sempre binária | `executor/run.py:266` só emite plano por par `[regra_a, regra_b]`, vindo de `direct_conflicts` |
| A-005 | Confirmada, **com alcance medido** | `direct_conflicts` sobre as 155 regras com `action`: **1 par** no catálogo inteiro (`SF-GRAPH-005` × `SF-LF-001`, `glue.default_arguments`: `add` × `remove`), e nenhuma fixture sozinha o produz — só a união da regra 29. A suíte usa 3 variantes desse par |

> **Risco declarado: retorno.** Hoje o debate alcança um único par de regras. O executor é genérico (qualquer par que `direct_conflicts` produza no futuro), mas o valor imediato é um caso. O operador decide seguir sabendo disso; nada aqui afirma ganho (regra 30).

---

## Architecture Overview

```text
                      mesmos insumos do arbitrate (findings + UNIÃO de facts + runtime)
                                             │
 sparkforge debate start --rules A,B ────────┤  recalcula os planos (executor, sem gravar)
                                             ▼  e congela o do par escolhido
 .sparkforge/debate/<debate_id>/  plan.json · submissions.jsonl · facts.jsonl
                                             │
 sparkforge debate next  --debate <id> ──────┤  brief do lado da vez │ done │ budget_exhausted
 sparkforge debate submit --debate <id> ─────┤  valida → reextrai evidência → grava Claim/
                                             │  Objection/Rebuttal (blackboard) → avança
                                             ▼
                              referee_over_blackboard (já existe) ──► Decision (vencedor | unresolved)

   gera as submissões (nunca dentro de sparkforge/):
     skills/run-debate/        subagente do host por lado (interativo)
     scripts/run_debate.py     claude -p por lado, workspace de prova (headless)

   mede (pacote de avaliação):
     sparkforge/evals/debate_grade.py  Decision × gabarito + custo dos transcripts
     evals/agentic/debate/<caso>/      3 variantes do par SF-GRAPH-005 × SF-LF-001
```

As dependências respeitam as duas fronteiras: `agentic/executor` (runtime) não importa `evals`; `evals/debate_grade` importa o executor e `facts/host_transcript`.

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/agentic/executor/debate_run.py` | Máquina de estados pura: `start`, `next`, `submit`, fechamento | stdlib; `executor/{run,plan}.py`, `agentic/{referee,blackboard,debate}.py` |
| `sparkforge/agentic/executor/debate_evidence.py` | Reextração da evidência nova com extratores da allowlist | `sparkforge/facts/*` (`extract*_path`) |
| `sparkforge/adapters/_core.py` + `cli.py` | `debate start/next/submit` ao lado de `debate referee` | argparse; padrão `arbitrate_findings` |
| `sparkforge/adapters/tools.py` | 3 tools MCP (`LOCAL_MUTATION`) | padrão `sparkforge_arbitrate` |
| `sparkforge/evals/debate_grade.py` | Pontua a `Decision` contra o gabarito e soma o custo dos transcripts | `host_transcript`, `evals/grade` |
| `scripts/run_debate.py` | Driver headless | `subprocess` (fora do pacote), workspace de prova do runner de eval |
| `skills/run-debate/SKILL.md` | Driver interativo | skill do repositório (+ `sync_skills.py`) |
| `evals/agentic/debate/<caso>/` | Gabarito: 3 variantes | findings, facts, `case.yaml` com `budget:`, `expected.yaml` |
| `fixtures/debate/<caso>/` | Goldens da máquina de estados (submissões gravadas, sem modelo) | JSON |

---

## Key Decisions

### Decision 1: O plano é congelado no `start`, e o estado vive no case

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** `arbitrate` devolve `debate_plans` no payload e não os grava; `digest` recalcula sem gravar. O debate precisa de um plano estável entre chamadas, e o DEFINE exige retomada (SC2).

**Choice:** `debate start` recebe os mesmos insumos do `arbitrate` (findings, facts repetível, runtime) mais `--rules A,B`. Ele recalcula os planos pelo mesmo caminho do executor e grava o do par em `.sparkforge/debate/<debate_id>/plan.json`, com a lista de `fact_id` da união. `debate_id = "dbt_" + sha1[:8]` do plano canônico. `next`/`submit` leem **só** esse diretório e o blackboard, sem caminho novo do argv.

**Rationale:** Retomada vira recálculo sobre arquivos. O mesmo `start` é idempotente: plano igual dá o mesmo id, e um segundo `start` com plano diferente para o mesmo par é recusado com `debate_exists_with_other_plan`.

**Alternatives Rejected:**
1. Gravar `debate_plans` no `arbitrate` — rejeitada: muda o `arbitrate`, fora de escopo.
2. Estado em memória do driver — rejeitada: sem retomada.

**Consequences:** um diretório por debate no case. `start` é o único verbo novo que lê arquivo de facts do argv, pelo mesmo helper do `arbitrate`.

---

### Decision 2: Lados são as regras; vez alternada A, B

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** A-002: sempre dois lados, cada um ancorado numa regra.

**Choice:** o lado A defende `rules[0]` e objeta `rules[1]`, e o lado B faz o inverso. A ordem por rodada é A depois B. A rodada conta quando os dois submeteram. O brief traz a regra defendida, a regra adversária, os `fact_id` de cada uma, as submissões anteriores (rotuladas `untrusted_content: true`, porque são texto de agente), o schema e o budget restante.

**Rationale:** Os papéis nascem do dado, sem "proponente/cético" inventado.

**Alternatives Rejected:** papéis fixos desacoplados das regras — rejeitada: exigiria escolher quem propõe.

---

### Decision 3: Evidência nova é REEXTRAÍDA pelo executor, nunca aceita do agente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Context:** O lado pode precisar de um fact que não está na união (é o que torna os casos decidíveis). Aceitar um fact escrito pelo agente seria aceitar evidência fabricada.

**Choice:** a submissão pode trazer `evidence_artifacts: [{"extractor": "<nome>", "path": "<relativo à raiz do case>"}]`. O executor valida o nome contra uma **allowlist** de extratores com `extract*_path` e o caminho **confinado à raiz do case** (`realpath` + prefixo, recusa `artifact_outside_case`). Então roda o extrator e acrescenta os facts resultantes a `facts.jsonl`. Só um `fact_id` produzido assim, ou já presente na união, pode ser citado.

**Rationale:** A mesma disciplina do `arbitrate` (§12.9): claim ancora em fact derivado de artefato, e não em texto.

**Alternatives Rejected:**
1. `new_facts` inline validados só por schema — rejeitada: o agente forjaria o fact.
2. Proibir evidência nova — rejeitada: os casos deixariam de ser decidíveis (SC6).

**Consequences:** o artefato precisa existir no case. O agente produz o artefato (ex.: dump de `collect lakeformation`) e o executor extrai.

---

### Decision 4: Fechamento sempre pelo `referee`; nunca maioria

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `next` fecha quando a última rodada completa não trouxe objeção nova (consenso) ou quando o `DebateBudget` do plano se esgota. No fechamento:
1. grava a `Decision` candidata: a claim de causa raiz sem objeção pendente, ou `unresolved`;
2. roda `referee_over_blackboard`;
3. se o veredito for `upheld: false`, a `Decision` gravada é trocada por `unresolved`, com as violações citadas.

`next` depois do fechamento devolve sempre o mesmo `done`.

**Rationale:** DEFINE G3. "Vencedor por maioria" seria julgamento sem garantia.

**Alternatives Rejected:** escolher pela contagem de evidência — rejeitada pelo operador na validação 2.

---

### Decision 5: CLI + 3 tools MCP

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:**
- `sparkforge debate start|next|submit` fica no mesmo subparser de `debate referee`.
- As tools são `sparkforge_debate_start`, `sparkforge_debate_next` e `sparkforge_debate_submit`, todas `LOCAL_MUTATION`. O `next` também é mutação, porque grava a `Decision` no fechamento.
- `submit` pela CLI recebe `--file`. Pela MCP recebe a submissão inline.

**Consequences:** move os sete registros manuais (`test_adapters_tools`, `test_harness_authorization`, `parity.yaml`, cobertura de agente, `manifest.json`, `surface.lock --update`, `claims.lock`), com o crescimento declarado no commit.

---

### Decision 6: Driver headless termina num bloco JSON; no workspace de prova

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (A-004 validada por smoke no build) |
| **Date** | 2026-09-11 |

**Choice:** `scripts/run_debate.py`, só com constantes e allowlists, como o runner de eval:
1. copia o caso da suíte **sem** `expected.yaml` para o workspace de prova;
2. roda `sparkforge arbitrate` e `debate start` ali;
3. repete: `next` → `claude -p` com o brief, e o protocolo pede um único bloco ` ```json ` no fim → extrai o último bloco → `submit`;
4. submissão recusada volta ao lado com o motivo e consome o budget.

Os transcripts ficam em `~/.sparkforge/debate-evals/<run>/<caso>/<n>-<lado>.jsonl`.

**Rationale:** O mesmo molde já medido no eval harness, com as mesmas defesas: allowlist, nada do argv em caminho, `encoding="utf-8"`.

---

### Decision 7: O grader mora na avaliação

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-11 |

**Choice:** `sparkforge/evals/debate_grade.py` lê a `Decision` do workspace e o `expected.yaml` do caso. Por caso sai:
- `outcome`: `correct_winner`, `wrong_winner`, `correct_unresolved`, `false_resolution` (fechou onde o gabarito é `unresolved`) ou `missed_resolution`;
- `rounds`, `refused_submissions`;
- custo somado dos transcripts via `host_transcript`, com byte e token separados.

A CLI é `python -m sparkforge.evals debate --run <nome>`, com nomes sob bases fixas, como no eval harness.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/agentic/executor/debate_run.py` | Create | Máquina de estados (D1, D2, D4) | @python-developer | None |
| 2 | `sparkforge/agentic/executor/debate_evidence.py` | Create | Reextração com allowlist (D3) | @python-developer | None |
| 3 | `sparkforge/adapters/_core.py` | Modify | `debate_start/next/submit` | @python-developer | 1, 2 |
| 4 | `sparkforge/adapters/cli.py` | Modify | Subcomandos no parser `debate` | @python-developer | 3 |
| 5 | `sparkforge/adapters/tools.py` | Modify | 3 tools MCP + handlers (D5) | @mcp-developer | 3 |
| 6 | `sparkforge/evals/debate_grade.py` + `sparkforge/evals/cli.py` | Create/Modify | Grader + subcomando `debate` (D7) | @python-developer | 1 |
| 7 | `scripts/run_debate.py` | Create | Driver headless (D6) | @python-developer | 3 |
| 8 | `skills/run-debate/SKILL.md` + espelhos (`scripts/sync_skills.py`) | Create | Driver interativo | @agent-creator | 5 |
| 9 | `fixtures/debate/<caso>/` (≥ 8) | Create | Goldens: submissões gravadas por desfecho e por recusa | @test-generator | 1 |
| 10 | `evals/agentic/debate/{lf_vence,graph_vence,sem_fato}/` | Create | Gabarito: 3 variantes do par, cada uma com `budget:` | @sf-agent-evaluation-specialist | 1 |
| 11 | `tests/test_agentic_debate_run.py`, `tests/test_agentic_debate_evidence.py`, `tests/test_fixtures_golden_debate.py`, `tests/test_evals_debate_grade.py`, `tests/test_debate_suite.py` | Create | Unidade, golden, grader, decidibilidade (SC6) | @test-generator | 1–10 |
| 12 | `tests/test_evals_invariants.py` | Modify | Módulos novos na lista de regra 23 | @test-generator | 1, 2, 6 |
| 13 | Registros de tool (7) + `docs/surface.lock.json` + `docs/claims.lock.json` | Modify | Custo da D5 | (general) | 5 |
| 14 | `docs/agentic-evolution-report.md`, `CLAUDE.md` (regra 29), `evals/README.md`, `README.md`, `docs/superpowers/STATUS.md` | Modify | "MISSING — executor de debate" deixa de ser MISSING; alcance de 1 par declarado | @code-documenter | 1–11 |

**Total Files:** 14 entradas (9–11 com vários arquivos).

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1–4, 6, 7 | Módulos Python puros e adapters |
| @mcp-developer (`voltagent-dev-exp:mcp-developer`) | 5 | Contrato de tool MCP |
| @agent-creator (`plugin-dev:agent-creator`) | 8 | Skill que conduz o host |
| @test-generator | 9, 11, 12 | Goldens e testes |
| @sf-agent-evaluation-specialist | 10 | Gabarito de agente |
| @code-documenter | 14 | Docs e STATUS |
| (general) | 13 | Registros e gates |

**Agent Discovery:** agentes do agentspec, do voltagent, do plugin-dev e `sf-*` do projeto, pela lista da sessão.

---

## Code Patterns

### Pattern 1: Estado derivado, sem memória

```python
def next_step(case_root: Path, debate_id: str) -> dict[str, Any]:
    estado = _load(case_root, debate_id)
    if estado.decision is not None:
        return {"status": "done", "decision": estado.decision}
    if _consenso(estado) or _budget_esgotado(estado):
        return _fechar(case_root, estado)
    return {"status": "brief", "brief": _brief(estado, lado=_lado_da_vez(estado))}
```

### Pattern 2: Submissão — valida tudo antes de gravar qualquer coisa

```python
def submit(case_root: Path, debate_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    estado = _load(case_root, debate_id)
    recusa = _recusa(estado, payload)
    if recusa is not None:
        return {"status": "refused", "reason": recusa}
    novos = extrair_evidencia(case_root, payload.get("evidence_artifacts") or [])
    recusa = _referencias(estado, payload, novos)
    if recusa is not None:
        return {"status": "refused", "reason": recusa}
    _gravar(case_root, estado, payload, novos)
    return {"status": "accepted", "next": next_step(case_root, debate_id)}
```

### Pattern 3: Gabarito

```yaml
# evals/agentic/debate/lf_vence/expected.yaml  (nunca copiado para o workspace)
schema_version: 1
rules: [SF-GRAPH-005, SF-LF-001]
winner: SF-LF-001
decided_by: lakeformation.access_model   # o fact que o lado precisa reextrair
```

---

## Data Flow

```text
1. arbitrate (existente) → debate.unresolved para SF-GRAPH-005 × SF-LF-001
2. debate start --rules SF-GRAPH-005,SF-LF-001 → plan.json congelado
3. next → brief do lado A → host gera → submit (validado, evidência reextraída)
4. next → brief do lado B → … até consenso ou budget
5. fechamento → referee → Decision (vencedor | unresolved)
6. debate_grade: Decision × expected.yaml + custo dos transcripts
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Claude Code (`claude -p`, subagentes) | Host que gera as submissões, fora de `sparkforge/` | Sessão do operador |
| Servidor MCP do SparkForge | Tools `sparkforge_debate_*` | Nenhuma |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Golden | Máquina de estados com submissões gravadas | `test_fixtures_golden_debate.py` | pytest | Todo desfecho e toda recusa |
| Unit | Reextração, allowlist, confinamento | `test_agentic_debate_evidence.py` | pytest | `artifact_outside_case`, extrator fora da lista |
| Unit | Retomada, idempotência do `start`, `budget_undeclared` | `test_agentic_debate_run.py` | pytest | AT-001, 002, 010 |
| Decidibilidade | Cada caso da suíte: sem o fact → `unresolved`; com o fact → gabarito | `test_debate_suite.py` | pytest, submissões determinísticas | SC6 |
| Grader | `debate_grade` sobre desfechos sintéticos | `test_evals_debate_grade.py` | pytest | AT-013 |
| Registros | 7 registros de tool, boundary, invariantes | existentes | pytest | Verdes antes dos lotes |
| E2E manual | Smoke A-004; skill A-006; baseline COULD | `run_debate.py` | `claude -p` | — |

AT-001…AT-014 do DEFINE mapeiam para as linhas acima: 001–011 no golden e na unidade, 012 no E2E, 013 no grader e 014 nas invariantes.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Sem `budget:` no case | `budget_undeclared`, nada gravado | No |
| Plano do par inexistente (arbitragem fechou) | `no_open_debate_for_rules` | No |
| `start` repetido com outro plano | `debate_exists_with_other_plan` | No |
| Submissão inválida | Recusa nomeada, estado inalterado, consome budget no driver | O driver reenvia |
| Extrator fora da allowlist ou caminho fora do case | `extractor_not_allowed` / `artifact_outside_case` | No |
| `claude -p` sem bloco JSON | O driver registra `no_json_block` e trata como submissão recusada | Conta no budget |
| Referee `upheld: false` | `Decision` `unresolved` com as violações | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `case.yaml: budget.max_rounds` | int | obrigatório (sem default) | Teto de rodadas (`DebateBudget`, 1–10) |
| `EVIDENCE_EXTRACTORS` | allowlist | extratores com `extract*_path` | O que a reextração pode rodar |
| driver `--repeat`, `--model`, `--max-budget-usd` | allowlist | como no runner de eval | Execução headless |

---

## Security Considerations

- Regra 23: nenhum provider nem `subprocess` em `sparkforge/`; `tests/test_evals_invariants.py` passa a cobrir os módulos novos.
- Evidência só reextraída pelo executor, com extrator na allowlist e caminho confinado ao case (D3).
- As submissões anteriores entram no brief rotuladas `untrusted_content: true`, porque são texto de agente.
- O driver roda no workspace de prova, sem `expected.yaml`, e grava transcript fora do repositório.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum log novo; o estado do debate é arquivo inspecionável |
| Metrics | O grader por caso; o custo vem dos transcripts |
| Tracing | N/A (OTel é outra frente) |

---

## Build Order

| Task | Entrega | Gate |
|------|---------|------|
| B1 | Smoke A-004: um brief manual → `claude -p` → último bloco JSON parseável | Reabre a D6 se falhar |
| B2 | Itens 1, 2, 9, 11 (goldens da máquina) | Todo desfecho e recusa com golden |
| B3 | Itens 3–5, 13 (adapters, tools, registros) | Registros rápidos verdes |
| B4 | Itens 6, 10, 11 (grader, suíte, decidibilidade) | SC6 |
| B5 | Item 7 (driver) + smoke real de 1 caso | AT-012 |
| B6 | Item 8 (skill) + verificação manual A-006 | — |
| B7 | Itens 12, 14 + lotes + gates | Lastro, números, surface lock |
| B8 (COULD) | Baseline Haiku N ≥ 3 da suíte | — |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | design-agent | Versão inicial; A-002 e A-005 confirmadas por medida; alcance de 1 par declarado |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_DEBATE_EXECUTOR.md`
