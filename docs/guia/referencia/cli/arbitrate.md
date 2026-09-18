<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge arbitrate`

Executor agentico deterministico: arbitra findings ja julgados e grava claim, evidencia, contradicao, lacuna e decisao no blackboard do case. Nao estima ganho, nao publica score, nao executa debate.

```bash
sparkforge arbitrate --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--findings` | sim | texto |  |  | Arquivo de findings (JSON) gerado por `judge --out`. Aceita a lista nua e o objeto com a chave `findings` (ou `items`). |
| `--facts` | sim | texto | sim |  | Arquivo de facts (JSON). Repetivel, e a repeticao e o ponto: o executor recebe a UNIAO dos facts do case -- o MESMO conjunto que `judge` recebeu para produzir aqueles findings. Alimenta-lo com um subconjunto fabrica claim desancorada que a execucao real nao produz. Aceita a lista nua e o objeto com a chave `facts` (ou `items`); fact sem `id` tem o id computado pelo conteudo. |
| `--repo` | não | texto |  | `.` | Raiz do case. O blackboard fica em <repo>/.sparkforge/blackboard/. |
| `--glue` | não | texto |  |  |  |
| `--emr` | não | texto |  |  | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `--databricks` | não | texto |  |  | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf; sem declaracao, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |

## Tool MCP equivalente

[`sparkforge_arbitrate`](../tools/sparkforge_arbitrate.md)
