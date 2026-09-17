# BUILD REPORT: Agentic Eval Harness

> Implementation report for Agentic Eval Harness

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AGENTIC_EVAL_HARNESS |
| **Date** | 2026-09-11 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_AGENTIC_EVAL_HARNESS.md](../features/DEFINE_AGENTIC_EVAL_HARNESS.md) |
| **DESIGN** | [DESIGN_AGENTIC_EVAL_HARNESS.md](../features/DESIGN_AGENTIC_EVAL_HARNESS.md) |
| **Status** | Complete |

Branch `feat/eval-harness-agentico`, criado a partir do HEAD de `feat/coletor-resource-link`. Tudo está no índice do git (staged) e nada foi commitado.

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 8/8 da ordem B1–B8 (G9, que era COULD, foi adiado) |
| **Files Created** | `sparkforge/facts/host_transcript.py`; `sparkforge/evals/{suite,grade,compare,cli,__main__}.py`; `scripts/run_agentic_eval.py`; `evals/agentic/{mcp.json,fase0/suite.yaml,fase0/baselines/2026-09-11-haiku-4-5/}`; `fixtures/host_transcript/` (21 casos + `_suite/`); 5 arquivos de teste |
| **Tests Passing** | Suíte completa em lotes: 5 284 + 4 302 + 2 156 passaram (goldens-4/5 e g-z por arquivo, os demais por lote). Depois das mudanças finais, 1 297 afetados, de novo verdes |
| **Agents Used** | 0 delegados, tudo `(direct)` |
| **Custo de host** | Smoke B1: US$ 0,12. Execução descartada (sem workspace): cerca de US$ 0,81. Execução interrompida pelo defeito de encoding: 8 perguntas. Baseline: US$ 6,68 |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| B1 | Smoke de A-002 | (direct) | ✅ | `claude -p --session-id` persiste `~/.claude/projects/<slug>/<uuid>.jsonl`. Só a configuração global custou 120 122 tokens de `cache_creation` |
| B2 | Extrator, fixtures, normalização, registros de kind | (direct) | ✅ | |
| B3 | `suite`, `grade`, `compare`, goldens, invariantes | (direct) | ✅ | |
| B4 | CLI + registros | (direct) | ✅ | Refeita: ver Deviations 1 e 2 |
| B5 | Gabarito agêntico | (direct) | ✅ | `fase0.xml` com 0 linhas alteradas |
| B6 | Runner | (direct) | ✅ | Refeito por segurança e por validade da prova |
| B7 | Docs e gates | (direct) | ✅ | Lastro, números, surface lock: 0 divergências |
| B8 | Baseline Haiku 4.5, N = 3 | (direct) | ✅ | `evals/agentic/fase0/baselines/2026-09-11-haiku-4-5/` |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| (direct) | todos | Padrões do DESIGN e do codebase (`host_usage.py`, `benchmark.py`, goldens por domínio) |

---

## Files Created

| File | Verified | Notes |
| ---- | -------- | ----- |
| `sparkforge/facts/host_transcript.py` | ✅ | 5 kinds, 9 razões de lacuna; `source_location` sem caminho absoluto |
| `sparkforge/evals/suite.py` | ✅ | Hash da suíte resolvida; leitura de `fase0.xml` sem parser XML |
| `sparkforge/evals/grade.py` / `compare.py` | ✅ | Sem nota composta; `median_low`; 3 recusas nomeadas |
| `sparkforge/evals/cli.py` + `__main__.py` | ✅ | `python -m sparkforge.evals grade|compare`, só nomes sob bases fixas |
| `scripts/run_agentic_eval.py` | ✅ | Allowlists; workspace de prova; pontua sozinho; monta o conjunto de N scorecards |
| `evals/agentic/mcp.json`, `evals/agentic/fase0/suite.yaml` | ✅ | 10 perguntas por índice + 3 de abstenção |
| `fixtures/host_transcript/` | ✅ | 15 de transcript, 1 de run, 5 de compare, sem `findings.json` |
| `tests/test_fixtures_golden_host_transcript.py` (98), `test_evals_suite.py` (24), `test_evals_normalize.py` (16), `test_cli_eval.py` (14), `test_evals_invariants.py` (6) | ✅ | |

