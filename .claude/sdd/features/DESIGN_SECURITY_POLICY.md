# DESIGN: Security Policy

> Technical design for implementing Security Policy (§16)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SECURITY_POLICY |
| **Date** | 2026-09-13 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SECURITY_POLICY.md](./DEFINE_SECURITY_POLICY.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
                     .sparkforge/policy.yaml  (schema, commitado)
                                 |
            sparkforge/policy/load.py: carregar() -> Politica | PolicyError
                 |                         |                          |
                 v                         v                          v
   hook.py (PreToolUse,             adapters/mcp.py main()      settings.py
   matcher Bash|Edit|Write)         -> para_call_policy()        sync-settings
   decide.py: dividir_comando,      -> build_server(policy=...)  -> .claude/settings.json
   decidir_bash, decidir_caminho    -> call_tool(policy=...)        permissions.ask
   deny: exit 2 + motivo            -> authorize(): denied,       (Bash(...), Edit(...),
   senao: exit 0 sem saida             classe/aprovacao,           Write(...),
   (importa so policy/ + yaml)         raizes [repo+extra_roots])  mcp__sparkforge__<tool>)
                                   policy invalida: toda chamada
                                   recusada (POLICY_INVALID)

   CLI: policy check | explain --bash/--path/--tool | sync-settings [--check]
   Tool: sparkforge_policy_explain (READ_ONLY)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `sparkforge/policy/schema.py` | Schema da policy (dict JSON Schema) e validacao | `jsonschema` (dependencia ja declarada) |
| `sparkforge/policy/load.py` | `carregar(raiz)`: acha `.sparkforge/policy.yaml`, valida, devolve `Politica` ou levanta `PolicyError`; `None` sem arquivo | `yaml` |
| `sparkforge/policy/decide.py` | Puro: `dividir_comando`, `decidir_bash`, `decidir_caminho`, `decidir_tool` -> `Decisao(decision, rule, reason)` | `fnmatch`, `re` |
| `sparkforge/policy/hook.py` | `python -m sparkforge.policy.hook`: le o stdin do Claude Code, decide, sai 2 com motivo em `deny` | stdlib + os dois acima |
| `sparkforge/policy/settings.py` | Gera `permissions.ask` a partir das regras `ask`; `--check` compara | `json` |
| `sparkforge/policy/mcp.py` | `para_call_policy(politica, raiz)`: `CallPolicy` com allowlist = catalogo menos `denied`, aprovacoes da policy, raizes | importa `adapters.tools` (so no servidor, nunca no hook) |
| `agents/autonomy.py` | `root` passa a aceitar uma sequencia de raizes | mudanca local em `_argumento_fora_da_raiz` |
| `adapters/mcp.py` | `build_server(transport, policy=None)`; `main()` carrega a policy | `functools.partial(call_tool, policy=...)` |
| `adapters/{_core,cli,tools}.py` | Verbos `policy check|explain|sync-settings`, tool `sparkforge_policy_explain` | padrao dos verbos existentes |

---

## Key Decisions

### Decision 1: Uma fonte, tres portas; o hook so aplica `deny`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** O `PreToolUse` do Claude Code so decide `allow`/`deny` (documentacao oficial, busca literal por `"ask"`: NOT FOUND). `ask` existe nas regras `permissions.ask`, avaliadas deny -> ask -> allow, e pedem confirmacao ate em modo auto.

**Choice:** `.sparkforge/policy.yaml` e a fonte. Regras `deny` sao aplicadas pelo hook (Bash, Edit, Write) e pelo servidor MCP (`tools.denied`). Regras `ask` viram `permissions.ask` geradas por `policy sync-settings`, com `--check` no teste. As aprovacoes de classe sao declaradas na policy e passadas a `CallPolicy`.

**Rationale:** cada porta faz so o que o mecanismo dela sustenta, e as tres leem a mesma decisao de `decide.py`.

**Alternatives Rejected:**
1. `ask` virar `deny` no hook - rejeitado pelo operador no brainstorm: mais atrito, mesma protecao.
2. Hook para tools MCP - rejeitado: o servidor ja impoe, e o hook pagaria 0,476 s de import de `adapters.tools` por chamada.

