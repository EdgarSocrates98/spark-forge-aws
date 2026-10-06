# ADR-013: Persistencia de scorecard de modelo — DEFERRED

## Status

Deferred — reabre quando existir consumidor real do arquivo.

## Context

`ModelScorecard` (`sparkforge/economy/model_router.py`) agrega observacoes de
qualidade por recorte (provider, model, task_type) e alimenta o
`AdaptiveModelRouter` **em memoria** — os scorecards entram por construcao.

`agentic_doctor` (`sparkforge/adapters/_core.py`) confere a existencia de
`.sparkforge/model-scorecards.json` como readiness check, mas **nenhum caminho
le ou escreve esse arquivo**: o check existe para declarar `unresolved`
honesto quando a fonte nao existe, e e isso que ele reporta hoje.

O router inteiro opera em modo SHADOW (`observe_adaptive_route` compara a
rota adaptativa contra o plano declarativo e emite recibo — a decisao nao
aplica nada), `activation_ready` sai `False` por construcao na avaliacao do
seed, e `provider_availability` sai `unresolved` porque o core e offline e
nao sonda provider. Nenhuma dessas tres propriedades muda nesta onda — elas
sao o comportamento correto por desenho, e esta ADR registra por que a
persistencia do scorecard NAO e construida agora.

## Decision

Nao construir armazenamento persistente de scorecards nesta onda.

Persistir o que nenhum consumidor le e superficie que parece capacidade sem
ser — exatamente o que o principio desta onda ("RUNTIME BEHAVIOR > FILE
EXISTENCE") proibe. Um arquivo `model-scorecards.json` escrito sem leitor
produziria a alucinacao estrutural de que o router observa qualidade de
provider, quando hoje ele so ranqueia o que o chamador declara.

A cadeia causal correta e: primeiro existe quem **escreve** observacoes
(fonte real de medicao de qualidade por recorte), depois existe quem **le**
(o router, na promocao). As duas pontas dependem de `provider_tokens` e
medicao de host que o core offline nao produz.

## Reopen triggers

Reabre quando **as duas** condicoes existirem:

1. um consumidor real do arquivo — um caminho que monte
   `AdaptiveModelRouter(scorecards=...)` a partir dele, com teste que leia o
   formato versionado;
2. um produtor real — um caminho que escreva observacoes medidas (nao
   auto-declaradas) no recorte correto, respeitando que `absent` nao e
   `cold` e que maturidade jovem nao sustenta decisao ativa
   (`SCORECARD_MATURE_MIN_OBSERVATIONS`).

## Consequences

- **Positivas**: nenhum formato de arquivo inventado hoje viraria legado
  amanha; `agentic_doctor` continua dizendo a verdade (`unresolved`); a
  fronteira entre "router ranqueia declaracao" e "router observa realidade"
  permanece visivel.
- **Trade-offs**: scorecards nao sobrevivem entre processos — a maturidade
  recomeca `absent` a cada execucao. Isso e o estado verdadeiro do sistema,
  nao uma falta a esconder.
