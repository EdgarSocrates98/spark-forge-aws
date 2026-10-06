---
name: design-realtime-data-architecture
description: "Use quando houver requisitos de workload streaming e for necessário comparar candidatos por constraints, preservando assumptions, unresolved e ADR sem fabricar vencedor."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-realtime-candidate-matrix.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws architecture streaming
subagent: true
agent: streaming-realtime-architect
---

# Design Realtime Data Architecture

Use JSON offline para separar requisitos declarados de premissas e executar a
matriz de candidatos:

```bash
sparkforge-aws architecture streaming \
  --path workload-requirements.json \
  --out streaming-architecture.json
```

## Procedimento

1. Exija `requirements` para constraints operacionais: source, sink, state,
   `foreachBatch`, output mode, API e managed-only.
2. Registre `assumptions` separadamente. Nunca use hipótese como prova.
3. Leia `candidate_matrix`, `constraint_elimination` e `unresolved` antes do
   ADR.
4. Aceite `selected` somente quando exatamente um candidato permanecer
   suportado por constraints factuais.
5. Se houver empate, latência/custo não medidos ou requisitos ausentes,
   mantenha ADR `unresolved` e liste o artefato ou experimento que destrava.

## Limites

- `supported` significa somente "não eliminado pelas constraints fornecidas";
- a matriz não mede benchmark, custo, throughput, SLO ou disponibilidade;
- nenhum serviço é alterado e nenhuma infraestrutura é provisionada;
- a decisão exige validação de runtime, contrato, replay, segurança e rollback.

## Quando NÃO usar

Não use para ranking por preço, benchmark ou provisionamento. Requisitos não
declarados ficam unresolved.

## Referência rápida

Requirements e assumptions ficam separados; `fact_id` e `*.unresolved` guiam o
ADR; toda recomendação inclui `validation` e `rollback`.

## Red flags

Candidate supported não significa escolhido, capaz, barato ou exatamente-once.

## Contrato de qualidade SparkForge (v1)

O engine não inventa evidência: preserve facts, findings, `fact_id`, unresolved,
validation e rollback.

## Protocolo

Siga `AGENT_PROTOCOL.md`, não executa manutenção destrutiva; sobe qualquer
mudança de runtime ao operador.
