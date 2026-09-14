# BRAINSTORM: Autonomia L3 — pacote de proposta de PR

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L3_PROPOSAL |
| **Date** | 2026-09-14 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** L3 da autonomia (§15 de `prompt_new_evo.md`, "Propose to Production": open PR, attach evidence, attach benchmark, request human approval). Decidido antes: o pacote MONTA o pacote de PR em `.sparkforge/proposal/<id>/`, e quem roda git/gh é o host.

**Context Gathered:**
- O L2 (`sparkforge change sandbox`, PR #65) grava em `.sparkforge/sandbox/<id>/` as cópias `before/` e `after/` e um `report.json` com `files_changed`, `new`, `resolved`, `kept_count`, `moved_candidates`, `proof_obligations`, `next_steps`, `copy_skipped` e `scan_refused`. O `id` é sha256 do diff mais o manifesto do repositório. O diff original não fica guardado.
- O `scan` de cada cópia grava `facts_<analyze>.json` e `findings.json` em `<cópia>/.sparkforge/scan/`, a entrada que `receipt emit` (§14) e `report sign` (§22) pedem.
- `receipt_emit` exige `now` e é `_WRITE_IDEMPOTENT`; `report sign` grava um bloco de assinatura no fim de um relatório, amarrado a `fact_ids`, `rule_ids` e à versão do catálogo, e `report verify` diz qual parte divergiu.
- O ship do L1–L2 recomendou "abrir branch e PR a partir do `after/` do sandbox, com o relatório no corpo do PR".
- A policy padrão do §16 (`.sparkforge/policy.yaml`) não cita `git push` nem `gh pr create`.
- O projeto não usa `AutonomyLevel` para o §15: L1 e L2 têm `stage` próprio (`produce_change`, `sandbox_execute`), porque lá L1/L2 significam outra coisa.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/change/proposal.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `skills/propose-change-pr/`, `.sparkforge/policy.yaml` | Estende o módulo do §15 |
| Relevant KB Domains | Nenhum domínio do agentspec cobre o fluxo; `knowledge/` do projeto não tem página de git/gh | Padrões vêm do próprio repositório (sandbox, receipt, report sign, `run-debate`) |
| IaC Patterns | N/A | Nada de infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | De onde o L3 parte? | Do sandbox já rodado (`--sandbox <id>`) | Nada é julgado de novo; recusa `sandbox_desatualizado` se a árvore mudou |
| 2 | O que fazer com achados novos do sandbox? | Recusar P0/P1 novo; P2/P3 vão ao corpo do PR em atenção | `achado_novo_bloqueante`; diff que não move achado continua válido |
| 3 | O que entra no pacote? | Patch, rollback e PR; anexos medidos opcionais; cópia do report do sandbox; recibo de execução | Pacote auditável sem acesso ao sandbox |
| 4 | Há amostras além das sintéticas? | Só sintéticas | Casos no molde de `fixtures/change/` |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/change/*/input/` (repo, facts, request, `host.patch`) | 13 | Repos sintéticos com `main.tf`/`job.py` e diffs |
| Output examples | `fixtures/change/*/expected.json` | 13 | Forma do relatório do sandbox |
| Ground truth | `sparkforge/change/sandbox.py`, `receipt`, `report sign` | 3 | Contratos que o pacote compõe |
| Related code | Skill `run-debate` (host executa, pacote não chama provider) | 1 | Molde da skill do host |

**How samples will be used:**

- O golden roda o sandbox dentro do teste (como `plano_pelo_sandbox`) e depois o `change propose`, comparando o pacote byte a byte com `now` fixo.
- Um caso por recusa e um com anexos medidos.

---

## Approaches Explored

### Approach A: `change propose` + skill do host ⭐ Recommended

**Description:** `sparkforge/change/proposal.py` monta o pacote a partir do sandbox, sem git; `sparkforge change propose` e a tool `sparkforge_change_propose` gravam em `.sparkforge/proposal/<id>/`. Uma skill `propose-change-pr` guia o host a rodar o `commands.md`, parando para confirmação antes de `git push` e `gh pr create`.

**Pros:**
- Pacote testável por golden; git/gh nunca rodam no pacote.
- Mesmo molde de `run-debate` (§10): o pacote prepara, o host executa.

**Cons:**
- Mais uma tool no catálogo (102 -> 103) e os registros que isso move.

**Why Recommended:** Mantém a decisão "o pacote monta, o host abre" e reaproveita sandbox, recibo e assinatura.

---

### Approach B: Reusar o `report github`

**Description:** O corpo do PR sai do gerador de resumo do `report github`, alimentado pelos findings do sandbox.

**Pros:**
- Menos código de texto.

**Cons:**
- Acopla o L3 a um formato que responde outra pergunta (achados do código, não a mudança proposta).

---

### Approach C: Só skill no host

**Description:** A skill lê o `report.json` do sandbox e escreve o PR, sem código novo.

**Pros:**
- Nenhuma tool nova.

**Cons:**
- Contradiz "o pacote monta"; sem golden.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-14 |
| **Reasoning** | O pacote prepara e prova; o host executa com confirmação |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Entrada = sandbox já rodado; id da proposta = id do sandbox | O que se propõe é o que passou pelo scan antes/depois | Rodar o sandbox dentro do propose |
| 2 | Recusas antes de gravar: `sandbox_inexistente`, `sandbox_nao_aplicado`, `sandbox_desatualizado` (arquivo do repo difere de `before/`), `achado_novo_bloqueante` (P0/P1 em `new`) | O diff foi validado sobre uma árvore; outra árvore invalida a prova | Nunca recusar; recusar qualquer novo |
| 3 | Conteúdo: `change.patch`, `rollback.patch` (de `before/` para `after/`), `pr_body.md`, `commit_message.txt`, `branch.txt` (`sparkforge/change-<id8>`), `commands.md`, `evidence/sandbox_report.json`, `evidence/receipt.json`, `manifest.json` com sha256 | Auditável sem o sandbox | Só o diff |
| 4 | Anexos medidos opcionais (`--benchmark`, `--funcval`); sem eles, a medida sai como obrigação PENDENTE | Ganho só com dois runs medidos; o pacote nunca afirma | Estimar ganho |
| 5 | `pr_body.md` assinado pelo `report sign` com os findings de `after/` | `report verify` confere depois | Sem assinatura |
| 6 | Recibo com raiz em `after/`, spans de tool `unresolved` | O recibo não depende das chamadas anteriores do processo | Spans do processo |
| 7 | Tool `_WRITE_IDEMPOTENT`, `now` obrigatório na tool e opcional na CLI; dono `sf-verifier`; `stage: propose_change`, `git_run: false` | Mesma classe e mesmo `now` do recibo | `now` implícito |
| 8 | Skill `propose-change-pr` para o host, e `git push`/`gh pr create` como `ask` na policy padrão | "Request human approval" vira confirmação explícita nos dois lados | Só a skill |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `change propose --clean` | A pasta é ignorada pelo git; o operador a apaga | Yes |
| Labels, revisores e `--draft` no `gh pr create` | O comando mínimo com título e corpo basta; o host acrescenta | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Entrada, recusas e conteúdo do pacote | ✅ | Certo, segue | No |
| Tool, assinatura, recibo, skill do host e policy | ✅ | Certo, segue | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O sandbox do L2 prova o que um diff move nos achados, mas termina num relatório: transformar isso num PR revisável — patch, rollback, corpo com evidência, recibo e comandos — é trabalho manual, e nada impede um PR que introduza achado P0/P1 ou que parta de uma árvore diferente da validada.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador que rodou o sandbox | Montar o PR à mão a partir do `report.json` |
| Revisor do PR | Não sabe se a evidência corresponde à árvore do PR, nem o que falta medir |

### Success Criteria (Draft)
- [ ] Pacote byte a byte igual ao golden com `now` fixo
- [ ] 4 recusas, cada uma com golden ou teste
- [ ] `report verify` confere o `pr_body.md` do pacote
- [ ] Nenhum comando git/gh executado pelo pacote
- [ ] Policy padrão com `git push` e `gh pr create` em `ask`

### Constraints Identified
- Git/gh só no host
- Nenhuma afirmação de ganho
- `.sparkforge/proposal/` ignorado pelo git
- Tool nova move os registros manuais (surface, claims, policy, agentes)

### Out of Scope (Confirmed)
- Abrir o PR dentro do pacote
- `--clean`, labels, revisores, draft
- L4 (aplicar na árvore principal)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 de descoberta + 1 de abordagem + 1 de YAGNI |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 2 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_AUTONOMY_L3_PROPOSAL.md`
