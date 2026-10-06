# Evaluation Phase Readiness

Preparacao para a fase seguinte — **Evaluation-Driven Engineering** — sem
criar subsistemas novos. Este documento responde o que a instrumentacao
existente ja mede e onde a medicao ainda depende de fora do core.

- Escrito em: 2026-10-06
- BASE_SHA da onda de closure: `a1bf2ad`
- Regra permanente: o runtime nunca importa `sparkforge.evals`;
  a fronteira esta em `docs/harness/RUNTIME-VS-EVALUATION.md` e e
  defendida por `tests/test_harness_boundary.py`.

## Core metrics — o que e coletavel hoje

| metrica | origem | coletavel hoje? |
|---|---|---|
| context bytes | `payload_bytes` gravado por `call_tool` no ledger de contexto (`sparkforge/observability/context_ledger.py`) | sim — medido por chamada, recusas incluidas |
| context utilization | selecao do Context Gateway expoe `context_tree`/`execution_plan` + budget por profile (`economy`/`balanced`/`deep`) | sim — uso vs budget sai do resultado do gateway |
| evidence recall | `scripts/check_recall_economy.py` (piso de 100% por nome) + `match_rate` de `evaluate_golden_case` | sim — gate ja existe |
| provider token coverage | `tokens_status` por span (`agentops`), `provider_tokens` no ledger e nos decision receipts | **parcial** — so `measured` quando um transcript do host alimenta; caso contrario `tokens_unresolved`/`unresolved`, nunca zero |
| tool calls | ledger grava cada `call_tool` | sim |
| agent calls | spans/runs do AgentOps (`sparkforge/observability/agentops.py`) | sim — quando o host registra spans do run |
| review count | reviews/debates do executor agentic | parcial — contam quando o run e registrado no ledger AgentOps |
| debate count | `sparkforge/agentic/executor/debate_run.py` + spans | parcial — idem; o executor registra, a contagem sai dos spans gravados |
| recovery attempts | `RecoveryPolicy.next` / `RecoveryDecision.attempt` (`sparkforge/agentic/recovery.py`) | parcial — a decisao carrega `attempt`; uma serie temporal exige o run registrar as tentativas |
| recovery success | desfecho do span/run com recovery | parcial — derivavel quando o run registra outcome por tentativa |
| latency | `duration_seconds` por span; waiting entre spans em `agentops_critical_path` | sim — medido, nunca inferido |
| cost when observed | `cost_status` no AgentOps; `finops` exige `dpu_seconds` observado | sim — `when observed`; sem observacao volta `unresolved` |
| unresolved count | campo `unresolved` em envelopes, handoffs, resultados, receipts | sim — estrutural |

## As seis perguntas do prompt

**What can be measured today?**
Context bytes, utilizacao de contexto, evidence recall, tool calls,
latencia por span, unresolved count e custo — quando observado — sao
medidos hoje por instrumentacao existente (ledger, gateway, AgentOps,
gates de recall). Nenhum subsistema novo e necessario para comecar a
fase.

**What remains unresolved?**
`provider_tokens` sem transcript do host (permanece `tokens_unresolved`),
`provider_availability` do Model Router (offline por desenho),
`agentops_timeline` sem paginacao (BACKLOG), cobertura de medicao
fora dos caminhos instrumentados — latencia fim-a-fim de CLI e taxa de
resolucao sobre corpus real, ja registrados em `docs/harness/BASELINE.md`.

**What requires provider transcript?**
`provider_tokens` e qualquer comparacao de economia em tokens de
provedor. O core mede `payload_bytes`; tokens do provedor so entram por
transcript do host — regra do `tokens_unresolved`, nao inferencia.

**What requires cloud?**
Os verbos `collect *` (unico caminho que toca AWS), `dpu_seconds` real,
runs de Glue/EMR reais para custo observado. O core e offline por
construcao — o que exige nuvem fica marcado, nunca simulado.

**What is Lab-only?**
Os corpora de `evals/` e `fixtures/` (79 corpora golden), o seed offline
do Decision Plane (23 casos), o benchmark de profile
(`evals/token_efficient/suite.yaml` + `scripts/check_token_efficient_bench.py`)
e os testes de contrato — medem, mas sobre corpus de laboratorio.

**What is production-only?**
Transcripts de host reais, traces de runs reais no ledger AgentOps,
observacao de `provider_availability` e custo com `dpu_seconds` medido.

## Profile comparison (preparacao, nao resultado)

Comparacao `economy`/`balanced`/`deep` sobre os **mesmos cenarios** ja e
executavel: `evals/token_efficient/suite.yaml` +
`check_token_efficient_bench.py`. A leitura correta e Pareto em
qualidade/custo/latencia/seguranca/evidencia — nao existe winner global,
e nenhum sera inventado.

## Agent necessity (eval futura)

O par `with agent` / `without agent` exige corpus rotulado e harness que
rode os dois bracos no mesmo cenario — nao existe hoje e nao foi
construido nesta onda. Classificacao: **BACKLOG** da fase de avaliacao,
com gatilho = primeiro corpus de tarefas reais rotulado.

## O que deliberadamente NAO foi feito

- Nenhum mega dashboard — os dados acima ja sao coletaveis;
  a fase decide como agrega-los.
- Nenhum subsistema novo de metricas — a instrumentacao existente cobre
  o conjunto-core ou marca `unresolved` honestamente.
