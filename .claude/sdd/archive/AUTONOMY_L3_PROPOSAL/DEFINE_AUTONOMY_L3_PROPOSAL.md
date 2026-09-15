# DEFINE: Autonomia L3 — pacote de proposta de PR

> `sparkforge change propose --sandbox <id>` monta em `.sparkforge/proposal/<id>/` o pacote de um PR — patch, rollback, corpo assinado, evidência, recibo e os comandos que o host roda — a partir de um sandbox já validado, sem executar git nem gh.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L3_PROPOSAL |
| **Date** | 2026-09-14 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O sandbox do L2 prova o que um diff move nos achados, mas termina num `report.json`: transformar isso num PR revisável é trabalho manual do operador, e nada impede um PR que introduza achado P0/P1, que parta de uma árvore diferente da validada ou que afirme ganho sem medida.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador que rodou o sandbox | Leva a mudança de configuração até produção | Montar patch, rollback, corpo e comandos à mão a partir do `report.json` |
| Revisor do PR | Aprova a mudança | Não sabe se a evidência corresponde à árvore do PR, nem o que ainda falta medir |
| Host (agente com git/gh) | Abre o PR | Precisa de um roteiro fechado e de pontos de confirmação |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `change propose --sandbox <id>` monta o pacote em `.sparkforge/proposal/<id>/` sem executar git ou gh (`git_run: false`, `main_tree_touched: false`, `applied: false`) |
| **MUST** | Recusas antes de gravar: `sandbox_inexistente`, `sandbox_nao_aplicado`, `sandbox_desatualizado`, `achado_novo_bloqueante` |
| **MUST** | Pacote com `change.patch`, `rollback.patch`, `pr_body.md`, `commit_message.txt`, `branch.txt`, `commands.md`, `evidence/sandbox_report.json`, `evidence/receipt.json`, `manifest.json` |
| **MUST** | `pr_body.md` nunca afirma ganho; medida ausente sai como obrigação pendente |
| **MUST** | Tool `sparkforge_change_propose` (`_WRITE_IDEMPOTENT`, `now` obrigatório), dono `sf-verifier` |
| **SHOULD** | `pr_body.md` assinado pelo `report sign` com os findings de `after/`, conferível por `report verify` |
| **SHOULD** | Anexos medidos opcionais: `--benchmark` (facts de `bench.*`) e `--funcval` (resultado de `funcval compare`) viram seção do PR |
| **SHOULD** | Skill `propose-change-pr` para o host, e `git push *` e `gh pr create *` como `ask` na policy padrão |
| **COULD** | Manual `docs/guia/usos/change.md` ganha a seção do L3 |

---

## Success Criteria

- [ ] Golden do pacote igual byte a byte em 2 execuções seguidas com o mesmo `now` (idempotência)
- [ ] 4 de 4 recusas cobertas por golden ou teste de unidade, cada uma sem nenhum arquivo gravado
- [ ] `report verify` devolve `status: verified` para o `pr_body.md` de 1 pacote golden
- [ ] 0 chamada a `subprocess`, `git` ou `gh` em `sparkforge/change/proposal.py` (teste por AST)
- [ ] `git apply --check` do `change.patch` passa contra a árvore de origem no teste, e o `rollback.patch` devolve os bytes originais
- [ ] Policy padrão com 2 regras novas em `ask`, e `.claude/settings.json` regenerado com `Bash(git push *)` e `Bash(gh pr create *)`
- [ ] Tools 102 -> 103; suíte em 9 lotes com 0 falha; gates de lastro, números e superfície sem divergência

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Pacote completo | Sandbox aplicado sobre `main.tf` com o valor do `tune` | `change propose --sandbox <id> --now <iso>` | Os 9 arquivos gravados; `manifest.json` com sha256 de cada um |
| AT-002 | Idempotência | AT-001 | Rodar de novo com o mesmo `now` | Bytes idênticos |
| AT-003 | Sandbox inexistente | `id` sem `report.json` | `change propose` | `sandbox_inexistente`, nada gravado |
| AT-004 | Sandbox recusado | `report.json` com `applied: false` | `change propose` | `sandbox_nao_aplicado` |
| AT-005 | Árvore mudou | Arquivo do repo editado depois do sandbox | `change propose` | `sandbox_desatualizado` com os caminhos |
| AT-006 | Achado novo P0/P1 | Sandbox cujo `new` tem um P1 | `change propose` | `achado_novo_bloqueante` com rule_id e subject |
| AT-007 | P2/P3 novo | Sandbox cujo `new` tem só P3 | `change propose` | Pacote gravado; o P3 aparece em "atenção" no `pr_body.md` |
| AT-008 | Sem medida | Sem `--benchmark`/`--funcval` | `change propose` | `pr_body.md` lista benchmark e funcval como obrigações PENDENTES; nenhuma frase de ganho |
| AT-009 | Com medida | `--benchmark` com `bench.run_delta` | `change propose` | Seção de medida com os deltas e o fact_id, sem conclusão de ganho |
| AT-010 | Assinatura | AT-001 | `report verify --report pr_body.md --findings after/.sparkforge/scan/findings.json` | `verified` |
| AT-011 | Recibo | AT-001 | Ler `evidence/receipt.json` | Raiz em `after/`, facts e findings do scan, spans `unresolved` |
| AT-012 | Patch aplica | AT-001 | `git apply --check` numa cópia da árvore de origem | Passa; `rollback.patch` devolve os bytes |
| AT-013 | Sem git no pacote | `proposal.py` | Teste por AST | Nenhum import de `subprocess` nem chamada de `git`/`gh` |
| AT-014 | Policy | Policy padrão | `policy sync-settings` | `permissions.ask` com as duas regras novas |

