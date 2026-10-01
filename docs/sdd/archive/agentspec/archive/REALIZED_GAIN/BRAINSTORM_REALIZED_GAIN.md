# BRAINSTORM: Realized Gain Ledger

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REALIZED_GAIN |
| **Date** | 2026-09-13 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** §21 de `prompt_new_evo.md`, "O FinOps deveria fechar o ciclo": manter a recusa de inventar `expected_gain` e acrescentar o **Realized Gain Ledger** -- `baseline_run` contra `candidate_run`, medindo wall clock, custo de compute, S3, shuffle, CPU, memoria, tokens, custo de modelo, tool calls e tempo humano, e publicando "Observed improvement: 17.4%", "Observed monthly savings: $...", intervalo de confianca e N. "Mudamos, medimos e foi isso que aconteceu."

**Context Gathered:**
- `glue.job_run` carrega por run `execution_time_s`, `dpu_seconds` (com `dpu_source`), `state`, `started_on`/`completed_on`, `worker_type`, `number_of_workers`, `autoscaling`, `glue_version`, `execution_class`. `glue.run_cost` carrega `cost`, `currency`, `dpu_hours`, `price_per_dpu_hour` e a fonte do preco.
- Nenhum desses fatos carrega volume lido. O `capacity` (`sparkforge/capacity/plan.py`) ja resolve isso: volume de um run e a soma de `bytes_read` dos `spark.sql.scan` do arquivo daquele run; o historico e UM ARQUIVO POR RUN; a tolerancia vem de `workload.declared` (`volume_tolerance`, padrao 0,25); run sem scan sai como `volume_unknown`.
- Os fixtures de `capacity` e `finops` tem de 3 a 30 runs por job.
- Regras que limitam o recorte: 12 (nunca interpolar entre capacidades), 13 (nunca estimar economia: exige o custo do run que nao aconteceu), 14 (sem `dpu_seconds` nao ha custo), 22 a 25 (byte e token nao se somam; token e dolar so com fonte), 30 (sem benchmark da camada agentica).
- `benchmark` compara dois event logs por tempo de task (nao e relogio); o Change Proof ja recusa atribuicao com mais de uma mudanca.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/finops/realized.py` (novo), `adapters/{_core,cli,tools}.py`, `fixtures/gain/` | Ao lado do relatorio financeiro; reusa `_volume_de` do capacity |
| Relevant KB Domains | Nenhum dominio do KB do agentspec cobre FinOps de Glue; a fonte e o proprio repositorio | Padroes: `capacity/plan.py`, `facts/run_cost.py`, `finops/report.py` |
| IaC Patterns | N/A | Nada de infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Qual o recorte? (ledger de runs medidos / eixo no proof / lista completa do §21) | **Ledger de runs medidos**: N runs de baseline contra N candidatos do mesmo job | Tempo, DPU-segundos e custo por run; economia mensal e atribuicao recusadas |
| 2 | Como se diz o que e baseline e candidato? (dois arquivos / historico + data / ids) | **Dois conjuntos de arquivos**, `--baseline` e `--candidate` repetiveis, um arquivo por run | Molde do `benchmark --before/--after` e do `--history` do capacity |
| 3 | O que se publica sobre as amostras? (mediana e faixa / bootstrap / media) | **Mediana, minimo, maximo e N** por lado; `amostra_insuficiente` com menos de 3 runs | Sem intervalo de confianca parametrico |
| 4 | Que amostra ancora os testes? (fixtures / runs reais / casos novos) | **Historicos dos fixtures** de `capacity` e `finops`, recortados, mais casos novos para as marcas | Repo publico: nada real |
| 5 | Como tratar volume diferente? (criterio do capacity / normalizar / ignorar) | **Criterio do capacity**: medianas de volume alem da tolerancia -> `volume_diverge`; sem scan -> `volume_desconhecido` | Normalizar por GB supoe tempo linear no volume (regra 12) |
| 6 | Qual abordagem? (A verbo `gain` / B modo do `finops`) | **A** | Verbo de topo proprio; `finops` continua com uma forma de saida |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/capacity/*/`, `fixtures/finops/*/` | 3 a 30 runs por job | `glue.job_run` e `glue.run_cost` sinteticos |
| Output examples | `finops`/`capacity` (saidas atuais) | 2 | Forma de recusa e descarte (`history_file_not_one_run`, `volume_unknown`) |
| Ground truth | Casos novos com mediana calculavel a mao | a criar | Delta conferido por conta simples |
| Related code | `capacity/plan.py::_volume_de`, `facts/run_cost.py`, `finops/report.py` | 3 | Volume por run, custo por run, recusas |

**How samples will be used:**

