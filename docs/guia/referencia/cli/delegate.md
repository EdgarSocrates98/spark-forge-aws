<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws delegate`

Descobre, planeja e executa delegação governada a especialistas opcionais (data-sentinel, forge-doctor-data).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws delegate discover`](#sparkforge-aws-delegate-discover) | Descobre especialistas declarados: PATH, pacote, handshake, manifesto de capabilities. |
| [`sparkforge-aws delegate handoffs`](#sparkforge-aws-delegate-handoffs) | Lista EvidenceHandoffs persistidos em .sparkforge_aws/delegation/handoffs/. |
| [`sparkforge-aws delegate plan`](#sparkforge-aws-delegate-plan) | Planeja a delegação para uma intenção — determinístico, sem executar. |
| [`sparkforge-aws delegate run`](#sparkforge-aws-delegate-run) | Executa uma capability declarada de um especialista sob governança. |

## `sparkforge-aws delegate discover`

Descobre especialistas declarados: PATH, pacote, handshake, manifesto de capabilities.

```bash
sparkforge-aws delegate discover --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--provider` | não | `data-sentinel-forge`, `forge-doctor-data` |  |  |  |
| `--no-probe` | não | liga/desliga |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws delegate handoffs`

Lista EvidenceHandoffs persistidos em .sparkforge_aws/delegation/handoffs/.

```bash
sparkforge-aws delegate handoffs --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws delegate plan`

Planeja a delegação para uma intenção — determinístico, sem executar.

```bash
sparkforge-aws delegate plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `intent` (posicional) | sim | texto |  |  | Intenção em texto livre. |
| `--authorize` | não | `LOCAL_READ`, `LOCAL_WRITE`, `EXTERNAL_READ`, `EXTERNAL_WRITE`, `DESTRUCTIVE`, `COST_BEARING` | sim |  | Concede autorização a um nível de risco (pode repetir). |
| `--no-probe` | não | liga/desliga |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws delegate run`

Executa uma capability declarada de um especialista sob governança.

```bash
sparkforge-aws delegate run --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `provider` (posicional) | sim | `data-sentinel-forge`, `forge-doctor-data` |  |  |  |
| `capability` (posicional) | sim | texto |  |  | Id da capability declarada. |
| `--target` | não | texto |  |  | Arquivo/diretório alvo. |
| `--job` | não | texto |  |  | Nome do Glue job (sentinel). |
| `--run-id` | não | texto |  |  | Job run id (sentinel). |
| `--profile` | não | texto |  |  | AWS profile (sentinel cloud). |
| `--region` | não | texto |  |  | AWS region (sentinel cloud). |
| `--platform` | não | texto |  |  | Plataforma (sentinel analyze). |
| `--check` | não | texto |  |  | Check único (doctor scan). |
| `--timeout` | não | texto |  |  | Timeout em segundos. |
| `--no-persist` | não | liga/desliga |  |  |  |
| `--authorize` | não | `LOCAL_READ`, `LOCAL_WRITE`, `EXTERNAL_READ`, `EXTERNAL_WRITE`, `DESTRUCTIVE`, `COST_BEARING` | sim |  | Concede autorização a um nível de risco (pode repetir). Capabilities EXTERNAL_READ/COST_BEARING (glue diagnose, glue runs, etc.) não executam sem este grant. |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
