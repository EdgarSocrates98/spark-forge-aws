---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_PRODUCT/build_report.md
  sha256: "c1a52ba3f71a5bf482e2ab502e080ac49d3981971834f689c7753a2da68803a8"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity, claims_gate, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "T1–T6 não registraram red/green por instrução explícita do operador; a validação final é feita depois do fechamento de todas as fases."
  - "L1/L2 não foram iniciados neste host; disponibilidade de Docker, imagens e digests continua dependente de lab doctor e execução explícita."
  - "Forge Lab lifecycle permanece CLI-first e não cria uma tool MCP nova; a análise topológica existente continua separada e read-only."
---

# FORGE_LAB_PRODUCT — entrega

## Hipótese

Confirmada no escopo offline: um único registry e uma única DSL compilam
cenários para planos equivalentes entre Compose e Testcontainers; captura,
receipt, oracle independente, promoção revisada e guardas de mutação preservam
evidência sem afirmar performance não medida.

## O que foi entregue

- Foundation contracts, registry versionado e fidelidade L0–L3.
- Golden 20 declarativo, generators determinísticos, workloads separados e
  faults allowlisted.
- Runtime guardado, doctor, Compose/Testcontainers e contrato AWS opt-in.
- Run directories, probes, artifacts, receipts, oracle independente,
  equivalência multi-engine e promoção de fixtures.
- CLI completa: doctor, profiles, scenarios, verify, describe, plan, run,
  inspect, analyze, compare, promote-fixture, reproduce e lifecycle guardado.
- Knowledge, README operacional, schemas, referência CLI e mirrors de agentes.

## Limites explícitos

O Lab não simula AWS, não substitui execução real e não prova throughput,
latência, custo ou exactly-once por declaração. Execução L3 exige região,
owner, TTL, budget, prefixo, tags, `--execute` e `--confirm`; ausência de
evidência permanece `UNRESOLVED`.

## Gates

Os gates de superfície, referências, SDD, skills, agents e números correntes
serão registrados após a suíte final. Nenhuma mutação AWS ou Docker foi feita.
