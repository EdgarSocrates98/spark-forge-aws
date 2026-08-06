---
name: glue-incremental-performance-architect
description: Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key sobre tabela Iceberg bilionária, batching por lote, OOM que só aparece depois de horas, ou carga que varia de dezenas a milhões de registros — e for preciso orquestrar as skills especializadas em vez de mexer isoladamente num sintoma. Use também quando a pergunta for "o job incremental tá tão lento quanto o full", "o job só morre de memória depois de um bom tempo rodando" ou "esse job tem dois jeitos de rodar e não sei qual tá causando o problema", mesmo que ninguém fale em full/incremental. Se você está prestes a mexer em workers, shuffle partitions ou cache antes de mapear a biblioteca inteira, pare — é exatamente isso que este documento existe para evitar. Leia `PROMPT_INICIAL_MESTRE.md` primeiro.
---

# Glue Incremental Performance Architect

Tuning localizado num job com dois fluxos é a forma mais cara de errar aqui: corrige um sintoma no incremental enquanto a causa real está no full, ou vice-versa, e o próximo ciclo reproduz o problema porque nada na arquitetura mudou. Esta skill não substitui as skills especializadas — ela decide a ordem em que rodam e recusa fechar a investigação enquanto full, incremental, latest-per-key, batching e OOM não estiverem todos mapeados.

## Sequência obrigatória

### 1. Leia `PROMPT_INICIAL_MESTRE.md`

A missão completa, os 20 entregáveis esperados, e por que "aumentar workers" nunca é a primeira resposta.

### 2. Mapeie a biblioteca

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json
sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/callgraph.json
```

`callgraph.reachable_spark_work` mostra, por função, todo o trabalho Spark (`pyspark.*`) alcançável a partir de cada entrypoint — é como se separa o que o fluxo full aciona do que o incremental aciona sem ler a biblioteca inteira à mão. Duas entradas com call graphs que convergem no mesmo trabalho pesado é o primeiro sinal de scan global disfarçado de incremental.

### 3. Julgue o inventário

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped
```

Sem flag de versão neste ponto, e de propósito: o `facts.json` do passo 2 vem de `analyze pyspark`, que lê AST e não observa runtime, então `runtime` volta vazio com `detected_from: []` — e as regras `SF-PY-*` deste inventário são estruturais, sem `runtime_scope`, então nada é perdido. Digitar uma versão aqui seria declarar de memória o que ninguém verificou.

Numa investigação deste tamanho, porém, o eixo de infraestrutura **não** pode ficar descoberto até o fim: o que aparecer em `--show-skipped` com `reason: runtime_scope` são as seis regras `SF-GLUE-*`, e elas continuam puladas em toda rodada seguinte enquanto o runtime for vazio. Feche isso cedo, extraindo a fonte em vez de declarando o palpite:

```bash
sparkforge analyze terraform --path <dir.tf> --out .sparkforge/facts_tf.json
sparkforge judge --facts .sparkforge/facts.json --facts .sparkforge/facts_tf.json --show-skipped
```

`--facts` é repetível, e a partir daí `runtime.detected_from` passa a dizer `["terraform"]` e a matriz de compatibilidade preenche `spark`, `python` e `iceberg` junto — o contexto que toda recomendação versionada desta investigação vai precisar. Se o repositório tem mais de um módulo declarando `glue_version` diferente, `runtime.divergences` mostra os dois: num job com fluxos full e incremental isso costuma ser dois jobs Glue distintos, e descobrir isso na primeira rodada vale mais que qualquer finding de código.

Preste atenção especial a `SF-PY-004` (action ou write dentro de loop): se aparecer, domina qualquer outro diagnóstico e mascara o resto — `ROUTE-004` em `routing.yaml` manda direto para `analyze-batch-loop` quando isso acontece, antes de qualquer outra investigação.

### 4. Deixe next-step orquestrar as skills especializadas

```bash
sparkforge next-step --repo <repo> --findings .sparkforge/findings.json
```