**Consequences:**
- `permissions.ask` do `.claude/settings.json` passa a ser GERADO: editar a mao faz `--check` falhar.
- O limite da documentacao ("a Bash rule ... isn't a security boundary around the program") vale para o hook tambem, e vai declarado no `THREAT-MODEL.md`.

---

### Decision 2: A policy e carregada na fronteira do servidor MCP, e policy invalida recusa tudo

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** `call_tool` e chamado por todos os testes de tools, com caminhos temporarios; carregar a policy dentro dele mudaria todos. `build_server` ja monta `executar = functools.partial(call_tool, channel="mcp", transport=...)`.

**Choice:** `build_server(transport, policy=None)` repassa `policy` no `partial`. `main()` carrega `carregar(raiz)`, com `raiz = CLAUDE_PROJECT_DIR` ou o diretorio corrente. Sem arquivo: `policy=None`, comportamento de hoje. Policy invalida: o servidor sobe e toda chamada devolve `error_code: POLICY_INVALID` com o erro de schema (o operador ve por que, e nada roda sob uma politica que ele acredita valer).

**Rationale:** nao-regressao medida (os testes chamam `build_server()` sem `main()`); fail-closed onde a policy existe.

**Alternatives Rejected:**
1. Carregar dentro de `call_tool` - rejeitado: muda todos os testes e todo uso da CLI.
2. Servidor que nao sobe com policy invalida - rejeitado: o cliente ve "nao conecta" sem pista; o erro por chamada nomeia a causa.

**Consequences:**
- A CLI nao aplica a policy (ela e a porta do operador humano); a policy governa agentes.

---

### Decision 3: Casamento de comando -- quebra de composto, sintaxe do Claude Code

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** `dividir_comando(cmd)` separa em `&&`, `||`, `;`, `|` e quebra de linha; desembrulha `$( )`, crase e `( )`; tira atribuicoes iniciais `VAR=valor` e os invólucros `sudo`, `env`, `nohup`, `time`, `timeout <n>`; recursa em `bash -c "<...>"` / `sh -c`. Cada subcomando e casado com `fnmatch` contra a regra na sintaxe do Claude Code (`terraform destroy *` casa `terraform destroy -auto-approve`; `terraform destroy` sozinho casa exato ou com argumentos). Caminho: `file_path` do Edit/Write relativo a raiz, casado com a regra de `paths` (`rules/catalog/**`, `*.tf` em qualquer profundidade).

**Rationale:** a mesma sintaxe permite geracao 1:1 para `Bash(...)` e `Edit(...)`, e a quebra cobre as formas que a documentacao do Claude Code tambem cobre.

**Consequences:** alias de shell, script que chama `terraform` por dentro e invocacao por caminho absoluto (`/usr/bin/terraform`) nao casam -- limite declarado.

---

### Decision 4: Varias raizes na cadeia

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Context:** A-003. `_argumento_fora_da_raiz(arguments, root)` confere cada caminho com `resolve_within(root, valor)`.

**Choice:** `root` aceita `Path | str | Sequence[Path | str]`; o caminho e aceito se `resolve_within` o aceita em alguma raiz. Com uma raiz, a decisao e a de hoje (teste de nao-regressao).

---

### Decision 5: Policy padrao e aprovacoes

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-13 |

**Choice:** `.sparkforge/policy.yaml` commitado:

```yaml
version: 1
tools:
  denied: []
  approvals: [LOCAL_MUTATION, CLOUD_READ, CLOUD_MUTATION]
  ask:
    classes: [CLOUD_MUTATION]
extra_roots: []
bash:
  - {rule: "terraform destroy *", decision: ask, reason: "destroi infraestrutura"}
  - {rule: "terraform apply *", decision: ask, reason: "muda infraestrutura"}
  - {rule: "aws s3 rm *", decision: ask, reason: "apaga objetos no S3"}
  - {rule: "aws lakeformation revoke-permissions *", decision: ask, reason: "tira permissao"}
  - {rule: "*expire_snapshots*", decision: ask, reason: "manutencao destrutiva do Iceberg (regra 10)"}
paths:
  - {rule: "rules/catalog/**", decision: ask, reason: "muda o catalogo de regras"}
  - {rule: "**/*.tf", decision: ask, reason: "muda infraestrutura declarada"}
```

