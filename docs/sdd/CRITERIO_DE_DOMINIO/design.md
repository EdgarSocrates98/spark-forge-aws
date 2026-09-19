---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/CRITERIO_DE_DOMINIO/define.md
  sha256: "e7c38105162307b4edc4f9cd32b8e2a2389300b5d10eaf1f7dd7b2adb4f76394"
files:
  - {path: tests/test_criterio_de_dominio.py, action: create, reason: "os tres gates (AC1 a AC4), a remocao (AC5), o criterio escrito (AC6) e os documentos vivos (AC8)"}
  - {path: agents/sf-orchestrator.md, action: delete, reason: "os sete sf-* so alcancaveis por __agentic_*__ saem (D2); este e o representante, os outros seis seguem a mesma tarefa, e os espelhos .claude/.agents/.github saem pelo sync, os .codex/agents/*.toml por git rm"}
  - {path: skills/agentic-orchestration/SKILL.md, action: delete, reason: "as cinco skills que so os sete declaram saem (D4); esta e a representante"}
  - {path: agents/spark-performance-architect.md, action: modify, reason: "a secao Mudanca no job pede spec passa a citar sparkforge_sdd_check, sparkforge_sdd_status e sparkforge_sdd_stamp (D3)"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "saem as sete rotas __agentic_*__ dos sete: AGENT-011, 012, 014, 015, 016, 027 e 028"}
  - {path: config/agents.yaml, action: modify, reason: "lido por sparkforge/registry/loader.py; saem sf-orchestrator, sf-pyspark-specialist, sf-storage-specialist e sf-token-verifier (D5)"}
  - {path: tests/test_canonical_registry.py, action: modify, reason: "test_registry_loading pede sf-pyspark-specialist; passa a pedir sf-runtime-specialist (D5)"}
  - {path: knowledge/tool-specialization-matrix.md, action: modify, reason: "lido por sparkforge/knowledge_drift.py; as linhas PySpark e Iceberg e Parquet passam aos donos classicos (D6)"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 dos documentos de knowledge tocados"}
  - {path: fixtures/knowledge_drift/filtro_por_url/expected/result.json, action: modify, reason: "golden lista agents/*.md que citam a URL; regenerado, so saem os caminhos dos agentes removidos (D6)"}
  - {path: scripts/sync_skills.py, action: modify, reason: "tabelas de despacho citam as cinco skills"}
  - {path: tests/test_sync_render.py, action: modify, reason: "RELACAO_MEDIDA e a tabela de agent unico citam os sete e as cinco"}
  - {path: manifest.json, action: modify, reason: "lista de skills"}
  - {path: docs/surface.lock.json, action: modify, reason: "a superficie de skills encolhe (regra 26)"}
  - {path: docs/guia/referencia/agents/README.md, action: modify, reason: "referencia gerada; as paginas dos sete e das cinco saem"}
  - {path: docs/gates-por-mudanca.md, action: modify, reason: "secao nova Criterio de dominio: artefato antes de nome (D7)"}
  - {path: CLAUDE.md, action: modify, reason: "uma linha apontando para o criterio (D7)"}
  - {path: AGENTS.md, action: modify, reason: "a mesma linha, e a lista de coordenadores sf-* (D8)"}
  - {path: docs/guia/05-agents-e-skills.md, action: modify, reason: "documento vivo e numeros (D8, D9)"}
  - {path: docs/guia/usos/iceberg-e-parquet.md, action: modify, reason: "documento vivo (D8)"}
  - {path: docs/operations-guide.md, action: modify, reason: "documento vivo (D8)"}
  - {path: docs/teams-catalog.md, action: modify, reason: "documento vivo (D8)"}
  - {path: docs/vnext/AGENT-CATALOG.md, action: modify, reason: "documento vivo, auditado (D8)"}
  - {path: docs/agentic-evolution.md, action: modify, reason: "documento vivo, apontado pelo CLAUDE.md (D8)"}
  - {path: knowledge/domain-tool-matrix.md, action: modify, reason: "documento de knowledge vivo (D8)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "coordenadores, skills e rotas (D9)"}
  - {path: README.md, action: modify, reason: "coordenadores e skills (D9)"}
  - {path: docs/guia/12-espelhos-e-dependencias.md, action: modify, reason: "contagem de coordenadores e skills despachaveis (D9)"}
  - {path: .devin/README.md, action: modify, reason: "contagem de coordenadores e skills (D9)"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo e contagens movem alegacoes"}
decisions:
  - id: D1
    choice: "O teste novo mora em tests/test_criterio_de_dominio.py e le o proprio repositorio. Area e o prefixo do rule_id ate o ultimo hifen. Rota por artefato e a rota cujo when contem, em qualquer profundidade, uma condicao findings_area ou fact; rota cujo when so tem condicao case (scope.entrypoints) nao conta. Coordenador e todo agents/*.md fora de agents/executors/."
    rejected: ["estender tests/test_sf_stubs.py: aquele arquivo trava a remocao de uma feature, este trava o criterio para toda a proxima", "exigir que TODA rota do coordenador seja por artefato: quatro coordenadores com rota real tambem tem modo __agentic_*__, e o define deixou esse modo fora de escopo"]
    rollback: "git revert do commit"
  - id: D2
    choice: "Saem sf-analytics-specialist, sf-graph-specialist, sf-neptune-specialist, sf-orchestrator, sf-pyspark-specialist, sf-storage-specialist e sf-token-verifier, com as rotas AGENT-011, 012, 014, 015, 016, 027 e 028. As areas deles continuam coordenadas por quem ja as tem com rota real: SF-PY, SF-PLAN, SF-CG, SF-GRAPH por pyspark-code-reviewer; SF-ICE, SF-PQ por iceberg-performance-engineer; SF-DQ por data-quality-reviewer; SF-BENCH, SF-GLUE, SF-EMR, SF-ENV pelos coordenadores classicos e sf-runtime-specialist."
    rejected: ["dar rota real aos sete: todas as areas deles ja tem coordenador com rota, e uma segunda rota para a mesma area so empata no roteador"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D3
    choice: "sparkforge_sdd_check, sparkforge_sdd_status e sparkforge_sdd_stamp passam a ser citadas em spark-performance-architect, na secao Mudanca no job pede spec, que ja descreve o SDD do perfil operator."
    rejected: ["um executor: executor extrai e julga, nao conduz fase de spec"]
    rollback: "git revert do commit"
  - id: D4
    choice: "Saem analyze-analytics, analyze-graph-data, design-neptune-graph, agentic-orchestration e token-efficient-agent: 128 a 252 palavras de texto generico, sem tool nem artefato, e sem dono que fica."
    rejected: ["realocar token-efficient-agent: economia de token ja tem verbo proprio (economy report) e regras 22 a 28 no CLAUDE.md"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D5
    choice: "config/agents.yaml perde as entradas dos quatro que saem e que ele lista; os executores e sf-runtime-specialist ficam. tests/test_canonical_registry.py passa a pedir sf-runtime-specialist."
    rejected: ["manter as entradas: o registro carregaria agente sem arquivo"]
    rollback: "git revert do commit"
  - id: D6
    choice: "knowledge/tool-specialization-matrix.md troca sf-pyspark-specialist por pyspark-code-reviewer e sf-storage-specialist por iceberg-performance-engineer; o golden de fixtures/knowledge_drift/filtro_por_url e regenerado, e o diff so pode tirar caminhos de agents/ removidos."
    rejected: ["apagar as linhas da matriz: o dominio continua existindo, so muda de dono"]
    rollback: "git revert do commit"
  - id: D7
    choice: "O criterio e uma secao nova de docs/gates-por-mudanca.md, Criterio de dominio: artefato antes de nome, logo antes de Acrescentar uma AREA nova, com a frase do criterio, os tres niveis e o teste que os trava. CLAUDE.md e AGENTS.md ganham uma linha cada, sem numero, na secao de verificacao, apontando para ela."
    rejected: ["regra numerada 34 no CLAUDE.md: o arquivo guarda regra e ponteiro, e o detalhe do gate mora em gates-por-mudanca"]
    rollback: "git revert do commit"
  - id: D8
    choice: "Documento vivo troca o nome que saiu pelo dono novo ou tira a mencao, como no SF_STUBS. Os historicos (docs/delivery-report.md, docs/harness/MIGRATIONS-GLUE-GAP.md) ja tem nota de desvio do SF_STUBS e ficam."
    rejected: ["nova nota de desvio nos historicos: a nota existente diz que o documento cita nomes que nao existem mais, e vale igual"]
    rollback: "git revert do commit"
  - id: D9
    choice: "Os numeros publicados de coordenadores (19 para 12), skills (56 para 51) e rotas (47 para 40) ganham leitura nova no STATUS, no padrao das anteriores, e o README e o guia acompanham."
    rejected: ["reescrever as leituras antigas: o STATUS acumula leituras"]
    rollback: "git revert do commit"
covers:
  - {part: "gate", acceptance: [AC1, AC2, AC3, AC4]}
  - {part: "remocao e realocacao", acceptance: [AC5, AC7]}
  - {part: "criterio escrito", acceptance: [AC6]}
  - {part: "documentos e numeros", acceptance: [AC8, AC9]}
---

# CRITERIO_DE_DOMINIO — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| gate | `tests/test_criterio_de_dominio.py` | AC1–AC4 |
| remoção e realocação | 7 agentes, 5 skills, 7 rotas, `config/agents.yaml`, `spark-performance-architect`, matriz de especialização e golden de drift | AC5, AC7 |
| critério escrito | `docs/gates-por-mudanca.md`, `CLAUDE.md`, `AGENTS.md` | AC6 |
| documentos e números | vivos, STATUS, README, guia | AC8, AC9 |

## Medidas que sustentam o desenho

- Rotas dos sete: AGENT-011, 012, 014, 015, 016, 027 e 028, todas `__agentic_*__`.
- Tools que ficariam órfãs sem realocação: as três `sparkforge_sdd_*`, só citadas por
  `sf-orchestrator`.
- `CLAUDE.md` 24 440 bytes e `AGENTS.md` 22 502 bytes, teto de 26 000: a linha cabe.
- Lição do SF_STUBS aplicada: o `git grep` pelos nomes que saem rodou antes do
  manifesto (22 arquivos fora de `agents/` e `skills/`), e `.codex/agents/` sai por
  `git rm`, porque o `sync_skills.py` não o gera.