**Modificados:**
- `scripts/regen_fixtures.py`.
- `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`.
- `README.md`, `CLAUDE.md`, `evals/README.md`, `docs/superpowers/STATUS.md`.
- `docs/claims.lock.json` e as alegações movidas: VNX-357/358/469/640/673/674/675/726.

`sparkforge/adapters/_core.py`, `cli.py` e `tests/test_capability_parity.py` voltaram ao HEAD.

---

## Verification Results

### Lint Check

```text
ruff check sparkforge/ scripts/ tests/<novos>   ->  sem violações
```

**Status:** ✅ Pass

### Type Check

```text
N/A — o repositório não configura mypy
```

**Status:** ⏭️ Skipped

### Tests

```text
Lotes a-c 2142, d-e 286, f-sem-golden 1870, goldens-1..3 2160 -> passaram
goldens-4, goldens-5, g-z (um processo por arquivo): 5284 passaram, 3 falharam
  -> test_harness_boundary (runtime importava avaliacao) e test_status_numbers_gate (numeros publicados)
  -> corrigidos; 1297 testes afetados rodados de novo: passaram
check_evals.py 10/10 | check_vnext_claims 0 | check_status_numbers 0 | check_surface_lock 0
Snyk Code em sparkforge/evals e scripts/run_agentic_eval.py: 0 achados
```

