# BRAINSTORM: Security Policy

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SECURITY_POLICY |
| **Date** | 2026-09-13 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** §16 de `prompt_new_evo.md`, "A seguranca agentic pode virar outro grande diferencial": mapear o Forge ao OWASP Agent Control Standard (inspecionavel, rastreavel, instrumentavel, hooks de middleware, politicas declarativas, enforcement em runtime), com um `AgentPolicy` declarativo (`allowed_tools`, `allowed_paths`, `allowed_hosts`, `max_cost`, `network_policy`, `approval_policy`, `autonomy_level`...), hooks (`BeforeToolCall`, `BeforeShell`, `BeforeWrite`, `BeforeModelCall`...) e decisoes `ALLOW/DENY/ASK/SANDBOX_ONLY/ALLOW_WITH_LIMITS`; opcionalmente AgentCore Gateway + Cedar.

**Context Gathered:**
- A cadeia de autorizacao ja existe e e imposta: `sparkforge/agents/autonomy.py:authorize()` (classe de tool derivada das anotacoes MCP, allowlist, denylist, perfil como teto, aprovacao por classe, confinamento de caminho) e `CallPolicy`, que `adapters/tools.py:call_tool` consulta antes de despachar; o handler nao roda quando a decisao recusa. Mas ela so morde quando alguem monta uma `CallPolicy` em codigo.
- O gap declarado em `docs/harness/AUTHORIZATION-CHAIN.md`, `CURRENT-HARNESS-GAP.md` (§41) e `THREAT-MODEL.md` (T-024 Parcial): nao ha hook `PreToolUse`; `terraform destroy` por `Bash` nunca passa pela cadeia. `.claude/settings.json` so tem o hook `SessionStart` do caveman, travado por `tests/test_execution_surface.py::HOOKS_DO_PROJETO`.
- Protocolo conferido na documentacao oficial (2026-09-13): o `PreToolUse` recebe `tool_name` e `tool_input` (`command` no Bash) e so decide `allow`/`deny` -- `"ask"` NAO aparece como `permissionDecision` (busca literal no markdown da pagina de hooks: NOT FOUND). Exit 2 bloqueia; outro codigo nao-zero e erro nao-bloqueante. `ask` existe nas regras nativas `permissions.ask` do `settings.json`: avaliadas deny -> ask -> allow, pedem confirmacao ate em modo auto e dentro de subshell; so `bypassPermissions` pula. A propria documentacao avisa que regra de Bash casa o texto do comando e "isn't a security boundary around the program".
- Medido: importar `sparkforge.agents.autonomy` custa 0,036 s e `yaml` 0,019 s; `sparkforge.adapters.tools` custa 0,476 s -- o hook, que roda em todo Bash, nao pode importa-lo.
- Regra 23: o pacote nao chama modelo; `BeforeModelCall` nao tem o que interceptar aqui.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/policy/` (novo: schema, carga, `decide`, hook), `adapters/{_core,cli,tools}.py`, `.sparkforge/policy.yaml`, `.claude/settings.json`, `fixtures/policy/` | Ao lado de `agents/autonomy.py`, que continua a cadeia |
| Relevant KB Domains | Nenhum dominio do KB do agentspec cobre hooks do Claude Code; fontes: documentacao oficial de hooks e de permissoes, `AUTHORIZATION-CHAIN.md`, `THREAT-MODEL.md` | Consultar no design |
| IaC Patterns | Regras sobre `terraform`, `aws s3 rm`, `lakeformation revoke-permissions` | Nada de infraestrutura nova |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual o recorte? (policy declarada + hook / so hook / so policy) | **Policy declarada + hook** | Uma fonte, varias portas |
| 2 | Sem arquivo de politica, o que o hook faz? (policy padrao commitada / nada / default no codigo) | **Policy padrao commitada**; repo sem arquivo = hook nao faz nada | Fecha o T-024 neste repo sem regressao em outros |
| 3 | Se o hook quebrar? (para so com policy invalida / para sempre / passa sempre) | **Policy invalida bloqueia; pacote que nao importa passa com aviso** | Quem escreveu a policy acredita que ela morde |
| 4 | Que amostras? (entradas sinteticas do hook / so unidade / transcripts reais) | **Entradas sinteticas do hook** | `fixtures/policy/` com stdin, policy e decisao esperada |
| 5 | Onde mora a logica? (modulo unico / script fora / hook em shell) | **Modulo unico no pacote** | `sparkforge/policy/`, hook por `python -m` |
| 6 | Como realizar `ask`, se o hook so faz allow/deny? (gerar permissions.ask / padrao deny / ask vira deny) | **policy.yaml gera `permissions.ask`**; o hook so aplica `deny` | Uma fonte, gerador com teste de drift |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/policy/<caso>/input.json` | a criar | O JSON que o Claude Code manda no stdin (`tool_name`, `tool_input`) |
| Output examples | `fixtures/policy/<caso>/expected.json` | a criar | Decisao, regra que casou, codigo de saida do hook |
| Ground truth | Documentacao oficial de hooks e permissoes | 2 paginas | Formato do stdin, exit 2, precedencia deny -> ask -> allow |
| Related code | `agents/autonomy.py` (`authorize`, `CallPolicy`, `tool_class`), `tests/test_execution_surface.py`, `tests/test_harness_authorization.py` | 3 | Cadeia existente e a lista fechada de hooks |

