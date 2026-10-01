# DEFINE: Stage → linha de codigo

> O `report github` passa a localizar findings de stage, e os de `job_run`/`table` que citam um stage na evidencia, na linha da ACAO que originou o stage, lida do `spark.stage.callsite` do event log. Quando nao localiza, a recusa diz exatamente por que.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STAGE_CALLSITE_LOCATION |
| **Date** | 2026-09-11 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O `report github` recusa como `runtime` todo finding de stage, mesmo quando o event log registrou em que linha do job o stage nasceu (`collect at /opt/spark/work/jobs/lib/job.py:42`). O skew ou o spill medidos nunca aparecem na linha do diff. E a recusa generica nao diz o que falta para localizar: nome de stage sem callsite, callsite em Scala, ou arquivo que nao casa com o repositorio.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Revisor do PR de job PySpark | Revisa o diff | O finding de runtime fica so no resumo, longe do codigo que gerou o stage |
| Engenheiro de dados | Mantem o job | Nao sabe qual acao do codigo originou o stage problematico |
| Dono da plataforma | Opera o CI | Nao sabe por que um finding de runtime nao virou alerta; o `runtime` generico nao diz o que destravaria |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: um finding com `subject.type = stage`, ou um `job_run`/`table` cuja `evidence` cite um fact de stage, procura na uniao o `spark.stage.callsite` do mesmo `stage_id` e do mesmo `provenance.artifact` (lido do fact de stage da evidencia) |
| **MUST** | G2: sem artefato disponivel (finding de stage sem fact de stage na evidencia), usa o callsite do `stage_id` quando ele e unico na uniao; mais de um e recusa `callsite_ambiguo` |
| **MUST** | G3: callsite Python resolvido: `attrs.path` testado do sufixo mais longo ao mais curto contra as `--source-root`; o primeiro nivel que casa exatamente um arquivo vence; dois ou mais no mesmo nivel e `caminho_ambiguo`, sem cair para o sufixo mais curto; linha = `measures.line` |
| **MUST** | G4: recusas precisas no lugar do `runtime` para quem tem stage: `callsite_sem_forma`, `callsite_ausente`, `callsite_nao_python`, `callsite_ambiguo`, alem das ja existentes. `runtime` fica para `job_run`/`table` sem fact de stage na evidencia |
| **MUST** | G5: mensagem do resultado, do resumo e da anotacao acrescenta "linha da acao `<metodo>` que originou o stage `<id>` (nao e a causa)" |
| **MUST** | G6: nenhum extrator muda; os goldens de `fixtures/bridge/` e do event log ficam intactos |
| **SHOULD** | G7: callsite Scala (`arquivo_nao_python`): linha lida do `subject.symbol` por `^(\w+) at (.+):(\d+)$`; localiza se o arquivo existir sob as raizes (mesmo casamento por sufixo do nome); senao, `callsite_nao_python` |
| **SHOULD** | G8: `sarif-upload` ganha o caso `stage_python` na matriz e roda de novo por `workflow_dispatch` |

---

## Success Criteria

