# SparkForge Fase 5a.2 — Cobrir as dívidas da 5a: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** fechar as duas dívidas que a Fase 5a abriu, e tornar real a Task 5 que ela entregou fraca. Hoje o runtime só existe se o operador digitar a versão; nenhum extrator alimenta a detecção. E cinco regras recomendam AQE e `REBALANCE` sem saber se a versão suporta.

**Architecture:** a máquina de detecção já existe e é boa — `detect_runtime` tem precedência por fonte (`event_log` > `terraform` > `requirements`), resolve divergência, e emite `env.runtime_signal`. Ela só nunca é alimentada: `build_runtime_context` passa apenas `{"cli": ...}`. Três correções encadeadas: o event log passa a observar a versão, `judge` passa a derivar fontes dos facts, e as skills param de exigir que o operador saiba a versão.

**Tech Stack:** Python stdlib, YAML declarativo, pytest.

**Origem:** dívidas registradas em [`../STATUS.md`](../STATUS.md) ao fechar a
[Fase 5a](2026-08-01-sparkforge-fase5a-escopo.md). Mesma branch, `feat/fase5a-escopo`.

---

## Fatos verificados antes de escrever este plano

```
sparkforge/adapters/_core.py:104-121   build_runtime_context -> detect_runtime({"cli": ...})
                                        nenhum fact alimenta a deteccao
sparkforge/facts/event_log.py:34-48     EMITTED_KINDS: 11 kinds, NENHUM carrega versao
sparkforge/facts/terraform.py:72        "glue_version" ja e lido como tf.attribute
sparkforge/facts/runtime_detect.py:44   _PRECEDENCE = ("event_log", "terraform", "requirements")
sparkforge/facts/runtime_detect.py:62-66 _source_rank: origem fora da precedencia -> ULTIMO
```

Consequência de `_source_rank`: `"cli"` não está em `_PRECEDENCE`, então hoje ranqueia por último. Quando os facts começarem a alimentar a detecção, uma flag `--glue 5.0` **perde** para o `glue_version` lido do Terraform, e a discordância vira `env.runtime_signal` com divergência — que é exatamente o que `SF-ENV-001` existe para reportar. Isso é comportamento desejável, não acidente, mas precisa ser declarado em vez de emergir.

