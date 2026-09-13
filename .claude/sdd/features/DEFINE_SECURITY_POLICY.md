# DEFINE: Security Policy

> Uma politica declarada (`.sparkforge/policy.yaml`) imposta em tres portas -- servidor MCP, hook `PreToolUse` e regras `permissions.ask` -- para que acao destrutiva por shell, escrita sensivel e tool que grava ou coleta passem por decisao registrada.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SECURITY_POLICY |
| **Date** | 2026-09-13 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Designed) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

A cadeia de autorizacao do SparkForge (`authorize()` + `CallPolicy`) decide e impoe dentro do processo Python, mas so quando alguem monta a politica em codigo, e nenhuma porta impede um agente de rodar `terraform destroy`, `aws s3 rm` ou editar `rules/catalog/` pelo shell: o T-024 do `THREAT-MODEL.md` continua Parcial, e o gap do hook `PreToolUse` (§41) esta declarado em tres documentos.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador que roda agentes no repositorio | Usa Claude Code com o SparkForge | Um agente pode destruir infraestrutura ou apagar dado pelo Bash sem confirmacao |
| Mantenedor de seguranca | Revisa o que o agente pode fazer | A politica nao e declarada nem inspecionavel: mora em codigo, e so onde alguem a montou |
| Agente host via MCP | Chama tools | Nao tem como perguntar "esta chamada seria permitida?" antes de tentar |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `.sparkforge/policy.yaml` com schema: `tools` (denied, approvals, ask por classe ou nome), `bash` e `paths` (regras na sintaxe do Claude Code com `decision: ask\|deny` e `reason`), `extra_roots` |
| **MUST** | Hook `PreToolUse` (`python -m sparkforge.policy.hook`, matcher `Bash\|Edit\|Write`) aplica as regras `deny`: exit 2 com o motivo; quebra comando composto antes de casar |
| **MUST** | `sparkforge policy sync-settings` gera `permissions.ask` no `.claude/settings.json` a partir das regras `ask` (Bash, Edit/Write e `mcp__sparkforge__<tool>`); `--check` falha quando diverge |
| **MUST** | O servidor MCP carrega a policy ao subir e a passa ao `call_tool`: `denied` recusa, classe sem aprovacao recusa, caminho fora do repositorio e das `extra_roots` recusa; sem arquivo, comportamento de hoje |
| **MUST** | Policy invalida: hook sai 2 e o servidor MCP recusa as chamadas com o erro de schema; `sparkforge` nao importavel: hook sai com erro nao-bloqueante e aviso |
| **MUST** | Policy padrao commitada: `terraform destroy`/`apply`, `aws s3 rm`, `aws lakeformation revoke-permissions`, `expire_snapshots`, escrita em `rules/catalog/**` e `*.tf`, e tools `CLOUD_MUTATION` em `ask`; nada em `deny`; classes de mutacao pre-aprovadas para nao recusar o que o MCP faz hoje |
| **SHOULD** | `sparkforge policy check` (valida e lista) e `sparkforge policy explain --bash\|--path\|--tool` (decisao e regra que casou), com a tool `sparkforge_policy_explain` READ_ONLY |
| **SHOULD** | `THREAT-MODEL.md` (T-024), `AUTHORIZATION-CHAIN.md` e `CURRENT-HARNESS-GAP.md` atualizados, com o limite "regra casa texto, nao programa" declarado |
| **COULD** | Aviso no `sparkforge doctor` quando `.claude/settings.json` diverge da policy |

---

## Success Criteria

- [ ] SC1: com a policy padrao, `policy explain --bash` devolve `ask` para os 5 padroes destrutivos inclusive compostos (`cd infra && terraform destroy -auto-approve`) e `allow` para `git status`; e as 7 regras `ask` (5 de Bash, 2 de caminho) mais as tools `CLOUD_MUTATION` aparecem em `permissions.ask` depois do `sync-settings`.
- [ ] SC2: uma regra `deny` faz o hook sair 2 com o motivo em 100% dos casos de `fixtures/policy/` que a casam, e sair 0 sem saida nos que nao casam.
- [ ] SC3: o hook responde em menos de 0,2 s por chamada (medido sobre os casos de fixture), sem importar `sparkforge.adapters.tools`.
- [ ] SC4: policy invalida faz o hook sair 2 e o `call_tool` do servidor recusar; o handler nao roda.
- [ ] SC5: sem `.sparkforge/policy.yaml`, hook e servidor MCP se comportam como hoje (os testes atuais de `call_tool` passam sem mudanca).
- [ ] SC6: com a policy padrao carregada, nenhuma tool que o MCP chama hoje com caminho dentro do repositorio passa a ser recusada; uma chamada com caminho fora da raiz e das `extra_roots` e recusada.
- [ ] SC7: tool nova com registros, `test_execution_surface` com o hook na lista fechada, surface e claims em dia; suite nos 9 lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Destrutivo em ask | policy padrao | `policy explain --bash "terraform destroy"` | `ask`, regra `terraform destroy *` |
| AT-002 | Composto | policy padrao | `explain --bash "cd infra && terraform destroy -auto-approve"` | `ask` (o subcomando casa) |
| AT-003 | Comum passa | policy padrao | `explain --bash "git status"` | `allow`, nenhuma regra |
| AT-004 | Deny no hook | policy com `aws s3 rm *` em deny | stdin do hook com `aws s3 rm s3://b/k` | exit 2, motivo no stderr/JSON |
| AT-005 | Hook sem regra | policy padrao | stdin com `ls` | exit 0 sem saida |
| AT-006 | Escrita sensivel | policy com `rules/catalog/**` em deny | stdin de `Edit` com `file_path` `rules/catalog/x.yaml` | exit 2 |
| AT-007 | Policy invalida | `policy.yaml` com `decision: talvez` | hook e `call_tool` do servidor | hook exit 2; `call_tool` recusa com erro de schema |
| AT-008 | Sem policy | repositorio sem o arquivo | hook e servidor | hook exit 0; `call_tool` como hoje |
| AT-009 | Geracao | policy padrao | `policy sync-settings` e depois `--check` | `permissions.ask` com as regras; `--check` sai 0; editar o settings a mao faz `--check` sair 1 |
| AT-010 | Tool negada | policy com `tools.denied: [sparkforge_scan]` | chamada MCP a `sparkforge_scan` | `UNAUTHORIZED`; o handler nao roda |
| AT-011 | Caminho fora | policy padrao | `sparkforge_analyze_pyspark` com `path` em `/tmp` | recusa por caminho fora da raiz; com `/tmp` em `extra_roots`, passa |
| AT-012 | Nao-regressao do MCP | policy padrao | cada tool de mutacao local chamada com caminho dentro do repo | nenhuma recusa nova |
| AT-013 | Hook barato | casos de `fixtures/policy/` | tempo por chamada | < 0,2 s |

