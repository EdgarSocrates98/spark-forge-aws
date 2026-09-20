---
sdd: 1
feature: SFN_HISTORY
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_HISTORY/define.md
  sha256: "3bf9ee33edd322694a301a5e7be794ab9e831c94d1110c12db3fc5f98ffef818"
files:
  - {path: sparkforge/facts/sfn_history.py, action: create, reason: "extrator do historico (sfn.execution, sfn.attempt, sfn.job_run, sfn.unresolved, sfn.analyzed) e a derivacao pura sfn.retry_observado (D1, D2, D5)"}
  - {path: tests/test_sfn_history.py, action: create, reason: "AC1, AC2, AC3 e AC7"}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "fuse() chama build_sfn_retry_observado, como ja chama build_sfn_glue_link e build_af_glue_link (D5)"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "funcao publica de analyze sfn-history (D3)"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "subcomando analyze sfn-history --path (D3)"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tool sparkforge_analyze_sfn_history, READ_ONLY (D3)"}
  - {path: rules/catalog/sfn-history.yaml, action: create, reason: "area SF-SFNX, SF-SFNX-001 a 003 (D4)"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rota AGENT-088 por findings_area SF-SFNX para glue-infra-reviewer (D6)"}
  - {path: agents/glue-infra-reviewer.md, action: modify, reason: "declara SF-SFNX, cita a tool nova e a description acompanha (D6)"}
  - {path: .claude/agents/glue-infra-reviewer.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .agents/agents/glue-infra-reviewer.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .github/agents/glue-infra-reviewer.agent.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .codex/agents/glue-infra-reviewer.toml, action: modify, reason: "espelho que o sync nao gera: a secao nova a mao"}
  - {path: knowledge/stepfunctions/execution-history.md, action: create, reason: "as frases citadas da pagina da API, o que cada evento sustenta e as lacunas (D7)"}
  - {path: knowledge/stepfunctions/glue-integration.md, action: modify, reason: "a lacuna 1 (composicao dos retries) passa a apontar o artefato que a destrava"}
  - {path: knowledge/INDEX.md, action: modify, reason: "o documento novo na secao de orquestracao"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 dos documentos de knowledge, por _content_sha256"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "a URL da API, por refresh_knowledge.py --offline --update"}
  - {path: fixtures/sfn_history, action: create, reason: "corpus novo: uma fixture por regra, as negativas, o par ASL + historico e os casos de leitura incompleta (D8)"}
  - {path: tests/test_fixtures_golden_sfn_history.py, action: create, reason: "golden do corpus, com a linha literal FIXTURES = ROOT / \"fixtures\" / \"sfn_history\""}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "FIXTURES_SFN_HISTORY e regen_sfn_history"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "extrator novo nas listas manuais"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "extrator novo na lista de imports"}
  - {path: tests/test_adapters_tools.py, action: modify, reason: "lista literal da superficie e argumento real da tool nova"}
  - {path: tests/test_harness_authorization.py, action: modify, reason: "contagem de tools que declaram caminho"}
  - {path: tests/test_fixtures_golden_mcp_parity.py, action: modify, reason: "tool nova depois do golden entra em NOVAS_DEPOIS_DO_GOLDEN"}
  - {path: tests/test_databricks_rule_audit.py, action: modify, reason: "sfn_history entra em SO_AWS (D4)"}
  - {path: sparkforge/agentic/executor/debate_evidence.py, action: modify, reason: "sfn-history na allowlist de extratores de evidencia"}
  - {path: docs/agentic-evolution-report.md, action: modify, reason: "a contagem da allowlist"}
  - {path: fixtures/debate/retomada/expected/brief.json, action: modify, reason: "o brief lista a allowlist; regenerado pelo caminho do proprio teste"}
  - {path: parity.yaml, action: modify, reason: "capacidade com tools, cli e knowledge"}
  - {path: manifest.json, action: modify, reason: "tools e knowledge_base.rule_count"}
  - {path: docs/surface.lock.json, action: modify, reason: "tool e knowledge novos (regra 26, bytes no commit)"}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_sfn_history.md, action: create, reason: "pagina gerada da tool"}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "indice gerado"}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "pagina gerada do verbo"}
  - {path: docs/guia/referencia/agents/glue-infra-reviewer.md, action: modify, reason: "pagina gerada do coordenador"}
  - {path: docs/guia/usos/step-functions.md, action: modify, reason: "o manual ganha a secao do historico: como salvar e o que ele responde"}
  - {path: docs/guia/06-extrair-julgar-compor.md, action: modify, reason: "o verbo novo na tabela e as contagens"}
  - {path: docs/guia/07-conhecimento-e-catalogo.md, action: modify, reason: "contagem de regras e areas"}
  - {path: fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, action: modify, reason: "goldens de assessment carregam a contagem do catalogo (tres cenarios e dois holdout; este e o representante)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "regras, tools, extratores, kinds, rotas, fixtures, fontes"}
  - {path: README.md, action: modify, reason: "contagem de regras, tools e extratores"}
  - {path: CLAUDE.md, action: modify, reason: "contagem de tools e de tools com detail_level"}
  - {path: AGENTS.md, action: modify, reason: "mesma contagem"}
  - {path: GUIA_DE_USO.md, action: modify, reason: "mesma contagem"}
  - {path: .devin/README.md, action: modify, reason: "mesma contagem"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "alegacoes de corpus e de tools"}
  - {path: docs/harness/AUTHORIZATION-CHAIN.md, action: modify, reason: "alegacoes de len(TOOLS)"}
  - {path: docs/harness/CURRENT-HARNESS-GAP.md, action: modify, reason: "alegacoes de contagem"}
  - {path: docs/harness/ICEBERG-GAP.md, action: modify, reason: "alegacao da contagem de fontes vigiadas"}
  - {path: docs/gates-por-mudanca.md, action: modify, reason: "a secao do criterio de dominio cita os dominios que entraram por artefato"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo e contagens movem alegacoes"}
decisions:
  - id: D1
    choice: "Modulo sparkforge/facts/sfn_history.py, prefixo sfn. (o mesmo do ASL: e o mesmo dominio, e o kind diz a natureza -- sfn.task e declaracao, sfn.attempt e medida). Le o JSON salvo de get-execution-history, no formato da resposta da API (objeto com events[] e nextToken opcional) e tambem a forma de lista crua de eventos. Kinds: sfn.execution, sfn.attempt, sfn.job_run, sfn.unresolved, sfn.analyzed. Uma tentativa e o par entre um TaskScheduled e o proximo evento terminal do mesmo estado (TaskSucceeded, TaskFailed, TaskTimedOut, TaskStartFailed, TaskSubmitFailed); o estado vem do TaskStateEntered mais recente, pelo encadeamento de previousEventId."
    rejected: ["prefixo proprio hist.: separaria em dois dominios o que o operador ve como um", "parsear o CloudWatch Logs do EXPRESS: formato diferente, e o define poe fora de escopo"]
    rollback: "git revert dos commits da feature"
  - id: D2
    choice: "Duracao e medida entre timestamps de eventos, e sai em measures com a unidade no nome (duration_seconds). Contagem de tentativas e measure. Nada de custo: a regra 13 do CLAUDE.md proibe atribuir custo a causa, e a regra 25 exige cost_basis para dolar."
    rejected: ["estimar DPU-segundos do JobRun a partir da duracao do Task: o Task mede espera, nao consumo"]
    rollback: "git revert do commit"
  - id: D3
    choice: "Verbo sparkforge analyze sfn-history --path e tool MCP sparkforge_analyze_sfn_history (path, detail_level), READ_ONLY, no molde de analyze step-functions. Teto de tamanho pelo _teto_para do scan: historico de execucao longa chega a megabytes."
    rejected: ["coletor com credencial (abordagem C do explore)"]
    rollback: "git revert do commit"
  - id: D4
    choice: "Area SF-SFNX em rules/catalog/sfn-history.yaml (SFNX = Step Functions eXecution; SF-SFN ja e a definicao, e misturar declaracao com medida na mesma area tiraria do operador a distincao que a feature existe para fazer), runtime_scope {} nas tres, e sfn_history em SO_AWS. SF-SFNX-001 (P2, confirmed): tentativas observadas acima do teto declarado. SF-SFNX-002 (P1, confirmed): TaskTimedOut em Task .sync sem fim de JobRun no historico. SF-SFNX-003 (P1, confirmed): execucao abortada ou expirada com Task .sync sem evento terminal. As tres sao confirmed porque afirmam que algo ACONTECEU, lido do artefato de execucao."
    rejected: ["por as tres em SF-SFN: o operador perderia a diferenca entre o que declarou e o que aconteceu", "regra de duracao acima de um limiar: limiar de duracao de job nao tem fonte, e seria numero inventado"]
    rollback: "git revert do commit, e regen dos goldens de assessment"
  - id: D5
    choice: "Derivacao pura build_sfn_retry_observado(facts) em sfn_history.py, chamada por fusion.fuse(): casa sfn.attempt com sfn.task pelo nome do estado e emite sfn.retry_observado com tentativas_observadas, teto_declarado (1 + max_attempts efetivo) e a marca de quando o ASL nao esta no case. Sem ASL, nenhum link e a lacuna sai nomeada em sfn.unresolved."
    rejected: ["comparar dentro da regra: o motor nao cruza dois kinds por chave (o mesmo motivo do bridge.py)"]
    rollback: "git revert do commit"
  - id: D6
    choice: "glue-infra-reviewer declara SF-SFNX e ganha a rota AGENT-088; a description acompanha sem usar `: ` (armadilha registrada no AIRFLOW_DAG)."
    rejected: ["coordenador novo: uma area so nao justifica, e o criterio de dominio exige area que julga"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D7
    choice: "knowledge/stepfunctions/execution-history.md com as frases citadas, uma tabela do que cada tipo de evento sustenta, e as lacunas (forma do output do Glue, EXPRESS fora, historico truncado). A lacuna 1 de glue-integration.md passa a apontar este artefato como o que a destrava."
    rejected: ["escrever no mesmo documento de glue-integration: sao dois artefatos, e o documento ja tem seis lacunas"]
    rollback: "git revert do commit"
  - id: D8
    choice: "Corpus fixtures/sfn_history/<caso>/input e expected, sintetico a partir da forma de evento publicada: retry_acima_do_declarado (ASL + historico, dispara 001), retry_dentro_do_declarado (negativa), task_timed_out_sync (002), execucao_abortada_com_task_em_voo (003), execucao_limpa (negativa), sem_execution_data (sem output: sfn.job_run ausente e unresolved nomeado), historico_truncado (nextToken), evento_desconhecido, json_invalido e historico_sem_asl (o confronto nao acontece e a lacuna sai nomeada)."
    rejected: ["historico real: nenhum foi observado, e caso real nunca entra no repositorio"]
    rollback: "git rm do corpus"
covers:
  - {part: "extrator", acceptance: [AC1, AC2, AC3]}
  - {part: "verbo e tool", acceptance: [AC7]}
  - {part: "regras e area", acceptance: [AC5, AC6, AC8]}
  - {part: "confronto declarado x medido", acceptance: [AC4]}
  - {part: "knowledge e registros", acceptance: [AC9, AC10]}
---

# SFN_HISTORY — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator | `sparkforge/facts/sfn_history.py`, `tests/test_sfn_history.py` | AC1–AC3 |
| verbo e tool | `_core.py`, `cli.py`, `tools.py`, `parity.yaml`, testes de superfície | AC7 |
| regras e área | `rules/catalog/sfn-history.yaml`, `routing.yaml`, coordenador, corpus e golden | AC5, AC6, AC8 |
| confronto | `build_sfn_retry_observado` e `fusion.py` | AC4 |
| knowledge e registros | documento, manifesto offline, lock de fontes, superfície, referência, números | AC9, AC10 |

## Medidas que sustentam o desenho

- Precedente inteiro, duas vezes: `docs/sdd/STEP_FUNCTIONS/` e `docs/sdd/AIRFLOW_DAG/`.
- Precedente do confronto entre declarado e medido: `sparkforge/facts/bridge.py`.
- Precedente de artefato de execução salvo: `sparkforge/facts/event_log.py`.
- Armadilhas já pagas: `description` de agente sem `: `; o golden do debate muda quando a
  allowlist de extratores muda, e precisa ser regenerado na mesma tarefa.
