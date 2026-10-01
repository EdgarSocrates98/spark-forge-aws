<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge report`

Assinatura de CORRESPONDENCIA do relatorio: prova que o texto foi derivado daquela evidencia com aquele catalogo. Nunca autoria.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge report github`](#sparkforge-report-github) | Projeta findings ja julgados para o GitHub: SARIF para o Code Scanning e resumo Markdown para o PR, em .sparkforge/report/ (nomes fixos), e uma anotacao ::error/::warning/::notice por finding com linha no stdout. Finding sem linha no repositorio sai no resumo com o motivo. Nao chama rede. |
| [`sparkforge report sign`](#sparkforge-report-sign) | Escreve o bloco de assinatura no fim do relatorio. Reassinar e barato e devolve o mesmo arquivo quando nada mudou. |
| [`sparkforge report verify`](#sparkforge-report-verify) | Confere a assinatura e diz QUAL parte divergiu: evidencia, catalogo ou corpo. Sai com codigo 1 quando nao corresponde. |

## `sparkforge report github`

Projeta findings ja julgados para o GitHub: SARIF para o Code Scanning e resumo Markdown para o PR, em .sparkforge/report/ (nomes fixos), e uma anotacao ::error/::warning/::notice por finding com linha no stdout. Finding sem linha no repositorio sai no resumo com o motivo. Nao chama rede.

```bash
sparkforge report github --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--findings` | sim | texto |  |  | Saida de `judge --out` (findings.json). |
| `--facts` | sim | texto | sim |  | Facts da UNIAO do case (repetivel): o fact de evidencia de codigo empresta a linha a um finding que nao tem a propria. |
| `--repo` | não | texto |  | `.` | Raiz do repositorio git. A saida vai para <repo>/.sparkforge/report/. |
| `--source-root` | não | texto | sim |  | Diretorio (relativo a --repo) que foi passado a um `analyze --path`, repetivel, na mesma ordem. O caminho dos findings e relativo a ele. |
| `--fail-on` | não | `P0`, `P1` |  |  | Sai com codigo 1 quando ha finding desta severidade ou pior. |
| `--category` | não | texto |  |  | Categoria do upload no Code Scanning (automationDetails.id). |
| `--source-freshness` | não | liga/desliga |  |  | Secao Fontes que pedem releitura no resumo, com o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_report_github`](../tools/sparkforge_report_github.md)

## `sparkforge report sign`

Escreve o bloco de assinatura no fim do relatorio. Reassinar e barato e devolve o mesmo arquivo quando nada mudou.

```bash
sparkforge report sign --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--report` | sim | texto |  |  | Markdown do relatorio. E reescrito no lugar. |
| `--findings` | sim | texto |  |  | Arquivo de findings (JSON) gerado por `judge --out`. E dele que saem os quatro campos nao-corpo da assinatura: `evidence` (os fact_id citados), `rule_id`, `catalog_version` e `schema_version`. O arquivo de FACTS nao tem os tres ultimos -- por isso o verbo pede findings, e nao facts. |

### Tool MCP equivalente

[`sparkforge_report_sign`](../tools/sparkforge_report_sign.md), [`sparkforge_report_verify`](../tools/sparkforge_report_verify.md)

## `sparkforge report verify`

Confere a assinatura e diz QUAL parte divergiu: evidencia, catalogo ou corpo. Sai com codigo 1 quando nao corresponde.

```bash
sparkforge report verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--report` | sim | texto |  |  |  |
| `--findings` | sim | texto |  |  | O mesmo arquivo de findings contra o qual o relatorio foi assinado. |

### Tool MCP equivalente

[`sparkforge_report_sign`](../tools/sparkforge_report_sign.md), [`sparkforge_report_verify`](../tools/sparkforge_report_verify.md)
