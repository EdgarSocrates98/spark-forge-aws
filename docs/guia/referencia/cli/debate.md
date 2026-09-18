<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge debate`

Conduz e arbitra o protocolo de debate do case. Nao gera argumento: quem escreve cada submissao e o host.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge debate next`](#sparkforge-debate-next) | O brief do lado da vez, ou `done` com a Decision. Grava a Decision no fechamento; depois dele devolve sempre o mesmo `done`. |
| [`sparkforge debate referee`](#sparkforge-debate-referee) | Diz se o fechamento declarado pode ser publicado: hipotese que sobrevive, claim sem evidencia, objecao sem replica, referencia pendurada. |
| [`sparkforge debate start`](#sparkforge-debate-start) | Congela o plano de debate do par --rules A,B em <repo>/.sparkforge/debate/<debate_id>/, a partir dos MESMOS insumos do `arbitrate`. Recusa `budget_undeclared` sem `budget:` no case.yaml. |
| [`sparkforge debate submit`](#sparkforge-debate-submit) | Valida e grava a submissao do lado da vez. Recusa por nome e deixa o estado igual. |

## `sparkforge debate next`

O brief do lado da vez, ou `done` com a Decision. Grava a Decision no fechamento; depois dele devolve sempre o mesmo `done`.

```bash
sparkforge debate next --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do case. |
| `--debate` | sim | texto |  |  | O `debate_id` que `start` devolveu. |

### Tool MCP equivalente

[`sparkforge_debate_next`](../tools/sparkforge_debate_next.md), [`sparkforge_debate_start`](../tools/sparkforge_debate_start.md), [`sparkforge_debate_submit`](../tools/sparkforge_debate_submit.md)

## `sparkforge debate referee`

Diz se o fechamento declarado pode ser publicado: hipotese que sobrevive, claim sem evidencia, objecao sem replica, referencia pendurada.

```bash
sparkforge debate referee --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_debate_referee`](../tools/sparkforge_debate_referee.md)

## `sparkforge debate start`

Congela o plano de debate do par --rules A,B em <repo>/.sparkforge/debate/<debate_id>/, a partir dos MESMOS insumos do `arbitrate`. Recusa `budget_undeclared` sem `budget:` no case.yaml.

```bash
sparkforge debate start --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--rules` | sim | texto |  |  | As duas regras em contradicao, `A,B`. O lado A defende a primeira. |
| `--findings` | sim | texto |  |  | Arquivo de findings (JSON) gerado por `judge --out` -- o mesmo do `arbitrate`. |
| `--facts` | sim | texto | sim |  | Arquivo de facts (JSON). Repetivel: o plano e recalculado sobre a UNIAO dos facts do case, o mesmo conjunto que `arbitrate` recebeu. |
| `--repo` | não | texto |  | `.` | Raiz do case. |
| `--glue` | não | texto |  |  |  |
| `--emr` | não | texto |  |  | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `--databricks` | não | texto |  |  | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved; sem declaracao, SF-ENV-006 avisa que regra de plano calada nao e evidencia. |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_debate_next`](../tools/sparkforge_debate_next.md), [`sparkforge_debate_start`](../tools/sparkforge_debate_start.md), [`sparkforge_debate_submit`](../tools/sparkforge_debate_submit.md)

## `sparkforge debate submit`

Valida e grava a submissao do lado da vez. Recusa por nome e deixa o estado igual.

```bash
sparkforge debate submit --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do case. |
| `--debate` | sim | texto |  |  | O `debate_id` que `start` devolveu. |
| `--file` | sim | texto |  |  | A submissao (objeto JSON), no schema que o brief publica em `submission_schema`. |

### Tool MCP equivalente

[`sparkforge_debate_next`](../tools/sparkforge_debate_next.md), [`sparkforge_debate_start`](../tools/sparkforge_debate_start.md), [`sparkforge_debate_submit`](../tools/sparkforge_debate_submit.md)
