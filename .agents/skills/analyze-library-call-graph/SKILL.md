---
name: analyze-library-call-graph
description: Use quando o job Glue chama uma biblioteca Python com múltiplos módulos, factories, decorators ou helpers, e você precisa saber onde estão leituras, actions, caches, loops, UDFs, mudanças de Spark config e writes que não aparecem ao olhar só o entrypoint — count() escondido em logger, persist sem unpersist, write dentro de helper três chamadas abaixo. Use também quando perguntarem "essa lib tem algum job escondido", "de onde vem essa action extra", "até onde essa função chega" ou "isso é seguro de chamar", mesmo sem mencionar grafo de chamadas. Se você está prestes a seguir import por import manualmente para responder isso, rode `sparkforge analyze pyspark` e depois `sparkforge analyze call-graph` em vez disso — ele devolve a profundidade mínima e o caminho até cada trabalho Spark alcançável, o que uma lista de arestas sozinha não responde.
subagent: true
---

# Analyze Library Call Graph

## Por que uma lista de arestas não basta

Seguir imports manualmente até achar a função que executa trabalho Spark é viável para dois ou três níveis; a partir daí, revisor humano perde o fio. E mesmo achando a aresta `caller -> callee`, uma lista de arestas não responde a pergunta que importa: **essa action está a que profundidade do entrypoint, e por qual caminho se chega até ela?** Trabalho em profundidade 0 já está na cara de quem lê o entrypoint. Trabalho em profundidade 2 ou mais é exatamente o que passa despercebido numa revisão — e é o que esta skill existe para expor.

## Procedimento

### 1. Extraia os facts

```bash
sparkforge analyze pyspark --path <diretório-da-lib> --out .sparkforge/facts.json
```

Isso produz, entre outros, `pyspark.callgraph_edge` (aresta caller→callee) e os facts de trabalho Spark (`pyspark.read`, `.action`, `.write`, `.cache`, `.join`, ...) ancorados na função onde ocorrem.

### 2. Derive o grafo

```bash
sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/callgraph.json
```

Isso deriva estrutura a partir dos facts já extraídos — não reparseia nada. Produz quatro kinds: `callgraph.function`, `callgraph.reachable_spark_work`, `callgraph.cycle`, `callgraph.summary`.

### 3. Comece pelo summary

`callgraph.summary` traz `function_count`, `defined_function_count`, `entrypoint_count`, `max_depth`, `has_cycle` e três medidas que precisam ser lidas juntas:

- `unreachable_from_entrypoint_count` — nós que nenhuma travessia alcança. Só acontece em componente cíclico sem entrada; **não** é medida de código morto.
- `unreferenced_function_count` + `attrs.unreferenced_functions` — funções definidas (nível de módulo ou aninhadas), sem decorator, fora de `__all__`, que ninguém neste corpus chama e cujo nome não é lido em nenhum arquivo do corpus. A lista vem com os nomes: é ela que se leva ao operador, nunca a contagem sozinha.
- `opaque_caller_function_count` — quantas funções ficaram **fora** dessa população por serem método, decoradas ou exportadas. Se esse número é grande, a lista acima cobre pouco do módulo.

`attrs.dynamic_dispatch_present: true` significa que há `getattr` no corpus — com ele, qualquer nome da lista pode estar sendo chamado por string.

### 4. Leia `callgraph.reachable_spark_work` ordenado por `min_depth`

Um exemplo real desse fact:

```json
{
  "kind": "callgraph.reachable_spark_work",
  "subject": {"symbol": "run_pipeline", "file": "lib/pipeline.py", "line": 12},
  "measures": {"min_depth": 2, "occurrence_count": 1},
  "attrs": {
    "entrypoint": "run_pipeline",
    "work_kind": "pyspark.action",
    "via": ["run_pipeline", "_validate_batch", "_log_progress"]
  }
}
```