- Recortar historicos existentes em baseline e candidato por capacidade.
- Casos novos: amostra insuficiente, jobs diferentes, run sem DPU, moeda diferente, volume divergente, run que falhou.

---

## Approaches Explored

### Approach A: Verbo `gain` ⭐ Recommended

**Description:** Modulo puro `sparkforge/finops/realized.py` com `realized_gain(baseline, candidate, declared)`; verbo de topo `sparkforge gain --baseline <run.json>... --candidate <run.json>...`; tool `sparkforge_gain` READ_ONLY que declara caminho.

**Pros:**
- Uma pergunta por verbo, como `capacity`, `finops` e `benchmark`.
- Reusa o criterio de volume e o formato de descarte do capacity.

**Cons:**
- Mais uma tool na superficie.

**Why Recommended:** e o molde de todo verbo de topo do projeto, e cada peca tem precedente medido.

---

### Approach B: Modo do `finops`

**Description:** `sparkforge finops --baseline --candidate`, sem verbo novo.

**Pros:**
- Nenhuma tool nova.

**Cons:**
- O `finops` passa a ter duas formas de saida e responde duas perguntas diferentes.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-13, nesta sessao |
| **Reasoning** | Uma pergunta por verbo; precedentes medidos para volume, descarte e custo |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Um arquivo por run, e so runs bem-sucedidos entram | E como o scan fica ligado ao run certo (precedente do capacity); run que falhou distorce o tempo | Arquivo com varios runs |
| 2 | `job_name` diferente entre os lados e erro com codigo 2 | Comparar jobs diferentes nao e ganho de nada | Aviso |
| 3 | Delta das medianas, em valor e em %, por metrica | Mediana resiste a um run lento | Media |
| 4 | Quatro marcas no delta, que mostram sem chamar de ganho: `amostra_insuficiente`, `volume_diverge`, `volume_desconhecido`, `custo_indisponivel` | Regra 20: dizer por que o numero nao fecha | Esconder o delta |
| 5 | Tres recusas fixas: `economia_mensal`, `atribuicao_causal`, `intervalo_de_confianca` | Regras 12 e 13; sem run de controle nao ha atribuicao | Publicar projecao |
| 6 | Capacidade de cada lado sai como informacao | A mudanca de capacidade costuma ser a propria mudanca | Marcar como problema |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Custo de S3, CPU, memoria | Nao ha fato por run no `glue.job_run`; utilizacao do CloudWatch e outra leitura | Yes |
| Tokens, custo de modelo, tool calls | Moram no `economy report` (regras 22 a 25) | No (outro verbo) |
| Tempo humano | Nenhuma fonte no pacote | No |
| Economia mensal | Projecao sobre runs que nao aconteceram (regras 12 e 13) | No |
| Intervalo de confianca | N pequeno; mediana e faixa no lugar | Yes, com N grande |
| Coletar os runs sozinho | O operador coleta com `collect glue-job-runs` | Yes |
| Normalizar por volume (s/GB, $/GB) | Supoe tempo linear no volume (regra 12) | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura: modulo puro, um run por arquivo, mediana/faixa/N, marcas, recusas, verbo e tool | ✅ | "Sim, segue" | No |
| Corte: fora da frente | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Depois de uma mudanca num job Glue, o operador nao tem como dizer, com os runs que ja aconteceram, quanto o tempo, os DPU-segundos e o custo mudaram -- e o SparkForge recusa estimar ganho, mas nao publica o ganho OBSERVADO.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Engenheiro de dados que aplicou uma mudanca | Compara runs a mao, sem saber se o volume era o mesmo |
| Responsavel por custo da plataforma | Recebe "melhorou X%" sem N nem faixa |
| Agente host via MCP | Nao tem verbo para "o que mudou depois da mudanca" |

### Success Criteria (Draft)
- [ ] Com baseline e candidato de fixture, o verbo publica N, mediana, minimo e maximo por lado e o delta das medianas, conferiveis por conta simples.
- [ ] Cada uma das quatro marcas tem caso de fixture e aparece no delta afetado.
- [ ] `refused` traz sempre `economia_mensal`, `atribuicao_causal` e `intervalo_de_confianca`.
- [ ] Jobs diferentes entre os lados saem com codigo 2.

### Constraints Identified
- Regras 12, 13, 14, 22 a 25 e 30.
- Um arquivo por run.
- Tool nova move os registros manuais (declara caminho: 86 -> 87).

### Out of Scope (Confirmed)
- S3, CPU, memoria, tokens, custo de modelo, tool calls, tempo humano.
- Economia mensal, intervalo de confianca, normalizacao por volume, coleta automatica.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 6 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_REALIZED_GAIN.md`
