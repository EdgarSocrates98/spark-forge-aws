# Realized Gain Ledger

`sparkforge gain` responde uma pergunta só: **entre os runs medidos antes e
depois de uma mudança, quanto o tempo, os DPU-segundos e o custo mudaram?**

O SparkForge recusa estimar ganho (regra 13 do `CLAUDE.md`): "você economizaria
Y" exige o custo do run que não aconteceu. O ledger é o outro lado dessa recusa.
Ele só compara runs que **já aconteceram**, e diz em marca quando a comparação
não sustenta a palavra "ganho".

## Uso

```bash
sparkforge gain \
  --baseline runs/antes/run_01.json --baseline runs/antes/run_02.json ... \
  --candidate runs/depois/run_01.json --candidate runs/depois/run_02.json ...
```

Cada arquivo é um conjunto de facts de run, na forma que
`sparkforge analyze glue-job-runs --out <arquivo>` produz — o mesmo histórico
que `capacity` e `workload` leem. A tool MCP é `sparkforge_gain`
(`READ_ONLY`), com `baseline_paths` e `candidate_paths`.

## O que sai

Para cada métrica — `execution_time_s`, `dpu_seconds` e `cost` — e para cada
lado: `n`, `median`, `min` e `max`. Depois, o delta das medianas em valor
(`delta`) e em percentual (`delta_pct`, sobre a mediana do baseline).

O que conta:

- só `glue.job_run` com `state` `SUCCEEDED`; os outros saem contados em
  `discarded.run_nao_sucedido`;
- o custo é o `glue.run_cost` do **mesmo** `job_run_id`, na mesma moeda;
- o volume de cada run é o dos `spark.sql.scan` do mesmo arquivo, pelo mesmo
  critério do `capacity` — e só quando o arquivo tem um run, porque com vários
  não há como ligar o scan ao run.

Os dois lados precisam ser do mesmo job e ter ao menos um run válido; senão a
saída é erro de entrada (exit 2), não um delta.

A capacidade de cada lado (`glue_version`, `worker_type`,
`number_of_workers`, `autoscaling`, com a contagem de runs) sai como
informação. Mudar capacidade é uma das mudanças que o ledger mede, então ela não
é marca.

## As marcas

O delta sai **sempre**. As marcas dizem quando ele não é ganho:

| Marca | Quando |
|---|---|
| `amostra_insuficiente` | menos de 3 runs num dos lados |
| `volume_desconhecido` | um dos lados não tem volume medido |
| `volume_diverge` | as medianas de volume diferem mais que a tolerância |
| `custo_indisponivel` | só em `cost`: algum run sem `glue.run_cost`, ou moedas diferentes |

A tolerância de volume é a de `workload.declared` (`volume_tolerance`) quando o
job a declara, e 0,25 quando não — a mesma do `capacity`. Sem `dpu_seconds` não
há custo (regra 14), e é por isso que o custo tem marca própria.

## O que ele recusa, sempre

Três campos saem em `refused`, com o motivo:

- `economia_mensal` — projetar sobre runs que não aconteceram (regras 12 e 13);
- `atribuicao_causal` — sem run de controle, o delta mistura a mudança com tudo
  o que mudou junto (dado, cluster, concorrência);
- `intervalo_de_confianca` — a amostra típica é pequena; mediana e faixa no
  lugar.

## Exemplo medido

`fixtures/gain/ganho_por_capacidade` recorta `capacity/cheapest_that_fits`:
G.1X ×10 contra G.2X ×10, 10 runs de cada lado, 2 GB nos dois. A mediana do
tempo vai de 900 s para 500 s (**−44,4%**) e a dos DPU-segundos de 900 para
1000 (**+11,1%**). O ledger mostra os dois números lado a lado e não escolhe
qual deles é "o ganho". O custo sai com `custo_indisponivel`, porque o recorte
não tem `glue.run_cost`.
