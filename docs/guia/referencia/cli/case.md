<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge case`

Gerencia o estado do case em .sparkforge/case.yaml.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge case get`](#sparkforge-case-get) | Le o case atual. |
| [`sparkforge case open`](#sparkforge-case-open) | Cria um case novo, em fase intake. |
| [`sparkforge case update`](#sparkforge-case-update) | Atualiza fase, gate ou registra uso de skill no case. |

## `sparkforge case get`

Le o case atual.

```bash
sparkforge case get --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_case_get`](../tools/sparkforge_case_get.md), [`sparkforge_case_open`](../tools/sparkforge_case_open.md), [`sparkforge_case_update`](../tools/sparkforge_case_update.md)

## `sparkforge case open`

Cria um case novo, em fase intake.

```bash
sparkforge case open --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--case-id` | sim | texto |  |  |  |
| `--now` | sim | texto |  |  | Timestamp ISO 8601. Nunca lido do relogio pela CLI. |
| `--glue` | não | texto |  |  |  |
| `--emr` | não | texto |  |  | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--facts` | não | texto | sim |  | Arquivo de facts (JSON) gerado por `analyze`. Repetivel. O runtime do case passa a sair do que os extratores observaram, nao so das flags. |
| `--strict-gates` | não | liga/desliga |  |  | Grava no case que gate com produtor declarado passa a bloquear a transicao de fase. A escolha e do case, nao da invocacao: vale pela investigacao inteira, e quem retoma noutra maquina herda o rigor de quem abriu. Sem a flag, o comportamento e o de sempre (gate advisory). |
| `--reopen` | não | liga/desliga |  |  | Recomeca do zero por cima de um case que ja existe. Sem esta flag, abrir sobre um case existente e RECUSADO: sobrescrever apagaria a fase, o rigor e os overrides gravados. O `strict_gates` do case atual e herdado -- `--strict-gates` sobe o rigor, e nada o baixa por omissao de flag. |

### Tool MCP equivalente

[`sparkforge_case_get`](../tools/sparkforge_case_get.md), [`sparkforge_case_open`](../tools/sparkforge_case_open.md), [`sparkforge_case_update`](../tools/sparkforge_case_update.md)

## `sparkforge case update`

Atualiza fase, gate ou registra uso de skill no case.

```bash
sparkforge case update --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |
| `--phase` | não | texto |  |  |  |
| `--gate` | não | texto |  |  |  |
| `--gate-value` | não | `true`, `false` |  | `true` |  |
| `--skill` | não | texto |  |  |  |
| `--now` | não | texto |  |  |  |
| `--outcome` | não | texto |  |  |  |
| `--hypothesis` | não | texto |  |  | Afirmacao testavel a registrar no case. Exige `--prediction` e `--experiment`: afirmacao sem previsao nao e testavel, e previsao sem experimento nao diz quem a testa. |
| `--prediction` | não | texto |  |  | O que muda no numero se a hipotese valer. |
| `--experiment` | não | texto |  |  | Como medir a previsao. |
| `--close-hypothesis` | não | `ID` |  |  | Fecha a hipotese com este id. Exige `--hypothesis-outcome`. O registro e acrescimo: a afirmacao original fica onde esta. |
| `--hypothesis-outcome` | não | `confirmed`, `refuted`, `abandoned` |  |  | Desfecho do experimento. `abandoned` existe porque a terceira coisa que acontece de verdade e o experimento nunca rodar. |
| `--evidence` | não | texto |  |  | Onde ler o que fechou a hipotese (stage, run, arquivo de facts). |
| `--override-gate` | não | texto |  |  | Passa por cima de um gate num case estrito, quando o dado genuinamente nao existe (job descontinuado, ambiente que sumiu). Exige `--reason`. Fica gravado no case como lista: dois overrides do mesmo gate sao dois fatos, e nenhum apaga o outro. |
| `--reason` | não | texto |  |  | Motivo do `--override-gate`. Sem ele o override e recusado. |
| `--facts` | não | texto | sim |  | Arquivo de facts (JSON) que comprova os gates da fase pedida. Repetivel. Num case estrito, e daqui que sai a evidencia que destrava `--phase`. |

### Tool MCP equivalente

[`sparkforge_case_get`](../tools/sparkforge_case_get.md), [`sparkforge_case_open`](../tools/sparkforge_case_open.md), [`sparkforge_case_update`](../tools/sparkforge_case_update.md)
