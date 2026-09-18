<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge judge`

Aplica o catalogo de regras versionado sobre facts ja extraidos.

```bash
sparkforge judge --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts (JSON) gerado por `analyze`. Repetivel: regra que correlaciona extratores diferentes (SF-GLUE-004 cruza tf.attribute com pyspark.write) so dispara com as duas fontes na mesma chamada. |
| `--glue` | não | texto |  |  |  |
| `--emr` | não | texto |  |  | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `--databricks` | não | texto |  |  | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved; sem declaracao, SF-ENV-006 avisa que regra de plano calada nao e evidencia. |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--severity` | não | texto | sim |  | Filtra por severidade. Repetivel. |
| `--out` | não | texto |  |  | Escreve a lista completa de findings (JSON) neste arquivo. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--show-skipped` | não | liga/desliga |  |  |  |
| `--source-freshness` | não | liga/desliga |  |  | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

## Tool MCP equivalente

[`sparkforge_judge`](../tools/sparkforge_judge.md)