---

## Out of Scope

- Executar git ou gh dentro do pacote
- `change propose --clean`
- Labels, revisores e `--draft` no `gh pr create`
- L4 (aplicar na árvore principal) e L5
- Rodar benchmark ou funcval: o pacote só anexa o que já foi medido

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Nada de `subprocess` no pacote (regra do §15 e do L2) | Os comandos viram texto em `commands.md` |
| Technical | Tool nova move os registros manuais (lista de tools, autorização, paridade de capacidade, agentes, manifest, surface, claims, policy sync) | Registros no build |
| Technical | `pr_body.md` termina no bloco de assinatura; `report sign` recusa texto depois dele | O corpo é fechado antes de assinar |
| Technical | `.sparkforge/proposal/` ignorado pelo git | `.gitignore` ganha a linha |
| Technical | Repo público | Fixtures sintéticos no molde de `fixtures/change/` |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/change/{proposal,refusals}.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `skills/propose-change-pr/`, `.sparkforge/policy.yaml`, `.gitignore` | Estende o módulo do §15 |
| **KB Domains** | Nenhum domínio do agentspec cobre o fluxo; padrões do próprio repositório (sandbox, receipt, report sign, skill `run-debate`) | O design lê os três módulos |
| **IaC Impact** | None | |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `before/` do sandbox é cópia byte a byte da árvore de origem (menos os pulos), e comparar cada arquivo do inventário atual com ela detecta árvore mudada | `sandbox_desatualizado` falso positivo ou negativo | [x] `sandbox.executar` copia `copia.origens` para `before/` |
| A-002 | O diff original não fica guardado; `change.patch` regenerado de `before/` para `after/` nos `files_changed` equivale a ele para `git apply` | Patch diferente do validado | [ ] conferir com `git apply --check` no build |
| A-003 | O scan de `after/` deixa `facts_<analyze>.json` e `findings.json` em `after/.sparkforge/scan/`, entrada válida para `receipt_emit` e `report sign` | Recibo e assinatura sem entrada | [x] `_scan_gravar` |
| A-004 | O bloco de assinatura do `report sign` não atrapalha a leitura do corpo no GitHub | Corpo do PR poluído | [ ] conferir os delimitadores no design |
| A-005 | O recibo aceita montar a parte de spans como `unresolved` sem `run_id` do processo | Recibo dependente das chamadas anteriores | [ ] conferir em `sparkforge/receipt/` no design |
| A-006 | Regra `bash` com `ask` vira `Bash(<regra>)` no `permissions.ask` pelo `sync-settings` | Confirmação só na skill | [x] `policy/settings.py::regras_ask` |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Lacuna entre o sandbox e o PR, e os três riscos nomeados |
| Users | 3 | Operador, revisor e host |
| Goals | 3 | MoSCoW com cinco MUST |
| Success | 3 | Idempotência, recusas, verificação, AST e policy medidos |
| Scope | 2 | A-002, A-004 e A-005 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-002, A-004 e A-005 são conferências de design e build.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | define-agent | Initial version, a partir de BRAINSTORM_AUTONOMY_L3_PROPOSAL.md |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_AUTONOMY_L3_PROPOSAL.md`