**Rationale:** `authorize()` exige aprovacao para LOCAL_MUTATION, CLOUD_READ, CLOUD_MUTATION e DESTRUCTIVE; pre-aprovar as tres que o catalogo usa mantem o MCP de hoje (AT-012). DESTRUCTIVE fica sem aprovacao de proposito (classe sem membro hoje). `ask` de CLOUD_MUTATION vira `mcp__sparkforge__<tool>` em `permissions.ask`, e o Claude Code pergunta.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/policy/__init__.py`, `schema.py`, `load.py` | Create | Schema, carga, `Politica`, `PolicyError` | @python-developer | None |
| 2 | `sparkforge/policy/decide.py` | Create | Decisao pura e quebra de comando | @python-developer | 1 |
| 3 | `sparkforge/policy/hook.py` | Create | Entrada do `PreToolUse` | @python-developer | 1, 2 |
| 4 | `sparkforge/policy/settings.py` | Create | Geracao e conferencia de `permissions.ask` | @python-developer | 1 |
| 5 | `sparkforge/policy/mcp.py` | Create | `para_call_policy` | @python-developer | 1 |
| 6 | `sparkforge/agents/autonomy.py` | Modify | Varias raizes | @python-developer | None |
| 7 | `sparkforge/adapters/mcp.py` | Modify | `build_server(policy=)`, carga no `main()`, `POLICY_INVALID` | @python-developer | 5 |
| 8 | `sparkforge/adapters/{_core,cli,tools}.py` | Modify | Verbos e tool `sparkforge_policy_explain` | @python-developer | 2, 4 |
| 9 | `.sparkforge/policy.yaml` | Create | Policy padrao | (general) | 1 |
| 10 | `.claude/settings.json` | Modify | Hook `PreToolUse` e `permissions.ask` gerado | (general) | 3, 4, 9 |
| 11 | `fixtures/policy/<caso>/` + `tests/test_fixtures_golden_policy.py` | Create | Stdin do hook, policy e decisao esperada; hook por subprocess | @test-generator | 3 |
| 12 | `tests/test_policy_decide.py`, `tests/test_policy_mcp.py` | Create | Unidade da decisao, varias raizes, servidor com policy | @test-generator | 2, 5, 6, 7 |
| 13 | `tests/test_execution_surface.py` | Modify | Comando do hook em `HOOKS_DO_PROJETO` | (general) | 10 |
| 14 | Registros de tool nova, `agents/sf-security-reviewer.md`, `docs/guia/usos/politica-de-seguranca.md`, referencia, `THREAT-MODEL.md`, `AUTHORIZATION-CHAIN.md`, `CURRENT-HARNESS-GAP.md`, STATUS, contagens, surface, claims | Modify/Create | Tool nova e documentacao | (general) | 8 |

**Total Files:** 14 entradas

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-8 | Python puro com dataclasses, no molde dos modulos do projeto |
| @test-generator | 11, 12 | Unidade e golden pytest |
| (general) | 9, 10, 13, 14 | Configuracao, registros e docs do proprio repositorio; build direto |

---

## Code Patterns

### Pattern 1: Decisao pura

```python
from dataclasses import dataclass
from fnmatch import fnmatchcase

ALLOW, ASK, DENY = "allow", "ask", "deny"
_ORDEM = {DENY: 0, ASK: 1, ALLOW: 2}


@dataclass(frozen=True)
class Decisao:
    decision: str
    rule: str | None = None
    reason: str | None = None
    segment: str | None = None


def _casa(regra: str, segmento: str) -> bool:
    if regra.endswith(" *"):
        base = regra[:-2]
        return segmento == base or fnmatchcase(segmento, regra)
    return fnmatchcase(segmento, regra)


def decidir_bash(comando: str, regras: list[dict]) -> Decisao:
    melhor = Decisao(ALLOW)
    for segmento in dividir_comando(comando):
        for regra in regras:
            if _casa(regra["rule"], segmento) and _ORDEM[regra["decision"]] < _ORDEM[melhor.decision]:
                melhor = Decisao(regra["decision"], regra["rule"], regra.get("reason"), segmento)
    return melhor
```

### Pattern 2: Hook

```python
import json
import os
import sys
from pathlib import Path


