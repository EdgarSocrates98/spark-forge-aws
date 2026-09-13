<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge runtime`

Deteccao de runtime Glue/EMR/Spark/Python/Iceberg/Athena.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge runtime detect`](#sparkforge-runtime-detect) | Deriva a matriz de runtime a partir de facts ja extraidos e de flags. |

## `sparkforge runtime detect`

Deriva a matriz de runtime a partir de facts ja extraidos e de flags.

```bash
sparkforge runtime detect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--glue` | não | texto |  |  |  |
| `--emr` | não | texto |  |  | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--facts` | não | texto | sim |  | Arquivo de facts (JSON) gerado por `analyze`. Repetivel. A versao OBSERVADA pelos extratores (`tf.attribute` glue_version, `spark.runtime_version`) entra como fonte propria -- sem isto, so as flags alimentam a deteccao. |

### Tool MCP equivalente

[`sparkforge_runtime_detect`](../tools/sparkforge_runtime_detect.md)
