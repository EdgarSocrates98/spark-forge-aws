---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_CROSS_ARTIFACT/explore.md
  sha256: "94efe26f070bca77d728efe33e2e9699979b09179a9e03015aac9909625d0cbc"
hypothesis:
  claim: "A composição offline entre job Glue Streaming observado e aws_glue_job Terraform transforma drift de configuração em evidência julgável sem confundir ausência com consistência."
  prediction: "Identidade literal única produz link com campos comparados; divergências produzem finding; identidade ou valores ausentes/não literais produzem unresolved nomeado."
  experiment: "Executar fixtures match/divergent/unresolved, fundir e julgar regras, conferir paridade pelo fuse existente e rodar gates do catálogo, SDD, docs e superfície."
acceptance:
  - id: AC1
    statement: "Um job Glue observado e um recurso aws_glue_job Terraform com o mesmo name literal produzem glue.streaming.terraform_link com source_fact_ids e status de comparação."
    verified_by: {kind: test, ref: tests/test_streaming_glue_cross_artifact.py::test_matches_effective_glue_job_to_terraform_resource}
  - id: AC2
    statement: "A composição compara somente valores observados/literais para glue_version, RTM, language e worker_count; cada divergência fica nomeada e a ausência fica unresolved."
    verified_by: {kind: test, ref: tests/test_streaming_glue_cross_artifact.py::test_reports_drift_and_unresolved_fields_without_inference}
  - id: AC3
    statement: "SF-GLUESTREAM-004 julga drift de configuração e SF-GLUESTREAM-005 julga cross-artifact não resolvido com evidência do link/recusa."
    verified_by: {kind: test, ref: tests/test_streaming_glue_cross_artifact.py::test_cross_artifact_rules_are_evidence_backed}
  - id: AC4
    statement: "Fuse permanece backward compatible e idempotente; casos sem Glue/TF não recebem facts novos."
    verified_by: {kind: test, ref: tests/test_streaming_glue_cross_artifact.py::test_fuse_cross_artifact_is_guarded_and_idempotent}
  - id: AC5
    statement: "Fixtures, knowledge, skill, prompt coverage, SDD e gates registram que o link não prova runtime live, execução nem resultado funcional."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; drift declarado vira finding P0/P1 conforme regra, blind spot permanece unresolved e payload carrega apenas resumo + refs."
    source: "pytest focalizado, goldens, judge e gates offline"
out_of_scope:
  - "collector live de Glue, Terraform Cloud ou AWS Config"
  - "parse completo de HCL/state e resolução de interpolação"
  - "prova de execução, latência, capacidade, custo ou semântica de entrega"
  - "inferir nome do job a partir do resource_name quando name não for literal"
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Preservar name literal em ambos os artefatos e valores Terraform observáveis."
  - id: U2
    blocks: [AC5]
    unlock: "Regenerar referências, mirrors, locks, manifesto e números correntes após a mudança."
change_kinds: [extractor, fixture_corpus, knowledge_doc, rule, agent_or_skill, status_numbers]
---

# STREAMING_GLUE_CROSS_ARTIFACT — definição

O resultado é um fato composto offline, não uma afirmação de que o job foi
aplicado ou executado.
