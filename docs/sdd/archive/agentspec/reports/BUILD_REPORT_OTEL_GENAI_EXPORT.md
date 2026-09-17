# BUILD REPORT: OpenTelemetry GenAI export

> Implementation report for OTEL_GENAI_EXPORT

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | OTEL_GENAI_EXPORT |
| **Date** | 2026-09-11 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_OTEL_GENAI_EXPORT.md](../features/DEFINE_OTEL_GENAI_EXPORT.md) |
| **DESIGN** | [DESIGN_OTEL_GENAI_EXPORT.md](../features/DESIGN_OTEL_GENAI_EXPORT.md) |
| **Status** | Complete (B1–B8) |

Branch `feat/otel-genai`, a partir da `main` (com #48, #49 e #50).

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | B1–B8 |
| **Files Created** | `sparkforge/observability/otlp.py`, `fixtures/otel/` (4 casos), `tests/test_observability_otlp.py`, `tests/test_fixtures_golden_otel.py`, `tests/test_check_otel_collector.py`, `scripts/check_otel_collector.py`, `.github/otel-collector.yaml`, `docs/opentelemetry.md` |
| **Files Modified** | `facts/host_transcript.py` (+ 15 goldens), `observability/context_ledger.py`, `adapters/{tools,mcp,_core,cli}.py`, `scripts/regen_fixtures.py`, `.github/workflows/ci.yml`, registros de tool nova (`tests/test_adapters_tools.py`, `tests/test_harness_authorization.py`, `tests/test_fixtures_golden_mcp_parity.py`, `parity.yaml`, `manifest.json`, `config/agents.yaml`, `sf-synthesizer` + espelhos), `tests/test_context_ledger.py`, `tests/test_adapters_mcp.py`, `CLAUDE.md`, `AGENTS.md`, `GUIA_DE_USO.md`, `.devin/README.md`, `docs/superpowers/STATUS.md`, `docs/surface.lock.json`, `docs/claims.lock.json` + 4 docs de `docs/harness/` |
| **Tests Passing** | Suite completa, um processo por arquivo: 265 arquivos, 12 154 passed, 0 failed, 9 skipped |
| **Agents Used** | Nenhum delegado: o build foi direto |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| B1 | Horario no extrator do host | (direct) | ✅ | `host_transcript@0.2.0`; diff dos goldens so em `attrs` e na versao do extrator; nenhum id de fact mudou |
| B2 | Canal medido | (direct) | ✅ | `mcp.py` passa `partial(call_tool, channel="mcp", transport=...)`; `record()` grava em `metadata`; teste de regra 27 com a montagem do span quebrada |
| B3 | `otlp.py` + unidade | (direct) | ✅ | 38 testes: ids, tempo, canal, recusas, provider, modelo, histogramas, forma OTLP |
| B4 | Verbo, CLI, tool e registros | (direct) | ✅ | Tool valida contra o proprio schema com um ledger real e o transcript de `correct_mcp`; mensagens de erro com o comando que resolve |
| B5 | `fixtures/otel/` + golden | (direct) | ✅ | 4 casos com spans de chamadas reais de `call_tool`; a CLI le de um `traces.db` real e bate byte a byte |
| B6 | Collector no CI, docs, gates | (direct) | ✅ | Conferidor testado contra os proprios goldens (identidade passa, token adulterado falha); surface +3 261 bytes; 22 alegacoes remediadas por id |
| B7 | Commit, PR #52, job `otel-collector` | (direct) | ✅ | https://github.com/EdgarSocrates98/spark-forge-aws/actions/runs/34642782123: o `otelcol-contrib` 0.160.0 leu os 4 goldens e o conferidor achou 13 spans e 11 pontos de metrica iguais, inclusive o histograma de token de bucket unico (A-005) |
| B8 | Este relatorio e statuses | (direct) | ✅ | — |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| (direct) | todos | O DESIGN atribuia python-developer, test-generator e ci-cd-specialist. Cada passo dependia de medida do anterior (forma dos spans no disco e no buffer, canal, horario na fonte), como nos PRs #50 e #51 |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge scripts tests -> All checks passed!
```

**Status:** ✅ Pass

### Type Check

```text
N/A — o repositorio nao configura mypy
```

**Status:** ⏭️ Skipped

### Tests

```text
Suite completa, um processo por arquivo: 265 arquivos, 12 154 passed, 0 failed, 9 skipped
check_vnext_claims 0 | check_status_numbers --strict 0 | check_surface_lock 0 | check_evals 10/10
Snyk Code (sparkforge/observability, sparkforge/adapters, scripts/check_otel_collector.py): 0
```

**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | O `traces.db` tambem guarda spans do `AgentOpsTracker` (`task`, `routing`, `model`), que viraria `execute_tool` | Recusa nomeada `componente_nao_tool`, com caso no golden (`sparkforge_erro`) |
| 2 | O `economy_report` recebe o transcript por `host_transcript`, chave que a cadeia de autorizacao nao reconhece como caminho | A tool nova usa `host_transcript_path`: a cadeia confina o arquivo, e as tools que declaram caminho vao de 81 para 82 |
| 3 | O span do disco traz `metadata_json` (string) e o do buffer traz `metadata` (dict) | A projecao normaliza os dois; o golden passa pela CLI lendo de um `traces.db` real |
| 4 | O conferidor do Collector casava ponto de metrica por subconjunto de atributos, e o `invoke_agent.duration` de dois casos com o mesmo horario se confundia | Igualdade nos atributos de semconv (`gen_ai.*`, `mcp.*`, `error.*`) e subconjunto so no resto |
| 5 | Duas alegacoes (`VNX-357`, `VNX-358`) com o mesmo `43` na mesma linha | As duas medem o numero de arquivos golden, e as duas viraram 44 a mao, com a nota no manifesto |
| 6 | Sem Docker nesta maquina | O job `otel-collector` so roda no CI; o conferidor foi testado localmente contra os proprios goldens |
| 7 | Primeiro run do job `otel-collector` no CI: `JSONDecodeError`, porque o conferidor leu `traces.json` com o exporter `file` no meio da escrita de uma linha | Linha incompleta conta como "ainda nao chegou" e o laco de `--wait` rele; teste com linha truncada no fim |
| 8 | O log do Collector 0.160.0 avisou que `otlpjsonfile` e alias obsoleto de `otlp_json_file` | Config do CI, documento, descricoes da CLI e da tool passam a usar `otlp_json_file`; a superficie ficou em +3 261 bytes |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `componente_nao_tool` | Exportar tudo / filtrar calado / recusar | Recusar com nome | Regra 20; a soma continua fechando |
| 2 | Chave do transcript na tool | `host_transcript` (como `economy_report`) / `host_transcript_path` | `host_transcript_path` | A cadeia de autorizacao confina o caminho |
| 3 | Horario dos spans da fixture | Relogio real / normalizado | Normalizado (`span_id`, `start_time`, `end_time`) sobre chamadas reais | O golden nao pode depender do relogio de quem montou; nome, desfecho, bytes e canal sao os medidos |
| 4 | Onde a tool aparece no agente | Coordenador / executor | Passo novo no `sf-synthesizer`, ao lado de `report github` | E quem entrega o relatorio |
| 5 | Job do Collector | So `workflow_dispatch` / todo push e PR | Todo push e PR | Nao escreve fora do runner, ao contrario do `sarif-upload` |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Recusa `componente_nao_tool` a mais | Issue 1 | Um motivo novo no schema e no documento |
| `host_transcript_path` na tool, `--host-transcript` na CLI | Issue 2 | A CLI fica igual ao `economy report`; a tool fica confinavel |
| `_core.telemetry_payload` separado de `telemetry_export` | O golden le `input/spans.json` e passa pelo mesmo caminho da CLI | Uma funcao a mais |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001, 003, 004 | ✅ | golden `sparkforge_ok` + `TestSpanDoSparkForge` + `TestFormaEDeterminismo` |
| AT-002 | ✅ | golden `sparkforge_erro` |
| AT-005, 009 | ✅ | golden `com_host` + `test_com_host_os_tokens_sao_os_do_host_usage` + `TestMetricas` |
| AT-006, 007 | ✅ | golden `host_sem_usage` |
| AT-008 | ✅ | `tests/test_fixtures_golden_host_transcript.py` (113 testes) |
| AT-010 | ✅ | `test_adapters_tools.py` (tool valida contra o schema e nao grava) |
| AT-011 | ✅ | `TestErrorShapesValidateToo` (`run_id` fora do padrao, exit 2 com comando) |
| AT-012 | ✅ | `TestOCanalMedido::test_gravar_o_canal_falhando_nao_derruba_a_chamada` |
| AT-013 | ✅ | https://github.com/EdgarSocrates98/spark-forge-aws/actions/runs/34642782123 |

**Success Criteria:** SC1–SC9 ✅.

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_OTEL_GENAI_EXPORT.md`