**How samples will be used:**

- Casos: `terraform destroy` composto (`cd infra && terraform destroy`), `aws s3 rm`, `git status` (allow), policy invalida (bloqueia), Edit em `rules/catalog/**`, tool MCP de coleta sem aprovacao (via `call_tool`).

---

## Approaches Explored

### Approach A: Modulo unico no pacote ⭐ Recommended

**Description:** `sparkforge/policy/` com schema, carga e `decide()` puro; `call_tool` a usa quando ha `.sparkforge/policy.yaml`; o hook e `python -m sparkforge.policy.hook`; o gerador escreve `permissions.ask`.

**Pros:**
- Uma fonte, uma decisao, testavel sem Claude Code.
- O hook importa so o modulo de politica (~0,05 s).

**Cons:**
- O hook depende de `sparkforge` importavel no Python do host (tratado como fail-open com aviso).

**Why Recommended:** reusa a cadeia que ja existe e mantem a regra "hook consulta classe, nao lista de comandos a mao" do plano do harness.

---

### Approach B: Script fora do pacote

**Description:** `scripts/policy_hook.py` com loader proprio.

**Cons:**
- Duas leituras da mesma policy.

---

### Approach C: Hook em shell

**Description:** grep de padroes em bash; tools MCP so no `CallPolicy`.

