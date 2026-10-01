# BRAINSTORM: Stage → linha de codigo

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STAGE_CALLSITE_LOCATION |
| **Date** | 2026-09-11 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** continuacao direta do `report github` (PR #50). Ele recusa como `runtime` todo finding de execucao sem linha no repositorio. A ponte codigo-execucao ja extrai `spark.stage.callsite` do nome do stage no event log (`collect at /opt/spark/work/job.py:99`). A ideia: usar o callsite para dar linha no PR a findings de stage.

**Context Gathered:**
- Branch `feat/stage-callsite-location`, empilhado sobre `feat/sarif-github-check` (PR #50), porque depende de `sparkforge/reporting/locate.py`.
- Forma medida do fact (`fixtures/bridge/*/expected/facts.json`): `subject {type: stage, symbol: "collect at /opt/spark/work/job.py:99", stage_id}`, `measures.line` (so quando resolvido), `attrs {resolved, method, file: "job.py" (nome base), path: "/opt/spark/work/job.py"}` ou `{resolved: false, reason, file}`.
- **Medido no corpus em 2026-09-11 (o denominador):**
  - dos **28** findings com `subject.type = stage`, **0** seriam localizados: **27** tem callsite nao resolvido e **1** nao tem callsite;
  - dos 31 facts de callsite dos goldens, **16** sao `sem_forma_de_callsite` (nome sintetico, ex. `stage_skewed_join`), **15** sao `arquivo_nao_python` (ex. `save at Etl.scala:120`) e **3** estao resolvidos, todos em `fixtures/bridge/`, cujos findings ja tem linha;
  - dos **60** findings de `job_run`, 54 estao em casos sem nenhum callsite.
- Em event log real de PySpark o nome do stage costuma ter a forma `acao at caminho:linha`, entao o ganho existe fora do corpus. Aqui ele so aparece com fixtures novas.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/reporting/locate.py` (resolucao), `sparkforge/reporting/github.py` (mensagem), `fixtures/sarif/` (3 casos novos), `.github/workflows/ci.yml` (matriz do `sarif-upload`) | Nenhum extrator muda |
| Relevant KB Domains | Spark event log (stage name/callsite), testing (golden em pares), static analysis reporting (SARIF) | Padrao dos pares de `fixtures/bridge/` |
| IaC Patterns | GitHub Actions (`ci.yml`) | Um caso a mais na matriz |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 0 | Seguir com 0 de 28 localizaveis no corpus? | Seguir, com fixtures novas | A medida de sucesso vive nas fixtures; o 0/28 e publicado como denominador |
| 1 | Quais findings podem ganhar linha? | Os de `stage`, e `job_run`/`table` cuja evidencia cite um fact de stage | Busca por `stage_id` e artefato de origem |
| 2 | Como casar o arquivo do cluster com o repositorio? | Maior sufixo unico | Do sufixo mais longo ao mais curto; empate no mesmo nivel e `caminho_ambiguo` |
| 3 | Criterio de sucesso? | Pares positivo/negativo + mensagem honesta | O alerta diz que a linha e da ACAO que originou o stage, nao a causa |
| 4 | Amostras? | Derivar de `fixtures/bridge/` | Event log sintetico com callsite realista |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/bridge/*/input/eventlog.jsonl` + `job.py` | 3 | Formato do nome do stage com callsite Python |
| Output examples | `fixtures/sarif/{stage_python,stage_scala,stage_negativos}/expected/` (a criar) | 3 casos | Golden |
| Ground truth | Distribuicao medida dos callsites do corpus (16/15/3) | 31 facts | Denominador publicado |
| Related code | `sparkforge/reporting/locate.py`, `sparkforge/facts/event_log.py` (callsite), `sparkforge/facts/bridge.py` | — | O extrator nao muda |

**How samples will be used:**

- Os casos novos partem do event log de `fixtures/bridge/`, com um finding de stage acrescentado.
- O invariante do corpus passa a exigir que nenhum finding de stage saia como `runtime`.

---

## Approaches Explored

### Approach A: resolver no `locate.py`, so para o SARIF ⭐ Recommended

**Description:**
- Finding de `stage`, ou `job_run`/`table` com fact de stage na evidencia, procura na uniao o `spark.stage.callsite` do mesmo `stage_id` e do mesmo `provenance.artifact`.
- O arquivo e casado pelo maior sufixo unico do caminho do cluster contra as `--source-root`.
- Scala le a linha do `subject.symbol` por padrao estrito.
- As recusas ficam precisas (`callsite_sem_forma`, `callsite_ausente`, `callsite_nao_python`).
- A mensagem diz "linha da acao `<metodo>` que originou o stage N (nao e a causa)".

**Pros:**
- Pequeno: nenhum kind novo, nenhum extrator mexido.
- A recusa fica mais informativa mesmo quando nao localiza.

**Cons:**
- So o `report github` se beneficia.

**Why Recommended:** o sufixo so se resolve com as `--source-root`, que so o `report github` conhece. O corpus mostra que o ganho depende de nome de stage real, e nao de mais derivacao.

---

### Approach B: fact derivado na ponte (`bridge.stage_located`)

**Description:** o extrator `bridge` emite stage → arquivo:linha no `analyze`, e qualquer verbo o consome.

**Pros:**
- Reuso por outros verbos (regra 33).

**Cons:**
- A ponte roda com caminhos relativos ao `--path` de cada `analyze` e nao conhece as raizes do repositorio.
- Seria um kind novo, com os registros de extrator e os goldens da ponte refeitos, para um consumidor so.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-11 |
| **Reasoning** | A resolucao depende das raizes que so o `report github` recebe |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Busca por (`stage_id`, `provenance.artifact`) | Dois event logs na uniao colidem no `stage_id 0` | So `stage_id` |
| 2 | Maior sufixo unico do `attrs.path`, sem cair para o sufixo mais curto quando ha empate | Empate e ambiguidade, e nao licenca para chutar | So nome base; mapa `--cluster-root` declarado |
| 3 | Scala: a linha vem do `subject.symbol` por `^<metodo> at <arquivo>:<linha>$` | O extrator nao grava a linha de callsite nao-Python; mudar o extrator refaria goldens | Exigir fact com linha |
| 4 | A mensagem declara que a linha e da ACAO que originou o stage | Skew e spill nascem num join ou shuffle antes da acao; afirmar causa seria falso | Mensagem sem ressalva |
| 5 | `runtime` fica so para `job_run`/`table` sem evidencia de stage | Recusa precisa diz o que destravaria a localizacao | Manter `runtime` para tudo |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| "Stage dominante" de um `job_run` (o mais caro) | Heuristica, nao medida | Yes, com criterio medido |
| Mapa declarado `--cluster-root` | O sufixo unico resolve sem configuracao; o mapa entra se o sufixo gerar ambiguidade demais em repo real | Yes |
| Fact derivado na ponte (abordagem B) | Um consumidor so | Yes |

Entram no MVP: recusas precisas, `job_run` pela evidencia de stage, callsite Scala e nova rodada do `sarif-upload`.

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Forma (busca por stage e artefato, sufixo unico, Scala pelo symbol, recusas, mensagem) | ✅ | "Sim, segue" | No |
| Prova (3 casos em pares, invariante "nenhum stage sai `runtime`", 0/28 publicado, `sarif-upload` com `stage_python`) | ✅ | "Sim, escreve o BRAINSTORM" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O `report github` recusa como `runtime` todo finding de stage, mesmo quando o event log diz em que linha do job o stage nasceu. O revisor do PR nao ve na linha do diff o skew ou o spill que o event log mediu.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Revisor do PR de job PySpark | O finding de runtime aparece so no resumo, longe do codigo |
| Engenheiro de dados | Nao sabe qual acao do codigo gerou o stage problematico |

### Success Criteria (Draft)
- [ ] `stage_python`: finding de stage e `job_run` com evidencia de stage localizados em `jobs/lib/job.py:42`; dois event logs com `stage_id 0` nao se confundem.
- [ ] `stage_scala`: localizado em `src/Etl.scala:120`.
- [ ] `stage_negativos`: `callsite_sem_forma`, `callsite_ausente`, `callsite_nao_python` e `caminho_ambiguo`, um de cada.
- [ ] Mensagem com "linha da acao ... (nao e a causa)" no SARIF, no resumo e na anotacao.
- [ ] Corpus: nenhum finding de stage sai como `runtime`; o denominador (0 de 28 localizados) fica publicado no STATUS.
- [ ] `sarif-upload` com `stage_python`, aceito pelo GitHub.

### Constraints Identified
- Regra 20: a recusa ganha nome preciso.
- Nenhum extrator muda; o golden da ponte fica intacto.
- Caso real nunca entra em arquivo: fixtures sinteticas.

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Afirmar a causa do stage.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 9 (1 de continuidade, 4 de discovery, 1 de abordagem, 1 de YAGNI, 2 de validacao) |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_STAGE_CALLSITE_LOCATION.md`
