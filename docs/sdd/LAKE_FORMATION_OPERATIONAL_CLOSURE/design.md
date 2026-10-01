---
sdd: 1
feature: LAKE_FORMATION_OPERATIONAL_CLOSURE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_OPERATIONAL_CLOSURE/define.md
  sha256: "3216abd562258e18e7e53d7722efe005bebb85f79671d08436dfee43dda1d6ab"
files:
  - {path: tests/test_lakeformation_operational_closure.py, action: create, reason: "Provas acceptance do delta operacional, escritas antes do código."}
  - {path: sparkforge/lakeformation/architecture.py, action: modify, reason: "Compor revisão operacional evidence-first sobre o decision engine existente, mantendo CLI/MCP no mesmo núcleo."}
  - {path: knowledge/lakeformation/capability-matrix.yaml, action: modify, reason: "Registrar células Glue 5.1/6.0 e formatos somente quando a fonte oficial fecha a capacidade; divergências permanecem unknown/version_dependent."}
  - {path: knowledge/lakeformation/operational-closure.md, action: create, reason: "Fonte interna de progressive disclosure, explain-access, root-cause, migração e runbooks com URLs oficiais."}
  - {path: docs/guia/usos/lake-formation-operacional.md, action: create, reason: "Guia operacional para entrada declarativa, saída, troubleshooting e rollback."}
  - {path: skills/lakeformation-architecture/SKILL.md, action: modify, reason: "Ensinar o contrato de revisão, preflight, migração e limites sem duplicar a matriz."}
  - {path: agents/sf-lake-formation-specialist.md, action: modify, reason: "Adicionar explain/root-cause/preflight e cross-review ao coordenador existente."}
  - {path: agents/sf-terraform-specialist.md, action: modify, reason: "Declarar revisão de Terraform como evidência de configuração, não como mutação."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Atualizar descrição/schema da tool existente para o payload operacional composto, sem criar tool paralela."}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "Registrar camada operacional e decision graph."}
  - {path: docs/vnext/CAPABILITY-MATRIX.md, action: modify, reason: "Registrar formatos/operações e fronteira unknown/version-dependent."}
  - {path: docs/vnext/KNOWLEDGE-MAP.md, action: modify, reason: "Registrar carregamento progressive-disclosure e runbooks."}

decisions:
  - id: D1
    choice: "Estender `sparkforge lakeformation architect` com uma seção `review` determinística, em vez de criar verbos/tools paralelos para cada capítulo do prompt."
    rejected: ["Criar `doctor`, `explain-access`, `migration` e `root-cause` novos, que duplicariam adapters e aumentariam a superfície sem outro produtor de facts.", "Colocar toda lógica no skill, que deixaria a capacidade sem prova executável e dependente do host."]
    rollback: "git revert do commit da composição; a tool volta a retornar somente routing/checks/decision do architecture engine."
  - id: D2
    choice: "Receber facts já extraídos como objetos declarativos opcionais e ancorar cada observação em kind/source/line; ausência permanece required_verification."
    rejected: ["Reabrir os extratores Terraform/PySpark para produzir um modelo duplicado de Lake Formation.", "Inferir ordem de execução sem linha/order observados, que confundiria ausência de evidence com fato."]
    rollback: "git revert do módulo de review; os extratores existentes permanecem inalterados."
  - id: D3
    choice: "Representar performance/FinOps como impacto condicional e medidas necessárias; números só entram de benchmark ou DPUSeconds declarados."
    rejected: ["Estimar percentuais de overhead ou economia a partir de documentação, que viola o contrato de medição do repositório.", "Ocultar o impacto, que impediria a decisão entre FGAC e FTA."]
    rollback: "git revert da seção performance_finops e do documento operacional; nenhuma execução AWS é afetada."
  - id: D4
    choice: "Manter divergência oficial como `version_dependent`/`unknown` e atualizar a matriz com Glue 6.0 somente para FTA e limitações explicitamente documentadas."
    rejected: ["Promover toda capacidade de Glue 5.1 para Glue 6.0 por analogia.", "Escolher uma página AWS divergente silenciosamente."]
    rollback: "Remover as células novas da capability matrix e restaurar seus estados unknown; o loader continua fail-closed."

covers:
  - {part: "operational review and code/IaC evidence", acceptance: [AC1, AC2, AC4]}
  - {part: "migration and capability closure", acceptance: [AC3, AC6]}
  - {part: "economy, progressive disclosure and parity", acceptance: [AC5, AC7]}
  - {part: "knowledge, runbooks, skills, agents and VNX", acceptance: [AC8]}
---

# LAKE_FORMATION_OPERATIONAL_CLOSURE — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| review evidence-first | `sparkforge/lakeformation/architecture.py`, testes | AC1, AC2, AC4 |
| migration/capability | `knowledge/lakeformation/capability-matrix.yaml`, testes | AC3, AC6 |
| parity/schema | `sparkforge/adapters/tools.py`, testes | AC7 |
| knowledge/runbooks | `knowledge/lakeformation/operational-closure.md`, `docs/guia/usos/lake-formation-operacional.md` | AC2, AC3, AC4, AC5, AC8 |
| skill/agents/VNX | skill, agentes, `docs/vnext/` | AC5, AC8 |

## Contrato `review`

`analyze_architecture(payload)` preserva as chaves atuais e acrescenta:

```yaml
review:
  code_and_iac: {status, observed, findings, required_verification}
  access_explain: {nodes, edges, metadata_path, data_path}
  authorization: {metadata, data, credential_vending, separation}
  error_taxonomy: []
  root_cause: {status, symptom, possible_layers, evidence, hypotheses, checks, required_proof, fix, verification}
  migration: {status, from, to, breaking_changes, semantic_changes, security_changes, performance_changes, cost_changes, testing_plan, rollback_plan}
  preflight: []
  performance_finops: {claims, measurements_required, observed_measurements}
  cross_review: []
  progressive_disclosure: {dimensions, knowledge_refs, runbooks}
```

O contrato não chama AWS. `facts`, `errors`, `migration` e `benchmark` são
entradas declaradas; o output nunca transforma `unknown` em `false`.

## Conhecimento consultado

- `sparkforge rules lookup --category lakeformation-fgac` e `--category cross-account`;
- `sparkforge knowledge path --file knowledge/glue/lakeformation-fgac.md`;
- `sparkforge knowledge path --file knowledge/lakeformation/capability-matrix.yaml`;
- fontes AWS Glue/Lake Formation/EMR registradas em `knowledge/sources.lock.json`,
  incluindo `migrating-version-51.html`, `migrating-version-60.html`,
  `security-lf-enable.html`, `security-access-control-fta.html` e
  `cross-account-permissions.html`.
