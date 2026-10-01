# BRAINSTORM: Debate ROI Gate (§11)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_ROI_GATE |
| **Date** | 2026-09-14 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Shipped |

---

## Initial Idea

**Raw Input:** §11 de `prompt_new_evo.md`, "Debate ROI Gate": antes de abrir um debate, avaliar `complexity`, `uncertainty`, `contradiction_count`, `severity`, `reversibility`, `evidence_gap` e `expected_information_gain`, para não pôr agentes discutindo o que um `if` resolve. Primeira das duas frentes que o operador escolheu para fechar o documento.

**Context Gathered:**
- Plano de debate só existe quando o `arbitrate` não fecha: `_arbitra_pares` (`sparkforge/agentic/executor/run.py`) devolve decisão OU plano, nunca os dois, e é o caminho único de `run_executor` e de `open_debate_plans`. Não fecha com `escalate`, `experiment` ou sem claim vencedora.
- `debate_run.start` congela o plano do par vindo de `open_debate_plans` e já recusa por nome (`budget_undeclared`, `no_open_debate_for_rules`, `invalid_rules`, ...). Recusa não grava nada.
- O catálogo produz UM par de contradição direta: `SF-GRAPH-005` × `SF-LF-001`, só na união de `fixtures/graph/import_sem_jar_no_iac` e `fixtures/infra_code/fgac_com_jar_extra`. Os 13 goldens de `fixtures/debate/` rodam sobre ele.
- Medido nessa união: `SF-LF-001` é P0 (`dependency.remove_library`, `remove`), `SF-GRAPH-005` é P1 (`dependency.declare_in_iac`, `add`); a arbitragem pede `experiment`; o case tem 1 `Unknown` e nenhum cita o par (`_fala_de`).
- `rules/catalog/action_kinds.yaml` tem 70 `kind` e 6 direções; nenhuma menção a reversibilidade no catálogo (0 ocorrências de `reversib`, `irreversible`, `blast`, `destructive`).
- O finding traz `severity`, `rollback`, `validation` e `action` (`sparkforge/findings/models.py`).
- O trace `arbitration` tem id content-addressed sobre o corpo: acrescentar campo nele move o id de todo trace já gravado.
- Precedente de política declarada no catálogo: `rules/catalog/proof_axes.yaml` (§20).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/agentic/executor/gate.py` (novo), `run.py` (`_arbitra_pares`, trace), `debate_run.py` (`start`), `rules/catalog/{action_kinds,debate_gate}.yaml` | Estende o executor determinístico e o de debate |
| Relevant KB Domains | Nenhum domínio do agentspec cobre arbitragem; `genai` (multi-agente) só como contexto | Padrões vêm do próprio repositório (plan, digest, proof_axes, recusas nomeadas) |
| IaC Patterns | N/A | Nada de infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O que o gate decide, e onde age? | Veredito dentro do plano + `debate start` recusa | Um cálculo só serve `arbitrate` e `start`; o veredito aparece antes da tentativa |
| 2 | De onde vem a reversibilidade? | Declarada por `kind` em `action_kinds.yaml` | 70 declarações revisáveis, travadas por teste; é política, não fact (regra 11) |
| 3 | Quais vereditos, e como decidir? | Três vereditos por regra ordenada, mais `unresolved` | Sem pesos nem limiar de nota: pesos seriam convenção sem calibração, o defeito apontado em `assess_claim` |
| 4 | Que amostras? | Só sintéticas | Par real + findings sintéticos nos testes e goldens |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/graph/import_sem_jar_no_iac/expected`, `fixtures/infra_code/fgac_com_jar_extra/expected` | 2 | A união que produz o único par real |
| Output examples | `fixtures/debate/*/expected/` | 13 | Rastro da máquina de estados; devem continuar iguais |
| Ground truth | Medida acima: par real = P0/P1, `experiment`, 0 lacuna citando | 1 | O par real sai `debater` |
| Related code | `run.py::_arbitra_pares`, `plan.py`, `debate_run.start`, `proof_axes.yaml` | 4 | Moldes de caminho único, recusa nomeada e política declarada |

**How samples will be used:**

- Golden novo por veredito que não seja `debater` (`experimentar_antes`, `nao_debater`, `unresolved`), com findings e facts sintéticos.
- Teste de unidade do gate cobrindo a ordem das regras.
- Os 13 goldens atuais servem de prova de que o par real continua abrindo debate.

---

## Approaches Explored

### Approach A: módulo `gate.py` chamado em `_arbitra_pares` ⭐ Recommended

**Description:** função pura que recebe o par, o `ArbitrationResult`, os findings, as lacunas, o vocabulário de `kind` e a política, e devolve `{verdict, reasons, signals, refused}`. Todo plano aberto ganha o bloco `gate`; `debate_run.start` recusa por nome quando o veredito não é `debater`.

**Pros:**
- `_arbitra_pares` já é o caminho único de `arbitrate` e `open_debate_plans`, e tem à mão tudo que o gate lê.
- Sem tool nem verbo novo; a superfície cresce só em texto de schema.

