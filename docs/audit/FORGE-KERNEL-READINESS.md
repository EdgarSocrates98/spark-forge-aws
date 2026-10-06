# Forge Kernel readiness — comparacao documental

§60-63: **nao extrair kernel ainda**; apenas comparar, em documento, os
primitivos candidatos entre `Spark Forge` e um consumidor externo
(`API Forge`, o irmao que consumiria um kernel compartilhado). Nenhum
codigo foi movido; isto e somente o mapa de prontidao.

- Escrito em: 2026-10-06
- Regra: `same semantics` / `similar semantics` / `domain-specific` /
  `not ready`. Um primitivo so e `same semantics` quando a forma serializa
  e a semantica nao dependem do dominio Spark.

## Primitivos candidatos

| primitivo | onde mora | semantica vs um consumidor externo | classe |
|---|---|---|---|
| `TrustEnvelope` | `agentic/trust.py` | generico: trust label + authority + taint + provenance; nenhum campo Spark | **same semantics** |
| `ContextRef` | `context/gateway_models.py` + `gateway_refs.py` | ref a contexto com kind/trust — generico, mas o vocabulario de `kind` e o do catalogo deste repo | **similar semantics** |
| `EvidenceRef` | `agentic/executor/debate_evidence.py`, `evals/evidence.py` | ref a evidencia ancorada; forma generica, produtores aqui sao os extractors deste dominio | **similar semantics** |
| `DecisionReceipt` | `economy/decision_receipts.py`, `decision/receipts.py` | receipt content-addressed de decisao de rota/orcamento — forma generica, payload e desta plataforma | **similar semantics** |
| `Budget` | `agentic/budget.py`, `agentic/executor/plan.py` | orcamento de agente (tokens/bytes/calls) — generico | **same semantics** |
| `RecoveryDecision` | `agentic/recovery.py` | politica deterministica retry/abort/escalate — generico | **same semantics** |
| `RouteHealth` | `economy/model_router.py::route_health()` | existe como **metodo** que devolve dict (`budget_health`, `provider_availability=unresolved`, `context_sufficiency`, `fallback_availability`) — nao e um tipo nomeado | **not ready** — promover a primitivo so quando um consumidor precisar da forma |
| `ForgeTask` | `protocols/forge.py` | task do Forge Protocol v1 — generico por desenho (id deterministico, `requested_by` ja aceita `api-forge`) | **same semantics** |
| `ForgeResult` | `protocols/forge.py` | result com `evidence_bundle` + `unresolved` separados — generico por desenho | **same semantics** |

## O que falta para extrair

- **Um segundo consumidor real.** `api-forge` hoje e um `requested_by`
  num teste (`tests/test_agentic_os_v2.py`), nao um servico. Sem
  consumidor, um kernel extraido e uma fronteira sem pressao.
- **`RouteHealth` como tipo.** Hoje e um metodo; virar primitivo exige o
  consumidor declarar os campos que precisa.
- **Vocabulario de `kind`/contexto neutro.** `ContextRef` e
  `EvidenceRef` carregam o vocabulario deste repo; um kernel exige a
  forma neutra ou um namespace de dominio declarado.

## Decisao

**NOT_NOW.** Os primitivos ja nasceram com a semantica certa
(`DATA_ONLY`, `unresolved` nomeado, ids deterministicos) — a extracao e
barata *quando* houver consumidor. Extrair antes disso cria um pacote
sem cliente e um segundo lugar para os mesmos contratos divergirem.
Gatilho: um consumidor fora deste repo importando um dos primitivos
`same semantics`; a decisao reabre por ADR + evidencia, conforme
`docs/audit/ARCHITECTURE-FREEZE.md`.

## Forger readiness (§65)

O que um orquestrador externo precisa continua possivel sobre Forge
Protocol v1:

- **capability discovery** — `sparkforge protocols`/`forge card` expoem
  capacidades declaradas;
- **task submission** — `ForgeTask` admissivel com id deterministico;
- **result** — `ForgeResult` com estados do vocabulario v1;
- **evidence** — `evidence_bundle` separado do resultado;
- **unresolved** — primeiro-class em todo resultado, nunca arredondado.

Nenhuma orquestracao nova foi adicionada aqui — The Forger pertence ao
projeto dele; Spark Forge permanece interoperavel por v1.
