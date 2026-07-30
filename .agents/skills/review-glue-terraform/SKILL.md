---
name: review-glue-terraform
description: Use quando revisar o Terraform/IaC de jobs Glue (worker type, Auto Scaling junto com number_of_workers, execution class, timeout, max_concurrent_runs com bookmarks, max_retries com escrita não idempotente, default arguments, Spark UI/event logs, segredo em argumento) em busca de configuração contraditória, observabilidade ausente ou incompatível com o runtime. Use também quando a pergunta for "esse .tf tá certo", "por que a config que eu mudei no Terraform não fez efeito" ou "tem credencial exposta nesse job", mesmo que ninguém fale em regra. Se você está prestes a ler o .tf linha por linha comparando contra a doc do Glue, rode `sparkforge analyze terraform` e `sparkforge judge` em vez disso — o extrator lê os blocos aws_glue_job deterministicamente e o catálogo aplica as regras SF-GLUE por recurso.
---

# Review Glue Terraform

Ler `.tf` linha por linha e comparar contra a documentação do Glue de memória é lento e não reproduz entre analistas. O extrator lê cada bloco `aws_glue_job` de forma determinística; o catálogo aplica as regras `SF-GLUE-*` sobre o que ele achou.

Seu trabalho é **coletar, rodar, e interpretar por recurso** — nunca por arquivo, e nunca combinando atributos de dois recursos diferentes. Ver seção abaixo sobre por que isso importa.

## Procedimento

### 1. Extraia os facts

```bash
sparkforge analyze terraform --path <diretório ou arquivo.tf> --out .sparkforge/facts.json
```

Leia `unresolved`: interpolação `${...}`, heredoc, `dynamic`, `for_each` e qualquer expressão HCL fora do que este parser de linha entende viram `tf.unresolved` com um motivo — nunca um valor adivinhado. Um `for_each` no corpo de um `resource` faz o recurso inteiro virar um único `tf.unresolved`: o parser nunca finge ler atributo "literal" de um recurso que na prática o Terraform gera N vezes, um por item, com valores que só existem em runtime.

### 2. Se for avaliar SF-GLUE-004, extraia também o código

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts_pyspark.json
```

`SF-GLUE-004` (retry maior que zero com escrita não idempotente) precisa de `tf.attribute` (`max_retries`) e `pyspark.write` (`mode: append`) **na mesma chamada de `judge`**. `judge` lê um único `--facts`; una os dois arrays JSON num arquivo antes de julgar — é mesclagem de lista JSON simples, não existe verbo `sparkforge` para isso. Julgar os dois arquivos separados nunca faz `SF-GLUE-004` disparar, porque nenhum dos dois sozinho carrega as duas metades da evidência.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped
```

### 4. Interprete, e reporte por recurso

## Por que o motor não combina recursos por acidente — e onde ainda pode

`SF-GLUE-001` (Auto Scaling junto com `number_of_workers`) e `SF-GLUE-003` (`max_concurrent_runs` > 1 com bookmarks) declaram `same_subject: true` no catálogo. Isso obriga todas as condições da regra a serem satisfeitas pelo **mesmo** recurso (`aws_glue_job.<nome>`, não o arquivo inteiro). Sem essa guarda, um arquivo com dois blocos `aws_glue_job`, cada um correto isoladamente, poderia disparar a regra combinando um atributo do primeiro com um atributo do segundo — acusar configuração correta destrói a confiança no resto do relatório. `judge` já garante isso; sua parte é **nunca** escrever "o arquivo X tem o problema Y" quando X tem mais de um recurso — escreva "o recurso `aws_glue_job.foo` tem Y", ancorado em `finding.subject.symbol`.

`SF-GLUE-002` (observabilidade ausente) é o caso oposto e vale conhecer: ela não usa `same_subject`, porque checa ausência de `tf.observability.spark_ui` no conjunto inteiro de facts passado a `judge`. Numa análise com vários jobs no mesmo diretório, basta **um** deles ter Spark UI habilitado para que a condição `absent` deixe de disparar — mesmo que outros três jobs no mesmo diretório não tenham. Se precisa confirmar observabilidade job por job, rode `analyze terraform` escopado a um arquivo por vez, ou verifique manualmente `tf.observability.spark_ui` por `subject.symbol` na lista de facts antes de concluir "observabilidade presente" para o conjunto todo.

`SF-GLUE-006` (segredo em default argument) tem precedência sobre qualquer achado de performance no mesmo relatório — é achado de segurança, reporte primeiro.

## Referência rápida

Regras desta área, e o fact que cada uma consome. Os limiares e severidades **não** estão aqui de propósito — consulte com `sparkforge rules lookup --id <ID>`.

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-GLUE-001` | `tf.attribute` (`same_subject`) | Auto Scaling habilitado junto com `number_of_workers` no mesmo recurso |
| `SF-GLUE-002` | `tf.module_analyzed` + ausência de `tf.observability.spark_ui` | Sem `--enable-spark-ui` e `--spark-event-logs-path` — checagem é sobre o conjunto de facts, não por recurso |
| `SF-GLUE-003` | `tf.attribute` (`same_subject`) | `max_concurrent_runs` > 1 com bookmarks habilitados no mesmo recurso |
| `SF-GLUE-004` | `tf.attribute` + `pyspark.write` | `max_retries` > 0 com escrita `append` — exige unir facts de Terraform e de código |
| `SF-GLUE-005` | `tf.attribute` + `spark.stage.spill` | **Bloqueada** (`blocked_on: extrator-de-diff-terraform`) — precisa de diff entre duas leituras; nunca dispara hoje |
| `SF-GLUE-006` | `tf.attribute` (`attrs.secret_pattern_match`) | Segredo (padrão AKIA, URL com senha, alta entropia sob chave suspeita) em default argument |

## Quando NÃO usar

- Você quer decidir tamanho/perfil de worker a partir de métricas de execução: use `tune-glue-job`.
- O problema está no código ou nos dados, não na configuração: comece pelo diagnóstico com `sparkforge-diagnose`.
- Revisão de código de aplicação PySpark, não de infraestrutura: use `review-pyspark-pr`.

## Red flags

- Reportar um achado `same_subject` como se fosse do arquivo, sem citar o `symbol` do recurso — o motor te deu o recurso exato, use-o.
- Concluir "observabilidade OK para todos os jobs" a partir de `SF-GLUE-002` não disparar, quando o conjunto tem vários recursos e a checagem é global, não por recurso.
- Sugerir mais workers sem baseline de CPU/heap/spill/tasks — essa evidência vem de `analyze-spark-ui`, não deste catálogo.
- Copiar configuração entre versões de Glue sem checar `knowledge/runtime-compatibility.md`.
- Expor segredo em exemplo, log ou default argument ao documentar o achado de `SF-GLUE-006`.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
