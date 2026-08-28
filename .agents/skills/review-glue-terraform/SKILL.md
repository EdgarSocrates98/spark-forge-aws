---
name: review-glue-terraform
description: Use quando revisar o Terraform/IaC de jobs Glue (worker type, max_capacity junto com worker_type/number_of_workers, execution class, timeout, max_concurrent_runs com bookmarks, max_retries com escrita não idempotente, default arguments, Spark UI/event logs, segredo em argumento) em busca de configuração contraditória, observabilidade ausente ou incompatível com o runtime. Use também quando a pergunta for "esse .tf tá certo", "por que a config que eu mudei no Terraform não fez efeito" ou "tem credencial exposta nesse job", mesmo que ninguém fale em regra. Se você está prestes a ler o .tf linha por linha comparando contra a doc do Glue, rode `sparkforge analyze terraform` e `sparkforge judge` em vez disso — o extrator lê os blocos aws_glue_job deterministicamente e o catálogo aplica as regras SF-GLUE por recurso.
subagent: true
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

`SF-GLUE-004` (retry maior que zero com escrita não idempotente) precisa de `tf.attribute` (`max_retries`) e `pyspark.write` (`mode: append`) **na mesma chamada de `judge`**. `--facts` é repetível: passe os dois arquivos na mesma chamada e `judge` une e deduplica as listas antes de julgar — não mescle JSON na mão. Julgar os dois arquivos separados nunca faz `SF-GLUE-004` disparar, porque nenhum dos dois sozinho carrega as duas metades da evidência.

Quando a revisão é de um **PR** — e não de um estado parado —, o que mudou é evidência própria, e `analyze terraform` sozinho não a produz: ele lê um estado. Use `terraform-diff`, que compara os dois e marca `tf.attribute` com `changed: true`:

```bash
sparkforge analyze terraform-diff \
  --before <dir-do-estado-anterior> --after <dir-do-estado-proposto> \
  --out .sparkforge/tf_diff.json
```

É o que `SF-GLUE-005` consome para acusar `worker_type` aumentado no PR. Ela precisa também de `spark.job.spill_summary` e `spark.executor.memory_usage` de um event log real do run que motivou a mudança (`sparkforge analyze event-log`): sem essas duas, "sem evidência de limitação de memória" seria indistinguível de "ninguém mediu", e a regra se recusa a fazer essa confusão — sai em `skipped` com `reason: requires_facts`.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped

# com o código junto, para SF-GLUE-004:
sparkforge judge \
  --facts .sparkforge/facts.json \
  --facts .sparkforge/facts_pyspark.json \
  --show-skipped

# revisão de PR, para SF-GLUE-005:
sparkforge judge \
  --facts .sparkforge/tf_diff.json \
  --facts .sparkforge/facts_eventlog.json \
  --show-skipped
