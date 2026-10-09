---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_EVALS/plan.md
  sha256: "1c9b655d838f1b7b689608fdf1a10613ed2ce4f416ecd403520e34126651f430"
tasks:
  - id: T1
    status: skipped
  - id: T2
    status: skipped
claims:
  - text: "A suite offline declara eixos de qualidade/economia, oito casos seed, expected, forbidden, unresolved, evidence, routing, arquitetura e limites de contexto."
    evidence_ref: "tests/test_platform_evals.py::test_platform_eval_contract_has_quality_and_economy_axes"
  - text: "A política de provider tokens separa bytes de tokens e exige transcript do host para resolver tokens."
    evidence_ref: "tests/test_platform_evals.py::test_platform_eval_knowledge_separates_tokens_and_bytes"
change_id: null
---

# PLATFORM_INTELLIGENCE_EVALS — relatório do build

## Entrega

As duas tarefas foram implementadas anteriormente: contrato/checker/seed pack
(`d7e8c8c`) e política documentada (`0721e1c`). O checker é offline e não chama
provider, AWS ou runtime externo.

## Desvio de execução dos testes

T1–T2 estão `skipped` porque a implementação precede este relatório e o
histórico não preserva comandos vermelhos reproduzíveis. Nenhum exit foi
inventado. A validação atual foi executada com
`python -m pytest tests/test_platform_evals.py -q --basetemp
.sparkforge_aws/local/pytest-platform-evals`, que terminou com `2 passed`.

## Revisão

A revisão contra define/design confirmou que quality axes e economy axes são
separados, que cada caso exige evidence e que `provider_tokens` só é resolvido
com `host_transcript_ref`; sem transcript permanece
`unresolved_without_host_transcript`. O seed é declarado como seed e não como
corpus de produção.