---

## Out of Scope

- `max_cost`, `max_tokens`, `max_runtime`, `max_files_modified`, `SANDBOX_ONLY`, `ALLOW_WITH_LIMITS` (sandbox e o §15).
- `allowed_hosts`, `network_policy`, `data_classification`, AgentCore Gateway e Cedar.
- Hooks de modelo (regra 23), de commit, de deploy e `AfterToolCall`.
- Hook para tools MCP (o servidor ja impoe; o hook pagaria 0,48 s por chamada).
- `ask` pelo hook (o `PreToolUse` so decide `allow`/`deny`).

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | `PreToolUse` so decide `allow`/`deny`; `ask` so por `permissions.ask` (documentacao oficial, 2026-09-13) | Duas portas para a mesma regra, uma fonte |
| Technical | `tests/test_execution_surface.py`: lista fechada `HOOKS_DO_PROJETO` e `CONSTRUCOES_PROIBIDAS` (sem `$(`, crase, `eval`, pipe para shell, rede) | O comando do hook e `python -m ...` puro |
| Technical | `authorize()` exige aprovacao para LOCAL_MUTATION, CLOUD_READ, CLOUD_MUTATION e DESTRUCTIVE | A policy padrao pre-aprova as classes que o MCP usa hoje |
| Technical | Regra 23 e nao-regressao do `call_tool` sem policy | Carga da policy na fronteira do servidor, nao dentro do `call_tool` |
| Technical | Regra de Bash casa o texto do comando, nao o programa | Limite declarado; nao se afirma fronteira de seguranca |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/policy/` (novo), `sparkforge/adapters/{mcp,_core,cli,tools}.py`, `sparkforge/agents/autonomy.py` (raizes extras), `.sparkforge/policy.yaml`, `.claude/settings.json`, `fixtures/policy/`, `docs/harness/*.md` | O modulo de politica nao importa `adapters` |
| **KB Domains** | Nenhum dominio do KB do agentspec; fontes: documentacao oficial de hooks e permissoes do Claude Code, `docs/harness/AUTHORIZATION-CHAIN.md`, `THREAT-MODEL.md` | Consultar no design |
| **IaC Impact** | None | Regras sobre comandos de IaC, nada provisionado |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `PreToolUse` recebe `tool_name` e `tool_input.command` (Bash) / `tool_input.file_path` (Edit, Write) e respeita exit 2 como bloqueio | Hook nao morde | [x] documentacao oficial, 2026-09-13 (`file_path` a conferir no design) |
| A-002 | `permissions.ask` com `Bash(...)`, `Edit(...)` e `mcp__sparkforge__<tool>` pede confirmacao ate em modo auto | O `ask` nao aparece ao operador | [x] para Bash e Edit na documentacao de permissoes; MCP a conferir |
| A-003 | `authorize()` pode receber mais de uma raiz (repositorio + `extra_roots`) sem mudar a decisao de hoje com uma raiz | Refatorar o confinamento | [ ] conferir `_argumento_fora_da_raiz` no design |
| A-004 | O servidor MCP sabe a raiz do projeto ao subir (cwd ou `CLAUDE_PROJECT_DIR`) | Policy carregada do lugar errado | [ ] |
| A-005 | Gerar `permissions` no `.claude/settings.json` nao quebra `test_vendor_caveman` nem `test_execution_surface` | Gates vermelhos | [x] os dois so leem marketplace, plugins e hooks |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Gap declarado em tres documentos, com o T-024 |
| Users | 3 | Tres personas com dor nomeada |
| Goals | 3 | MoSCoW com as tres portas e o padrao |
| Success | 3 | Sete criterios com numero ou comportamento conferivel |
| Scope | 2 | A-003 e A-004 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

- A-003 (raizes extras na cadeia) e A-004 (raiz do projeto no servidor MCP): resolver no design, medindo.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | define-agent | Versao inicial a partir de BRAINSTORM_SECURITY_POLICY.md; confinamento com `extra_roots` decidido; `ask` das tools MCP por `permissions.ask` |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SECURITY_POLICY.md`
