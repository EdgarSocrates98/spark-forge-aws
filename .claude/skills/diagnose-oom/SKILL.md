---
name: diagnose-oom
description: Use quando um job Glue falha com OutOfMemory, "Container killed by YARN", "GC overhead limit exceeded", ExecutorLostFailure, "exceeds spark.driver.maxResultSize" ou estoura o Python worker, e você precisa classificar se é driver, executor, broadcast, metadata ou plan/lineage explosion antes de mitigar.
---

# Diagnose OOM

## Classificar primeiro

- driver OOM;
- executor JVM OOM;
- Python worker OOM;
- container killed;
- GC overhead exceeded;
- broadcast OOM/failure;
- max result size;
- metadata explosion;
- plan/lineage explosion;
- Arrow/Pandas memory pressure.

## Coletar

- exceção completa;
- componente;
- stage/task;
- executor;
- batch/iteração;
- heap e GC antes da falha;
- spill;
- tamanho da maior partição;
- broadcast size;
- result size;
- número de arquivos/manifests;
- tamanho do plano;
- caches ativos;
- objetos coletados no driver.

## Diferenciação

Não tratar todo OOM como falta de memória:
- skew causa uma task gigante;
- collect causa driver OOM;
- batching pode acumular lineage/commits;
- broadcast indevido replica dados;
- UDF/Pandas pode estourar Python worker;
- metadata de milhões de arquivos pode estourar driver;
- persistência pode ocupar memória útil.

## Saída

```yaml
oom:
  location:
  exception:
  stage:
  task:
  batch_number:
  evidence:
  probable_cause:
  confidence:
  immediate_mitigation:
  structural_fix:
  validation:
  rollback:
```

## Quando NÃO usar

- Não há falha, só lentidão/custo: use `sparkforge-diagnose` ou `analyze-spark-ui`.
- O OOM ocorre dentro de um loop de batches: combine com `analyze-batch-loop`.
- A causa é uma chave quente confirmada: aprofunde em `diagnose-data-skew`.

## Referência rápida

| Sintoma na exceção/log | Classificação | Mitigação inicial (não estrutural) |
|---|---|---|
| `maxResultSize exceeded` / falha logo após `collect` | Driver OOM | remover collect/toPandas; agregar distribuído |
| `Container killed by YARN ... memory limits` | Container / executor overhead | reduzir partição; revisar off-heap/PySpark memory |
| `GC overhead limit exceeded` | Memory/GC-bound | reduzir dados por task; revisar cache |
| falha em `BroadcastExchange` | Broadcast OOM | remover hint; medir tamanho serializado |
| driver estoura ao planejar tabela enorme | Metadata explosion | reduzir nº de arquivos/manifests; manutenção Iceberg |
| erro no Python worker / Arrow | Python/Pandas pressure | limitar UDF; ajustar batch do Arrow |

## Red flags

- Aumentar worker type/memória como primeira e única resposta.
- Tratar como "pouca memória" um OOM cuja causa raiz é skew, collect, broadcast ou lineage.
- Não registrar em qual iteração/batch a falha ocorre em jobs com loop.