```

Sem flag de versão, de propósito: esta é a skill em que o próprio fact já carrega a versão. `judge` lê o `tf.attribute` de `key: glue_version` dos facts da mesma chamada e preenche `glue`; `spark`, `python` e `iceberg` saem daí pela matriz de compatibilidade do Glue. Confirme no campo `runtime` da saída, que traz o contexto efetivamente usado para filtrar por versão — `detected_from: ["terraform"]` é a prova de que veio do `.tf`, não de palpite.

Dois casos em que o `.tf` **não** alimenta a detecção, e nos dois `runtime.glue` volta vazio:

- `glue_version = var.glue_version` (ou `local.`, ou interpolação): o extrator guarda o texto da referência, não a versão, e a leitura é descartada em vez de gravar `"var.glue_version"` como se fosse versão — é o mesmo `tf.unresolved` do passo 1.
- `glue_version` dentro de `default_arguments`: chave homônima que é argumento de job, não a versão do runtime.

Nesses casos, e só neles, declare você: `--glue 5.1`, com a versão vinda de onde ela realmente está (o `tfvars`, o módulo chamador, o console). A flag é declaração de quem sabe, não campo a preencher por obrigação. Sem versão nenhuma, `SF-GLUE-002..007` são puladas com `reason: runtime_scope`, visível em `--show-skipped` — o eixo fica descoberto, mas você **sabe** que ficou. Chutar a versão é pior: julga as seis contra o limiar errado sem nada na saída denunciando isso.

Se dois módulos declararem `glue_version` diferentes, nenhum vence em silêncio — `runtime.divergences` lista os dois valores com o arquivo de cada um, e a discordância é achado próprio (`SF-ENV-001`), não detalhe de configuração.

### 4. Interprete, e reporte por recurso

## Por que o motor não combina recursos por acidente — e onde ainda pode

`SF-GLUE-002` (observabilidade ausente), `SF-GLUE-003` (`max_concurrent_runs` > 1 com bookmarks) e `SF-GLUE-007` (`max_capacity` junto com `worker_type`) declaram `same_subject: true` no catálogo. Isso obriga todas as condições da regra a serem satisfeitas pelo **mesmo** recurso (`aws_glue_job.<nome>`, não o arquivo inteiro). Sem essa guarda, um arquivo com dois blocos `aws_glue_job`, cada um correto isoladamente, poderia disparar a regra combinando um atributo do primeiro com um atributo do segundo — acusar configuração correta destrói a confiança no resto do relatório. `judge` já garante isso; sua parte é **nunca** escrever "o arquivo X tem o problema Y" quando X tem mais de um recurso — escreva "o recurso `aws_glue_job.foo` tem Y", ancorado em `finding.subject.symbol`.

Uma regra `same_subject` emite **um finding por recurso** que casa, cada um com a evidência só daquele recurso. Quatro jobs sem observabilidade são quatro achados de `SF-GLUE-002`, não um: a contagem que você reportar é a contagem de recursos afetados, e conferir `subject.symbol` de cada finding é o que separa "um job para corrigir" de "quatro".

`SF-GLUE-002` é o caso que mais depende disso. Ela ancora em `tf.resource` (um por bloco `aws_glue_job`) e checa a ausência de `tf.observability.spark_ui` **dentro daquele recurso**. Ancorada no arquivo, um único job com Spark UI habilitado bastaria para mascarar todos os outros do mesmo diretório. `tf.module_analyzed` continua sendo exigido em `requires_facts`: ele prova que o extrator de Terraform rodou, para que um repositório sem `.tf` nenhum apareça como `skipped`, nunca como "sem observabilidade".

`SF-GLUE-006` (segredo em default argument) tem precedência sobre qualquer achado de performance no mesmo relatório — é achado de segurança, reporte primeiro.

## Referência rápida

Regras desta área, e o fact que cada uma consome. Os limiares e severidades **não** estão aqui de propósito — consulte com `sparkforge rules lookup --id <ID>`.

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-GLUE-002` | `tf.resource` (`same_subject`) + ausência de `tf.observability.spark_ui` | Sem `--enable-spark-ui` e `--spark-event-logs-path` naquele recurso — um achado por job afetado |
| `SF-GLUE-003` | `tf.attribute` (`same_subject`) | `max_concurrent_runs` > 1 com bookmarks habilitados no mesmo recurso |
| `SF-GLUE-004` | `tf.attribute` + `pyspark.write` | `max_retries` > 0 com escrita `append` — exige unir facts de Terraform e de código |
| `SF-GLUE-005` | `tf.attribute` com `changed: true` (via `analyze terraform-diff`) + `spark.job.spill_summary` + `spark.executor.memory_usage` | `worker_type` aumentado no PR sem spill no run que motivou a mudança — exige os dois estados do módulo e um event log real |
| `SF-GLUE-006` | `tf.attribute` (`attrs.secret_pattern_match`) | Segredo (padrão AKIA, URL com senha, alta entropia sob chave suspeita) em default argument |
| `SF-GLUE-007` | `tf.attribute` (`same_subject`) | `max_capacity` definido junto com `worker_type` no mesmo recurso — API antiga e API >= 2.0 de capacidade não coexistem |

## Quando NÃO usar

- Você quer decidir tamanho/perfil de worker a partir de métricas de execução: use `tune-glue-job`.
- O problema está no código ou nos dados, não na configuração: comece pelo diagnóstico com `sparkforge-diagnose`.
- Revisão de código de aplicação PySpark, não de infraestrutura: use `review-pyspark-pr`.

## Red flags

- Reportar um achado `same_subject` como se fosse do arquivo, sem citar o `symbol` do recurso — o motor te deu o recurso exato, use-o.
- Reportar "um job sem observabilidade" quando `SF-GLUE-002` disparou para três: a regra emite um finding por recurso, então conte os findings e cite cada `subject.symbol`.
- Sugerir mais workers sem baseline de CPU/heap/spill/tasks — essa evidência vem de `analyze-spark-ui`, não deste catálogo.
- Copiar configuração entre versões de Glue sem checar `knowledge/runtime-compatibility.md`.
- Expor segredo em exemplo, log ou default argument ao documentar o achado de `SF-GLUE-006`.

## Preservar o resultado, com o verbo que produz a evidência

Worker type e número não movem o dado. Duas linhas do mesmo `aws_glue_job` movem: `bookmark`,
que decide o que o próximo run lê — e cujo sintoma é lacuna ou duplicata, nunca erro —, e
`--conf` em default argument, que alcança o Spark do job inteiro. As três chegam no mesmo diff
de Terraform.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts`
é repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu
**antes** de a mudança tocar o alvo — um `overwrite` no meio o apaga sem deixar rastro.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não
entrega: contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies
detectou divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das
outras quatro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva você **não executa** — recomende, e a confirmação de escopo e
retenção **sobe a quem pode ser perguntado**: o agente pai que despachou, ou o
operador na sessão. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a
confirmação aqui não é difícil: é impossível — por isso a regra 9 de
`AGENT_PROTOCOL.md` manda não executar e devolver a decisão a quem pode ser
perguntado.
