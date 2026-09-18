---
sdd: 1
feature: DATABRICKS_SPARK
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/DATABRICKS_SPARK/define.md
  sha256: "6281deaa9efb51ccfed5de213152837b634ef7f0f1451d2ccaa7bb7660921b12"
files:
  - {path: tests/test_databricks_runtime_matrix.py, action: create, reason: "teste de AC2, escrito antes do codigo"}
  - {path: tests/test_databricks_platform.py, action: create, reason: "testes de AC1, AC3, AC4, AC5, AC7 e AC8, escritos antes do codigo"}
  - {path: tests/test_databricks_rule_audit.py, action: create, reason: "teste de AC6: regra sem escopo alcancavel por artefato Spark generico nao remedia com termo de AWS fora da lista de excecoes"}
  - {path: knowledge/databricks/runtime-matrix.yaml, action: create, reason: "matriz Databricks Runtime -> Spark como dado, com fonte e data no nivel do documento e vocabulario fechado (spark)"}
  - {path: knowledge/databricks/runtime-matrix.md, action: create, reason: "documento com a secao Fontes que a watchlist le, a normalizacao do rotulo 15.4.x-scala2.12 e as lacunas U1 e U2"}
  - {path: sparkforge/facts/runtime_matrix.py, action: modify, reason: "load_databricks(), no molde de load_emr_serverless, com lru_cache e vocabulario fechado"}
  - {path: sparkforge/facts/runtime_detect.py, action: modify, reason: "_PLATFORM_KEYS ganha databricks, DATABRICKS_MATRIX deriva spark, normalizacao do rotulo, fact databricks.photon com state on/off/undeclared, EMITTED_KINDS"}
  - {path: sparkforge/findings/models.py, action: modify, reason: "RuntimeContext ganha databricks e photon, e to_dict os serializa"}
  - {path: sparkforge/rules/engine.py, action: modify, reason: "motivo de pulo databricks.photon.unresolved quando runtime databricks com photon on e a regra exige kind de plano (plan.*, spark.sql.*)"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "_runtime_reading le spark.conf_effective com a chave de versao do Databricks Runtime; build_runtime e build_runtime_context recebem databricks e photon como fonte cli"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "--databricks e --photon nos mesmos parsers do --emr, e no laco que itera as flags de runtime"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "entradas databricks e photon nos mesmos schemas MCP que ja aceitam emr"}
  - {path: sparkforge/tuning/spark_conf.py, action: modify, reason: "recusa shuffle_partitions_auto quando o valor efetivo ou pedido de spark.sql.shuffle.partitions e auto"}
  - {path: rules/catalog/env.yaml, action: modify, reason: "regra nova SF-ENV-006 (photon undeclared sob databricks), e SF-ENV-001, 004 e 005 citando Databricks ao lado de Glue e EMR"}
  - {path: rules/catalog/spark-plan.yaml, action: modify, reason: "SF-PLAN-004 com remediacao neutra de plataforma"}
  - {path: rules/catalog/parquet.yaml, action: modify, reason: "SF-PQ-002 com remediacao neutra de plataforma"}
  - {path: rules/catalog/pyspark.yaml, action: modify, reason: "SF-PY-008, 009, 010 e 012 com remediacao neutra de plataforma"}
  - {path: rules/catalog/timeout.yaml, action: modify, reason: "SF-TIMEOUT-001 com remediacao neutra de plataforma"}
  - {path: rules/catalog/spark-ui.yaml, action: modify, reason: "SF-UI-003, 004, 005 e 006 com remediacao neutra de plataforma"}
  - {path: fixtures/runtime/databricks_flag_runtime, action: create, reason: "AC1: declaracao cli deriva spark pela matriz"}
  - {path: fixtures/runtime/databricks_event_log_runtime, action: create, reason: "AC3: a chave de versao em spark.conf_effective detecta a plataforma"}
  - {path: fixtures/runtime/databricks_divergent_spark, action: create, reason: "AC4: spark do event log diverge da matriz e vira divergencia"}
  - {path: fixtures/eventlog/databricks_skewed_stage, action: create, reason: "AC8: par de fixtures/eventlog/skewed_stage sob runtime databricks"}
  - {path: tests/test_fixtures_golden_runtime.py, action: modify, reason: "REQUIRED_FIXTURES com os tres casos novos"}
  - {path: tests/test_fixtures_golden_eventlog.py, action: modify, reason: "REQUIRED_FIXTURES com o caso pareado"}
  - {path: tests/test_runtime_detect.py, action: modify, reason: "listas de plataforma e matriz conhecidas pelo teste"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "kind novo databricks.photon alcancavel pela regra SF-ENV nova"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "golden que dispara a regra SF-ENV nova"}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "regen dos casos novos se o corpus exigir entrada propria; golden nunca escrito a mao"}
  - {path: fixtures/scan, action: modify, reason: "summary.json regenerados: RuntimeContext.to_dict ganha databricks e photon"}
  - {path: manifest.json, action: modify, reason: "rule_count mais um"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 dos documentos novos de knowledge/databricks"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "fontes Databricks novas na watchlist"}
  - {path: docs/surface.lock.json, action: modify, reason: "crescimento declarado pelas flags e parametros MCP novos (regra 26)"}
  - {path: docs/guia/referencia, action: modify, reason: "referencia gerada dos verbos e tools que ganham flag"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo move alegacoes de corpus do gate de lastro"}
  - {path: README.md, action: modify, reason: "Databricks como plataforma declarada, com o que fica fora"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "estado da frente DATABRICKS_SPARK"}
decisions:
  - id: D1
    choice: "Plataforma databricks como chave nova de _PLATFORM_KEYS e campo novo de RuntimeContext, no molde de emr."
    rejected: ["so o fact env.platform, sem campo: nenhuma regra poderia declarar runtime_scope por versao de Databricks Runtime", "enum platform no RuntimeContext: mudaria in_scope, codigo provado nas bordas (comentario em findings/models.py)"]
    rollback: "git revert dos commits da plataforma e python scripts/regen_fixtures.py para voltar os goldens"
  - id: D2
    choice: "Matriz em knowledge/databricks/runtime-matrix.yaml com uma unica coluna spark; rotulo 15.4.x-scala2.12 normalizado para 15.4; versao fora da matriz deixa spark vazio, sem inventar."
    rejected: ["dict literal em runtime_detect.py: fato externo sem fonte e data, o defeito que load_emr corrigiu", "colunas python e scala agora: nenhuma regra consome e a pagina de versoes suportadas nao as publica"]
    rollback: "git revert do commit da matriz"
  - id: D3
    choice: "Photon declarado por --photon on|off. On: o engine pula regras cujo requires_facts tem kind de plano, motivo databricks.photon.unresolved. Nao declarado: julga normal e a regra SF-ENV nova avisa que silencio de regra de plano nao e evidencia."
    rejected: ["filtro apos judge em cada chamada: sao oito chamadas de run_judge em _core.py, e esquecer uma e silencio", "campo novo por regra no catalogo: muda loader e schema para um sinal que e de runtime", "recusa por padrao sem declaracao: tira o valor das regras de plano de todo job Databricks", "sem flag, so U2: AC5 dependeria de workspace"]
    rollback: "git revert do commit de Photon; o engine volta aos tres motivos de pulo"
  - id: D4
    choice: "Regra sem escopo alcancavel pelos kinds que um job Databricks produz (extratores Spark genericos e runtime_detect) so cita termo de AWS se citar o Databricks no mesmo texto; o resto ganha texto neutro. Medido: 14 regras, e so SF-PQ-002 fica como excecao escrita no teste."
    rejected: ["proposed_change_by_platform no schema: muda loader, engine e README do catalogo", "so lista de excecoes: usuario Databricks continua lendo DPU", "runtime_scope glue como etiqueta: o defeito documentado em docs/gates-por-mudanca.md"]
    rollback: "git revert do commit do catalogo e python scripts/regen_fixtures.py"
  - id: D5
    choice: "tune recusa com shuffle_partitions_auto quando spark.sql.shuffle.partitions vale auto; nenhuma regra le o valor, entao o catalogo nao muda por isso."
    rejected: ["derivar numero fixo por cima de auto: desliga o auto-optimized shuffle sem avisar", "tratar auto como default 200: a fonte diz que auto e opt-in e escolhe o numero pelo plano"]
    rollback: "git revert do commit de tuning"
  - id: D6
    choice: "Flags --databricks e --photon nos mesmos verbos e schemas MCP do --emr."
    rejected: ["so runtime detect, judge e tune: os outros verbos ficariam sem jeito de declarar Databricks e o laco de flags ganharia excecao"]
    rollback: "git revert do commit das flags e python scripts/check_surface_lock.py --update"
  - id: D7
    choice: "Fixtures nos corpora existentes fixtures/runtime e fixtures/eventlog; AC8 pareia fixtures/eventlog/skewed_stage."
    rejected: ["corpus novo fixtures/databricks: move os gates de corpus e o glob do verify_wheel sem necessidade"]
    rollback: "git revert do commit das fixtures"
covers:
  - {part: "matriz", acceptance: [AC2]}
  - {part: "deteccao", acceptance: [AC1, AC3, AC4]}
  - {part: "photon", acceptance: [AC5]}
  - {part: "auditoria", acceptance: [AC6]}
  - {part: "tune", acceptance: [AC7]}
  - {part: "par de fixtures", acceptance: [AC8]}
  - {part: "superficie", acceptance: [AC9]}
---

# DATABRICKS_SPARK — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| matriz | `knowledge/databricks/runtime-matrix.{yaml,md}`, `sparkforge/facts/runtime_matrix.py` | AC2 |
| detecção | `runtime_detect.py`, `findings/models.py`, `adapters/_core.py`, `fixtures/runtime/databricks_*` | AC1, AC3, AC4 |
| photon | `rules/engine.py`, regra SF-ENV nova em `env.yaml` | AC5 |
| auditoria | cinco arquivos do catálogo, `tests/test_databricks_rule_audit.py` | AC6 |
| tune | `tuning/spark_conf.py` | AC7 |
| par de fixtures | `fixtures/eventlog/databricks_skewed_stage` | AC8 |
| superfície | `adapters/cli.py`, `adapters/tools.py`, `docs/surface.lock.json`, `docs/guia/referencia` | AC9 |

## Medidas que sustentam o desenho

- `RuntimeContext` está serializado em 15 goldens de `fixtures/scan/`. Por isso
  D1 regenera goldens pelo `regen_fixtures.py`, nunca à mão.
- `run_judge` tem oito chamadas em `sparkforge/adapters/_core.py`. Por isso D3
  põe a recusa de Photon no engine, que é o ponto único.
- Das 231 regras executáveis com `runtime_scope` vazio, as que exigem só kinds
  de extratores genéricos de Spark (event log, plano, métricas SQL, AST PySpark,
  footer Parquet e derivados) ou de `runtime_detect` e citam termo de AWS
  (Glue, DPU, EMR, Lake Formation, Athena, DynamicFrame) são 14: SF-ENV-001, 004
  e 005, SF-PLAN-004, SF-PQ-002, SF-PY-008, 009, 010 e 012, SF-TIMEOUT-001 e
  SF-UI-003, 004, 005 e 006. `--conf` saiu da lista de termos porque é flag do
  `spark-submit`, não de AWS. O teste de AC6 recalcula o conjunto a partir de
  `EMITTED_KINDS`, sem lista de regras escrita à mão.
- `tune` lê o valor atual de `spark.sql.shuffle.partitions` como texto
  (`_procedencia`) e deriva um número por cima dele. Com `auto`, isso proporia
  desligar o auto-optimized shuffle.

## Conhecimento consultado

- Versões suportadas do Databricks Runtime e Spark correspondente:
  docs.databricks.com/aws/en/release-notes/runtime/ (2026-09-11).
- `spark.databricks.clusterUsageTags.sparkVersion` como propriedade local de
  TaskContext, valor `16.3`, Databricks Runtime 16.3+:
  docs.databricks.com/aws/en/udf/udf-task-context (2026-09-11). A presença no
  event log continua U1.
- Photon: fallback para Spark, cor na UI, `runtime_engine = PHOTON`:
  docs.databricks.com/aws/en/compute/photon (2026-09-11). O sinal no event log
  continua U2.
- `spark.sql.shuffle.partitions = auto` é opt-in, default 200, AQE ligado por
  padrão no Databricks: docs.databricks.com/aws/en/optimizations/aqe
  (2023-10-12).
- Guarda de versão e o defeito da etiqueta de serviço: `docs/gates-por-mudanca.md`,
  seção de `runtime_scope`.

## O que U1 e U2 significam para o build

AC3 prova que a leitura da chave funciona quando ela está presente; se um event
log real a traz continua sendo U1, e o ship diz isso. AC5 prova a recusa sob
`--photon on`; a detecção automática de Photon fica para quando U2 abrir.
