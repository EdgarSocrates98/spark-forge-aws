---
sdd: 1
feature: STREAMING_GLUE_RUNTIME_OBSERVATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RUNTIME_OBSERVATION/define.md
  sha256: "f1fd1e551588903382d94d41328c01da633b12915b78be3c5d0fbb188b0648ec"
files:
  - {path: sparkforge/facts/glue_streaming.py, action: modify, reason: "Preservar worker_type e normalizar os campos de capacidade efetiva disponíveis no dump."}
  - {path: sparkforge/facts/streaming_glue_runtime.py, action: create, reason: "Compor definição Glue Streaming e runs terminais em runtime_link/unresolved."}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "Invocar a composição somente quando os fatos fonte existirem."}
  - {path: rules/catalog/glue-streaming.yaml, action: modify, reason: "Julgar drift observado e lacuna de runtime com evidence-first."}
  - {path: fixtures/streaming_glue_runtime_observation, action: create, reason: "Golden corpus consistente, drift e unresolved."}
  - {path: scripts/regen_streaming_glue_runtime_observation.py, action: create, reason: "Regenerar facts/findings deterministicamente a partir dos inputs."}
  - {path: tests/test_streaming_glue_runtime_observation.py, action: create, reason: "Testar contrato, fuse, regras e goldens."}
  - {path: tests/test_fixtures_golden_streaming_glue_runtime_observation.py, action: create, reason: "Registrar o corpus no gate de goldens."}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "Registrar kinds derivados do novo compositor."}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "Registrar kinds fonte/derivados para reachability."}
  - {path: knowledge/glue-streaming-rtm.md, action: modify, reason: "Documentar run observado e limites de amostra."}
  - {path: skills/review-glue-streaming/SKILL.md, action: modify, reason: "Adicionar passo operacional para coletar/analisar runs e usar fuse."}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "Atualizar evidência e gap de Glue runtime observado."}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "Cobrar documentação do novo fluxo."}

decisions:
  - id: D1
    choice: "Comparar definição efetiva com facts glue.job_run por job_name literal e único, gerando um fact composto antes do judge."
    rejected: ["Casamento por resource name Terraform ou por posição do arquivo, que pode ligar jobs diferentes.", "Regra tentando combinar dois facts, que o motor não suporta com rastreabilidade adequada."]
    rollback: "Reverter o commit da feature; pools sem o novo módulo continuam com os facts originais e as regras 001-005."
  - id: D2
    choice: "Tratar versão, worker_type, worker_count e estado como campos observados; ausência de qualquer eixo comparável vira unresolved."
    rejected: ["Inferir capacidade por worker type, duração ou nome de serviço.", "Converter ausência de run em consistent."]
    rollback: "Remover o link derivado e as regras 006-007; manter os extratores individuais inalterados."
  - id: D3
    choice: "Reutilizar fuse, analyze glue-job-runs, collector e surface existente, sem tool/CLI novo."
    rejected: ["Novo analyze glue-streaming-runtime, que aumenta superfície e payload para o mesmo contrato."]
    rollback: "Reverter apenas a chamada guarded no fuse e retirar docs da nova composição."

covers:
  - {part: "capacidade efetiva", acceptance: [AC1]}
  - {part: "runtime_link", acceptance: [AC2, AC3]}
  - {part: "fuse e catálogo", acceptance: [AC4, AC5]}
  - {part: "docs e workflow", acceptance: [AC6]}
---

# STREAMING_GLUE_RUNTIME_OBSERVATION — desenho

## Modelo

`glue.streaming.job` é o lado efetivo/configurado e `glue.job_run` é o lado
observado. O novo compositor não lê arquivos: recebe facts, faz match por
`attrs.name == subject.job_name` literal e único, e emite:

- `glue.streaming.runtime_link`: medidas de runs, valores observados,
  `drifts`, `unresolved_fields` e `source_fact_ids`;
- `glue.streaming.runtime.unresolved`: motivo nomeado quando identidade,
  amostra ou eixo observado não permite comparação.

O status do link é `consistent`, `divergent` ou `unresolved`; os dois primeiros
só existem quando todos os eixos selecionados têm evidência. O compositor não
agrega duração, DPU ou throughput e não transforma um run terminal em prova de
saúde de streaming.

## Conhecimento consultado

- `sparkforge rules lookup --category glue_streaming`, executado sobre o
  catálogo atual: `SF-GLUESTREAM-001..005` e seus limites.
- `knowledge/glue-streaming-rtm.md`, que ancora Glue 6.0/RTM e exige unresolved
  para capacidade ausente.
- `sparkforge/facts/glue_job_run.py`, que preserva `GlueVersion`, `WorkerType`,
  `NumberOfWorkers`, `JobRunState` e `job_run_id` do artefato terminal.

## Segurança e economia

O compositor usa somente facts já sanitizados pelo collector; não toca AWS,
não transporta `ErrorMessage`, não cria tool nova e mantém o surface lock
inalterado. `source_fact_ids` permite reextração sem copiar payload inteiro.
