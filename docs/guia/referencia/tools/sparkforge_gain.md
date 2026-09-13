<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_gain`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Realized Gain Ledger: o ganho OBSERVADO entre runs ja medidos de um job Glue antes (`baseline_paths`) e depois (`candidate_paths`) de uma mudanca. Cada caminho e um arquivo de facts de runs (`analyze glue-job-runs --out`); so runs SUCCEEDED contam, e os lados precisam ser do mesmo job. Por lado e por metrica (tempo de execucao, DPU-segundos, custo do `glue.run_cost` do mesmo run): N, mediana, minimo e maximo, e o delta das medianas em valor e %. O delta sai sempre, com as marcas que dizem quando ele NAO e ganho: amostra_insuficiente (< 3 runs), volume_diverge / volume_desconhecido (bytes varridos, criterio do capacity), custo_indisponivel. O QUE ELA NAO FAZ, e isto e contrato: nao projeta economia mensal, nao atribui o delta a mudanca (sem run de controle) e nao publica intervalo de confianca -- as tres saem em `refused`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `baseline_paths` | string ou array de string | sim | Arquivos de facts dos runs de antes da mudanca. |
| `candidate_paths` | string ou array de string | sim | Arquivos de facts dos runs de depois da mudanca. |

## Na CLI

[`sparkforge gain`](../cli/gain.md)

## Capacidade

show the observed gain between measured runs

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
