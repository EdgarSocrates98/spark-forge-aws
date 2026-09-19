---
sdd: 1
feature: STEP_FUNCTIONS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STEP_FUNCTIONS/define.md
  sha256: "da628411f242bd489413b3a7ee5a4eb8cd5a38200578668ce6a08e3eaebb0e68"
files:
  - {path: sparkforge/facts/stepfunctions.py, action: create, reason: "extrator de ASL: sfn.state_machine, sfn.task, sfn.unresolved, sfn.analyzed; e a derivacao pura sfn.glue_job_link sobre a uniao dos facts (D1, D2, D5)"}
  - {path: tests/test_stepfunctions.py, action: create, reason: "AC1, AC2, AC6 e AC7"}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "fuse() chama a derivacao sfn.glue_job_link, no molde de build_lakeformation (D5)"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "funcao publica de analyze step-functions (D3)"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "subcomando analyze step-functions --path (D3)"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tool sparkforge_analyze_step_functions, READ_ONLY (D3)"}
  - {path: rules/catalog/stepfunctions.yaml, action: create, reason: "area SF-SFN, SF-SFN-001 a SF-SFN-004 (D4)"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rota AGENT por findings_area SF-SFN para glue-infra-reviewer (D6)"}
  - {path: agents/glue-infra-reviewer.md, action: modify, reason: "declara SF-SFN em rule_areas e cita a tool nova (D6); espelhos pelo sync, .codex a mao"}
  - {path: knowledge/stepfunctions/glue-integration.md, action: create, reason: "as frases citadas das seis paginas e as lacunas nomeadas (D7)"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 do documento novo, por _content_sha256"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "as URLs novas, por refresh_knowledge.py --offline --update"}
  - {path: fixtures/stepfunctions, action: create, reason: "corpus novo: um caso por regra, um limpo, um com JobName dinamico, um describe-state-machine EXPRESS e um par ASL + Terraform (D8)"}
  - {path: tests/test_fixtures_golden_stepfunctions.py, action: create, reason: "golden do corpus, com a linha literal FIXTURES = ROOT / \"fixtures\" / \"stepfunctions\" que test_fixtures_kind_coverage casa"}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "FIXTURES_STEPFUNCTIONS e regen_stepfunctions"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "extrator novo nas listas manuais"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "extrator novo na lista de imports que o registro de kinds le"}
  - {path: tests/test_adapters_tools.py, action: modify, reason: "lista literal da superficie e argumento real da tool nova"}
  - {path: tests/test_harness_authorization.py, action: modify, reason: "contagem de tools que declaram caminho"}
  - {path: parity.yaml, action: modify, reason: "capacidade com tools e cli da tool nova"}
  - {path: manifest.json, action: modify, reason: "tools e knowledge_base.rule_count"}
  - {path: rules/catalog/action_kinds.yaml, action: modify, reason: "so se o action.kind das regras novas nao existir no vocabulario fechado"}
  - {path: docs/surface.lock.json, action: modify, reason: "tool e knowledge novos (regra 26, bytes no commit)"}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "referencia gerada: pagina da tool nova e do verbo"}
  - {path: docs/guia/usos/step-functions.md, action: create, reason: "manual de uso: como coletar o ASL e o que as quatro regras dizem"}
  - {path: fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, action: modify, reason: "goldens de assessment carregam a contagem do catalogo (tres cenarios e dois holdout, representante)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "regras, tools, extratores"}
  - {path: README.md, action: modify, reason: "contagem de regras e tools"}
  - {path: docs/claims.lock.json, action: modify, reason: "len(TOOLS), corpus de .py e contagens movem alegacoes"}
decisions:
  - id: D1
    choice: "Um modulo so, sparkforge/facts/stepfunctions.py, com prefixo de kind sfn. (a CLI oficial e aws stepfunctions, e sfn e o prefixo de ARN arn:aws:states e do nome curto usado pela propria AWS em SFN; nenhum kind existente comeca com sfn). Le .asl.json, .json com StartAt e States, e a saida de describe-state-machine (objeto com definition string e type). Caminha States recursivamente em Parallel.Branches[] e Map.ItemProcessor (e o legado Map.Iterator). Kinds: sfn.state_machine (1 por arquivo: tipo STANDARD, EXPRESS ou undeclared; query language), sfn.task (1 por Task: path do estado, resource, service, api, pattern request_response|sync|callback, job_name, job_name_dynamic, retriers com error_equals, max_attempts efetivo e max_attempts_defaulted, has_catch, timeout_seconds ou timeout_declared false), sfn.unresolved (reason: invalid_json, not_a_state_machine, definition_not_string, resource_dynamic), sfn.analyzed (sempre)."
    rejected: ["ler aws_sfn_state_machine do Terraform: o definition costuma vir de templatefile ou jsonencode, fora do alcance estatico (fora de escopo no define)", "kind generico orch.*: Control-M ja tem ctm.*, e cada orquestrador tem semantica de retry propria"]
    rollback: "git revert dos commits da feature"
  - id: D2
    choice: "Os defaults publicados moram no extrator como constantes com a URL ao lado: MaxAttempts 3 (concepts-error-handling), TimeoutSeconds 99,999,999 (state-task). O fact grava o efetivo e a marca de omitido; a regra julga o efetivo. JobName em Arguments/Parameters: literal quando string sem .$ e sem {% %}; dinamico quando a chave termina em .$ ou o valor e expressao JSONata."
    rejected: ["deixar o default para a regra: a regra nao sabe o default, e expr nao tem funcao (regra 33)"]
    rollback: "git revert do commit"
  - id: D3
    choice: "Verbo sparkforge analyze step-functions --path <arquivo|diretorio>, e tool MCP sparkforge_analyze_step_functions com os mesmos argumentos (path, detail_level como as vizinhas analyze_*), READ_ONLY, erro acionavel citando o comando. Funcao em _core no molde de _extract_controlm_jobs_facts."
    rejected: ["coletor aws stepfunctions describe-state-machine: exige credencial; o operador cola a saida em arquivo e o analyze le"]
    rollback: "git revert do commit"
  - id: D4
    choice: "Area SF-SFN em rules/catalog/stepfunctions.yaml, runtime_scope {glue: '*'} nas quatro (todas julgam como o Glue e disparado, e o eixo glue satisfaz a auditoria de texto AWS de tests/test_databricks_rule_audit.py). SF-SFN-001 (P1, structural): sfn.task service glue, api startJobRun, pattern request_response, com Next. SF-SFN-002 (P2, structural): sfn.task glue sync com retrier cujo error_equals contem States.ALL ou States.TaskFailed e max_attempts efetivo > 0; severity sobe para P1 se max_attempts_defaulted. SF-SFN-003 (P1, confirmed): sfn.task pattern sync e sfn.state_machine type EXPRESS no mesmo arquivo. SF-SFN-004 (P2, structural): sfn.glue_job_link com sfn_retry_effective > 0 e glue_max_retries > 0. Cada regra com sources das paginas citadas, validation, rollback e action de vocabulario existente quando houver."
    rejected: ["regra de Timeout do Task contra o Timeout do job: o que acontece com o JobRun no States.Timeout nao e documentado (fora de escopo no define)", "regra de Catch ausente: falta de Catch e politica, nao defeito, e a documentacao so diz que o default e falhar a execucao"]
    rollback: "git revert do commit, e regen dos goldens de assessment"
  - id: D5
    choice: "Derivacao pura build_sfn_glue_link(facts) em stepfunctions.py, chamada por fusion.fuse() como build_lakeformation: para cada sfn.task glue com job_name literal, procura tf.attribute key name com value igual e mesmo recurso aws_glue_job, e le o tf.attribute key max_retries do mesmo recurso; emite sfn.glue_job_link com job_name, resource, glue_max_retries (0 quando o atributo nao existe, com marca), sfn_retry_effective (soma dos max_attempts efetivos que casam falha de Glue). job_name dinamico sai sfn.unresolved reason job_name_dynamic; nome sem aws_glue_job correspondente sai sfn.unresolved reason job_definition_absent. EMITTED_KINDS e SOURCE_KINDS declarados."
    rejected: ["juntar no motor de regras: _same_subject agrupa por symbol ou file:line, e os dois lados tem subject diferente (o mesmo motivo do bridge.py)", "casar por substring do nome: nome de job e chave exata na API"]
    rollback: "git revert do commit"
  - id: D6
    choice: "glue-infra-reviewer declara SF-SFN (a descricao dele ja e definicao do job Glue, retries e Terraform) e ganha a rota AGENT-086 por findings_area SF-SFN; a secao nova cita sparkforge_analyze_step_functions. Coordenador novo nao entra: o criterio exige area que julga, e SF-SFN e uma so."
    rejected: ["coordenador sf-step-functions-specialist novo: foi removido no SF_STUBS por ser nome sem artefato; voltar com uma area so seria o mesmo nome com um arquivo"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D7
    choice: "knowledge/stepfunctions/glue-integration.md com as frases citadas (as seis paginas), a data de leitura, e tres lacunas nomeadas: composicao dos retries, JobRun no States.Timeout, ASL real nao observado. Secao ## Fontes com as URLs para o sources.lock."
    rejected: ["guardar as frases so no explore: knowledge e o que o agente consulta offline; o explore e registro da feature"]
    rollback: "git revert do commit"
  - id: D8
    choice: "Corpus fixtures/stepfunctions/<caso>/input e expected, sintetico a partir dos exemplos oficiais: glue_sem_sync, glue_retry_implicito, express_com_sync (describe-state-machine), limpo, job_name_dinamico, e retry_duas_camadas (ASL + main.tf do job com max_retries 2). Golden por scripts/regen_fixtures.py."
    rejected: ["fixture real: nenhum ASL real foi observado, e caso real nunca entra no repositorio"]
    rollback: "git rm do corpus"
covers:
  - {part: "extrator", acceptance: [AC1, AC2]}
  - {part: "verbo e tool", acceptance: [AC7]}
  - {part: "regras e area", acceptance: [AC3, AC4, AC5, AC8]}
  - {part: "derivacao", acceptance: [AC6]}
  - {part: "knowledge e registros", acceptance: [AC9, AC10]}
---

# STEP_FUNCTIONS — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator | `sparkforge/facts/stepfunctions.py`, `tests/test_stepfunctions.py` | AC1, AC2 |
| verbo e tool | `_core.py`, `cli.py`, `tools.py`, `parity.yaml`, testes de superfície | AC7 |
| regras e área | `rules/catalog/stepfunctions.yaml`, `routing.yaml`, `glue-infra-reviewer`, corpus e golden | AC3–AC5, AC8 |
| derivação | `build_sfn_glue_link` e `fusion.py` | AC6 |
| knowledge e registros | documento, manifesto offline, lock de fontes, superfície, referência, números | AC9, AC10 |

## Medidas que sustentam o desenho

- Precedente de forma: `sparkforge/facts/controlm_jobs.py` (JSON versionado como fonte) e
  o conjunto de 30 arquivos que ele tocou (medido por `git grep` em 2026-09-19).
- Precedente de cruzamento: `build_lakeformation` chamado em `sparkforge/facts/fusion.py`.
- O lado do Glue já é fact: `tf.attribute` com `key: max_retries` (lido pela
  `SF-GLUE-004`) e `key: name` no mesmo recurso.
- `glue-infra-reviewer` declara hoje `SF-GLUE` e `SF-ENV`.