def main() -> int:
    from sparkforge.policy.decide import DENY, decidir_entrada
    from sparkforge.policy.load import PolicyError, carregar

    entrada = json.load(sys.stdin)
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or ".")
    try:
        politica = carregar(raiz)
    except PolicyError as exc:
        print(f"sparkforge policy invalida: {exc}", file=sys.stderr)
        return 2
    if politica is None:
        return 0
    decisao = decidir_entrada(entrada, politica, raiz)
    if decisao.decision == DENY:
        print(f"bloqueado pela policy ({decisao.rule}): {decisao.reason}", file=sys.stderr)
        return 2
    return 0
```

### Pattern 3: Hook no `.claude/settings.json`

```json
{
  "matcher": "Bash|Edit|Write",
  "hooks": [
    {"type": "command", "command": "python -m sparkforge.policy.hook", "timeout": 10,
     "statusMessage": "sparkforge: conferindo a policy..."}
  ]
}
```

---

## Data Flow

```text
1. Claude Code vai rodar Bash/Edit/Write -> stdin do hook {tool_name, tool_input, cwd}
   |
   v
2. carregar(CLAUDE_PROJECT_DIR): sem arquivo -> exit 0; invalida -> exit 2
   |
   v
3. decidir_entrada: Bash -> dividir_comando -> regras bash; Edit/Write -> file_path relativo -> regras paths
   |
   v
4. deny -> exit 2 + motivo; ask/allow -> exit 0 (o ask ja esta em permissions.ask e o Claude Code pergunta)

MCP: main() -> carregar -> para_call_policy -> build_server(policy) -> call_tool(policy) -> authorize(roots)
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Claude Code hooks (`PreToolUse`) | stdin JSON / exit code | Nenhuma |
| Claude Code permissions (`permissions.ask`) | `.claude/settings.json` gerado | Nenhuma |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | Quebra de comando, casamento, schema, geracao de `ask`, varias raizes | `tests/test_policy_decide.py` | pytest | AT-001 a AT-003, AT-009 |
| Golden (subprocess) | `python -m sparkforge.policy.hook` com stdin de fixture e `CLAUDE_PROJECT_DIR` no caso | `tests/test_fixtures_golden_policy.py` | pytest | AT-004 a AT-008, AT-013 |
| Integracao MCP | `build_server(policy)`/`call_tool(policy)` com policy padrao, deny, invalida, caminho fora | `tests/test_policy_mcp.py` | pytest | AT-010 a AT-012 |
| Registros | Tool nova, hook na lista fechada, settings em dia | suites existentes | pytest | SC7 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Policy invalida (schema/YAML) | Hook exit 2 com a mensagem; servidor `POLICY_INVALID` por chamada; `policy check` exit 2 | No |
| `sparkforge` nao importavel no Python do hook | `ModuleNotFoundError` -> exit 1 (nao-bloqueante no Claude Code), stderr aparece | No |
| stdin sem JSON | exit 2 (nao ha como decidir) | No |
| `file_path` fora da raiz | decidido pelo caminho absoluto contra as regras; nunca lido | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `tools.denied` | list | `[]` | Tools recusadas no servidor |
| `tools.approvals` | list de classes | `[]` sem arquivo; padrao commitado: 3 classes | Classes pre-aprovadas |
| `tools.ask.classes` / `tools.ask.names` | list | `[]` | Viram `mcp__sparkforge__<tool>` em `permissions.ask` |
| `extra_roots` | list | `[]` | Raizes alem do repositorio |
| `bash[]`, `paths[]` | regras | padrao commitado | `rule`, `decision`, `reason` |

---

## Security Considerations

- A policy nunca amplia o que a cadeia recusa: perfil, denylist e confinamento continuam; ela so declara aprovacoes e recusas.
- Limite declarado: regra casa texto, nao programa (documentacao do Claude Code); `THREAT-MODEL.md` registra.
- `bypassPermissions` pula `permissions.ask` (documentado); o hook `deny` continua valendo nesse modo.
- O hook nao escreve nada e nao acessa rede.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | stderr do hook no `deny`; o Claude Code o mostra |
| Metrics | Nenhuma nova |
| Tracing | Recusa do servidor ja vai ao ledger por `call_tool` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | design-agent | Versao inicial; A-003 (varias raizes) e A-004 (`CLAUDE_PROJECT_DIR`) resolvidos |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SECURITY_POLICY.md`
