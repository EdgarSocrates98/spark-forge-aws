# Architecture Freeze

Declaracao do estado arquitetural do Spark Forge ao fim da onda de
final-hardening. Freeze aqui significa: **mudanca arquitetural agora exige
evidencia** — medida de gap + ADR + evidencia de avaliacao. Nao significa
paralisia; significa que o shape atual e o default ate que a avaliacao
prove o contrario.

- Declarado em: 2026-10-06
- Baseline da onda: `a1bf2ad` (`origin/main`)

## Congelado

| plano | superficie |
|---|---|
| Agentic Runtime | `sparkforge_aws/agentic/` — dispatch, handoff admission, executores |
| Decision Plane | `sparkforge_aws/decision/` — kernel bounded, receipts, fachada legado |
| Governor | gates de autoridade/autonomia no runtime agentic |
| Recovery | `sparkforge_aws/agentic/recovery.py` — policy deterministica |
| Trust Plane | `sparkforge_aws/agentic/trust.py` — TrustEnvelope, TrustLabel, Taint |
| Memory | handoff-aware, `MEMORY` rank — evidencia, nunca autoridade |
| Context Gateway | `sparkforge_aws/context/` — role plans, profiles, fail-closed |
| Model Router contracts | SHADOW-only; `provider_availability` unresolved por desenho |
| AgentOps contracts | ledger, spans, `tokens_status`/`cost_status` com `unresolved` |
| Forge Protocol v1 | `sparkforge_aws/protocols/forge.py` — preservado, sem quebra |
| MCP surface architecture | 143 tools full / 7 compact — trava em `docs/surface.lock.json` |

## O que ainda pode mudar durante o freeze

- bug fixes
- security fixes
- dependency updates (com gates de supply-chain)
- knowledge updates (`rules/catalog/`, docs, skills)
- spec compatibility (ex.: acompanhar bindings A2A)
- performance improvements **provadas por evidencia** (mesmo caso, baseline)
- pequenos aprimoramentos operacionais

## O que exige sair do freeze

`new runtime` · `new router` · `new governor` · `new memory architecture`
· `new protocol abstraction` · `new agent framework` · `new kernel`

Cada um exige, juntos:

1. **measured gap** — o gap medido, nao a preferencia;
2. **ADR** — em `docs/vnext/adrs/`;
3. **evaluation evidence** — a avaliacao que sustenta a mudanca.

## O que nao e blocker

Provider offline, CI indisponivel, A2A experimental, Decision Plane
fora de `ACTIVE`, scorecard in-memory, paginacao nao necessaria hoje —
nenhum e `P0`. Blocker de freeze e somente: bug de runtime conhecido,
bypass de seguranca, inconsistencia de autoridade, corrupcao de
evidencia ou comportamento-core nao reproduzivel.

## Freeze exit

A fase corrente passa a ser **Evaluation-Driven Engineering**: as
metricas de `docs/audit/EVALUATION-PHASE-READINESS.md` sao a evidencia
que o freeze exige. Sair do freeze = gap medido + ADR + avaliacao.
