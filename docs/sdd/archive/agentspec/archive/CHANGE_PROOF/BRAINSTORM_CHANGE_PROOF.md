# BRAINSTORM: Change Proof

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHANGE_PROOF |
| **Date** | 2026-09-12 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Complete (Defined) |

---

## Initial Idea

**Raw Input:** Frente §20 de `prompt_new_evo.md`, "Change Proof". Cada alteracao recomendada viria com obrigacoes de prova -- "Proof of Correctness", "Proof of Safety", "Proof of Improvement" quando mensuravel -- e, se nao for possivel provar, `UNPROVEN`. Branch `feat/change-proof`, a partir da `main` (ja com #54; o ship da frente 8 esta no PR #55).

**Context Gathered:**
- **O que ja existe:**
  - Toda regra com recomendacao carrega `action` (`kind`, `target`, `direction`, `moves`), `risks`, `tradeoffs`, `validation` e `rollback`, e esses campos viajam ate o `Finding` (`findings/models.py:83-91`).
  - `action.moves` e vocabulario fechado de **23 eixos** (o mais usado e `correctness.write_result`, em 42 regras).
  - Dois comparadores ja emitem facts de antes e depois, e ja tem regras de veredito:
    - `funcval compare` emite `funcval.check_delta`/`funcval.analyzed`, julgados por `SF-FVAL-001` a `004` (contagem, schema, chave duplicada, agregado fora da tolerancia) e `SF-FVAL-005` (validacao parcial).
    - `benchmark` emite `bench.run_delta`/`bench.stage_delta` sobre cinco medidas (`total_task_ms`, `total_input_bytes`, `total_spill_bytes`, `total_gc_ms`, `total_task_count`), julgados por `SF-BENCH-002` (piorou) e `003` (ganho com mais spill ou GC); `SF-BENCH-001` (volumes diferentes) e `004` (stages nao casados) invalidam a comparacao. O `bench.run_delta` ja omite o percentual quando a medida some de um lado.
  - `root_cause` roda o `judge` por dentro e recebe findings e `skipped` com os kinds que faltam (`run_judge(..., return_skipped=True)`, `adapters/_core.py:3363`).
  - O `sf-verifier` "tenta REFUTAR cada achado": e a mesma semantica aplicada a mudanca.
  - O loader do catalogo so pega regra da chave `rules:`; um YAML sem ela convive em `rules/catalog/` (como `action_kinds.yaml`) e vai para o wheel pelo `force-include`.
- **O que nao existe:**
  - Nada liga a `validation` de uma regra a um fact que a prove: os 479 itens de `validation` sao prosa.
  - Nenhum verbo diz, depois de aplicada uma recomendacao, se ela quebrou o resultado, se piorou o que ela deveria melhorar, ou se o problema sumiu.
- **Medido em 2026-09-12:**
  - 190 regras; 155 com `action`/`validation`, 154 com `rollback`.
  - Dos 479 itens de `validation`: 161 citam contagem, 52 chave, 40 agregado, 30 schema (o que `funcval` mede); 32 event log/stage, 24 tempo, 19 custo.
  - Das 155 regras com `action`: **61** tem algum eixo que `funcval` ou `bench` ja medem; **43** tem eixos sem comparador nenhum (`dependency.delivered_artifacts` 8, `observability.diagnostic_artifacts` 7, `cost.provisioned_capacity_time` 6, `storage.file_layout` 6...); **51** nao declaram eixo (38 delas sao `direction: investigate`).
  - `runtime.wall_clock` nao tem medida direta: o bench compara tempo de task SOMADO, que e proxy e nao relogio.
  - Forma dos `subject` nos goldens: `line`, `col`, `end_line`, `snippet` (71 findings de `source_location`), `stage_id`, `job_run_id` e `event` mudam entre antes e depois sem que nada tenha sido resolvido; em `job_run` o proprio `symbol` as vezes e o id do run.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/proof/` (modulo puro); `rules/catalog/proof_axes.yaml` (mapa eixo -> fonte, chave estavel por tipo de subject); `adapters/_core.py`, `cli.py`, `tools.py`; `agents/executors/sf-verifier.md`; `fixtures/proof/` | Verbo de topo: compoe sobre findings e facts, julga no processo, nao le artefato de job |
| Relevant KB Domains | Validacao funcional (`funcval`), benchmark (`bench.*`), motor de regras (`judge`, `skipped`) | Reusa os veredictos que ja existem |
| IaC Patterns | Nenhum | So codigo e registros manuais |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | De onde sai a obrigacao de prova? | Dos eixos de `action.moves` | Um YAML mapeia cada um dos 23 eixos para a fonte que o mede; os 479 itens de prosa ficam como explicacao |
| 2 | Que desfechos existem? | `refuted`, `not_refuted`, `inconclusive`, `unproven` | Nunca "provado": proxy de funcval e delta de bench nao provam equivalencia |
| 3 | Onde aparece? | Verbo de topo `proof`, tool READ_ONLY | No molde de `arbitrate`/`root_cause`; o recibo cita depois, sem acoplar agora |
| 4 | Obrigacao de resolucao? | Sim | A regra que recomendou deixa de disparar na mesma chave estavel, julgada sobre o depois; cobre as 155 regras |
| 5 | Atribuicao com varias mudancas? | O operador declara `--applied` | Com mais de uma, melhoria sai `inconclusive` (`attribution_shared`); correcao e resolucao seguem por finding |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/pyspark/collect_unbounded` | 1 | Antes que dispara `SF-PY-002`; o depois corrigido e montado a partir dele |
| Input files | `fixtures/bench/` | 7 | `clean_improvement`, `regression_slower`, `different_input_volume`, `most_stages_renamed`, `faster_but_spilling`, `one_side_missing`, `migracao_entre_runtimes` |
| Input files | `fixtures/funcval/` | 10 | `clean_equivalence`, `count_diverged`, `schema_diverged`, `duplicate_key_appeared`, `partial_coverage`... |
| Output examples | `fixtures/proof/*/expected/result.json` | ~8 casos | Um por desfecho e por fonte |
| Ground truth | Regras `SF-FVAL-*` e `SF-BENCH-*` | 9 | Os veredictos que a prova le, sem reimplementar |

**How samples will be used:**

- Os pares de `bench/` e `funcval/` dao o desfecho de eixo sem inventar numero: o `judge` sobre eles ja produz os veredictos.
- A resolucao usa um antes real (`collect_unbounded`) e tres depois montados: corrigido, ainda com `collect()` e sem os facts de PySpark.
- Nenhum caso real entra em arquivo.

---

## Approaches Explored

### Approach A: so compoe ⭐ Recommended

**Description:** resolucao para os findings de `--applied`, julgando `--after-facts` no processo. Obrigacao por eixo pelo mapa `proof_axes.yaml`: correcao pelos veredictos `SF-FVAL`, melhoria por `bench` e `SF-BENCH`. Os eixos sem comparador saem `unproven` com a medida que os destravaria. Nenhum comparador novo.

**Pros:**
- Reusa os dois comparadores e as nove regras de veredito que ja existem e tem golden.
- Toda regra ganha ao menos uma obrigacao avaliavel (a resolucao).
- Os 43 eixos sem fonte viram uma lista nomeada do que falta construir.

**Cons:**
- 43 regras ficam com eixo `unproven` ate existir comparador para ele.

**Why Recommended:** e o menor passo que da desfecho real sem inventar medida, e deixa a lacuna escrita. Confianca 0,85.

---

### Approach B: A + comparador generico

**Description:** tudo de A, mais um comparador antes/depois para kinds de run unico (`glue.run_cost`, contagem de snapshots e delete files, layout do S3) com `--before-facts`.

**Pros:**
- Cobre parte dos 43 eixos.

**Cons:**
- Motor de diff novo.
- Custo antes/depois esbarra nas regras 12 e 13.

**Why not:** escopo grande e risco de estimar ganho por tras de um delta.

---

### Approach C: so lista obrigacoes

**Description:** deriva e lista as obrigacoes e os facts que as provariam, sem avaliar desfecho.

**Pros:**
- Barato, util para planejar.

**Cons:**
- Nunca diz `refuted` nem `not_refuted`.

**Why not:** nao responde a pergunta do §20.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-12 |
| **Reasoning** | Desfecho real sobre veredictos que ja existem, lacuna nomeada, nenhum comparador novo |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Obrigacao derivada de `action.moves` por um mapa versionado `rules/catalog/proof_axes.yaml` (sem chave `rules:`) | Vocabulario fechado de 23 eixos; nao reescreve o catalogo | Anotar os 479 itens de `validation`; tres provas fixas |
| 2 | Quatro desfechos: `refuted`, `not_refuted`, `inconclusive`, `unproven`; nunca `proven` | Proxy de funcval nao prova equivalencia (o `sf-synthesizer` ja proibe "resultado identico"); delta nao prova melhoria atribuivel | `proven` como no §20; `proven` so para medida exata |
| 3 | Verbo de topo `sparkforge proof` e tool `sparkforge_proof` READ_ONLY | Compoe sobre findings e facts, como `arbitrate` e `root_cause` | Dentro do recibo; campo no `Finding` |
| 4 | Obrigacao de resolucao para todo finding aplicado, julgando `--after-facts` no processo com `run_judge(..., return_skipped=True)` | A diferenca entre "resolvida" e "muda por falta de artefato" so aparece no `skipped`; um arquivo de findings do depois nao a carrega | `--after-findings` |
| 5 | Resolucao: dispara de novo na mesma chave -> `refuted`; regra em `skipped` -> `unproven` com os kinds que faltam; avaliada e nao disparou -> `not_refuted` | Ausencia so vale se a regra podia disparar | Tratar ausencia como resolucao |
| 6 | Chave estavel declarada por tipo de subject no mesmo YAML: `source_location` -> `(file, symbol)`; `tf_resource`, `stage`, `table`, `plan_node` -> `symbol`; `job_run` -> `job_name` quando existe; tipo sem chave -> resolucao `inconclusive` (`subject_sem_chave_estavel`) | `line`, `col`, `snippet`, `stage_id`, `job_run_id` e `event` mudam sem que nada seja resolvido | Comparar o `subject` inteiro |
| 7 | Correcao (`correctness.*`): `SF-FVAL-001..004` disparado -> `refuted`; `SF-FVAL-005` -> `inconclusive`; sem `funcval.analyzed` -> `unproven` | Os veredictos ja existem e tem golden | Reavaliar os deltas dentro da prova |
| 8 | Melhoria (`scan.bytes_read`, `shuffle.spill_bytes`, `scan.task_count`): delta na direcao declarada -> `not_refuted`; contra, ou `SF-BENCH-002` -> `refuted`; `SF-BENCH-001`/`004` ou percentual omitido -> `inconclusive` | Direcao ja declarada na `action` | Limiar proprio de melhoria |
| 9 | `runtime.wall_clock` usa `bench.total_task_ms` com `proxy: task_ms_nao_e_wall_clock` | O bench soma tempo de task, nao mede relogio | Tratar como medida direta |
| 10 | `--applied` declarado pelo operador; com mais de um, obrigacoes de bench -> `inconclusive` (`attribution_shared`) | Separar o delta entre mudancas exige o run que nao aconteceu (regra 13) | Toda recomendacao do case; uma mudanca por vez |
| 11 | Eixo sem comparador -> `unproven` com a medida que o destravaria, declarada no mapa | Regra 20: lacuna com nome | Omitir a obrigacao |
| 12 | `refused` fixo com `proven` e `gain_estimate`; nenhum valor medido copiado alem do delta de bench como veio | Regras 13 e 30 | — |
| 13 | Dono: `sf-verifier`, checagem 7 ("a mudanca aplicada se sustentou?"); `parity.yaml` ganha "prove what an applied change did and did not break" | O verificador ja tenta refutar | `sf-synthesizer` |
| 14 | Teste do mapa: todo eixo usado em `moves` tem entrada, e toda fonte aponta para kind que existe em `EMITTED_KINDS` | O mapa nao pode envelhecer calado quando um eixo novo entra | Lista sem teste |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| "Proof of Correctness/Safety/Improvement" como `proven` | Nenhuma medida do pacote prova equivalencia ou melhoria atribuivel | No, com as medidas de hoje |
| Apply in Sandbox e as etapas de execucao do §20 | E autonomia L2 (§15); a prova le o depois que o operador produziu | Yes, com a frente §15 |
| Security Validation e Cost Validation como etapas proprias | Seguranca entra pela resolucao (a regra de segredo deixa de disparar); custo antes/depois esbarra nas regras 12 e 13 | Yes, custo com comparador proprio |
| Comparador generico antes/depois (abordagem B) | Motor de diff novo | Yes |
| Estimativa de ganho | Regra 13 | No |
| Acoplar ao recibo | Mistura proveniencia com julgamento; o recibo pode citar o resultado depois | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| 1: obrigacoes, desfechos, chave estavel, V1 a V4 | ✅ | "Sim, segue" | No |
| 2: saida, superficie, dono, registros, fixtures, fora do escopo | ✅ | "Sim, escreve o documento" | No |

**Invariantes aprovados:**
- V1: nunca `proven`; os quatro desfechos sao os unicos.
- V2: nenhum ganho estimado; o delta de bench e repassado como medido, com a direcao.
- V3: toda obrigacao `unproven` diz a medida que a destravaria.
- V4: finding fora de `--applied` fica fora da prova.

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O SparkForge recomenda mudancas com `validation` e `rollback` escritos em prosa -- 479 itens em 155 regras --, e nenhum verbo diz, depois que o operador aplicou uma delas, se o resultado continuou o mesmo, se o que ela deveria melhorar piorou ou se o problema sumiu. Os comparadores que responderiam (`funcval`, `benchmark`) e as nove regras de veredito ja existem, mas nada os liga a recomendacao que motivou a mudanca.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Engenheiro que aplicou a recomendacao | Nao tem como saber, com o que ja mediu, se a mudanca quebrou o resultado ou nao resolveu nada |
| Revisor do PR da mudanca | Recebe "funcionou" sem saber qual obrigacao foi medida e qual ficou sem medida |
| `sf-verifier` | Tenta refutar achados, mas nao tem como refutar uma mudanca aplicada |

### Success Criteria (Draft)
- [ ] Um caso golden por desfecho e por fonte em `fixtures/proof/`: resolucao `not_refuted`, `refuted` e `unproven`; correcao `refuted` e `inconclusive`; melhoria `not_refuted`, `refuted` e `inconclusive`; `attribution_shared`.
- [ ] Nenhuma saida contem `proven`; toda obrigacao `unproven` nomeia a medida.
- [ ] Mudar so `line`/`snippet`/`stage_id`/`job_run_id` do subject nao muda o desfecho da resolucao.
- [ ] O teste do mapa cobre os 23 eixos de `moves` e toda fonte existe em `EMITTED_KINDS`.
- [ ] A tool valida contra o proprio schema com amostra real; registros, surface lock (crescimento declarado) e claims por lista de ids.
- [ ] Gates e suite por lotes com 0 falhas.

### Constraints Identified
- Regras 13 e 30: nenhum ganho estimado, nenhum "provado".
- Regra 12: melhoria so entre as execucoes que o operador mediu.
- Regra 20: lacuna com nome.
- Regra 26: a tool nova move a superficie.
- Caso real nunca entra em arquivo; os dez registros manuais de tool nova e dominio novo de fixture.

### Out of Scope (Confirmed)
- Tudo o que esta na tabela YAGNI acima.
- Mudar `Finding`, o catalogo das regras ou os comparadores existentes.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 8 (5 de discovery, 1 de abordagem -- que trouxe o refinamento `--after-facts` --, 2 de validacao) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |
| Duration | 1 sessao |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_CHANGE_PROOF.md`
