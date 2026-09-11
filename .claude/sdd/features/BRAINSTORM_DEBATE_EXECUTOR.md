# BRAINSTORM: Debate Executor

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_EXECUTOR |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** a frente de `prompt_new_evo.md` que o operador escolheu depois do eval harness: a decisão estrutural sobre a regra 23 do `CLAUDE.md` — o SparkForge passa ou não a executar agente e chamar provider. Cinco frentes dependem dela: AgentRuntime, executor de debate, model router, reputation e tournament.

**Context Gathered:**
- A regra 23 é medida e, desde `37cf718`, **testada**: `tests/test_evals_invariants.py` reprova import de SDK de provider, cliente Bedrock e `subprocess` nos módulos de avaliação.
- `sparkforge arbitrate` (executor determinístico, L0) emite `DebatePlan` quando a arbitragem não fecha, e para em `debate.unresolved`. `sparkforge debate referee` (tool `sparkforge_debate_referee`) já verifica o protocolo e recusa quatro coisas: hipótese que sobrevive ao fechamento, claim sem `evidence_refs`, objeção sem réplica e referência pendurada. Falta **quem gera as rodadas** (`docs/agentic-evolution-report.md`, "MISSING — executor de debate").
- `sparkforge/agentic/runtime.py` já abstrai **hosts** (Claude Code, Devin, Codex), e não providers. `sparkforge/economy/router.py` recomenda tier de modelo e não chama nada.
- **Precedente medido:** `scripts/run_agentic_eval.py` dispara `claude -p` de fora do pacote, e a regra 23 continua valendo para `sparkforge/`. É um meio-termo entre "chamar provider" e "não executar nada".
- **Baseline de 2026-09-11** (`evals/agentic/fase0/baselines/2026-09-11-haiku-4-5/`): Haiku acerta a resposta mas quase nunca passa pelas tools (3 de 39), e na raiz do repositório copiava o gabarito de `expected/`. Qualquer driver headless roda no workspace de prova.
- `DebateBudget` e `should_trigger_debate()` existem e ninguém os consome no laço; as entidades `Claim`, `Objection`, `Rebuttal` e `Decision` já estão no blackboard.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | Máquina de estados em `sparkforge/agentic/executor/` (junto de `plan.py`, `digest.py`, `run.py`); verbos em `sparkforge/adapters/{cli,tools}.py` ao lado de `debate referee`; skill em `skills/`; driver headless em `scripts/run_debate.py`; grader em `sparkforge/evals/debate_grade.py`; suíte em `evals/agentic/debate/` | Runtime (executor) e avaliação (grader) em pacotes separados, respeitando `tests/test_harness_boundary.py` |
| Relevant KB Domains | agentspec: `genai` (orquestração multiagente), `testing`, `python`, `pydantic`. Repo: `docs/agentic-evolution-report.md`, `docs/superpowers/specs/2026-09-03-sparkforge-agentic-evolution-design.md`, `sparkforge/agentic/{debate,arbitration,blackboard,budget}.py`, `sparkforge/agentic/executor/` | O KB do agentspec traz padrão de orquestração genérico; o protocolo concreto é o do repositório |
| IaC Patterns | N/A | O driver headless usa o `claude` local, como o runner de eval |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O que motiva reabrir a regra 23? | Fechar o debate: gerar as rodadas que hoje terminam em `debate.unresolved` | O escopo é o executor de debate; router, reputation e tournament ficam fora |
| 2 | Em que contexto o debate roda até o fim? | Nos dois: sessão do host (interativo) e sem humano (CI/lote) | Uma lógica só com dois drivers, e o estado fora da conversa |
| 3 | Onde a geração (chamada de modelo) pode morar? | Nunca no pacote | A regra 23 fica intacta; o headless dispara um HOST de fora do pacote |
| 4 | O que conta como "debate fechado"? | Mecânica fim a fim mais gabarito medido | Suíte de contradições com resolução conhecida, pontuada pelo harness |
| 5 | De onde vem o gabarito? | Casos sintéticos construídos | Contradições cuja resolução depende de um fact que o papel precisa coletar |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/graph/import_sem_jar_no_iac` ∪ `fixtures/infra_code/fgac_com_jar_extra` | 1 caso real | O caso da regra 29: 3 findings, 60 facts, 1 contradição não resolvida, portanto um `DebatePlan` real |
| Output examples | saída de `sparkforge arbitrate` sobre o caso acima; exemplos de entrada de `sparkforge_debate_referee` | 1 + testes do referee | Formato de `DebatePlan` e da entrada do referee |
| Ground truth | `evals/agentic/debate/` (a criar) | ≥ 3 casos sintéticos | `winner: <rule_id>` ou `unresolved`, decidível por um fact que o papel precisa coletar |
| Related code | `sparkforge/agentic/executor/{plan,run,conflict}.py`, `sparkforge/agentic/{debate,budget,blackboard}.py`, `scripts/run_agentic_eval.py`, `sparkforge/evals/` | — | Plano, laço, budget, persistência, driver headless e grader a reusar |

**How samples will be used:**

- O caso da regra 29 como teste de ponta a ponta da mecânica.
- Os casos sintéticos como gabarito da suíte de debate, rodados no workspace de prova.
- Os transcripts dos papéis pontuados por `host_transcript`, para o custo por debate.

---

## Approaches Explored

### Approach A: Debate como protocolo de dados, com dois drivers fora da geração ⭐ Recommended

**Description:** a máquina de estados do debate fica pura no pacote. `debate start|next|submit` transforma o `DebatePlan` em briefs por papel (proponente, cético), valida e grava a submissão de cada papel no blackboard, decide o próximo passo e fecha pelo `referee`, gravando a `Decision`. A geração fica em dois drivers: uma skill que conduz os subagentes do host e `scripts/run_debate.py`, que dispara `claude -p` por papel. Uma suíte `evals/agentic/debate/` mede o desfecho contra o gabarito.

**Pros:**
- Regra 23 intacta, e uma lógica só para os dois contextos.
- Máquina de estados testável por golden.
- Retomada gratuita, porque o estado mora no blackboard.
- Reusa `arbitrate`, `referee`, o runner de eval e o harness.

**Cons:**
- É a mais trabalhosa.
- Três tools MCP novas movem `surface.lock` e os sete registros manuais.

**Why Recommended:** confiança 0,80, com base no codebase: o padrão executor determinístico → plano → verificação já existe, e só falta o laço. O runner de eval é o precedente de geração fora do pacote.

---

### Approach B: Só no host, conduzido por skill

**Description:** uma skill ensina o host a conduzir as rodadas e chamar o `referee` no fim. O pacote não muda.

**Pros:**
- Mais rápida, sem código novo.

**Cons:**
- Não atende o modo sem humano (resposta 2).
- O estado vive na conversa do host, sem golden nem retomada.

---

### Approach C: Executor inteiro em `scripts/`

**Description:** um script headless monta os prompts, conduz as rodadas e grava o resultado.

**Pros:**
- Rápido para o lote.

**Cons:**
- A lógica do debate fica fora dos goldens.
- O driver interativo teria de duplicá-la.

---

## Data Engineering Context (if applicable)

N/A.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11, nesta sessão |
| **Reasoning** | Cobre os dois contextos com uma lógica só, mantém a regra 23 e deixa o desfecho mensurável pelo harness existente |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | A regra 23 continua: nenhum SDK de provider nem chamada de modelo em `sparkforge/` | Resposta 3; a regra agora tem teste (`tests/test_evals_invariants.py`) | Extra opcional com SDK; pacote irmão com adapters |
| 2 | A geração acontece num HOST disparado de fora do pacote (skill interativa; `claude -p` headless em `scripts/`) | Precedente do runner de eval | Chamada direta de provider |
| 3 | O estado do debate mora no blackboard do case; `next` recalcula tudo dele | Retomada sem mecanismo novo | Estado em memória do driver |
| 4 | Dois papéis, proponente e cético; pedir evidência é o papel chamando tools do SparkForge | A contradição do catálogo é binária; o `referee` já verifica | Os sete papéis do "Scientific Debate" |
| 5 | Evidência nova entra pela união de facts do case, nunca como texto solto | A mesma regra do `arbitrate` (§12.9) | Aceitar evidência textual do papel |
| 6 | `submit` recusa por nome (`dangling_evidence_ref`, claim sem evidência, hipótese fechando causa raiz, papel ou rodada fora de vez) e não avança o estado | O mesmo vocabulário do `referee` | Default silencioso |
| 7 | A parada vem do consenso sem objeção nova ou do `DebateBudget`; sempre fecha pelo `referee`; `upheld: false` gera `Decision` `unresolved` | Vencedor por maioria seria julgamento sem garantia (memória "fato versus julgamento") | Maioria de evidência quando o budget acaba |
| 8 | `debate start/next/submit` como tools MCP `LOCAL_MUTATION`, com o crescimento declarado no commit | Hosts diferentes (Claude Code, Devin) acessam igual; precedente `arbitrate` | Só CLI |
| 9 | O driver headless roda no workspace de prova | O baseline mostrou o agente copiando o gabarito | Rodar na raiz do repositório |
| 10 | O grader da suíte fica em `sparkforge/evals/debate_grade.py` (avaliação), separado da máquina de estados (runtime) | `tests/test_harness_boundary.py` | Grader dentro do executor |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Papéis Evidence Collector, Experiment Designer, Risk Reviewer, Verifier | Dois papéis bastam para a contradição binária; o `referee` já verifica | Yes |
| Debate ROI gate com métricas novas | `should_trigger_debate` já decide se cabe | Yes |
| Adapters Strands, OpenAI Agents, LangGraph, AgentCore, A2A | Só o `claude -p` headless tem precedente medido | Yes |
| Driver headless para Devin | O extrator só lê transcript do Claude Code | Yes |
| Model router, reputation, tournament | Precisam de muitos debates medidos antes | Yes |
| Executor de experimento | Debate pede evidência; executar experimento é outra frente | Yes |
| OTel GenAI e Execution Receipt | Frentes próprias do `prompt_new_evo.md` | Yes |
| Benchmark debate × arbitragem determinística | Resposta 4: mecânica mais gabarito; a comparação fica para depois | Yes |
| SDK de provider (em extra ou pacote irmão) | Resposta 3 | Yes, por decisão explícita |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura e fluxo (máquina de estados, dois drivers, estado no blackboard, 3 tools MCP) | ✅ | Confirmado | No |
| Contrato do papel, parada e gabarito (schema da submissão, recusas, referee sempre fecha, suíte sintética no workspace de prova) | ✅ | Confirmado | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Quando a arbitragem determinística não fecha uma contradição, o SparkForge emite um `DebatePlan` e para em `debate.unresolved`, porque nada gera as rodadas. O `referee` existe, mas não tem o que verificar sem um humano preenchendo o debate à mão.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador numa sessão de host | Recebe `debate.unresolved` e precisa conduzir o debate à mão, sem estado nem retomada |
| Execução em lote/CI | Não tem como resolver contradição sem humano |
| Frentes futuras (router, reputation, benchmark da regra 30) | Não têm debates medidos sobre os quais trabalhar |

### Success Criteria (Draft)
- [ ] Sobre o caso da regra 29, `debate start → next/submit → referee` termina com `Decision` gravada nos dois drivers, e a retomada depois de matar o driver no meio continua do mesmo ponto.
- [ ] 100% das submissões inválidas saem recusadas com o nome da razão, sem avançar o estado (golden por razão).
- [ ] A suíte `evals/agentic/debate/` tem ≥ 3 casos sintéticos com gabarito, e o grader reporta por caso `winner` acertado ou não e `unresolved` correto, com custo dos transcripts em colunas separadas.
- [ ] Os invariantes de `tests/test_evals_invariants.py` e `tests/test_harness_boundary.py` seguem verdes: 0 SDK de provider, 0 `subprocess` em `sparkforge/`.
- [ ] Uma execução real da suíte (N ≥ 3) fica registrada como baseline, sem afirmação de ganho.

### Constraints Identified
- Regra 23: a geração só por host disparado de fora do pacote.
- Regra 29/30: o executor é L0 (`applied_changes: false`); nenhum ganho afirmado sem o outro lado.
- Fronteira runtime/avaliação (`tests/test_harness_boundary.py`).
- Três tools MCP novas: `surface.lock` e os sete registros manuais (memória `tool-nova-move-registros-manuais`).
- Workspace de prova para o driver headless; caso real nunca entra em arquivo.

### Out of Scope (Confirmed)
- Todos os itens da seção YAGNI.
- Mudar a semântica do `referee` ou do `arbitrate`.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 de descoberta + 1 de YAGNI + 2 validações |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 9 |
| Validations Completed | 2 |
| Duration | Uma sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_DEBATE_EXECUTOR.md`
