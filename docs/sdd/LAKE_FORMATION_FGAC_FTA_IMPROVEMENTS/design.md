---
sdd: 1
feature: LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS/define.md
  sha256: "f3a92f665b304fe104ee664309166751b8ea1b039ddfbfdbe406c5fa17c236b6"
files:
  - {path: tests/test_lakeformation_fgac_fta_improvements.py, action: create, reason: "Provas dos sete gaps e dos contratos de integração."}
  - {path: sparkforge_aws/lakeformation/architecture.py, action: modify, reason: "Enforce capabilities por perna, resolução cross-account, Hybrid Access e migração explícita."}
  - {path: sparkforge_aws/lakeformation/catalog_routing.py, action: modify, reason: "Comparar ownership, glue.id e glue.account-id contra contextos declarados sem alias."}
  - {path: knowledge/lakeformation/capability-matrix.yaml, action: modify, reason: "Expandir células version-aware com fonte e limitação por operação."}
  - {path: knowledge/lakeformation/fgac-fta-improvements.md, action: create, reason: "Registrar decisões, limites e exemplos operacionais do novo contrato."}
  - {path: skills/lakeformation-architecture/SKILL.md, action: modify, reason: "Orientar source/target, capability enforcement, routes e Hybrid Access."}
  - {path: agents/sf-lake-formation-specialist.md, action: modify, reason: "Adicionar coordenação das novas dimensões sem mutação AWS."}
  - {path: agents/sf-runtime-specialist.md, action: modify, reason: "Registrar migration intent separado da análise corrente."}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "Documentar decision graph com source/target e governance mode."}
  - {path: docs/vnext/CAPABILITY-MATRIX.md, action: modify, reason: "Documentar enforcement por status e matriz ampliada."}
  - {path: docs/vnext/KNOWLEDGE-MAP.md, action: modify, reason: "Adicionar fonte operacional e progressive disclosure da melhoria."}

decisions:
  - id: D1
    choice: "Manter uma única entrada analyze_architecture e adicionar source_decision/target_decision e capability_checks ao output."
    rejected: ["Criar verbos separados para source, target e migration, que duplicariam CLI/MCP e perderiam paridade.", "Escolher somente target, que apaga a leitura governada da origem."]
    rollback: "git revert do commit da engine; o contrato anterior retorna sem as novas chaves."
  - id: D2
    choice: "Usar evidence.capability_verification para fechar limited/version_dependent; not_supported nunca pode ser promovido por payload."
    rejected: ["Promover status por configuração nominal, que transforma declaração em prova.", "Tratar toda célula version_dependent como supported por analogia entre releases."]
    rollback: "git revert do enforcement e restaurar a matriz anterior; nenhuma AWS mutation existe."
  - id: D3
    choice: "Modelar cross_account_resolution.mode com resource_link, explicit_catalog_id, shared_catalog e other_supported_route; Glue ETL pode fechar explicit_catalog_id com CatalogId."
    rejected: ["Exigir resource link para todo cross-account, contrariando o caminho CatalogId documentado para Glue ETL.", "Aceitar direct_s3 como substituto de catálogo governado."]
    rollback: "git revert da resolução; rota anterior fica unresolved sem alterar dados."
  - id: D4
    choice: "Separar access_governance_mode (lakeformation, iam, hybrid) de table_access_model (fgac, fta)."
    rejected: ["Usar IAMAllowedPrincipals como proxy universal de modelo, que bloqueia Hybrid Access válido.", "Misturar FGAC/FTA com IAM/Lake Formation governance, que confunde duas dimensões."]
    rollback: "git revert dos checks de governance; access_model legado continua aceito como fallback."
  - id: D5
    choice: "Comparar glue.id com ownership e glue.account-id com expected context declarado, sem considerar divergência entre ambos como erro isolado."
    rejected: ["Exigir igualdade entre glue.id e glue.account-id, que descarta configurações semanticamente válidas.", "Inferir expected context a partir de uma conta única, contrariando o contrato de múltiplas dimensões."]
    rollback: "git revert do routing sem alterar catálogo ou configuração."

covers:
  - {part: "capability enforcement", acceptance: [AC1, AC6]}
  - {part: "source target and catalog routing", acceptance: [AC2, AC3, AC7]}
  - {part: "governance and migration", acceptance: [AC4, AC5]}
  - {part: "integration and documentation", acceptance: [AC8]}
---

# LAKE_FORMATION_FGAC_FTA_IMPROVEMENTS — desenho

## Contrato de saída

`decision` preserva `capability` como célula primária para compatibilidade e
acrescenta `source_decision`, `target_decision`, `capability_checks`,
`cross_account_resolution` e `access_governance_mode`. Cada perna contém
formato, operação, status da célula, status final, checks e
`required_verification`.

## Gates e rollback

Mudança é offline e declarativa. Gates derivados dos `change_kinds`: knowledge
offline/source lock, espelhos, referência de superfície e claims vNext. Cada
commit é reversível por `git revert`; não há AWS write.

## Conhecimento consultado

`sparkforge-aws rules lookup --category lakeformation-fgac` confirmou as restrições
FGAC/FTA e escrita. Documentação AWS version-aware acima confirmou CatalogId sem
resource link em Glue ETL e Hybrid Access com IAMAllowedPrincipals opt-in.