- [ ] SC1: `fixtures/sarif/stage_python`: o finding de stage e o `job_run` com evidencia de stage localizados em `jobs/lib/job.py:42`; com dois event logs na uniao, ambos com `stage_id 0`, cada finding pega o callsite do proprio artefato.
- [ ] SC2: `fixtures/sarif/stage_scala`: localizado em `src/Etl.scala:120`.
- [ ] SC3: `fixtures/sarif/stage_negativos`: exatamente uma recusa de cada, `callsite_sem_forma`, `callsite_ausente`, `callsite_nao_python`, `caminho_ambiguo` e `callsite_ambiguo`.
- [ ] SC4: o texto "(nao e a causa)" aparece em **100%** dos resultados SARIF localizados por callsite, nas anotacoes deles e nas linhas do resumo.
- [ ] SC5: no corpus de `fixtures/`, **0** findings com stage saem como `runtime`; os 28 findings de stage saem com motivo `callsite_*`, com a distribuicao medida publicada no STATUS (hoje 0 de 28 localizados).
- [ ] SC6: os 4 casos anteriores de `fixtures/sarif/` continuam byte a byte, e o invariante "nenhum finding some" continua verde.
- [ ] SC7: `sarif-upload` com `stage_python` aceito (`processing_status: complete`, `results_count` = resultados do SARIF).
- [ ] SC8: gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock`, `check_evals`, `ruff`) e suite por lotes verdes.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Stage com callsite Python | Finding de stage, callsite resolvido `.../jobs/lib/job.py:42`, `jobs/lib/job.py` no repo | `report github` | Resultado em `jobs/lib/job.py:42`, mensagem com "(nao e a causa)" |
| AT-002 | `job_run` pela evidencia | `job_run` cuja evidencia cita o fact do stage 3 | `report github` | Localizado pelo callsite do stage 3 |
| AT-003 | Dois event logs | Dois artefatos na uniao, cada um com `stage_id 0` e callsite em arquivo diferente | `report github` | Cada finding na linha do callsite do seu artefato |
| AT-004 | Sufixo ambiguo | `lib/job.py` em `a/` e em `b/`, caminho do cluster `.../lib/job.py` | `report github` | `caminho_ambiguo`, sem tentar so `job.py` |
| AT-005 | Nome sintetico | Stage `stage_skewed_join` (callsite `sem_forma_de_callsite`) | `report github` | `callsite_sem_forma` |
| AT-006 | Sem callsite | Stage sem fact de callsite na uniao | `report github` | `callsite_ausente` |
| AT-007 | Scala no repo | `save at Etl.scala:120`, `src/Etl.scala` sob as raizes | `report github` | Resultado em `src/Etl.scala:120` |
| AT-008 | Scala fora do repo | `save at Etl.scala:120`, sem `.scala` sob as raizes | `report github` | `callsite_nao_python` |
| AT-009 | Stage sem artefato e dois callsites | Finding de stage sem fact de stage na evidencia; dois callsites `stage_id 0` na uniao | `report github` | `callsite_ambiguo` |
| AT-010 | Corpus | Todos os goldens de `fixtures/` | Projecao | Nenhum finding de stage como `runtime`; SARIF + recusa = total |
| AT-011 | Regressao | Os 4 casos anteriores de `fixtures/sarif/` | Golden | Byte a byte iguais |
| AT-012 | Upload real | `workflow_dispatch` com `stage_python` | `upload-sarif` | `complete`, `results_count` igual |

---

## Out of Scope

- "Stage dominante" de um `job_run` sem evidencia de stage.
- Mapa declarado `--cluster-root`.
- Fact derivado na ponte (`bridge.stage_located`) e qualquer mudanca de extrator.
- Afirmar a CAUSA do stage: a linha e da acao, e o texto diz isso.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 20: recusa tem nome | Cada falha de localizacao tem motivo proprio |
| Technical | Fixtures sinteticas (caso real nunca entra em arquivo) | Os casos partem de `fixtures/bridge/` |
| Technical | O golden dos 4 casos anteriores nao pode mudar | O motivo `runtime` desses casos (`so_runtime`, `misto`) so muda se houver stage; o DESIGN confere |
| Technical | Regex estrito para Scala (regra 33 aplicada com ressalva: a derivacao fica na apresentacao, nao no motor) | Formato fora do padrao vira `callsite_sem_forma`, e nao palpite |
| Resource | Mais uma analise no Code Scanning deste repo, so no branch | `workflow_dispatch` |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/reporting/locate.py`, `sparkforge/reporting/github.py`, `fixtures/sarif/` (3 casos), `scripts/regen_fixtures.py` (so se os casos precisarem), `.github/workflows/ci.yml` | Branch empilhado sobre o PR #50 |
| **KB Domains** | Spark event log (stage name, callsite), testing (golden em pares), SARIF | — |
| **IaC Impact** | Modify existing (`ci.yml`, um item de matriz) | — |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | 27 dos 28 findings de stage do corpus citam um fact de stage com `provenance.artifact` na evidencia | Mais casos caem em G2 | [x] medido em 2026-09-11 |
| A-002 | O fact de callsite carrega o mesmo `provenance.artifact` do fact de stage do mesmo event log | A busca por artefato nao casaria; o DESIGN confere no extrator | [x] 34 de 34 pares do corpus |
| A-003 | O caminho do cluster em `attrs.path` usa `/` como separador | Precisaria normalizar `\` de cluster Windows | [x] 34 de 34 |
| A-004 | Os casos `so_runtime` e `misto` do golden atual nao tem findings de stage | Seus goldens mudariam de `runtime` para `callsite_*` | [x] nenhum cita stage na evidencia |
| A-005 | O GitHub aceita resultado num `.scala` como em `.py` | SC7 so cobre `.py`; Scala fica provado por golden e schema | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | O que o event log sabe e o PR nao mostra, com denominador medido |
| Users | 3 | Tres papeis, cada um com a dor ligada a uma saida |
| Goals | 3 | 8 metas com MoSCoW, cada uma ligada a SC ou AT |
| Success | 3 | Casos, recusas e contagens exatas |
| Scope | 2 | A-002 e A-004 ficam para o DESIGN conferir |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-002, A-003 e A-004 sao conferidas no inicio do DESIGN; A-005 fica declarada.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-11 | define-agent | Versao inicial, a partir de `BRAINSTORM_STAGE_CALLSITE_LOCATION.md` |

---

## Next Step

**Next:** `/ship .claude/sdd/features/DEFINE_STAGE_CALLSITE_LOCATION.md`
