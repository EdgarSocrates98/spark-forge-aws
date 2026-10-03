---
sdd: 1
feature: FORGE_LAB_DIGITAL_TWIN
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_DIGITAL_TWIN/explore.md
  sha256: "b686f6d82c64de885b0b599b8262de6fa99bea0ae0f8016e3fe814c1d700e630"
hypothesis:
  claim: "Um contrato de Forge Lab com topologia e failure scenarios declarados reduz a distância entre diagnóstico offline e reprodução local."
  prediction: "O operador consegue validar a topologia, listar dependências e selecionar cenários de broker, skew, lag, checkpoint, small files, schema e CDC restart sem o SparkForge executar ações destrutivas."
  experiment: "Carregar o lab.yaml sintético pelo analisador e comparar a saída canônica com o compose e o catálogo de cenários versionados."
acceptance:
  - id: AC1
    statement: "O contrato valida componentes mínimos, dependências e cenários de falha, preservando unresolved para referências ausentes."
    verified_by: {kind: test, ref: "tests/test_forge_lab.py::test_forge_lab_validates_topology_and_scenarios"}
    guard: "A implementação foi construída em fases anteriores sob a regra do plano de executar a suíte apenas após o fechamento do Forge Lab; não existe red histórico verificável para este teste e o gate não deve aceitar um exit inventado."
  - id: AC2
    statement: "O analisador retorna perfil offline, componentes, ordem topológica e cenários sem executar Docker ou sistemas externos."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli analyze forge-lab --path labs/forge-lab/lab.yaml"}
success:
  - id: SC1
    metric: "Componentes e cenários declarados aparecem na saída sem mutação externa"
    source: "saída de analyze forge-lab e fixture versionada"
out_of_scope:
  - "Subir/derrubar containers automaticamente."
  - "Garantir que imagens de terceiros estejam disponíveis sem pull e sem pin fornecido pelo operador."
  - "Benchmark de throughput/latência do laboratório."
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Disponibilidade local do Docker e imagens pinadas; a análise offline não resolve isso."
case_id: null
change_kinds: [tool_or_verb, dependency, knowledge_doc]
---

# FORGE_LAB_DIGITAL_TWIN — requisitos

O lab deve modelar transporte, processamento, lakehouse, catálogo, CDC e
observabilidade. Cenários são planos de ação com `action`, `target` e
`expected_evidence`; o analisador apenas os descreve e nunca os executa.
