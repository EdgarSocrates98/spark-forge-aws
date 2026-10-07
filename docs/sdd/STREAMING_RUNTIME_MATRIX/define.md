---
sdd: 1
feature: STREAMING_RUNTIME_MATRIX
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_RUNTIME_MATRIX/explore.md
  sha256: "0a85a74981a7bd7040d0825122b0421c03ae410074637102b6d1677a28d5f4bb"
hypothesis:
  claim: "Uma matriz evidence-first reduz o risco de aplicar capability upstream em runtime managed errado."
  prediction: "Cada linha P0 separa estado, versão/referência e limite; fontes citadas entram no source lock e o bundle offline permanece íntegro."
  experiment: "Rodar o teste da matriz, refresh offline, verificação do bundle e os gates de knowledge."
acceptance:
  - id: AC1
    statement: "A matriz separa upstream, managed e runtime observado, com VERIFIED, UNRESOLVED ou N/A + motivo."
    verified_by: {kind: test, ref: tests/test_streaming_runtime_matrix.py::test_streaming_runtime_matrix_has_explicit_states_and_boundaries}
  - id: AC2
    statement: "Toda fonte citada pela matriz está no source lock e o documento está no offline manifest."
    verified_by: {kind: test, ref: tests/test_streaming_runtime_matrix.py::test_every_streaming_matrix_source_is_in_the_offline_source_lock}
  - id: AC3
    statement: "O pacote offline verifica a matriz sem rede."
    verified_by: {kind: command, ref: python scripts/verify_offline_bundle.py --check}
success:
  - id: SC1
    metric: "AC1–AC3 verdes"
    source: "pytest da matriz e gates offline"
out_of_scope:
  - "runtime AWS live, tabela regional de MSK, release AWS do Managed Flink e benchmark"
  - "alterar runtime_scope de regra sem artefato observado"
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Regenerar o hash do offline manifest depois de qualquer edição em knowledge/"
change_kinds: [knowledge_doc]
---

# STREAMING_RUNTIME_MATRIX — definição
