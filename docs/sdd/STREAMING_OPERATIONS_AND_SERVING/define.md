---
sdd: 1
feature: STREAMING_OPERATIONS_AND_SERVING
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_OPERATIONS_AND_SERVING/explore.md
  sha256: "35b4eb8f9a0849869dd8248929bb7e8a851b8e0f76384c1f69f00d613862a14f"
hypothesis:
  claim: "Um contrato offline tipado torna lacunas operacionais de streaming detectáveis sem converter declaração em prova."
  prediction: "Contratos completos produzem facts por domínio; contratos incompletos e campos sensíveis produzem unresolved e regras acionáveis."
  experiment: "Executar fixtures complete, missing e redaction; comparar CLI/MCP, judge, catálogo, superfície e gates offline."
acceptance:
  - id: AC1
    statement: "SLO e FinOps preservam medidas declaradas com contexto mínimo e não calculam preço."
    verified_by: {kind: test, ref: tests/test_facts_streaming_ops.py::test_streaming_ops_preserves_declared_metrics_without_secret_values}
  - id: AC2
    statement: "Campos sensíveis não aparecem nos facts e a lacuna de redaction é preservada."
    verified_by: {kind: test, ref: tests/test_facts_streaming_ops.py::test_streaming_ops_redacts_secret_like_fields}
  - id: AC3
    statement: "Fixtures golden distinguem contrato completo, contrato ausente e redaction."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_ops.py::test_streaming_ops_goldens}
  - id: AC4
    statement: "CLI e MCP retornam o mesmo envelope determinístico para a mesma entrada."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_ops.py::test_cli_and_mcp_envelopes_match}
  - id: AC5
    statement: "Rules, skill, knowledge, mirrors, referências e números correntes permanecem sincronizados."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; eficácia live, preço e benchmark permanecem unresolved quando não observados."
    source: "pytest do extrator/fixtures/superfície e gates offline"
out_of_scope:
  - "collector live de IAM, KMS, VPC, CUR ou serving"
  - "cálculo de preço ou atribuição causal de custo"
  - "benchmark de latência, throughput, disponibilidade ou formato"
  - "provisionamento e alteração de infraestrutura"
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "Regenerar superfície, manifesto, fontes, bundle offline, mirrors e status após a mudança."
  - id: U2
    blocks: [AC5]
    unlock: "Adicionar collectors e evidência de runtime em wave posterior, com confirmação operacional."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, status_numbers]
---

# STREAMING_OPERATIONS_AND_SERVING — definição

O resultado é evidência declarada por domínio, não um score de prontidão. Cada
lacuna nomeia o artefato que falta para o próximo passo.
