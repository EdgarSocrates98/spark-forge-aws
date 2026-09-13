<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_emr_eks`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um dump JSON de execucao Amazon EMR on EKS (`describe-virtual-cluster` mais `describe-job-run`, as DUAS respostas no mesmo arquivo sob `virtualCluster` e `jobRun`): identidade e estado do cluster virtual (`emrc.virtual_cluster`), a execucao com release label, role de execucao e estado (`emrc.job_run`), as propriedades de `sparkSubmitParameters` (`emrc.spark_submit_parameters`), as `configurationOverrides` achatadas por classificacao (`emrc.configuration`) e os destinos de log (`emrc.monitoring`). NAO chama a API do `emr-containers` -- so le o JSON ja salvo em disco (`sparkforge_collect_emr_eks` ou `aws emr-containers describe-job-run` a mao fazem isso). FRONTEIRA QUE VALE PARA TODO FACT DAQUI, e ela e mais estreita que a do EMR Serverless: estes facts descrevem o que UMA EXECUCAO PEDIU, nunca o que o pod RECEBEU. O que roda de fato sai da imagem do container e do escalonador do Kubernetes, e nenhum dos dois esta neste dump. O POD TEMPLATE NAO E LIDO: quando a configuracao aponta um (`spark.kubernetes.driver.podTemplateFile` e o par do executor), o modulo emite a RECUSA com o path do template em vez de adivinhar o que ele contem -- le-lo exigiria um `GetObject` no S3 que este caminho nao faz. E O LADO EKS NAO EXISTE AQUI: nodegroup, autoscaling do cluster, pod pendente por falta de no, quota de namespace -- nada disso aparece em `emr-containers`. Sao outro servico, outro IAM e outra matriz de versao; pergunta sobre eles nao tem resposta nesta area, e a ausencia e decidida. Classificacao ou unidade fora do documentado vira `emrc.unresolved` contado, nunca valor adivinhado.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo ou diretorio com dumps de execucao EMR on EKS. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze emr-eks`](../cli/analyze.md)

## Capacidade

extract facts from an EMR on EKS job run dump

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
