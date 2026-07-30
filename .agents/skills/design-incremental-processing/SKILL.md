---
name: design-incremental-processing
description: Use quando um job dito incremental continua lento mesmo com pouca entrada, faz scan global, recomputa estado histórico, ou você precisa projetar bootstrap, ciclos, backfill, late data, deletes e idempotência de forma que a entrada pequena realmente reduza bytes e arquivos lidos.
---

# Design Incremental Processing

## Objetivo

Determinar se o job é realmente incremental e projetar uma estratégia segura para bootstrap, ciclos normais, backfill e recuperação.

## Investigar

- origem das mudanças;
- watermark;
- coluna de controle;
- snapshots;
- chaves afetadas;
- late-arriving data;
- correções retroativas;
- deletions;
- idempotência;
- replay;
- reprocessamento;
- backfill;
- full inicial;
- estado atual;
- histórico;
- partições/arquivos afetados;
- modo de escrita Iceberg.

## Teste central

Pergunte:

> Uma entrada de 26 mil registros reduz bytes lidos, arquivos planejados, registros antes dos exchanges e arquivos reescritos?

Se não, o fluxo é incremental apenas na entrada.

## Estratégias possíveis

- tabela current-state por chave;
- tabela de chaves afetadas;
- leitura por janela temporal segura;
- lookback configurável;
- snapshots comparados;
- changelog/CDC;
- merge seletivo;
- materialização de referências;
- bootstrap separado;
- manutenção Iceberg desacoplada.

## Contrato de saída

```yaml
incremental_design:
  source_of_changes:
  watermark:
  affected_keys:
  required_lookback:
  current_state_table:
  history_table:
  deduplication:
  late_data_policy:
  delete_policy:
  idempotency:
  replay_strategy:
  full_load_strategy:
  cyclic_load_strategy:
  backfill_strategy:
  failure_recovery:
  observability:
```

## Regras

- Não assumir que filtro por lista de chaves garante file pruning.
- Confirmar arquivos e bytes lidos.
- Preservar late data e correções retroativas.
- Não usar bookmark como solução universal.
- Separar estratégia full e incremental quando cargas forem radicalmente diferentes.

## Quando NÃO usar

- A carga é sempre full/bootstrap homogênea: foque em `sparkforge-diagnose`/`tune-glue-job`.
- O gargalo é especificamente o latest-per-key: use `optimize-latest-per-key`.
- O "incremental" é um loop de batches na aplicação: veja `analyze-batch-loop`.

## Referência rápida

| Falso incremental (sintoma) | Causa | Correção de projeto |
|---|---|---|
| entrada pequena, runtime igual ao full | scan global / recomputação | tabela current-state; leitura por janela |
| filtra por lista de chaves mas lê tudo | sem file pruning | tabela de chaves afetadas + merge seletivo |
| late data quebra o resultado | janela sem lookback | lookback configurável e seguro |
| replay duplica dados | escrita não idempotente | merge/upsert idempotente por chave |
| deletes não propagam | política de delete ausente | delete/merge explícito + validação |

## Red flags

- Tratar `job.commit()`/bookmark do Glue como solução universal de incremental.
- Confundir "entrada pequena" com "trabalho pequeno" sem medir bytes/arquivos lidos.
- Misturar estratégia full e incremental quando as cargas são radicalmente diferentes.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