Escopos não-vazios restantes, todos sobre Glue e todos expostos a esta dívida:
`SF-ENV-002`, `SF-ENV-003`, `SF-GLUE-001`, `SF-GLUE-002..006`.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/event_log.py` | passa a emitir `spark.runtime_version` |
| `sparkforge/facts/runtime_detect.py` | `cli` declarada na precedência |
| `sparkforge/adapters/_core.py` | `build_runtime_context` aceita facts e deriva fontes |
| `sparkforge/adapters/cli.py` | `judge` passa os facts que já carregou |
| `rules/catalog/pyspark.yaml`, `parquet.yaml`, `spark-ui.yaml` | `proposed_change` ramificado por versão |
| `skills/*/SKILL.md` | `--glue` vira opcional declarado, não placeholder obrigatório |
| `tests/test_runtime_inferred_from_facts.py` | **criado** — invariante da inferência |

---

## Task 1: O event log observa a versão do Spark

Hoje `EMITTED_KINDS` tem 11 kinds e nenhum carrega versão, apesar de o event log ser a fonte mais confiável na precedência declarada.

**Files:**
- Modify: `sparkforge/facts/event_log.py`
- Test: `tests/test_facts_event_log.py`

- [x] **Step 1: Descubra onde a versão está**

O event log do Spark carrega a versão em pelo menos dois eventos: `SparkListenerLogStart` tem o campo `Spark Version`, e `SparkListenerEnvironmentUpdate` traz `Spark Properties`. **Leia uma fixture real** em `fixtures/` antes de escolher, e diga no relatório qual evento você achou e em quais fixtures ele aparece. Se nenhuma fixture tiver o evento, diga — o extrator ainda deve saber lê-lo, mas a fixture precisa nascer.

- [x] **Step 2: Escreva o teste primeiro**

Em `tests/test_facts_event_log.py`, seguindo o estilo do arquivo. O fact novo é `spark.runtime_version`, com a versão em `attrs`. Cubra: evento presente, evento ausente (não emite nada, e **não** é erro), e versão malformada (vira `spark.unresolved`, o padrão que o extrator já usa para o que não deu para interpretar).

- [x] **Step 3: Implemente**

Acrescente o kind a `EMITTED_KINDS`. `event_log.py:524` tem a guarda `unknown = {f.kind for f in facts} - EMITTED_KINDS` — ela vai pegar se você esquecer.

- [x] **Step 4: Fixture**

Toda capacidade nova precisa de fixture golden. Siga o que `fixtures/` já faz para event log.

- [x] **Step 5: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_facts_event_log.py -q
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
git add sparkforge/facts/event_log.py tests fixtures
git commit -m "feat(facts): event log passa a observar a versao do Spark"
```

---

## Task 2: `judge` infere o runtime dos facts

A dívida central. `build_runtime_context` monta o contexto só de flags de CLI, e `in_scope` falha fechada — então os 8 guardas de versão restantes só funcionam se o operador digitar a versão.

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `sparkforge/facts/runtime_detect.py`, `sparkforge/adapters/cli.py`
- Create: `tests/test_runtime_inferred_from_facts.py`

- [x] **Step 1: Declare `cli` na precedência**

`_PRECEDENCE` não menciona `cli`, então `_source_rank` a joga para o fim por acidente de implementação, não por decisão. Torne explícito.

**Onde ela entra é decisão sua, com justificativa escrita no código.** Os dois argumentos:
- depois de `event_log`: o que foi observado no run real vence o que alguém digitou
- antes de tudo: uma flag explícita é uma afirmação do operador, e sobrepor-se a ela silenciosamente é o tipo de julgamento que a §1 do spec da Fase 0 proíbe

Seja qual for, a discordância entre fontes tem que continuar virando divergência em `env.runtime_signal` — nunca ser resolvida em silêncio. Prove isso com teste.

- [x] **Step 2: Derive fontes a partir dos facts**

`build_runtime_context` ganha um parâmetro de facts, opcional, com default que preserva o comportamento atual para todo chamador existente.

Mapeamento mínimo, e **verifique cada um lendo o extrator** antes de escrever:

| Fonte | Fact | Campo |
|---|---|---|
| `event_log` | `spark.runtime_version` (Task 1) | versão do Spark |
| `terraform` | `tf.attribute` com `attrs.key == "glue_version"` | versão do Glue |

`detect_runtime` já infere `spark`, `python` e `iceberg` de `GLUE_MATRIX` quando conhece `glue_version` — não reimplemente isso.

**Fronteira negativa, e ela importa:** derivar é ler o que o extrator já observou. Se nenhum fact carrega a informação, o campo fica vazio e a regra é pulada com motivo. Não adivinhe versão a partir de sintaxe de API, nome de bucket, ou qualquer outro sinal indireto — isso seria julgamento entrando na camada de fato, que é o inimigo declarado do projeto.

- [x] **Step 3: `judge` passa os facts**

O comando já carregou os facts para julgar. Passe-os. Cuidado com a ordem: o contexto tem que estar montado antes de `in_scope` rodar.

- [x] **Step 4: O invariante**

Crie `tests/test_runtime_inferred_from_facts.py`. Cubra, no mínimo:

- facts de Terraform com `glue_version` → as 8 regras de Glue avaliam **sem nenhuma flag**
- facts de event log com versão de Spark → `spark` preenchido no contexto
- CLI e facts discordando → divergência em `env.runtime_signal`, resolvida pela precedência que você declarou, **nunca em silêncio**
- nenhum fact com versão → contexto vazio, regras de Glue puladas com `reason: runtime_scope`, e isso **aparece** em `--show-skipped`

Prove sensibilidade: com a inferência desligada, o teste tem que ficar vermelho.

- [x] **Step 5: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_runtime_inferred_from_facts.py -q
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
git add sparkforge tests
git commit -m "feat(runtime): judge infere o runtime dos facts, nao so das flags"
```

Se golden mudar, **leia o diff antes de regenerar** — findings podem passar a existir onde antes a regra era pulada, e isso é o objetivo, mas você tem que confirmar que é isso e não outra coisa.

---

## Task 3: `proposed_change` ramificado por versão

Cinco regras têm gatilho agnóstico — corretamente, a Fase 5a mediu isso — mas recomendação que cita AQE ou o hint `REBALANCE`, ambos de Spark 3.2. Com escopo vazio elas disparam onde o conselho pode não se aplicar.

| Regra | Onde | O quê |
|---|---|---|
| SF-PY-005 | `proposed_change[1]` | "Preferir o hint REBALANCE… coopera com o AQE" |
| SF-PY-009 | `explanation` + `proposed_change[1]` | "o AQE já converte sort-merge em broadcast" |
| SF-PY-010 | `explanation` + `proposed_change[0]` | "Com AQE ativo, o coalescing… já ajusta a contagem" |
| SF-PQ-001 | `proposed_change[1]` | "…ou usar o hint REBALANCE antes da escrita" |
| SF-UI-006 | `proposed_change[1]` | "Aumentar spark.sql.shuffle.partitions e deixar o AQE coalescer" |

**Files:**
- Modify: `rules/catalog/pyspark.yaml`, `parquet.yaml`, `spark-ui.yaml`

- [x] **Step 1: Confirme a lista lendo**

Não confie na tabela acima. Releia as cinco e confirme o trecho exato. Se achar uma sexta com a mesma propriedade, **inclua e diga**. Se alguma da lista não tiver a propriedade, exclua e diga.

- [x] **Step 2: Escolha o mecanismo, e ele não pode ser um `if` escondido**

`proposed_change` é uma lista de strings no YAML. Você **não** vai inventar um mini-motor de template — o catálogo é dado editável e superfície de execução, e a Fase 0 restringe deliberadamente o que se avalia nele.

A saída barata e honesta: o texto do bullet declara a condição em vez de assumi-la. `"Preferir o hint REBALANCE (Spark >= 3.2; em 3.0/3.1 use repartition com a chave)"`. O operador lê a condição junto com a ação, e o motor continua não julgando nada.

Se você defender um mecanismo estruturado — por exemplo um campo novo `since` por bullet — **descreva antes de implementar** e relate: isso muda o schema do catálogo, o validador, os goldens e a renderização, e é decisão de arquitetura, não de redação.

- [x] **Step 3: Verifique e commite**

Golden vai mudar — `proposed_change` entra no payload do `Finding`. Diferencie campo a campo; só esse campo pode divergir.

```bash
rtk proxy python -m pytest -q
git add rules/catalog fixtures
git commit -m "fix(rules): recomendacao de AQE e REBALANCE nao declarava a versao"
```

---

## Task 4: As skills param de exigir que o operador saiba a versão

A Task 5 da Fase 5a entregou só um teste de guarda — verifica que toda invocação de `judge` passa **alguma** flag de runtime. É fraco: todas já passavam, e a flag é o placeholder `<versão>`, que o agente precisa preencher sem ter de onde tirar o valor.

Com a Task 2, `judge` infere. As skills mudam de "digite a versão" para "o motor infere, e diz o que inferiu".

**Files:**
- Modify: `skills/*/SKILL.md`, `tests/test_skill_content.py`

- [x] **Step 1: Levante o estado**

```bash
grep -n "sparkforge judge" skills/*/SKILL.md
```

São 24 invocações em 16 skills, todas com `--glue <versão>` ou equivalente.

- [x] **Step 2: Reescreva a orientação**

A flag vira **opcional declarada**, não obrigação: passe-a quando souber a versão; caso contrário o motor infere dos facts, e `--show-skipped` diz o que não deu para cobrir e por quê.

Não faça substituição mecânica. Cada skill investiga uma coisa: uma de infra Glue tem razão para insistir na versão; uma de código PySpark não tem. Leia cada uma e escreva o que faz sentido ali. **Diga no relatório quais você tratou de forma diferente e por quê.**

- [x] **Step 3: Fortaleça o teste**

`test_toda_invocacao_de_judge_passa_runtime` em `tests/test_skill_content.py` só exige *alguma* flag. Torne-o real: a skill tem que ou passar a flag correspondente ao que investiga, ou dizer explicitamente que confia na inferência. Escreva de forma que uma skill nova que só copie o comando alheio seja cobrada.

Prove sensibilidade por injeção, como a Fase 5a fez.

- [x] **Step 4: Espelhos, verificação e commit**

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
rtk proxy python -m pytest -q
git add skills tests .claude .agents .github
git commit -m "fix(skills): versao vira opcional declarada, nao placeholder obrigatorio"
```

---

## Task 5: Documentação e varredura

- [x] **Step 1: `rules/catalog/README.md`**

A seção "O que `runtime_scope` é, e o que ele não é" afirma que o guarda falha fechado porque `build_runtime_context` só lê flags. Isso deixa de ser verdade. Reescreva com o que passa a valer, e diga o que ainda falha fechado — porque algo sempre vai: quando nenhum extrator observou a versão, a regra continua sendo pulada, e isso é correto.

- [x] **Step 2: `STATUS.md`**

Números medidos. As duas dívidas saem da tabela como fechadas, com commit. A Task 5 da 5a deixa de ser descrita como entregue fraca. Registre o que a inferência **não** faz — a fronteira negativa do Step 2 da Task 2.

- [x] **Step 3: Varredura**

```bash
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
python scripts/sync_skills.py --check
python scripts/gen_requirements.py --check
python scripts/check_evals.py
```

Prove com comando, não com afirmação, que `sparkforge judge` sem flag nenhuma sobre um repositório com Terraform de Glue avalia as 8 regras de Glue.

- [x] **Step 4: Commit**

```bash
git add docs/superpowers rules/catalog/README.md
git commit -m "docs: fecha as dividas da Fase 5a"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Runtime vem de | só flags de CLI | facts observados, com flags como fonte declarada |
| Facts que carregam versão | 1 (`tf.attribute`/`glue_version`) | 2 — event log passa a observar Spark |
| `judge` sem flags sobre Terraform de Glue | 8 regras puladas | 8 avaliadas |
| Recomendação de AQE/`REBALANCE` | assume Spark 3.2 sem dizer | declara a condição no bullet |
| Guarda nas skills | exige *alguma* flag | exige a flag certa, ou inferência declarada |
