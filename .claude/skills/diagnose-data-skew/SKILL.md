---
name: diagnose-data-skew
description: Use quando o judge já disparou SF-UI-001 (skew de duração de task) e for preciso decidir entre skew de dados e skew de computação, tratar hot key, null ou valor sentinela, ou desenhar o experimento de mitigação (broadcast, AQE skew join, salting). Use também quando a pergunta for "uma task não termina", "uma chave concentra tudo", "o job trava numa partição só" ou "uma partição ficou gigante", mesmo sem citar SF-UI-001. Se você está prestes a aplicar salting ou repartition por instinto, rode `sparkforge collect event-log`, `sparkforge analyze event-log` e `sparkforge judge --show-skipped` em vez disso — cruzar SF-UI-001 com SF-UI-002 diz se é skew de dados (tratável na chave) ou de computação (repartition não muda nada, e é o erro mais caro desta análise).
---

# Diagnose Data Skew

Skew de duração sozinho não diz o que fazer. O tratamento depende inteiramente de uma pergunta: os bytes lidos também são desiguais, ou só a duração é? As respostas pedem tratamentos opostos, e tratar a errada é a forma mais cara de perder um ciclo de investigação.

## Procedimento

1. `sparkforge collect event-log --repo . --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>` — sem credencial, baixe manualmente e registre com `sparkforge.collect.register_artifact`.
2. `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts.json`. Leia `unresolved`: log truncado é ponto cego, não ausência de skew.
3. `sparkforge judge --facts .sparkforge/facts.json --show-skipped`. `--show-skipped` não é opcional aqui — distingue "não há skew" de "não coletei o dado que provaria skew". Sem flag de versão: `SF-UI-001` e `SF-UI-002`, as duas regras que decidem esta investigação, não guardam versão, então declarar runtime não muda o resultado. O que o event log declara (`spark.runtime_version`, a primeira linha do log) `judge` já lê sozinho — confira no campo `runtime` da saída, com `detected_from` dizendo de onde veio. Passe `--glue 5.1` só se souber a versão de fonte confiável e quiser cobrir também `SF-GLUE-*`; senão elas aparecem em `--show-skipped` com `reason: runtime_scope`, que aqui é ruído esperado e não lacuna de skew.
4. `sparkforge next-step --repo . --findings .sparkforge/findings.json` — a árvore de roteamento já resolve o discriminador abaixo sozinha (`ROUTE-006`/`ROUTE-007` em `rules/catalog/routing.yaml`); não escolha o caminho por julgamento próprio.

## O discriminador que decide o tratamento

Quando `SF-UI-001` (skew de duração) dispara, olhe imediatamente `SF-UI-002` (skew de input) no mesmo stage:

- **Os dois juntos** → skew de **dados**. Tratável na chave: null, hot key, valor sentinela. Siga para a tabela de tratamentos abaixo.
- **Só o de duração** → skew de **computação**. UDF caro em certas linhas, `explode` com fan-out desigual. Repartition não muda nada — o dado já está bem distribuído, o *trabalho* por linha é que é desigual. Tentar redistribuir aqui é o erro mais caro desta investigação: consome um ciclo inteiro e não move a agulha. Vá para `analyze-spark-plan` e `optimize-pyspark-code`.

## Diagnóstico semântico antes de tratar

Antes de tocar na distribuição, entenda:

- o significado de null/`UNKNOWN`/valor default na chave — filtrar pode alterar o resultado;
- se a duplicidade observada é esperada pela relação 1:1, 1:N ou N:N;
- se as hot keys podem ser processadas separadamente sem quebrar uma regra de negócio;
- se pré-agregação preserva o resultado final.

Medir, não estimar: `df.groupBy(chave).count().orderBy(desc("count")).limit(20)` sobre uma amostra, e `df.filter(col(chave).isNull()).count()`.

## Tratamentos, do mais barato ao mais invasivo

Ordem de custo crescente, detalhada com aplicabilidade e risco em `knowledge/spark/shuffle-join-skew.md` seção 3: filtrar/reduzir dado cedo → corrigir a chave ou a regra de negócio → broadcast do lado pequeno → pré-agregar → confiar no AQE skew join → separar a hot key e unir depois → salting seletivo → reprojetar a operação.

Salting é a resposta mais citada e raramente a melhor primeira tentativa. Nunca aplique sem: identificar as hot keys de fato, escolher o número de salts por evidência (não um número redondo), replicar apenas o lado necessário, estimar a expansão resultante, e validar duplicidade e semântica depois.

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-UI-001` | `spark.stage.task_duration` | Duração desigual entre tasks do mesmo stage |
| `SF-UI-002` | `spark.stage.task_input` | Bytes lidos desiguais — o discriminador entre skew de dado e de computação |

Limiares e severidade de cada regra vêm de `sparkforge rules lookup --id <ID>`, nunca de memória — um valor decorado vira mentira silenciosa quando o catálogo é atualizado.

## Quando NÃO usar

- Skew ainda não confirmado no Spark UI: comece por `analyze-spark-ui`.
- A task gigante vem de subparalelismo ou small files, não de chave quente: veja `analyze-spark-ui` / `optimize-parquet-layout`.
- O desbalanceamento é de arquivos por partição na escrita: use `optimize-parquet-layout` ou `optimize-iceberg-table`.
- Executor perdido é o sintoma dominante, não uma task lenta: vá para `diagnose-oom`.

## Red flags

- Aplicar salting ou repartition antes de checar `SF-UI-002` — se só `SF-UI-001` disparou, é skew de computação e a redistribuição não resolve nada.
- Salting global sem identificar as hot keys primeiro.
- Alterar a chave ou a regra de join sem validar duplicidade e semântica do resultado depois.

## Preservar o resultado, com o verbo que produz a evidência

Os três tratamentos mudam o dado de formas diferentes, e é por isso que a skill já mandava
"validar duplicidade e semântica do resultado depois" — sem dizer com quê. Salting acrescenta
coluna e exige uma segunda agregação para desfazer; pré-agregação só preserva o resultado se a
função for associativa e comutativa; e trocar a chave ou a regra de join muda a cardinalidade
por construção. Aqui a exigência ganha o produtor que lhe faltava.

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
