---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_EVALS/explore.md
  sha256: "4f90546dfff625dbde845fa931235aed3000faa7a7bf79731397c0eff51406d5"
hypothesis:
  claim: "Um contrato de eval que pontua fatos, findings, proibições, unresolved, arquitetura, evidence, routing e economia torna evolução do Control Plane auditável."
  prediction: "Cada caso valida shape e autoridade; métricas de provider tokens ficam unresolved sem transcript do host e bytes/tool calls permanecem medidas separadas."
  experiment: "Validar suite.yaml e casos seed por script offline, sem chamar provider ou executar suíte de produto."
acceptance:
  - id: AC1
    statement: "A suite declara métricas de qualidade, evidence, routing e economia e casos com expected/forbidden/unresolved."
    verified_by: {kind: command, ref: "python scripts/check_platform_eval_contract.py --path evals/platform_intelligence/suite.yaml"}
  - id: AC2
    statement: "A validação recusa caso sem required_evidence, expected_unresolved ou política explícita de provider tokens."
    verified_by: {kind: test, ref: "tests/test_platform_evals.py::test_platform_eval_contract_has_quality_and_economy_axes"}
success:
  - id: SC1
    metric: "Casos válidos / total de casos declarados e campos de economia sem conversão inventada"
    source: "saída de check_platform_eval_contract.py"
out_of_scope:
  - "Rodar a suíte de produto nesta sessão."
  - "Afirmar recall/precision de produção antes de corpus rotulado suficiente."
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Adicionar casos reais com expected facts/findings aprovados e transcript quando provider token for necessário."
case_id: null
change_kinds: [knowledge_doc]
---

# PLATFORM_INTELLIGENCE_EVALS — requisitos

O contrato deve separar qualidade e economia. `provider_tokens` somente aceita
valor com `host_transcript_ref`; caso contrário, `tokens_unresolved: true`.