**Cons:**
- Muda o schema publicado do plano e o enum de recusas do `debate start` (exceção declarada na paridade MCP).

**Why Recommended:** mesmo princípio do `open_debate_plans`: duas leituras de "este par vira debate?" divergiriam com o tempo.

---

### Approach B: gate dentro de `debate_plan()`

**Description:** `plan.py` calcula o veredito junto de participantes e budget.

**Pros:**
- Tudo do plano num lugar só.

**Cons:**
- `plan.py` hoje só roteia e orça; teria de receber findings, lacunas e o resultado da arbitragem, misturando responsabilidades.

---

### Approach C: gate só no `debate start`

**Description:** veredito calculado na hora de abrir o debate.

**Pros:**
- Menor mudança no `arbitrate`.

**Cons:**
- O `arbitrate` não mostra o veredito; o operador só descobre ao tentar.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-14, durante o CI do PR #69 |
| **Reasoning** | Caminho único e veredito visível antes da tentativa |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Regras avaliadas em ordem, primeira vence: `experimentar_antes` (lacuna citando o par com experimento que a mede) → `debater` (severidade em `debate_severities`, `kind` com `reversible: false`, ou `escalate`) → `nao_debater` (todos os sinais presentes, nenhum dos anteriores) → `unresolved` (falta severidade ou `reversible`) | Debate não cria a medida que falta; sinal ausente não pode destravar debate nem dispensá-lo | Binário debater/não debater; nota ponderada com limiar |
| 2 | `expected_information_gain` sai em `refused`, com motivo | Sem modelo de probabilidade não há fonte; número seria inventado | Proxy qualquer vestido de ganho de informação |
| 3 | `complexity` (participantes) e `contradiction_count` (diretas no case) saem medidos em `signals`, fora da ordem de decisão | O operador os manteve; num par único não variam e não podem decidir | Cortar os dois |
| 4 | Reversibilidade declarada por `kind` (`reversible: true\|false`) nos 70 `kind` | Revisável num lugar e travada por teste | Derivar da `direction`; deixar fora do gate |
| 5 | Limiar de severidade em `rules/catalog/debate_gate.yaml` (`debate_severities: [P0, P1]`) | Política declarada, no molde do `proof_axes.yaml` | Constante no código |
| 6 | Veredito persistido em trace próprio `kind: debate_gate`, com id content-addressed próprio | Pôr no trace `arbitration` moveria o id de todo trace já gravado | Entidade nova no blackboard; campo no trace existente |
| 7 | Recusas novas no `start`: `gate_experimentar_antes`, `gate_nao_debater`, `gate_unresolved`, cada uma nomeando a saída | Recusa tem nome (regra 20); nada é gravado | Aviso sem recusa |
| 8 | O gate não afirma economia, ganho nem ROI medido | Regra 30: não há benchmark da camada agêntica | Texto de "debate evitado economiza X" |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `--force` no `debate start` | Sobrescrever o veredito esvazia o gate; a recusa já nomeia a saída | Yes |
| `expected_information_gain` como sinal que decide | Sem fonte sem modelo (regra 23 empurra modelo para o host) | Yes, se o host fornecer medida |
| Tool ou verbo `debate gate` separado | O veredito viaja no plano do `arbitrate` e na recusa do `start` | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura, sinais e ordem dos vereditos | ✅ | Certo, segue | No |
| Recusas, trace próprio, política e testes | ✅ | Certo, segue | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Todo par que a arbitragem não fecha vira plano de debate, sem distinguir o par que exige debate do que pede medida antes ou do que é barato o bastante para decisão humana direta.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador do case | Abre debate caro para par de baixa severidade e reversível, ou debate o que um experimento resolveria |
| Host que executa o debate (`run-debate`) | Gasta rodadas de modelo sem saber se o debate tinha motivo |

### Success Criteria (Draft)
- [ ] Todo plano aberto traz `gate` com `verdict`, `reasons`, `signals` e `refused`.
- [ ] Os quatro vereditos têm golden ou teste com findings sintéticos.
- [ ] O par real sai `debater` e os 13 goldens de debate continuam iguais.
- [ ] `debate start` recusa os três vereditos que não são `debater`, sem gravar nada.
- [ ] Os 70 `kind` declaram `reversible`, e um teste derruba o gate quando falta.
- [ ] Nenhuma saída cita economia, ganho ou ROI medido.

### Constraints Identified
- Paridade MCP congelada no golden 1.29: mudança de schema e de enum declarada nas exceções.
- Regra 23: nada chama provider; regra 30: nada afirma ganho.
- Repositório público: só fixtures sintéticas.

### Out of Scope (Confirmed)
- `--force` no `debate start`.
- Tool ou verbo separado de gate.
- Gate sobre contradição condicional (`Objection`): só contradição direta vira plano hoje.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | 1 sessão, durante o CI do PR #69 |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_DEBATE_ROI_GATE.md`
