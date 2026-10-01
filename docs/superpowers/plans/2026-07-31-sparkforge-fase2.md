# SparkForge Fase 2 (executada) Implementation Plan — Desbloqueio Total do Catálogo

> **Status: CONCLUÍDO em 2026-07-31.** Documento **retroativo**, reconstruído dos
> commits depois da entrega. Checkboxes já marcados. Não re-execute.
>
> Estado corrente: [`../STATUS.md`](../STATUS.md).
> Decisões: [`../specs/2026-07-31-sparkforge-fase2-design.md`](../specs/2026-07-31-sparkforge-fase2-design.md).

> **Esta não é a Fase 2 do roadmap da §16 da Fase 0.** Aquela é expansão de
> knowledge + `refresh_knowledge`, e continua em aberto. Esta é o desbloqueio do
> catálogo que já existia.

**Goal:** zerar as duas contagens que tornavam o catálogo uma promessa —
**0 regras com `blocked_on`** e **43 de 43 regras provadas por uma fixture que as
faz disparar** — e travar os invariantes que impedem a regressão.

**Architecture:** nenhuma camada nova. Três extratores em `facts/`, dois kinds a
mais em `event_log.py`, uma correção na camada do SDK MCP em `adapters/mcp.py`,
e três corpora de fixture. Nenhuma regra nova no catálogo.

