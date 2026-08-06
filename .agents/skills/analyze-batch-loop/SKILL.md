---
name: analyze-batch-loop
description: Use quando o job processa dados em lotes com for/while, collect de chaves, isin(list) gigante ou filtros por batch id, ou dispara action/write/count/merge dentro de loop, e você suspeita de recomputação do DAG, lineage crescente, múltiplos commits Iceberg ou OOM acumulado por iteração. Use também quando perguntarem "por que esse batch demora mais a cada lote", "por que tem tantos commits/snapshots" ou "o job cresce com o número de lotes", mesmo sem mencionar loop explicitamente. Se você está prestes a contar iterações e estimar custo acumulado de cabeça, rode `sparkforge analyze pyspark` e filtre por `pyspark.loop` em vez disso — cada ocorrência já vem marcada com se contém action, write e a profundidade de aninhamento.
subagent: true
---

# Analyze Batch Loop

## Procedimento

### 1. Extraia os facts

```bash
sparkforge analyze pyspark --path <arquivo-ou-diretório> --out .sparkforge/facts.json --kind pyspark.loop
```

Sem `--kind`, a saída traz todos os facts; com `--kind pyspark.loop`, você já recebe só os loops relevantes. Cada `pyspark.loop` vem com `measures.loop_depth` (aninhamento) e `attrs.contains_action`/`attrs.contains_write`.

### 2. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped
```

Sem flag de versão: `SF-PY-004`, a regra que decide esta análise, é estrutural e não declara `runtime_scope` — passar ou omitir a versão não muda se ela dispara. E não haveria de onde tirá-la: os facts vêm de `analyze pyspark`, que lê AST e nunca observa versão de runtime. O campo `runtime` da saída volta vazio, com `detected_from: []`, e isso é o retrato correto do que foi observado, não uma falha. As regras que aparecem em `--show-skipped` com `reason: runtime_scope` são as de infraestrutura Glue, fora do alcance deste `facts.json`. Só declare `--glue 5.1` se souber a versão de fonte confiável e a pergunta tiver virado de infra; para inferir em vez de digitar, junte os facts do Terraform na mesma chamada (`--facts` é repetível).

`SF-PY-004` (severidade default `P0`) dispara quando `contains_action` ou `contains_write` é verdadeiro — o padrão "reexecuta o DAG a montante a cada iteração" descrito em `knowledge/spark/execution-model.md` seção 6.

### 3. Interprete o que o extrator não marca

`pyspark.loop` só é emitido quando o `for`/`while` contém uma action ou um write **dentro do próprio loop**. Isso deixa pontos cegos reais:

- Um loop que só acumula DataFrames numa lista Python (`resultados.append(df_lote)`), sem action nem write dentro dele, **não gera** `pyspark.loop` — mesmo crescendo lineage a cada iteração. O sintoma aparece depois, numa action única no fim, com plano gigante. Se suspeitar disso, procure `pyspark.chain` com `measures.length` alto perto do loop.
- `collect()` de lista de chaves antes do loop (`chaves = df.select("k").distinct().collect()`) aparece como `pyspark.driver_collect`, não como parte do `pyspark.loop` — correlacione os dois manualmente pela proximidade de linha.
- `isin(lista_de_chaves)` não tem fact próprio; ele aparece dentro de `pyspark.chain` como uma chamada de método comum. Não assuma pruning de arquivo só porque o filtro existe — confirme no plano físico (`analyze-spark-plan`) se há `PushedFilters`/`PartitionFilters` reais.

### 4. Pergunta central

> O batch reduz o scan e o shuffle desde a origem, ou o Spark recompõe o pipeline caro a cada action?

Para responder com evidência de execução (não só de código), correlacione com o Spark UI: N jobs quase idênticos com o mesmo primeiro stage é a assinatura de recomputação por iteração — veja `analyze-spark-ui`.

## Recomendações possíveis

- Escrever tudo numa única action, com `partitionBy` pela coluna de lote quando o objetivo é separar a saída.
- Se o loop é inevitável, materializar o DataFrame caro uma vez antes dele (tabela intermediária ou checkpoint).
- Reduzir na origem, com filtro que chegue ao pushdown, em vez de filtrar um DAG caro já construído.
- Trocar `collect` de chaves + `isin(list)` por join distribuído contra uma tabela de chaves.

## Quando NÃO usar

- Não há loop; o custo é de uma única passada: use `analyze-spark-plan`/`analyze-spark-ui`.
- O batching estoura memória e você precisa classificar o OOM: combine com `diagnose-oom`.
- O objetivo é desenhar o incremental de forma correta desde o início, não só consertar um loop existente: use `design-incremental-processing`.
- O loop existe dentro de uma biblioteca com múltiplos módulos e você ainda não sabe onde ele está: comece por `analyze-library-call-graph`.

## Referência rápida

| Padrão no loop | Por que dói | Refatoração |
|---|---|---|
| `write`/`append`/`merge` por iteração (`pyspark.loop` com `contains_write`) | N commits, snapshots e small files | acumular e escrever/commitar uma vez (staging) |
| `count`/`show` por iteração (`pyspark.loop` com `contains_action`) | recomputa o DAG caro a cada action | remover ou medir uma vez fora do loop |
| `collect` de chaves + `isin(list)` | driver carrega tudo; filtro não garante pruning | join distribuído por tabela de chaves |
| `cache` dentro do loop sem `unpersist` | memória cresce por iteração | materializar fora; liberar entre iterações |
| DataFrames acumulados em lista, sem action no loop | não gera `pyspark.loop`; lineage cresce sem sinal do extrator até a action final | `checkpoint` pontual ou reescrever a lógica |

## Red flags

- Assumir que `isin(lista_de_chaves)` garante file pruning sem confirmar no plano físico.
- "Batching" que apenas filtra um DAG caro antes de cada action, sem reduzir trabalho na origem.
- Tratar a ausência de `pyspark.loop` como prova de que não há recomputação — verifique se o loop só acumula DataFrames sem action interna antes de descartar a hipótese.
- Muitos commits Iceberg por lote gerando explosão de snapshots/manifests sem consolidação.

## Preservar o resultado, com o verbo que produz a evidência

Unificar N escritas de laço numa única action com `partitionBy` muda **quando** o dado fica
visível e **o que** um run parcial deixa gravado: o laço commitava por iteração, a action única
commita uma vez. Se algum consumidor lia entre iterações, o resultado que ele via muda, e
nenhum dos quatro eixos mede isso — eles comparam o estado final.

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