**Cons:**
- Lista de comandos mantida a mao, recusada pelo plano do harness (I4).

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-13, nesta sessao |
| **Reasoning** | Uma fonte e uma decisao; hook barato; teste sem host |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | `.sparkforge/policy.yaml` com schema e a fonte unica | Politica declarativa e inspecionavel (OWASP ACS) | Politica montada so em codigo |
| 2 | Tres portas: `call_tool` (MCP: allow/deny/ask por aprovacao), hook `PreToolUse` matcher `Bash\|Edit\|Write` (so deny, exit 2), `permissions.ask` gerado (ask) | O hook nao faz `ask` (documentacao oficial) | `ask` virar deny |
| 3 | Policy padrao commitada: destrutivos em `ask`, nada em `deny` | Fecha T-024 neste repo com o menor atrito | Deny por padrao |
| 4 | Sintaxe de regra = a do Claude Code (`terraform destroy *`, `rules/catalog/**`) | Geracao 1:1 para `Bash(...)`/`Edit(...)` | Sintaxe propria |
| 5 | Hook quebra comando composto (`&&`, `;`, `\|`, subshell) antes de casar; limite "texto, nao programa" declarado no THREAT-MODEL | Honestidade sobre o que morde | Afirmar fronteira de seguranca |
| 6 | Policy invalida: hook exit 2 e `call_tool` recusa; `sparkforge` ausente: hook exit 0 com aviso no stderr | Quem escreveu acredita que morde; clone sem instalacao nao trava | Fail-closed sempre |
| 7 | Verbos `policy check`, `policy explain` (tool `sparkforge_policy_explain` READ_ONLY) e `policy sync-settings [--check]` (so CLI, razao declarada: grava `.claude/settings.json`) | Inspecionavel e rastreavel | Sem verbo |
| 8 | Dono: `sf-security-reviewer` | Area de seguranca | - |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| `max_cost`, `max_tokens`, `max_runtime`, `max_files_modified` | Orcamento ja mora em `budget show`; limite de arquivo exige contador de sessao | Yes |
| `SANDBOX_ONLY`, `ALLOW_WITH_LIMITS` | Sandbox e a frente §15 | Yes |
| `allowed_hosts`, `network_policy`, `data_classification` | O pacote nao chama rede fora dos `collect_*`; classificacao de dado nao tem fonte | Yes |
| Integracao AgentCore Gateway + Cedar | Exige servico externo | Yes |
| `BeforeModelCall`/`AfterModelCall` | Regra 23: nao ha chamada de modelo no pacote | No |
| `BeforeCommit`, `BeforeDeployment`, `AfterToolCall` | Commit e deploy sao Bash (cobertos pelo hook); os spans do `call_tool` ja registram depois | Yes |
| Hook para tools MCP | `call_tool` ja impoe dentro do processo; o hook pagaria 0,48 s por chamada importando `adapters.tools` | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Politica e portas: fonte unica, tres portas, falhas, ressalva de fronteira | ✅ | "Sim, segue" | No |
| Formato, verbos e testes | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
A cadeia de autorizacao do SparkForge decide e impoe dentro do processo Python, mas so quando alguem monta a politica em codigo, e nada impede um agente de rodar `terraform destroy`, `aws s3 rm` ou editar o catalogo de regras pelo shell: o T-024 continua Parcial.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador que roda agentes no repo | Um agente pode destruir infraestrutura ou apagar dado pelo Bash sem confirmacao |
| Mantenedor de seguranca | Politica nao e declarada nem inspecionavel; esta espalhada em codigo |
| Agente host via MCP | Nao tem como perguntar "esta chamada seria permitida?" antes de tentar |

### Success Criteria (Draft)
- [ ] Com a policy padrao, `terraform destroy` (inclusive composto) e `aws s3 rm` pedem confirmacao no Claude Code (regras `permissions.ask` geradas) e uma regra `deny` faz o hook sair 2 com o motivo.
- [ ] `git status` e comandos fora das regras passam sem custo perceptivel (hook < 0,2 s).
- [ ] Policy invalida: hook sai 2 e `call_tool` recusa; sem `sparkforge` importavel, o hook sai 0 com aviso.
- [ ] `policy sync-settings --check` falha quando `.claude/settings.json` diverge do `policy.yaml`.
- [ ] `call_tool` com policy presente recusa tool de classe que exige aprovacao sem ela, e o handler nao roda.

### Constraints Identified
- Regra 23 (sem provider), `test_execution_surface.py` (lista fechada de hooks e sem construcao de execucao arbitraria), nao-regressao do `call_tool` sem policy.
- Hook so com `allow`/`deny`; `ask` so por `permissions.ask`.

### Out of Scope (Confirmed)
- Limites de custo/token/tempo/arquivos, sandbox, rede, classificacao de dado, Cedar, hooks de modelo/commit/deploy, hook para tools MCP.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 6 (mais YAGNI) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SECURITY_POLICY.md`
