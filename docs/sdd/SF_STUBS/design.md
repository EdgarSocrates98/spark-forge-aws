---
sdd: 1
feature: SF_STUBS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SF_STUBS/define.md
  sha256: "51ea5b2c5aad7ed40912f02f8a629b8d6eba90e4e30dfecee832528bd78822ce"
files:
  - {path: tests/test_sf_stubs.py, action: create, reason: "testes de AC1 a AC4, escritos antes da remocao"}
  - {path: rules/catalog/agentic-sf-agents.yaml, action: delete, reason: "area de coordenacao sem regra executavel; os outros 34 rules/catalog/agentic-sf-*.yaml saem pelo mesmo motivo e na mesma tarefa"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "saem as 54 rotas que recomendam agente oco ou disparam por findings_area de area oca (lista em D3)"}
  - {path: agents/sf-airflow-specialist.md, action: delete, reason: "os 19 agentes ocos saem de agents/ (lista em D1); este e o representante no manifesto, os outros 18 seguem a mesma tarefa"}
  - {path: agents/pyspark-code-reviewer.md, action: modify, reason: "recebe a secao Indice de codigo de sf-context-engineer, com as nove tools sparkforge_code_* (D4)"}
  - {path: agents/iceberg-performance-engineer.md, action: modify, reason: "recebe a skill iceberg-v3-readiness e a secao Subir o format version da tabela, com sparkforge_iceberg_assess_upgrade (D5)"}
  - {path: agents/data-quality-reviewer.md, action: modify, reason: "recebe a skill analyze-functional-rules, produtora do business_rule.schema.json (D6)"}
  - {path: agents/sf-analytics-specialist.md, action: modify, reason: "os 11 sf-* que ficam perdem as areas ocas de rule_areas (D2); este e o representante, os outros 10 seguem a mesma tarefa"}
  - {path: skills/design-airflow-pipelines/SKILL.md, action: delete, reason: "as 10 skills sem artefato e sem dono que fica saem (lista em D7); esta e a representante"}
  - {path: sparkforge/findings/schemas/business_rule.schema.json, action: modify, reason: "a descricao nomeia sf-functional-rules-specialist como produtor; passa a nomear data-quality-reviewer"}
  - {path: sparkforge/economy/router.py, action: modify, reason: "specialist_keywords aponta athena, dynamodb e step functions para skills que saem, e kinesis para streaming-reliability, que nunca existiu; as quatro entradas saem (D8)"}
  - {path: scripts/sync_skills.py, action: modify, reason: "a tabela de despacho lista as 10 skills que saem"}
  - {path: tests/test_sync_render.py, action: modify, reason: "a tabela literal de skill para coordenador cita os agentes e skills que saem"}
  - {path: manifest.json, action: modify, reason: "lista de skills e rule_count do knowledge_base"}
  - {path: docs/surface.lock.json, action: modify, reason: "a superficie de skills e agents encolhe (regra 26: o commit declara os bytes)"}
  - {path: docs/guia/referencia/agents/README.md, action: modify, reason: "referencia gerada por scripts/gen_reference_docs.py; as paginas dos agentes e skills que saem somem com ela"}
  - {path: AGENTS.md, action: modify, reason: "documento vivo que cita agentes e skills que saem (D9)"}
  - {path: docs/guia/05-agents-e-skills.md, action: modify, reason: "documento vivo (D9)"}
  - {path: docs/guia/usos/athena-e-sql.md, action: modify, reason: "documento vivo (D9)"}
  - {path: docs/guia/usos/iceberg-e-parquet.md, action: modify, reason: "documento vivo (D9)"}
  - {path: docs/teams-catalog.md, action: modify, reason: "documento vivo (D9)"}
  - {path: docs/operations-guide.md, action: modify, reason: "documento vivo (D9)"}
  - {path: docs/vnext/AGENT-CATALOG.md, action: modify, reason: "documento vivo e auditado pelo gate de lastro (D9)"}
  - {path: docs/vnext/DEMOS.md, action: modify, reason: "documento vivo e auditado pelo gate de lastro (D9)"}
  - {path: knowledge/domain-tool-matrix.md, action: modify, reason: "documento de knowledge vivo; move o offline-manifest (D9)"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 de knowledge/domain-tool-matrix.md"}
  - {path: docs/delivery-report.md, action: modify, reason: "historico: ganha nota de desvio no topo, sem reescrita (D9)"}
  - {path: docs/agentic-expansion.md, action: modify, reason: "historico: nota de desvio (D9)"}
  - {path: docs/harness/MIGRATIONS-GLUE-GAP.md, action: modify, reason: "historico e auditado: nota de desvio (D9)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "numeros correntes de regras, agents e skills (AC7)"}
  - {path: README.md, action: modify, reason: "cita 192 regras"}
  - {path: docs/guia/07-conhecimento-e-catalogo.md, action: modify, reason: "cita 192 regras"}
  - {path: fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, action: modify, reason: "golden de assessment carrega catalog_rules e a frase de cobertura com a contagem do catalogo; os tres goldens de fixtures/scenarios regeneram so nesses campos (D10); este e o representante"}
  - {path: evals/holdout/config_por_caminho_indireto/expected/assessment.json, action: modify, reason: "o mesmo nos dois goldens de evals/holdout (D10); este e o representante"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo e contagens movem alegacoes do gate de lastro"}
decisions:
  - id: D1
    choice: "Saem os 19 agentes cujas rule_areas sao todas areas ocas: sf-agent-builder, sf-agent-evaluation-specialist, sf-airflow-specialist, sf-athena-specialist, sf-context-engineer, sf-cost-reviewer, sf-data-architect, sf-dynamodb-specialist, sf-evidence-verifier, sf-functional-rules-specialist, sf-iceberg-specialist, sf-kinesis-specialist, sf-lambda-serverless-specialist, sf-lineage-specialist, sf-memory-engineer, sf-parquet-specialist, sf-s3-specialist, sf-schema-registry-specialist, sf-step-functions-specialist. A fonte e agents/; os espelhos .claude, .agents, .codex e .github saem pelo scripts/sync_skills.py."
    rejected: ["manter sf-context-engineer por ter secao real: as areas dele sao ocas, e a secao vale igual em quem ja revisa codigo", "apagar tambem os 11 com area executavel: sf-runtime-specialist e sf-lake-formation-specialist tem mais de mil palavras de procedimento proprio"]
    rollback: "git revert do commit da remocao, depois python scripts/sync_skills.py"
  - id: D2
    choice: "Os 11 sf-* que ficam (sf-orchestrator, sf-pyspark-specialist, sf-runtime-specialist, sf-storage-specialist, sf-lake-formation-specialist, sf-security-reviewer, sf-terraform-specialist, sf-graph-specialist, sf-neptune-specialist, sf-analytics-specialist, sf-token-verifier) perdem de rule_areas toda area que nao existe mais; nada mais muda no corpo deles."
    rejected: ["reescrever os corpos genericos: fora do escopo do define"]
    rollback: "git revert do commit"
  - id: D3
    choice: "Saem 54 rotas de routing.yaml: as 45 que recomendam um dos 19 (AGENT-017 a 025, 029 a 032, 034 a 036, 039 a 043, 045 a 047, 050 a 054, 056 a 062, 064, 066 a 070, 072 a 074) e as 9 que recomendam um sobrevivente mas disparam por findings_area de area oca (AGENT-033, 037, 038, 044, 048, 049, 055, 063, 065). Os ids que ficam nao sao renumerados."
    rejected: ["redirecionar as 45 para um sobrevivente: rota que dispara por area oca nunca casa, e a que dispara por __agentic_*__ nenhum codigo do pacote aciona", "renumerar os ids: id de rota e citado em documento e teste"]
    rollback: "git revert do commit"
  - id: D4
    choice: "A secao Indice de codigo de sf-context-engineer, com as nove tools sparkforge_code_*, passa inteira para pyspark-code-reviewer, que ja responde quem chama o que (skill analyze-library-call-graph)."
    rejected: ["sf-orchestrator: coordena fases, nao le codigo", "spark-performance-architect: coordena o diagnostico de job e delega a revisao de codigo a pyspark-code-reviewer"]
    rollback: "git revert do commit"
  - id: D5
    choice: "iceberg-performance-engineer declara a skill iceberg-v3-readiness e recebe a secao Subir o format version da tabela de sf-iceberg-specialist, que cita sparkforge_iceberg_assess_upgrade."
    rejected: ["sf-storage-specialist: tambem declara SF-ICE, mas e o coordenador generico; o especialista de Iceberg e o dono natural da decisao de format version"]
    rollback: "git revert do commit"
  - id: D6
    choice: "analyze-functional-rules fica, porque produz o payload que sparkforge/findings/validate.py::validate_business_rule confere; passa a ser declarada por data-quality-reviewer, e a descricao do schema troca o nome do produtor."
    rejected: ["apagar junto das outras: deixaria o schema business_rule sem skill que o produza", "sf-analytics-specialist: coordenador generico de 39 palavras"]
    rollback: "git revert do commit"
  - id: D7
    choice: "Saem as 10 skills que so os ocos declaram e que nao citam tool nem artefato: design-agent-systems, design-airflow-pipelines, design-dynamodb-model, design-lambda-serverless, design-step-functions-orchestration, engineer-agent-context, engineer-agent-memory, optimize-athena-queries, optimize-iceberg-tables, verify-agent-evidence. Todas tem de 104 a 208 palavras de texto generico."
    rejected: ["realocar optimize-athena-queries e optimize-iceberg-tables: athena-query-optimizer e iceberg-performance-engineer ja declaram optimize-iceberg-table e optimize-parquet-layout, com procedimento sobre tool real"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D8
    choice: "sparkforge/economy/router.py perde as entradas athena, dynamodb, step functions e kinesis de specialist_keywords: as tres primeiras apontam para skill que sai, e kinesis aponta para streaming-reliability, que nunca existiu. Com a mudanca, todo valor de specialist_keywords e uma skill que existe."
    rejected: ["apontar athena para optimize-parquet-layout: a palavra athena nao diz que o problema e layout"]
    rollback: "git revert do commit"
  - id: D9
    choice: "Documento vivo troca ou tira o nome que saiu: AGENTS.md, docs/guia/05-agents-e-skills.md, docs/guia/usos/athena-e-sql.md, docs/guia/usos/iceberg-e-parquet.md, docs/teams-catalog.md, docs/operations-guide.md, docs/vnext/AGENT-CATALOG.md, docs/vnext/DEMOS.md, knowledge/domain-tool-matrix.md. Documento historico ganha uma nota de desvio no topo e fica como estava: docs/delivery-report.md (relatorio de 2026-08-18), docs/agentic-expansion.md e docs/harness/MIGRATIONS-GLUE-GAP.md (mapa datado)."
    rejected: ["reescrever os historicos: a memoria do projeto trata spec e relatorio como registro, com secao de desvios"]
    rollback: "git revert do commit"
  - id: D10
    choice: "Os goldens de assessment que carregam a contagem do catalogo (tres em fixtures/scenarios, dois em evals/holdout) sao regenerados por scripts/regen_fixtures.py, e o diff de cada um e conferido: so catalog_rules, as contagens de regra sem guarda e a frase de cobertura mudam; findings e recusas ficam identicos."
    rejected: ["tirar a contagem do golden: ela e a cobertura declarada do verbo, e e isso que o golden trava"]
    rollback: "git revert do commit"
covers:
  - {part: "catalogo e roteamento", acceptance: [AC1, AC3]}
  - {part: "agentes", acceptance: [AC2]}
  - {part: "realocacao", acceptance: [AC4, AC5]}
  - {part: "espelhos e referencia", acceptance: [AC6]}
  - {part: "numeros e documentos", acceptance: [AC7, AC8]}
---

# SF_STUBS — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| catálogo e roteamento | 35 `rules/catalog/agentic-sf-*.yaml`, `routing.yaml` | AC1, AC3 |
| agentes | 19 `agents/sf-*.md` saem, 11 perdem áreas ocas | AC2 |
| realocação | `pyspark-code-reviewer`, `iceberg-performance-engineer`, `data-quality-reviewer`, schema `business_rule`, `economy/router.py` | AC4, AC5 |
| espelhos e referência | `sync_skills.py`, `test_sync_render.py`, `docs/guia/referencia/`, `surface.lock.json` | AC6 |
| números e documentos | `manifest.json`, STATUS, README, guia, documentos vivos e históricos, `claims.lock.json` | AC7 |

## Manifesto por representante

O manifesto lista um representante de cada grupo apagado (um `.yaml`, um agente, uma
skill) em vez de 64 linhas iguais. A lista inteira está nas decisões D1, D3 e D7, e o
teste novo a confere.

## Medidas que sustentam o desenho

- `load_catalog()`: 192 regras, 157 executáveis, 35 não executáveis (2026-09-19).
- `tests/test_agent_coverage.py` sem os 19: órfãs as 9 `sparkforge_code_*` e
  `sparkforge_iceberg_assess_upgrade` (medido no explore).
- `specialist_keywords` em `sparkforge/economy/router.py`: `streaming-reliability` não
  existe em `skills/` hoje.
- `.claude/agents/README.md` não é rastreado e `scripts/sync_skills.py` o apaga: copiar
  para fora antes do sync e devolver depois.
