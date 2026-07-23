---
name: optimize-latest-per-key
description: Use quando o job calcula o registro mais recente por chave (row_number/Window, max_by, max(struct), join-back) sobre tabelas Spark/Iceberg grandes com Window global, sort/shuffle de todo o histórico, empates por timestamp, late data ou recomputação a cada ciclo.
---

# Optimize Latest Per Key

## Mapear semântica

- chave de negócio;
- coluna temporal;
- desempate;
- registros nulos;
- múltiplos registros com mesmo timestamp;
- late-arriving data;
- correções;
- necessidade de histórico;
- colunas associadas ao registro vencedor.

## Estratégias a comparar

- `row_number` sobre Window;
- `max_by` quando semanticamente equivalente e suportado;
- agregação por máximo + join-back;
- tabela current-state;
- atualização somente das chaves afetadas;
- pré-compactação do changelog;
- redução temporal segura;
- sort order/layout Iceberg.

## Riscos

- Window global sobre bilhões de registros.
- Sort/shuffle de todo o histórico.
- Join-back multiplicando linhas em caso de empate.
- `max(struct(...))` com ordenação semântica incorreta.
- latest inconsistente por timezone ou timestamp nulo.
- recomputação em cada ciclo.

## Evidências

Registre:
- linhas e bytes antes/depois do filtro;
- distinct keys;
- tamanho e distribuição das chaves;
- exchange e sort no plano;
- spill;
- duração do stage;
- arquivos Iceberg lidos;
- frequência de recomputação.

## Saída

- semântica formal do latest;
- estratégia atual;
- custo físico;
- alternativas seguras;
- código;
- plano de benchmark;
- testes de empate, late data e replay.

## Quando NÃO usar

- Não é latest-per-key e sim skew genérico em join/agg: use `diagnose-data-skew`.
- O problema é a manutenção da tabela Iceberg em si: use `optimize-iceberg-table`.
- Precisa desenhar todo o fluxo incremental ao redor: use `design-incremental-processing`.

## Referência rápida

| Estratégia | Quando prefere | Cuidado |
|---|---|---|
| `row_number()` sobre Window | precisa de desempate/colunas do vencedor | Window global = sort/shuffle de todo histórico |
| `max_by(col, ts)` | latest de poucas colunas, suportado | semântica de empate; suporte da versão |
| agregação `max(ts)` + join-back | flexível | join-back duplica linhas em empate |
| tabela current-state incremental | recomputação a cada ciclo | manter idempotência e late data |
| redução temporal (janela segura) | histórico enorme | escolher lookback que não perca correções |

## Red flags

- Aplicar Window global sobre bilhões de registros a cada execução (recomputar histórico).
- `max(struct(ts, ...))` sem garantir a ordem semântica correta das colunas.
- Ignorar empates de timestamp e timezone/nulos ao definir o "mais recente".