Leitura: a partir do entrypoint `run_pipeline`, existe uma `pyspark.action` alcançável a profundidade 2, chegando por `run_pipeline -> _validate_batch -> _log_progress`. Nenhuma linha de `run_pipeline` chama `.count()` diretamente — está dentro de um helper de log, chamado por um helper de validação. É o `count()` escondido em logger que a revisão de entrypoint nunca acha.

### 5. Interprete `min_depth`

- `min_depth == 0`: trabalho Spark direto no entrypoint. Visível em qualquer revisão.
- `min_depth >= 1`: passou por pelo menos um helper. Quanto maior, mais camadas de indireção escondem o custo.
- Cruze `work_kind` com o tipo: `pyspark.cache` alcançável sem `pyspark.write`/`pyspark.action` correspondente no mesmo `via` sugere cache sem uso real; `pyspark.action` repetido em `occurrence_count > 1` a partir do mesmo entrypoint é candidato a DAG recomputado.

### 6. Verifique ciclos

`callgraph.cycle` lista funções em recursão ou recursão mútua, com `contains_spark_work`. Um ciclo que carrega trabalho Spark é candidato a recomputação por chamada recursiva, não só risco de estouro de pilha.

## O que o grafo não vê

Arestas só existem entre chamadas **estaticamente resolvidas dentro do mesmo arquivo** — `callee` precisa ser uma função local reconhecida pelo AST do mesmo módulo. Isso significa que:

- Chamada entre arquivos diferentes (`from outro_modulo import helper; helper(df)`) **não vira aresta**. Se a biblioteca tem vários módulos, rode `analyze pyspark` no diretório inteiro, mas saiba que o grafo resultante mostra conexões dentro de cada arquivo, não a costura entre eles.
- Dispatch dinâmico (função guardada em variável, passada como callback, resolvida por nome em runtime) não aparece como aresta.
- Uma função sem caller no grafo pode ser dead code **ou** pode ser chamada de fora do escopo analisado (outro módulo, um `DAG` do Glue, um teste). Confirme antes de reportar como morta.

## Quando NÃO usar

- O código é um único script curto sem biblioteca: vá direto a `optimize-pyspark-code`.
- Você já tem o mapa e quer atacar o batching ou o incremental especificamente: use `analyze-batch-loop` ou `design-incremental-processing`.
- Precisa do plano físico de uma query específica: use `analyze-spark-plan`.

## Referência rápida

| Fact | O que captura | Por que importa |
|---|---|---|
| `callgraph.function` | `fan_in`, `fan_out`, `spark_work_count`, `is_entrypoint`, `is_leaf` por função | Localiza concentração de trabalho e funções nunca chamadas |
| `callgraph.reachable_spark_work` | `min_depth` + `via` por par (entrypoint, tipo de trabalho) | Responde "a que profundidade, por qual caminho" — o que a lista de arestas sozinha não responde |
| `callgraph.cycle` | funções em ciclo + se carregam trabalho Spark | Recursão/recursão mútua com trabalho Spark embutido |
| `callgraph.summary` | contagem de funções definidas, arestas, entrypoints, profundidade máxima, símbolos sem referência no corpus | Visão geral antes de mergulhar caso a caso |

## Red flags

- Concluir a análise só pelo entrypoint, sem consultar `callgraph.reachable_spark_work`.
- Tratar `unreferenced_functions` como prova de código morto. A medida diz "sem referência **neste corpus**" — se o recorte é uma biblioteca, o chamador é a aplicação que a importa, e ela não está no recorte. Antes de propor remoção, confirme com o operador quem consome o módulo, e cheque `dynamic_dispatch_present`.
- Tratar `unreachable_from_entrypoint_count` como código morto: ele só marca componente cíclico sem entrada.
- Ignorar `callgraph.cycle` com `contains_spark_work: true` como só um risco de recursão, quando também é recomputação.
- Assumir que a ausência de aresta entre dois módulos significa que eles não se chamam — pode só significar que o extrator não resolve chamada cross-arquivo.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
