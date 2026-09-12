# BRAINSTORM: Simulate (what-if estrutural)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMULATE |
| **Date** | 2026-09-12 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Frente §19 de `prompt_new_evo.md`, "Counterfactual / What-if Analysis": `sparkforge simulate` responde o que acontece se a configuracao X mudar, que regras somem, que riscos aparecem -- "nao para inventar performance, para raciocinar sobre consequencias estruturais conhecidas". Branch `feat/simulate`, a partir da `main` (ja com #56 e #57).

**Context Gathered:**
- **O que ja existe:**
  - Todo kind de configuracao guarda a propriedade em `attrs.key` e o valor em `attrs.value`: `spark.conf_effective` (event log), `pyspark.conf_set` (codigo), `tf.spark_conf` e `tf.attribute` (Terraform), `emr.configuration`, `emrs.configuration`, `emrc.configuration`.
  - `judge_findings` julga os facts como chegam e nao roda derivacao nenhuma. A unica derivacao com porta de producao e o verbo `fuse` (`facts/fusion.py::fuse(facts)`, que chama `build_lakeformation`).
  - A chave estavel do Change Proof (`sparkforge/proof/keys.py`) compara findings de antes e depois sem que linha ou snippet contem.
  - `migration_assess` ja expande um par de versoes em degraus e julga cada um: mudar runtime nao e desta frente.
- **Medido em 2026-09-12:**
  - **29 regras** leem kinds de configuracao diretamente: `tf.attribute` 18 (`worker_type`, `glue_version`, `--job-bookmark-option`, `--enable-lakeformation-fine-grained-access`, `max_retries`...), EMR 6, `tf.spark_conf` 2, `pyspark.conf_set` 1, `mig.*` 2. **Nenhuma** le `spark.conf_effective` diretamente.
  - **20 regras** leem kinds DERIVADOS da configuracao: `lakeformation.*` 13, `sql.*` enriquecidos 4, `spark.timeout.*` 2, `iceberg.library_conflict` 1.
  - **`extract_timeout_diagnosis` nao tem porta de producao.** Os chamadores sao so testes; em `sparkforge/` a string aparece numa docstring de `facts/utilization.py`. Os facts `spark.timeout.*` so existem nos goldens, e `SF-TIMEOUT-001/002` nunca disparam num case real.

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O que o simulate muda? | Valor de configuracao | Runtime fica com `migration_assess`; aplicar recomendacao fica para depois |
| 2 | E os derivados? | Rederivar | Tira os kinds derivados e roda as mesmas derivacoes do produto nos dois lados |
| 3 | Qual camada o `--set` altera? | Uma camada nomeada | `--set tf:chave=valor`; prefixo obrigatorio |
| 4 | O timeout sem porta? | Ligar a derivacao primeiro | Passo 0 da frente: `fuse()` passa a chamar `extract_timeout_diagnosis` |

---

## Approaches Explored

### Approach A: so compoe ⭐ Recommended

**Description:** `simulate --facts <uniao> --set <camada>:<chave>=<valor>`. Aplica o valor nos facts da camada, tira os kinds derivados, rederiva com `fuse`, julga antes e depois (runtime redetectado por lado) e compara pela chave estavel. Tool READ_ONLY.

**Pros:** reusa o `judge`, o `fuse` e a chave estavel; a diferenca so pode vir do `--set`.

**Cons:** so move o que vira fact de configuracao; spill e tempo nao sao simulaveis.

**Why Recommended:** e consequencia conhecida, nao previsao. Confianca 0,85.

### Approach B: A + aplicar recomendacao

**Why not:** definir o que cada `action.kind` faz com os facts e modelar dezenas de tipos de acao.

### Approach C: so lista impacto estatico

**Why not:** nao diz se a regra dispara ou deixa de disparar com o valor novo.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-12 |
| **Reasoning** | Rejulgamento sobre facts alterados, pipeline simetrico, nenhuma medida prevista |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Camadas fixas: `tf` (`tf.spark_conf`, `tf.attribute`), `code` (`pyspark.conf_set`), `effective` (`spark.conf_effective`), `emr` (`emr.*`, `emrs.*`, `emrc.configuration`); prefixo obrigatorio | Regra 19: quem pediu contra quem venceu; a mudanca real e num arquivo so | Alterar todas as camadas |
| 2 | O `--set` so altera fact existente; chave ausente na camada -> recusa `chave_ausente_na_camada` | Nao ha como inventar o subject de um fact novo | Criar fact com subject sintetico |
| 3 | Os dois lados pelo mesmo pipeline: tira derivados, rederiva, redetecta runtime, julga | A diferenca so pode vir do `--set`; `--set tf:glue_version` muda o runtime | Julgar o antes como veio |
| 4 | Comparacao por `(rule_id, chave estavel)` com `proof.keys.stable_key` | Linha e snippet nao sao diferenca | Subject inteiro |
| 5 | Saida: `changes`, `disappeared`, `appeared`, `persisted_count`, `skipped_delta`, `runtime` antes/depois, `refused` fixo com `performance_prediction`, `dependency_incompatibility` (-> `migration_assess`) e `execution_graph` | As tres perguntas do §19 que o simulate nao responde saem nomeadas | Omitir |
| 6 | Passo 0: `fusion.fuse()` passa a chamar `extract_timeout_diagnosis`, como ja chama `build_lakeformation`; o DESIGN mede os goldens que mudam | Sem porta, o simulate seria o unico lugar a produzir `spark.timeout.*` e divergiria do `judge` | Simulate rederivar sozinho; timeout em `unresolved` |
| 7 | Verbo `simulate`, tool `sparkforge_simulate` READ_ONLY (declara `facts_path`); dono: o coordenador que declara `tune` | O `tune` propoe o valor, o simulate diz o que ele move | Coordenador novo |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Mudar versao de runtime | `migration_assess` ja faz | No |
| Aplicar recomendacao (`--apply`) | Modelar cada `action.kind` | Yes |
| Dependencias incompativeis | E o `migration_assess` | No |
| Grafo de execucao | Nao e previsivel a partir de configuracao | No |
| Previsao de medida | Regras 13 e 30 | No |
| Criar chave nova numa camada | Subject inventado | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| 1: camadas, aplicacao so em fact existente, pipeline simetrico, chave estavel, recusas, V1 a V4 | ✅ | "Sim, segue" | No |
| 2: passo 0, superficie, dono, fixtures, fora do escopo | ✅ | "Sim, escreve o documento" | No |

**Invariantes:** V1 nenhuma medida prevista; V2 `--set` so altera fact existente; V3 os dois lados pelo mesmo pipeline; V4 a comparacao ignora linha e snippet.

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Hoje, para saber o que uma mudanca de configuracao faria com os achados, o operador precisa aplica-la, extrair de novo e rejulgar. 29 regras leem configuracao e 20 leem derivados dela, e nenhum verbo responde "se eu mudar esta propriedade neste arquivo, o que some e o que aparece" antes de mudar. E a derivacao de timeout, que 2 regras exigem, nem chega ao produto.

### Success Criteria (Draft)
- [ ] Passo 0: `sparkforge fuse` produz `spark.timeout.*`; os goldens que mudam, medidos e com a razao.
- [ ] `fixtures/simulate/` com um caso por consequencia: regra some, regra aparece, runtime muda, derivado de Lake Formation, timeout, as duas recusas, e simetria (sem `--set`, diff vazio).
- [ ] Nenhuma medida prevista; `refused` com os tres itens.
- [ ] Tool READ_ONLY valida contra o schema com amostra real; registros, surface lock e claims por ids.
- [ ] Gates e suite por lotes com 0 falhas.

### Out of Scope (Confirmed)
- Tudo da tabela YAGNI.

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SIMULATE.md`
