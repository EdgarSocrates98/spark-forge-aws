---
sdd: 1
feature: LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/define.md
  sha256: "216c9db9f4342aeb4b8997ecd00b66e31d0155db72a73907d90f3f96f634f09a"
files:
  - {path: tests/test_lakeformation_prompt_acceptance.py, action: create, reason: "Testes acceptance para os requisitos ainda não cobertos do prompt, sem chamada AWS."}
  - {path: sparkforge_aws/lakeformation/architecture.py, action: modify, reason: "Estender migration, access graph, preflight, observabilidade e performance sobre o núcleo offline existente."}
  - {path: knowledge/lakeformation/operational-closure.md, action: modify, reason: "Documentar transições, CloudTrail consumidor/produtor, Iceberg path e limites de medição."}
  - {path: docs/guia/usos/lake-formation-operacional.md, action: modify, reason: "Atualizar runbook e explicar como ler as novas seções do review."}
  - {path: skills/lakeformation-architecture/SKILL.md, action: modify, reason: "Ensinar progressive disclosure, decisão de migração e observabilidade sem duplicar o código."}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "Registrar decision graph e fronteiras observadas/unresolved."}
  - {path: docs/vnext/CAPABILITY-MATRIX.md, action: modify, reason: "Apontar a auditoria de formatos/operações e transições sem suporte por analogia."}
  - {path: docs/vnext/KNOWLEDGE-MAP.md, action: modify, reason: "Mapear referências carregadas sob demanda e fontes de observabilidade."}
  - {path: docs/sdd/LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION/prompt-acceptance-audit.md, action: create, reason: "Matriz verificável dos 26 critérios da seção 79, incluindo evidência e limites."}

decisions:
  - id: D1
    choice: "Estender a seção review de lakeformation_architect e manter CLI/MCP idênticos, em vez de criar comandos paralelos."
    rejected: ["Criar sete tools para os sete novos grupos, duplicando payload e surface.", "Colocar decisões só na skill, sem teste executável."]
    rollback: "git revert dos commits do delta; a saída volta ao review operacional anterior sem alteração AWS."
  - id: D2
    choice: "CloudTrail, RAM e logs entram como evidence declarativa com estados pass/unresolved; o núcleo não coleta nem simula AWS."
    rejected: ["Inferir evento producer/consumer a partir do account_id.", "Tratar ausência de evento como ausência de acesso."]
    rollback: "git revert da seção observability; os campos novos desaparecem sem mudar facts existentes."
  - id: D3
    choice: "A matriz de aceite é versionada como documento/teste derivado do prompt, com cada critério apontando para prova e limite."
    rejected: ["Afirmar cobertura por busca textual no prompt.", "Reescrever o prompt para casar com a implementação."]
    rollback: "Remover a matriz e o teste; nenhuma decisão operacional é aplicada."

covers:
  - {part: "migration and decision graph", acceptance: [AC1, AC5]}
  - {part: "access, observability and preflight", acceptance: [AC2, AC3]}
  - {part: "performance and scenario matrix", acceptance: [AC4, AC6]}
  - {part: "acceptance audit and published guidance", acceptance: [AC7]}
---

# LAKE_FORMATION_PROMPT_ACCEPTANCE_COMPLETION — desenho

## Contrato de saída adicional

```yaml
review:
  access_explain:
    paths: []
    observability: {cloudtrail: {consumer: unknown, producer: unknown}}
  migration:
    transition_family: unknown
  preflight: []
  performance_finops:
    dimensions: {}
  decision_graph: {nodes: [], edges: [], unresolved: []}
```

Cada campo é composto da entrada declarada. `unknown`/`unresolved` permanece
quando o artefato correspondente não foi coletado.

## Conhecimento consultado

- `sparkforge-aws rules lookup --category lakeformation-fgac` e `--category cross-account`;
- `sparkforge-aws knowledge path --file knowledge/lakeformation/capability-matrix.yaml`;
- `sparkforge-aws knowledge path --file knowledge/lakeformation/operational-closure.md`;
- fontes AWS Glue/Lake Formation/EMR e Apache Iceberg já presentes nos locks do
  repositório, com runtime e data de verificação declarados.