**Branch:** `feat/fase2-desbloqueios` · **Faixa:** `dc80efd` … `b44edd0` ·
**Merge:** `bc53865` (PR #1).

---

## Fatos do ambiente no início da fase

- 43 regras, **5 com `blocked_on`**: SF-PQ-001, SF-PQ-003, SF-PQ-005, SF-ENV-002, SF-GLUE-005.
- 40 de 43 com golden positivo. Sem golden: SF-ENV-003, SF-GLUE-003, SF-GLUE-004.
- 25 tools MCP declarando `outputSchema`.
- 1621 testes.

---

## Task 1 — Consertar toda chamada de tool MCP

Commit: `dc80efd`. Encontrado ao subir o servidor de verdade e falar com ele por
HTTP — o commit anterior só provava a **construção** do app.

- [x] **Diagnóstico:** os 25 tools declaram `outputSchema`; o SDK exige `structuredContent` de quem declara; `_call_tool` devolvia só `TextContent`. Qualquer `tools/call` respondia `Output validation error: outputSchema defined but no structured output returned` — em stdio e em HTTP, no Claude Code e no Devin
- [x] **Por que nenhum teste pegava:** todos exercitavam `tools.call_tool` direto, e essa função nunca esteve quebrada. Faltava a camada do SDK entre ela e o cliente
- [x] Handler passa a devolver o dict cru; o SDK preenche `structuredContent` e segue serializando o JSON em `content`, então cliente que só lê texto não regride
- [x] Erro de fronteira sai como `CallToolResult(isError=True)`, não como dict — `{"error", "exit_code"}` não casa com o `outputSchema` e a validação trocaria a mensagem acionável do adapter por uma queixa de schema
- [x] **`/mcp` respondia 307.** `Mount("/mcp")` do Starlette só serve `/mcp/`; httpx não segue redirect em POST por default, então o `serverUrl` documentado falharia no Devin Desktop com "não conecta" e nenhuma pista. Rota resolvida no próprio handler comparando o caminho normalizado: `/mcp` e `/mcp/` servem, o resto é 404 explícito
- [x] Testes novos chamam o tool **através do handler do SDK** (sucesso com `structuredContent` validado contra o `outputSchema`, texto preservado, erro de fronteira com a mensagem do adapter, tool inexistente) e dirigem o app ASGI direto
- [x] Verificado fora do teste com servidor real: HTTP em `/mcp` e `/mcp/` (initialize, tools/list, tools/call com sucesso e com erro) e stdio

## Task 2 — Extrator `s3_listing`

Commit: `081a570`.

- [x] Lê dump de `aws s3api list-objects-v2`
- [x] Kinds: `s3.prefix_summary`, `s3.analyzed`, `s3.unresolved`
- [x] **Agrupa por (formato, compressão)** — prefixo real mistura Parquet, `_SUCCESS`, log `.gz` e CSV de carga inicial; sumário único diluiria um `.gz` de 4 GB na média do Parquet e SF-PQ-003 nunca casaria
- [x] **`IsTruncated: true` suprime o sumário** — `file_count`, `avg_file_bytes` e `max_file_bytes` sairiam de uma página apresentada como total
- [x] Desbloqueia SF-PQ-001 (small files), SF-PQ-003 (texto gzip não splitável) e SF-PQ-005 (cardinalidade de partição, com `catalog.table_partitions`)
- [x] `fixtures/s3/` — 5 fixtures: `small_files_prefix`, `gzip_text_not_splittable`, `overpartitioned_prefix`, `healthy_prefix` (negativa), `truncated_listing`

## Task 3 — Extrator `consumers`

Commit: `081a570`.

- [x] Lê o inventário **declarado** de consumidores de tabela
- [x] Kinds: `env.consumer`, `env.consumers_analyzed`, `env.unresolved`
- [x] **Único extrator do pacote que lê arquivo escrito por uma pessoa, de propósito** — derivar do histórico de queries do Athena veria só o Athena, com retenção limitada, e um consumidor Redshift ou EMR invisível viraria "sem consumidor"
- [x] Tabela ausente do inventário não produz fact; a sentinela distingue inventário vazio de inventário nunca lido
- [x] Desbloqueia SF-ENV-002 — Iceberg format V3, que o Athena não lê
- [x] `fixtures/consumers/` — 3: `v3_with_athena_consumer` (positiva), `v2_with_athena_consumer` (negativa), `malformed_inventory`

## Task 4 — `extract_terraform_diff`

Commit: `081a570`.

- [x] Compara dois diretórios — dois checkouts, dois `git worktree`, o main e o branch do PR
- [x] Marca `attrs.changed` com `previous_value`
- [x] **Não roda terraform**: lê o HCL, que é o que o revisor do PR vê
- [x] **Devolve só o lado DEPOIS** — devolver os dois faria toda regra contar cada recurso duas vezes e acusar o estado antigo, que ninguém pode mais consertar
- [x] `fixtures/tfdiff/` — 2 fixtures

## Task 5 — Consertar SF-GLUE-005, que tinha dois defeitos escondidos

Commit: `081a570`. Os dois só apareceram quando a regra passou a rodar.

- [x] **Defeito 1:** `spark.stage.spill` estava em `requires_facts` **E** em `absent:`, e o motor exige presença de todo kind de `requires_facts`. A regra era uma contradição; não podia disparar nunca
- [x] **Defeito 2:** mesmo corrigido, `absent:` continuaria errado — `event_log` emite esse fact para todo stage analisado, zero byte inclusive. A ausência significa "não analisei event log", não "não houve spill"
- [x] Novo kind `spark.job.spill_summary` em `event_log.py`, que responde no nível do job
- [x] Novo kind `spark.executor.memory_usage` (de `SparkListenerStageExecutorMetrics`), mantido em `requires_facts`: afirmar que não há limitação de memória sem ter visto uma medida de memória é o mesmo erro, um passo adiante

## Task 6 — Superfície e paridade

Commit: `081a570`.

- [x] `analyze s3-listing`, `analyze consumers`, `analyze terraform-diff` na CLI
- [x] Mesmos três no MCP — **28 tools**
- [x] `parity.yaml` e `manifest.json` atualizados
- [x] 79 testes unitários dos extratores novos + golden de cada corpus
- [x] Snyk 0; regeneração de fixtures idempotente
- [x] **1621 → 1700 testes. 43 regras, 0 bloqueadas, 40 com golden que dispara**

## Task 7 — Fechar as 3 regras sem golden positivo

Commit: `b44edd0`.

- [x] **Corpus novo `fixtures/infra_code/`**, com Terraform **e** código PySpark do mesmo job no mesmo `input/` — duas das três regras fazem uma pergunta que nenhum artefato responde sozinho
- [x] `observability_without_glue_context` → SF-ENV-003: `--enable-observability-metrics` ligado sem `GlueContext`. As métricas do Glue são publicadas pelo GlueContext; sem ele o argumento fica ligado, o operador acredita ter métrica, e o painel fica vazio
- [x] `retries_with_append_write` → SF-GLUE-004: `max_retries = 3` com escrita `append`. A retentativa reexecuta o job e `append` não é idempotente: cada tentativa soma os mesmos registros, o job é marcado como sucesso, e o dado sai duplicado sem erro no log
- [x] **As duas são a metade negativa uma da outra**: a de SF-ENV-003 não inicializa GlueContext e grava `overwrite` com `max_retries = 0`; a de SF-GLUE-004 inicializa GlueContext e grava `append` com `max_retries = 3`
- [x] Teste garante que **cada fixture dispara exatamente uma regra** — corpus de correlação é o mais fácil de contaminar, e fixture que prova duas coisas ao mesmo tempo não prova nenhuma com clareza
- [x] `bookmarks_with_concurrency` → SF-GLUE-003, de fonte única, em `fixtures/terraform/`: bookmark guarda progresso por JOB, não por execução; duas execuções concorrentes leem o mesmo ponto de partida e a última a terminar sobrescreve o marcador da outra
- [x] `scripts/regen_fixtures.py`

## Task 8 — Travar os invariantes

Commit: `b44edd0`, em `tests/test_fixtures_kind_coverage.py`.

- [x] Toda regra do catálogo precisa de uma fixture que a faça disparar
- [x] Todo `rule_id` que aparece num golden precisa existir no catálogo
- [x] As duas direções, porque as duas já quebraram
- [x] **1700 → 1726 testes. 43 regras, 0 bloqueadas, 43 com golden que dispara**

---

## Resultado

| | Início | Fim |
|---|---|---|
| Regras com `blocked_on` | 5 | **0** |
| Regras com golden que dispara | 40 de 43 | **43 de 43** |
| Tools MCP | 25 (toda chamada falhava) | **28**, funcionando em stdio e HTTP |
| Testes | 1621 | **1726** |

O que falta para uma regra disparar passa a ser sempre **coleta**, nunca código.
