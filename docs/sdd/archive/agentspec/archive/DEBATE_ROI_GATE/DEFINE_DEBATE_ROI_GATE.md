# DEFINE: Debate ROI Gate (§11)

> Todo par que a arbitragem não fecha passa por um portão determinístico que diz se o par pede debate, medida antes, ou decisão humana direta — e `debate start` só abre o debate quando o veredito é `debater`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_ROI_GATE |
| **Date** | 2026-09-14 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Todo par de contradição direta que a arbitragem não fecha vira plano de debate, sem distinguir o par que exige debate (alta severidade, mudança irreversível, arbitragem sem lastro) do que pede medida antes ou do que é barato o bastante para decisão humana direta — e debate é a etapa mais cara do fluxo, porque o host gasta rodadas de modelo.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador do case | Decide se abre o debate de um par | Abre debate caro para par de baixa severidade e reversível, ou debate o que um experimento mediria |
| Host que executa o debate (skill `run-debate`, `scripts/run_debate.py`) | Gasta as rodadas de modelo | Não sabe se o debate tinha motivo antes de gastar |
| Revisor do case | Audita por que houve ou não debate | O motivo não fica registrado em lugar nenhum |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Toda entrada de `debate_plans` (em `arbitrate` e em `open_debate_plans`) ganha o bloco `debate_gate` com `verdict`, `reasons`, `signals` e `refused`, calculado por um caminho só |
| **MUST** | Vereditos avaliados em ordem, primeiro que casa vence: `experimentar_antes` → `debater` → `nao_debater`; sinal que falta dá `unresolved` |
| **MUST** | `debate start` recusa por nome, sem gravar nada, os vereditos `experimentar_antes`, `nao_debater` e `unresolved` (`gate_experimentar_antes`, `gate_nao_debater`, `gate_unresolved`), cada recusa nomeando a saída |
| **MUST** | Os 70 `kind` de `rules/catalog/action_kinds.yaml` declaram `reversible: true\|false`, e um teste derruba o gate quando algum falta |
| **MUST** | Limiar de severidade declarado em `rules/catalog/debate_gate.yaml` (`debate_severities: [P0, P1]`) |
| **MUST** | `expected_information_gain` sai em `refused` com motivo; nenhuma saída cita economia, ganho ou ROI medido |
| **SHOULD** | `arbitrate` grava um trace `kind: debate_gate` por plano, com id content-addressed próprio, sem mudar o trace `arbitration` |
| **SHOULD** | `signals` traz `complexity` (participantes) e `contradiction_count` (contradições diretas do case), medidos e fora da ordem de decisão |
| **COULD** | Manual `docs/guia/usos/` do debate ganha a seção do gate |

---

## Success Criteria

- [ ] 4 de 4 vereditos (`experimentar_antes`, `debater`, `nao_debater`, `unresolved`) cobertos por golden ou teste de unidade com findings sintéticos
- [ ] O par real (`SF-GRAPH-005` × `SF-LF-001`) sai `debater`; os 13 goldens de `fixtures/debate/` passam sem regravação, e o `brief.json` de `retomada` continua igual byte a byte
- [ ] 3 de 3 recusas novas do `debate start` deixam o estado do case byte a byte igual
- [ ] 70 de 70 `kind` com `reversible` declarado
- [ ] 0 ocorrência de "economia", "ganho", "ROI" medido ou "saving" nos textos que o gate emite (teste por varredura)
- [ ] Tools continuam 103; suíte em 9 lotes com 0 falha; gates de lastro, números e superfície sem divergência

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Par real | União das fixtures da regra 29 (P0 + P1, arbitragem `experiment`, 0 lacuna citando o par) | `arbitrate` | `debate_gate.verdict = debater`, `reasons` nomeia a severidade; `debate start` abre como hoje |
| AT-002 | Medida antes | Findings sintéticos cujo `Unknown` cita uma das regras do par e tem experimento que o mede | `arbitrate`, depois `debate start` | `experimentar_antes`; `start` recusa `gate_experimentar_antes` nomeando o experimento; nada gravado |
| AT-003 | Barato para debater | Dois findings P2/P3, `kind` reversíveis, sem lacuna, arbitragem `experiment` | `arbitrate`, depois `debate start` | `nao_debater`; `start` recusa `gate_nao_debater` com as duas ações e o `rollback` de cada uma |
| AT-004 | Irreversível | P2 com `kind` de `reversible: false` | `arbitrate` | `debater`, motivo `irreversivel` |
| AT-005 | Sem lastro | P3 reversível com arbitragem `escalate` | `arbitrate` | `debater`, motivo `escalate` |
| AT-006 | Sinal faltando | `kind` sem `reversible` numa política de teste, ou finding sem `severity` | `arbitrate`, depois `debate start` | `unresolved` nomeando o sinal; `start` recusa `gate_unresolved` |
| AT-007 | Política ausente ou inválida | `debate_gate.yaml` inválido | `arbitrate` | Plano emitido do mesmo jeito, `debate_gate.verdict = unresolved` com a mensagem (regra 27) |
| AT-008 | Sinais | Qualquer plano aberto | Ler `debate_gate.signals` | `severity`, `reversible`, `arbitration`, `evidence_gap`, `complexity`, `contradiction_count`; `refused.expected_information_gain` com motivo |
| AT-009 | Vocabulário | `action_kinds.yaml` | Teste de vocabulário | 70 `kind` com `reversible` booleano; `kind` sem ele derruba o teste |
| AT-010 | Trace | AT-001 | Ler `traces.jsonl` do blackboard | Um trace `debate_gate` com id próprio; o id do trace `arbitration` igual ao de antes |
| AT-011 | Sem afirmação de ganho | Todos os textos do gate | Varredura | Nenhuma frase de economia ou ganho |
| AT-012 | Enum de recusa | `_DEBATE_REFUSAL_REASONS` e as constantes de `debate_run` | `test_cli_debate` e paridade MCP | Mesmo conjunto; enum cresce com os valores antigos primeiro, declarado na exceção da paridade |