**Status:** ✅ Pass (a suíte inteira precisou de dois recomeços por falta de memória do sistema, e o resto rodou um processo por arquivo)

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `Write` sobrescreveu `sparkforge/evals/__init__.py`, que já existia (o `EvaluationRunner` do router) | Restaurado com `git checkout` em seguida; os módulos novos convivem no pacote |
| 2 | `subject.type` é enum fechado | `source_location` |
| 3 | O scanner (hook de parada) acusou, em rodadas sucessivas, command injection e path traversal no runner e na CLI, e XML inseguro em `suite.py` | Desenho trocado, sem silenciar nada: nenhum valor livre do argv chega a `subprocess` nem a um caminho; leitura de XML sem parser; CLI só por nomes (escolha do operador). 14 achados prevenidos, feedback enviado |
| 4 | Âncora `glue.utilization.unresolved` sem verbo que a emita | Trocada por `plan.unresolved` |
| 5 | `test_evals_holdout` pegou o BRAINSTORM (em `.claude/`) citando o caminho do holdout | Frase reescrita |
| 6 | `test_codeintel_security`: dois `def acerto` no mesmo escopo viraram o mesmo nó | Funções de módulo com nomes distintos |
| 7 | `test_harness_boundary`: `_core.py` (runtime) importava `sparkforge.evals` (avaliação) | Verbo movido para `python -m sparkforge.evals`; adaptadores de volta ao HEAD |
| 8 | Primeira tentativa de baseline: 0 tools do SparkForge em 10 perguntas; o agente copiava `expected/findings.json` | Abortada. O runner passou a rodar numa cópia de prova sem gabarito, e o protocolo ganhou o separador `:` |
| 9 | Runner no Windows: `stdout` `None` diante de caractere fora do codepage | `encoding="utf-8", errors="replace"`; execução reiniciada do zero |
| 10 | Suíte morta duas vezes por falta de memória | Lotes pendentes rodados um processo por arquivo |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde trabalhar | branch atual / novo | `feat/eval-harness-agentico` | Não mistura com a entrega de resource link |
| 2 | Convivência com `sparkforge/evals/` | pacote novo / conviver | Conviver | O pacote já era de avaliação; é a fronteira que o gate protege |
| 3 | Defesa de XML | `defusedxml` no runtime / sem parser | Sem parser | Não mexe no lock |
| 4 | `required_tools` com alternativa | exigir todas / lista = qualquer uma | Lista | A pergunta 8 tem dois caminhos honestos |
| 5 | Igualdade da resposta | perdoar formatação / exata + protocolo | Exata; o protocolo diz o formato | Regra do `evals/README.md`: corrige-se o protocolo, não o grader |
| 6 | Transcript com dano parcial | `ungraded` / pontuar | Pontuar; `ungraded` só sem nenhuma mensagem de assistente | Linha ruim não apaga as boas |
| 7 | `findings.json` nas fixtures | vazio / ausente | Ausente | `host.*` não passa por `judge` |
| 8 | Fronteira runtime/avaliação | renomear o pacote / mover o verbo | Mover para `python -m sparkforge.evals` | Renomear escaparia do gate violando a intenção dele |
| 9 | Workspace de prova | só instruir o agente / tirar o gabarito | Tirar | A instrução não impediu a cópia; resposta disponível não mede capacidade |
| 10 | Execuções descartadas | publicar / descartar | Descartar e registrar | Não medem o que a suíte mede |
| 11 | G9 (COULD) | fazer / adiar | Adiar | Obrigaria a limpar os documentos SDD em `.claude/` |
| 12 | Números de `CLAUDE.md` (706,9×, 10,0×) | atualizar / deixar | Deixar | Fora de `audited_roots()` e já divergentes antes |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| 1. `sparkforge eval …` virou `python -m sparkforge.evals …` | `tests/test_harness_boundary.py` | Nenhum registro de paridade; `_core.py`/`cli.py` intocados |
| 2. A CLI recebe nomes (`--suite`, `--run`, `--baseline`, `--candidate`) sob bases fixas; `grade` grava dentro da execução; `compare` só imprime | Scanner de segurança + escolha do operador | Não aponta diretório arbitrário |
| 3. Runner sem `--suite`, `--out`, `--mcp-config`, `--claude`; ganhou workspace de prova, autopontuação e conjunto | Scanner + validade da prova | Suíte nova entra como constante |
| 4. `subject.type: source_location` | Enum do schema | Golden portável |
| 5. `abst-03` ancora em `plan.unresolved` | Sem verbo para `glue.utilization.unresolved` | — |
| 6. `suite.yaml` ganhou o separador `:` no protocolo; o hash mudou antes de qualquer baseline | Pergunta 1 respondida `SF-PY-005, 2` | O baseline publicado já usa o protocolo novo |
| 7. G9 não feito | Decision 11 | A suíte agêntica não é holdout |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001…AT-013 | ✅ | Goldens de `fixtures/host_transcript/` + `TestAdversarial` |
| AT-014 | ✅ | `test_scorecard_nao_soma_byte_com_token_nem_publica_nota` |
| AT-015…AT-019 | ✅ | Goldens `compare_*` + `test_cli_eval.py` |
| AT-020 | ✅ | `test_extracao_e_deterministica` |

**Success Criteria:**
- SC1–SC7 ✅.
- SC8 ✅: N = 3 × 13 = 39 transcripts, 100% pontuados, scorecards commitados.

---

## Performance Notes

| Metric | Actual |
|--------|--------|
| Golden do domínio | 98 testes em ~1,5 s |
| Baseline (Haiku 4.5, 39 sessões) | US$ 6,68; chamadas de tool com `median_low` 12–19 por execução |
| Resultado | Respostas `correct` 10/10/9 de 10; `abstained` 2/2/2 de 3; `tools_ok` 0/3/3 de 13. O agente responde lendo YAML e entradas, e não pelas tools |

---

## Data Quality Results (if applicable)

N/A.

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed (G9/COULD adiado, declarado)
- [x] All verification checks pass
- [x] All tests pass (os afetados foram rodados de novo depois das últimas mudanças)
- [x] No blocking issues
- [x] Acceptance tests verified (20/20)
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_AGENTIC_EVAL_HARNESS.md` (depois do commit, quando o operador autorizar).
