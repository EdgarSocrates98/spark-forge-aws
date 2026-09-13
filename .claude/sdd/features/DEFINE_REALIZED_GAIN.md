# DEFINE: Realized Gain Ledger

> O ganho OBSERVADO entre runs medidos de um job Glue antes e depois de uma mudanca -- tempo, DPU-segundos e custo, com mediana, faixa e N por lado -- sem projetar economia nem atribuir causa.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REALIZED_GAIN |
| **Date** | 2026-09-13 |
| **Author** | define-agent |
| **Status** | ✅ Complete (Built) |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Depois de aplicar uma mudanca num job Glue, o operador compara runs a mao, sem N, sem faixa e sem saber se o volume era o mesmo -- e o SparkForge, que recusa estimar ganho (regra 13), tambem nao publica o ganho que JA foi observado nos runs que aconteceram.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro de dados que aplicou a mudanca | Quer saber o que mudou nos runs seguintes | Compara medias a mao, e um run lento distorce |
| Responsavel por custo da plataforma | Aprova ou reverte mudancas por custo | Recebe "melhorou X%" sem N nem volume comparavel |
| Agente host via MCP | Fecha o ciclo de uma recomendacao | Nao tem verbo para o depois observado |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/finops/realized.py`: `realized_gain(baseline, candidate, declared)`; cada lado e uma lista de conjuntos de facts, um por arquivo |
| **MUST** | G2: run = cada `glue.job_run` com `state` `SUCCEEDED`; os outros saem em `discarded` com a contagem por motivo (`run_nao_sucedido`); `job_name` diferente entre os lados, ou lado sem nenhum run valido, sai com codigo 2 |
| **MUST** | G3: por lado e por metrica (`execution_time_s`, `dpu_seconds`, `cost`): N, mediana, minimo, maximo; delta = mediana do candidato menos a do baseline, em valor e em % do baseline |
| **MUST** | G4: custo pelo `glue.run_cost` do mesmo `job_run_id`; run sem custo, ou moedas diferentes entre os runs, marca `custo_indisponivel` na metrica `cost` (regra 14) |
| **MUST** | G5: volume de um run = soma de `bytes_read` dos `spark.sql.scan` do arquivo, SO quando o arquivo tem um run; medianas de volume dos dois lados alem da tolerancia -> `volume_diverge`; sem volume em algum lado -> `volume_desconhecido`; tolerancia de `workload.declared` (`volume_tolerance`) nos arquivos, senao a do capacity (0,25) |
| **MUST** | G6: menos de 3 runs num lado -> `amostra_insuficiente`; as marcas acompanham o delta e nunca o escondem |
| **MUST** | G7: `refused` fixo com `economia_mensal`, `atribuicao_causal`, `intervalo_de_confianca` |
| **MUST** | G8: CLI `sparkforge gain --baseline <facts> [--baseline ...] --candidate <facts> [--candidate ...]` e tool `sparkforge_gain` READ_ONLY com `baseline_paths` e `candidate_paths` |
| **SHOULD** | G9: a capacidade de cada lado (versao, worker, workers, autoscaling) sai como informacao |
| **COULD** | G10: `docs/realized-gain.md` com a saida, as marcas e as recusas |

---

## Success Criteria

- [ ] SC1: com baseline e candidato recortados de `fixtures/capacity/cheapest_that_fits` (30 runs, uma capacidade por lado), N, mediana, minimo, maximo e o delta batem com a conta feita a mao sobre os mesmos numeros.
- [ ] SC2: cada marca (`amostra_insuficiente`, `volume_diverge`, `volume_desconhecido`, `custo_indisponivel`) tem um caso de fixture e aparece so na metrica que ela afeta.
- [ ] SC3: `refused` traz sempre os tres itens de G7, em todos os casos.
- [ ] SC4: jobs diferentes e lado sem run valido saem com codigo 2; run nao `SUCCEEDED` sai em `discarded`.
- [ ] SC5: tool nova validada por amostra real; registros de tool nova (declara caminho: 86 -> 87); surface lock com o crescimento declarado; claims por lista de ids; suite por lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Ganho observado | 3+ runs de uma capacidade no baseline e 3+ de outra no candidato, volume dentro da tolerancia | `sparkforge gain` | N, mediana, min, max por lado e o delta das medianas, sem marca |
| AT-002 | Amostra insuficiente | candidato com 2 runs | `gain` | delta presente, marcado `amostra_insuficiente` |
| AT-003 | Jobs diferentes | baseline de um job, candidato de outro | `gain` | codigo 2 nomeando os dois jobs |
| AT-004 | Run que falhou | um run `FAILED` no candidato | `gain` | fora da conta, em `discarded.run_nao_sucedido` |
| AT-005 | Volume diverge | medianas de `bytes_read` alem de 25% | `gain` | delta marcado `volume_diverge` |
| AT-006 | Volume desconhecido | arquivo com varios runs, ou sem `spark.sql.scan` | `gain` | delta marcado `volume_desconhecido` |
| AT-007 | Custo | runs com `glue.run_cost` pelo `job_run_id` | `gain` | metrica `cost` com mediana e delta na moeda |
| AT-008 | Sem custo | run sem `glue.run_cost` (ou moeda diferente) | `gain` | `cost` marcado `custo_indisponivel`; tempo e DPU seguem |
| AT-009 | Recusas | qualquer caso | `gain` | `refused` com os tres itens |
| AT-010 | Tolerancia declarada | `workload.declared` com `volume_tolerance: 0.5` | `gain` com volume 40% maior | sem `volume_diverge` |
| AT-011 | Lado vazio | nenhum run `SUCCEEDED` num lado | `gain` | codigo 2 |

---

## Out of Scope

- Custo de S3, CPU, memoria, tokens, custo de modelo, tool calls, tempo humano.
- Economia mensal, intervalo de confianca, normalizacao por volume (s/GB, $/GB).
- Coletar os runs (o operador usa `collect glue-job-runs` e `analyze glue-job-runs`).
- Derivar custo que o arquivo nao traz.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regras 12, 13, 14, 22 a 25, 30 | Nada de projecao, atribuicao, custo sem DPU, ou token somado a byte |
| Technical | Volume so e ligavel a um run quando o arquivo tem um run (medido: o historico do capacity e um arquivo por run; o `analyze glue-job-runs` gera um arquivo com varios) | Arquivo com varios runs e aceito, e o volume dele sai desconhecido |
| Technical | Tool nova move os registros manuais | Tools 94 -> 95; READ_ONLY 62 -> 63; as que declaram caminho 86 -> 87 |
| Technical | `.claude/` e diretorio de plataforma | Documentos SDD sem chave de metadado de regra escrita com dois-pontos |
| Technical | INV-009 | Nenhum parametro de tool com `url` no nome |
| Resource | Repo publico | Fixtures sinteticos |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/finops/realized.py` (novo), `sparkforge/adapters/{_core,cli,tools}.py`, `fixtures/gain/`, `docs/realized-gain.md` | Ao lado do relatorio financeiro |
| **KB Domains** | Nenhum dominio do KB do agentspec cobre FinOps de Glue | Padroes: `capacity/plan.py` (`_volume_de`, descarte, tolerancia), `facts/run_cost.py`, `finops/report.py` |
| **IaC Impact** | None | — |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `glue.run_cost` tem o mesmo `job_run_id` do `glue.job_run` (medido: os dois subjects tem `job_name`, `job_run_id`, `symbol`, `type`) | Pareamento por outro campo | [x] |
| A-002 | Os runs de `fixtures/capacity/*/input/history/` separam capacidades distintas o bastante para recortar baseline e candidato | Casos novos precisariam ser escritos do zero | [x] |
| A-003 | `_volume_de` do capacity pode ser importado ou movido para um lugar comum sem mudar o capacity | Duplicacao do calculo de volume | [x] |
| A-004 | Os estados de run possiveis sao os da API do Glue (`SUCCEEDED`, `FAILED`, `TIMEOUT`, `STOPPED`, ...) e todos os fixtures atuais sao `SUCCEEDED` (medido) | O caso de run que falhou exige fixture nova | [x] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Recusa de estimar existe; o observado nao e publicado |
| Users | 3 | Tres personas |
| Goals | 3 | Metricas, marcas e recusas nomeadas |
| Success | 3 | Casos com fixture nomeada e conta conferivel |
| Scope | 2 | Fora de escopo explicito; o formato exato da saida fica para o design |
| **Total** | **14/15** | |

---

## Open Questions

Nenhuma que bloqueie o design. Ficam para ele: o dono da tool (coordenador que ja cita `sparkforge_finops`), o formato exato da saida e onde `_volume_de` passa a morar.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-13 | define-agent | Versao inicial, a partir de `BRAINSTORM_REALIZED_GAIN.md`. Refinado pela medida: arquivo com varios runs e aceito (o `analyze glue-job-runs` gera assim), e o volume so e conhecido em arquivo de um run; custo pareado por `job_run_id` |
| 1.1 | 2026-09-13 | design-agent | A-002 e A-003 confirmadas no design; dono `sf-verifier` |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_REALIZED_GAIN.md`
