---
name: diagnose-data-skew
description: Use quando o judge já disparou SF-UI-001 (skew de duração de task) e for preciso decidir entre skew de dados e skew de computação, tratar hot key, null ou valor sentinela, ou desenhar o experimento de mitigação (broadcast, AQE skew join, salting). Use também quando a pergunta for "uma task não termina", "uma chave concentra tudo", "o job trava numa partição só" ou "uma partição ficou gigante", mesmo sem citar SF-UI-001. Se você está prestes a aplicar salting ou repartition por instinto, rode `sparkforge collect event-log`, `sparkforge analyze event-log` e `sparkforge judge --show-skipped` em vez disso — cruzar SF-UI-001 com SF-UI-002 diz se é skew de dados (tratável na chave) ou de computação (repartition não muda nada, e é o erro mais caro desta análise).
---

# Diagnose Data Skew

Skew de duração sozinho não diz o que fazer. O tratamento depende inteiramente de uma pergunta: os bytes lidos também são desiguais, ou só a duração é? As respostas pedem tratamentos opostos, e tratar a errada é a forma mais cara de perder um ciclo de investigação.

## Procedimento

1. `sparkforge collect event-log --repo . --job-run <id> --bucket <bucket> --prefix <prefix> --now <ISO8601>` — sem credencial, baixe manualmente e registre com `sparkforge.collect.register_artifact`.
2. `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id>.jsonl --out .sparkforge/facts.json`. Leia `unresolved`: log truncado é ponto cego, não ausência de skew.
3. `sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped`. `--show-skipped` não é opcional aqui — distingue "não há skew" de "não coletei o dado que provaria skew".
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

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
