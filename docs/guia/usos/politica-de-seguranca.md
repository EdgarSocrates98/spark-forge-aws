# Política de segurança: o que um agente pode fazer neste repositório

## Receita rápida

```bash
# 1. A policy é válida? Quais regras ela tem?
sparkforge policy check

# 2. O que ela decide para um comando, um caminho ou uma tool?
sparkforge policy explain --bash "cd infra && terraform destroy -auto-approve"
sparkforge policy explain --path rules/catalog/pyspark.yaml
sparkforge policy explain --tool sparkforge_collect_glue_job

# 3. Depois de editar a policy, gere as regras de confirmação do Claude Code
sparkforge policy sync-settings

# 4. No CI: falha se o .claude/settings.json ficou diferente da policy
sparkforge policy sync-settings --check
```

## Para que serve

O arquivo `.sparkforge/policy.yaml` diz o que um agente pode fazer sozinho, o que precisa da sua confirmação e o que é proibido. Uma política só vale em três lugares:

| Onde | O que cobre | O que faz |
|---|---|---|
| Hook `PreToolUse` do Claude Code | Comandos de shell (`Bash`) e escrita de arquivo (`Edit`, `Write`) | Bloqueia as regras `deny` |
| `permissions.ask` do `.claude/settings.json` | Os mesmos, mais as tools MCP | Pede sua confirmação nas regras `ask`, inclusive no modo auto |
| Servidor MCP do SparkForge | As tools do SparkForge | Recusa tool negada e caminho fora do repositório |

O hook do Claude Code só sabe permitir ou bloquear. Por isso o "pergunte antes" mora nas regras `permissions.ask`, geradas a partir da policy pelo `sync-settings`.

## A policy que vem com o repositório

Nada é proibido. Pedem confirmação: `terraform destroy`, `terraform apply`, `aws s3 rm`, `aws lakeformation revoke-permissions`, qualquer `expire_snapshots`, escrita em `rules/catalog/**` e em arquivos `.tf`, e as tools que coletam da AWS (`collect_*`).

```yaml
version: 1
tools:
  denied: []
  approvals: [LOCAL_MUTATION, CLOUD_READ, CLOUD_MUTATION]
  ask:
    classes: [CLOUD_MUTATION]
extra_roots: []
bash:
  - rule: "terraform destroy *"
    decision: ask
    reason: "destroi infraestrutura; confirme escopo"
paths:
  - rule: "rules/catalog/**"
    decision: ask
    reason: "muda o catalogo de regras"
```

| Campo | Quer dizer |
|---|---|
| `tools.denied` | Tools do SparkForge que o servidor MCP recusa |
| `tools.approvals` | Classes de tool que rodam sem pedir (as três acima são o que o MCP já fazia) |
| `tools.ask` | Classes ou nomes de tool que pedem confirmação |
| `extra_roots` | Pastas fora do repositório onde as tools podem ler e gravar (fora delas, recusa) |
| `bash`, `paths` | Regras na mesma sintaxe do Claude Code: `terraform destroy *` casa com e sem argumentos; `**/*.tf` casa em qualquer pasta |

## Como ler a resposta do `explain`

```json
{
  "active": true,
  "subject_kind": "bash",
  "decision": "ask",
  "rule": "terraform destroy *",
  "reason": "destroi infraestrutura; confirme escopo",
  "subject": "terraform destroy -auto-approve",
  "enforced_by": "permissions.ask do .claude/settings.json"
}
```

- `decision`: `allow` (roda), `ask` (você confirma) ou `deny` (bloqueado).
- `subject`: o pedaço do comando que casou. O SparkForge quebra comandos compostos (`&&`, `;`, `|`, `$( )`, `bash -c`) e tira `sudo`, `env` e atribuições do começo antes de comparar.
- `enforced_by`: qual das três portas aplica a decisão.

## Quando algo dá errado

| Sintoma | Causa | Solução |
|---|---|---|
| Todo comando de shell é bloqueado com "policy invalida" | O `policy.yaml` não passa no schema | `sparkforge policy check` mostra o erro |
| Toda tool MCP responde `POLICY_INVALID` | O mesmo, visto pelo servidor | Corrija o arquivo e reinicie o servidor MCP |
| Uma tool responde "aponta para fora da raiz do case" | O caminho está fora do repositório | Mova o arquivo ou acrescente a pasta em `extra_roots` |
| O hook não faz nada | O `sparkforge` não está instalado no Python do Claude Code | `pip install -e .` na raiz do repositório |
| `sync-settings --check` sai 1 | Alguém editou `permissions.ask` à mão | `sparkforge policy sync-settings` |

## O que ela não garante

Regra de shell compara o **texto** do comando, não o programa que roda. Um alias, um script que chama `terraform` por dentro ou o caminho completo do binário escapam dela; a própria documentação do Claude Code diz o mesmo das regras de permissão. Trate a policy como guarda-corpo contra o erro comum, não como fronteira de segurança. No modo `bypassPermissions`, as regras `ask` não perguntam; as `deny` do hook continuam valendo.

## Próximos passos

- Referência: [`sparkforge policy`](../referencia/cli/policy.md) e [`sparkforge_policy_explain`](../referencia/tools/sparkforge_policy_explain.md).
- O modelo de ameaça que isto cobre: `docs/harness/THREAT-MODEL.md`, item T-024.
