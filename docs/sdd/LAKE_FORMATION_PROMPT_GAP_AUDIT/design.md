---
sdd: 1
feature: LAKE_FORMATION_PROMPT_GAP_AUDIT
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/define.md
  sha256: "06e2da7dda01c6d346b2b2711e2b4c5b17793eae8a953759e8affcba72c7c522"
files:
  - {path: tests/test_lakeformation_prompt_acceptance.py, action: modify, reason: "Adicionar provas executáveis para as combinações finais e os cinco gaps críticos."}
  - {path: sparkforge_aws/lakeformation/architecture.py, action: modify, reason: "Publicar seções estruturadas do migration report e referências de runtime no disclosure."}
  - {path: knowledge/lakeformation/operational-closure.md, action: modify, reason: "Documentar os runbooks que faltavam e a matriz final."}
  - {path: docs/guia/usos/lake-formation-operacional.md, action: modify, reason: "Expor leitura operacional dos novos casos e limites."}
  - {path: skills/lakeformation-architecture/SKILL.md, action: modify, reason: "Manter procedimento e progressive disclosure coerentes com o núcleo."}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "Registrar o contrato estruturado de migração e referências por engine."}
  - {path: docs/vnext/CAPABILITY-MATRIX.md, action: modify, reason: "Registrar que casos ausentes permanecem version-dependent/unknown."}
  - {path: docs/vnext/KNOWLEDGE-MAP.md, action: modify, reason: "Atualizar o mapa de disclosure e auditoria."}
  - {path: docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/prompt-acceptance-audit.md, action: create, reason: "Mapear o fechamento dos gaps contra os critérios do prompt."}

decisions:
  - id: D1
    choice: "Reforçar o teste acceptance existente e manter uma única saída lakeformation architect CLI/MCP."
    rejected: ["Criar uma nova tool para a auditoria, duplicando superfície e contrato."]
    rollback: "git revert do commit da feature; a saída volta ao contrato shipado anterior."
  - id: D2
    choice: "Representar as seções de migração como listas condicionais e verificáveis, sem preencher capacidades por analogia."
    rejected: ["Emitir recomendações de migração genéricas sem engine/runtime/operation."]
    rollback: "Remover o campo sections do migration report e manter os campos legados."

covers:
  - {part: "final knowledge matrix", acceptance: [AC1, AC2, AC4]}
  - {part: "structured migration report", acceptance: [AC3]}
  - {part: "documentation and audit", acceptance: [AC5]}
---

# LAKE_FORMATION_PROMPT_GAP_AUDIT — desenho

## Contrato

O núcleo continua recebendo um payload declarativo e retorna `consistent`,
`unresolved` ou `blocked`. A nova seção `review.migration.sections` é um mapa
fechado de dimensões do prompt; cada dimensão tem `status`, `items` e, quando
necessário, `requires_verification`.

## Conhecimento consultado

- `sparkforge-aws lakeformation architect --help` e o núcleo em
  `sparkforge_aws/lakeformation/architecture.py`;
- `knowledge/lakeformation/capability-matrix.yaml`;
- `knowledge/lakeformation/operational-closure.md`;
- `prompt_evo_fgac_fta_espec.md`, seções 66–79;
- fontes oficiais já registradas nos locks de Glue, Lake Formation e EMR.