---

## Out of Scope

- `--force` no `debate start` (sobrescrever o veredito)
- Tool ou verbo `debate gate` separado
- Gate sobre contradição condicional (`Objection`): só contradição direta vira plano hoje
- Calcular `expected_information_gain` (sem modelo de probabilidade; regra 23)
- Pesos, nota ou limiar numérico sobre os sinais
- Afirmar economia de debate evitado (regra 30)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `_arbitra_pares` é o caminho único de `run_executor` e `open_debate_plans` | O gate é chamado ali, e só ali |
| Technical | O plano congelado copia `entrada["plan"]`, e o `debate_id` é o hash dele | `debate_gate` fica ao lado de `plan` na entrada, nunca dentro dele |
| Technical | `sparkforge_debate_start` está no golden de paridade MCP 1.29 | Enum de recusa crescido declarado em `REESCRITAS_DEPOIS_DO_GOLDEN` |
| Technical | `gate` já nomeia o portão do `report github` em `tools.py` | O bloco se chama `debate_gate` |
| Technical | Regra 27: instrumentação e política inválida não derrubam a emissão do plano | Falha de política vira `unresolved` com motivo |
| Technical | Regras 23 e 30 | Nada chama provider; nada afirma ganho |
| Technical | Repo público | Findings e facts sintéticos |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/agentic/executor/{gate,run,debate_run}.py`, `rules/catalog/{action_kinds,debate_gate}.yaml`, `sparkforge/adapters/tools.py` (enum e descrições) | Estende os executores determinístico e de debate |
| **KB Domains** | Nenhum domínio do agentspec cobre arbitragem; padrões do repositório (`plan.py`, `digest`, `proof_axes.yaml`, recusas nomeadas do `debate_run`) | O design lê esses módulos |
| **IaC Impact** | None | |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Com `debate_gate` ao lado de `plan` na entrada, o plano congelado não muda | `debate_id` e `brief.json` de `retomada` mudariam | [x] `_plano_congelado` copia só `plan`, `recommendation` e `reason` |
| A-002 | `debate_plans` do `arbitrate` tem itens `{"type": "object"}` | Mudança de schema no `arbitrate` | [x] `tools.py`, schema de `debate_plans` |
| A-003 | `sparkforge_debate_start` está no golden 1.29 | Exceção de paridade desnecessária ou esquecida | [x] `fixtures/mcp_parity/tools_list_{stdio,http}.json` |
| A-004 | `experiments_from` liga cada experimento ao `Unknown` que ele mede, de modo que "lacuna citando o par com experimento" é conferível | `experimentar_antes` sem base | [ ] conferir em `executor/unknowns.py` no design |
| A-005 | A reversibilidade de cada um dos 70 `kind` é decidível pela descrição e pelas regras que o usam | Declaração errada muda veredito | [ ] lista revisada no design, com o critério escrito no cabeçalho do YAML |
| A-006 | `finding.severity` é a severidade efetiva (depois de `severity_by`), não o `severity_default` | Limiar aplicado à severidade errada | [x] `sparkforge/findings/models.py` |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Todo par aberto vira debate, sem triagem |
| Users | 3 | Operador, host e revisor |
| Goals | 3 | MoSCoW com seis MUST |
| Success | 3 | Vereditos, goldens intactos, recusas sem gravação, vocabulário e varredura medidos |
| Scope | 2 | A-004 e A-005 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-004 e A-005 são conferências de design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | define-agent | Initial version, a partir de BRAINSTORM_DEBATE_ROI_GATE.md |
| 1.1 | 2026-09-14 | ship-agent | Shipped and archived (PR #70) |

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_DEBATE_ROI_GATE.md`