Chame de novo depois de cada rodada de achados novos — a árvore de roteamento manda para `design-incremental-processing`, `optimize-latest-per-key`, `analyze-batch-loop`, `diagnose-oom`, `optimize-parquet-layout`, `optimize-iceberg-table` e `review-glue-terraform` na ordem que a evidência pede, não na ordem que parece intuitiva.

### 5. Formule a arquitetura-alvo

Só depois que full, incremental, latest-per-key, batching e OOM estiverem todos mapeados e classificados — nunca antes, mesmo que um deles já pareça óbvio.

### 6. Crie experimentos, meça e valide

```bash
sparkforge validate --findings .sparkforge/findings.json
```

Uma variável principal por experimento; sem baseline capturado (`benchmark-pyspark-job`) não há como provar impacto.

## Referência rápida

Não decida à mão qual skill vem a seguir — estas são as correlações que `routing.yaml` já codifica; rode `next-step` e leia `reason` e `evidence` na saída em vez de memorizar a tabela.

| Etapa da investigação | Regra de roteamento | Skill de apoio |
|---|---|---|
| mapear trabalho oculto, sem fact extraído ainda | `ROUTE-002` | `analyze-library-call-graph` |
| dois entrypoints, fluxos ainda não separados | `ROUTE-003` | `design-incremental-processing` |
| `SF-PY-004` presente — action/write em loop | `ROUTE-004` | `analyze-batch-loop` |
| `SF-UI-005` presente — executor perdido sem OOM de heap | `ROUTE-005` | `diagnose-oom` |
| `SF-PQ-001` ou `SF-ICE-001` presente — small files dominando | `ROUTE-009` | `optimize-parquet-layout` |
| `SF-ICE-002` ou `SF-ICE-003` presente — dívida de metadados | `ROUTE-010` | `optimize-iceberg-table` |
| facts extraídos, zero findings de código | `ROUTE-014` | `review-glue-terraform` |
| gargalo dominante identificado, sem baseline | `ROUTE-012` | `benchmark-pyspark-job` |

`optimize-latest-per-key` não tem regra de roteamento própria hoje: acione manualmente para cada tabela incremental relevante depois de `design-incremental-processing` separar os fluxos — é o passo do documento mestre que a árvore automática ainda não cobre.

## Por que "fechar cedo" é o erro mais caro aqui

Encerrar só com mais workers, mudança de `shuffle.partitions`, hint de broadcast, compactação ou cache — sem explicar a relação entre full, incremental, estado atual, scans globais e commits Iceberg — reproduz exatamente o sintoma que `PROMPT_INICIAL_MESTRE.md` existe para evitar. Nenhuma das 16 regras de `routing.yaml` aponta para "aumentar capacidade" como skill recomendada: se a investigação está prestes a terminar assim, é sinal de que full, incremental, latest-per-key, batching ou OOM ainda não foram mapeados por completo, não de que a resposta é capacidade.

## Quando NÃO usar

- O job tem um único fluxo simples e um sintoma isolado: use `sparkforge-diagnose` ou a skill específica direto.
- Você só quer revisar código, PR ou Terraform, sem investigar full/incremental: use a skill focada correspondente.
- Já mapeou tudo e falta apenas medir: vá direto para `benchmark-pyspark-job`.

## Red flags

- Fazer tuning localizado antes de mapear biblioteca, actions, batching, latest-per-key e OOM.
- Encerrar só com "mais workers", `shuffle.partitions`, broadcast, compactação ou cache, sem separar os DAGs de full e incremental.
- Tratar `optimize-latest-per-key` como opcional quando existe cálculo de mais recente por chave sobre histórico Iceberg — não há regra de roteamento que lembre disso por você.
- Ignorar `SF-PY-004` quando presente e seguir investigando joins ou skew antes de resolver o loop.

## Preservar o resultado, com o verbo que produz a evidência

A investigação que você coordena termina em mudança de lookback, de batching, de
latest-per-key ou de bookmark — as quatro decidem **quais linhas existem no destino**, não
quanto tempo o job leva. Um desempate de timestamp trocado não muda contagem nenhuma e muda a
linha que ficou.

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
manutenção destrutiva só com confirmação explícita. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.
