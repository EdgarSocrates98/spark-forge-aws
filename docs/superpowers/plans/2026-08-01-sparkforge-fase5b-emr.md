# SparkForge Fase 5b — EMR on EC2: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar ao EMR o eixo de infraestrutura que hoje só existe para Glue, e fazer o motor perceber quando duas plataformas são detectadas ao mesmo tempo — mesmo quando as versões derivadas coincidem.

**Architecture:** cinco camadas, na ordem em que uma habilita a seguinte. Plataforma vira coisa rastreada com fact próprio, `emr` entra no `RuntimeContext` com matriz e guard de drift, um extrator lê dump de cluster já coletado, uma área `SF-EMR` julga esses facts, e um coordenador próprio a torna alcançável.

**Tech Stack:** Python stdlib, YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-01-sparkforge-fase5-emr-design.md`](../specs/2026-08-01-sparkforge-fase5-emr-design.md) — §3.3, §4.2 a §4.5, e os critérios 3, 4, 5, 6, 7, 8, 9, 12 e 14. Os critérios 1, 2, 10, 11 e 13 foram fechados pela [Fase 5a](2026-08-01-sparkforge-fase5a-escopo.md).

**Base:** [Fase 5a](2026-08-01-sparkforge-fase5a-escopo.md) corrigiu o escopo e [5a.2](2026-08-01-sparkforge-fase5a2-dividas.md) fez o runtime vir dos facts. Esta fase nasce sobre uma base que diz a verdade sobre o próprio escopo — sem elas, toda regra `SF-EMR` nova herdaria os mesmos defeitos.

---

## Fatos do ambiente verificados antes de escrever este plano

```
RuntimeContext (findings/models.py:138-159)
    glue spark python iceberg athena detected_from divergences   -- sem `emr`

runtime_detect.py:174   glue_observations e SEPARADO de observations
runtime_detect.py:184   _build_facts itera SO observations
                        -> plataforma NUNCA vira env.runtime_signal

test_runtime_detect.py:5  test_matrix_matches_committed_knowledge
                          espelha knowledge/glue/runtime-matrix.md -- o guard de drift a copiar

test_agent_coverage.py:75 test_no_area_is_orphan
                          areas = {id.rsplit("-",1)[0]}; toda area precisa de `rule_areas` num coordenador

catalogo    48 regras | SF-ENV-001..004 usados, SF-ENV-005 livre
tools       30, todas alcancaveis
collect/aws.py  collect_event_log, collect_glue_job, collect_cloudwatch,
                collect_iceberg_metadata, collect_athena_workgroup
testes      2320 passando, 5 skipped
```

**A consequência que decide a Task 1.** O critério 12 exige sinal **mesmo quando as versões derivadas coincidem**. `SF-ENV-001` dispara sobre `env.runtime_signal` com `measures.distinct_versions > 1` — é comparação de *versão de componente*. Se Glue 4.0 e algum release EMR derivam o mesmo Spark 3.3.0, não há divergência de versão alguma, e a dupla detecção passa muda. Portanto o critério 12 **não é alcançável** por comparação de versão, sob nenhum ajuste. Identidade de plataforma precisa de fact próprio e regra própria.

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/emr_cluster.py` | extrator de dump de cluster EMR |
| `sparkforge/collect/` (função em `aws.py`) | coleta do dump, extra `[aws]` |
| `rules/catalog/emr-infra.yaml` | área `SF-EMR` |
| `knowledge/emr/runtime-matrix.md` | matriz de release, fonte do guard de drift |
| `agents/emr-infra-reviewer.md` | coordenador da área |
| `skills/review-emr-cluster/SKILL.md` | skill da investigação |
| `tests/test_facts_emr_cluster.py` | extrator |
| `tests/test_platform_divergence.py` | critério 12 |
| `fixtures/emr/*` | golden bidirecional por regra |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/findings/models.py` | `emr` em `RuntimeContext` |
| `sparkforge/facts/runtime_detect.py` | `EMR_MATRIX`, `env.platform`, `emr` observado |
| `sparkforge/adapters/_core.py`, `cli.py`, `tools.py` | verbos e tools novos |
| `rules/catalog/env.yaml` | `SF-ENV-005` |
| `knowledge/sources.lock.json` | fonte da matriz EMR na watchlist |

---

## Task 1: Plataforma vira coisa rastreada

Primeiro, e independente de todo o resto — fecha o critério 12, que a §3.3 do spec registrou como **não coberto** justamente para ninguém assumir que estava.

**Files:**
- Create: `tests/test_platform_divergence.py`
- Modify: `sparkforge/facts/runtime_detect.py`, `rules/catalog/env.yaml`

- [ ] **Step 1: Reproduza o silêncio**

Monte um `sources` com Glue e EMR cujas versões derivadas **coincidam**, e mostre que hoje não sai sinal nenhum. Se você não conseguir fazer as versões coincidirem com a matriz atual, force o cenário — o ponto é o mecanismo, não o par de versões.

Cole a saída. Ela é a justificativa da task.

- [ ] **Step 2: O teste, primeiro**

Em `tests/test_platform_divergence.py`. O invariante: **duas plataformas detectadas produzem sinal, independentemente das versões**. Cubra as versões coincidindo e as divergindo — o primeiro caso é o que o critério 12 exige e o que nenhum teste atual pega.

- [ ] **Step 3: `env.platform`**

`_build_facts` itera só `observations`, e `glue_observations` está fora. Não force plataforma para dentro de `observations`: os dois têm semântica diferente — `observations` são versões de componente, e `SF-ENV-001` conta `distinct_versions`. Plataforma é **identidade**, e a pergunta é "quantas?", não "quais versões?".

Emita um fact próprio, `env.platform`, com as plataformas detectadas e de onde vieram. Decida o formato exato lendo como `env.runtime_signal` é montado, e mantenha `subject`, `attrs` e `provenance` no padrão do arquivo.

- [ ] **Step 4: `SF-ENV-005`**

Regra irmã de `SF-ENV-001`, sobre `env.platform`, disparando quando mais de uma plataforma é detectada.

Escreva-a lendo `rules/catalog/README.md` — todos os campos obrigatórios, `sources` declarada, sem percentual de ganho. `explanation` tem que dizer **por que isso importa**: um job roda num runtime só, então duas plataformas detectadas significam que uma das fontes descreve outra coisa — e todo achado de infraestrutura daquele relatório está ancorado na plataforma errada.

Fixture bidirecional: uma que dispara, uma limpa.

- [ ] **Step 5: `emr` no `RuntimeContext`**

O campo, com default `""`, e em `to_dict()`. Mínimo para a Task 1 funcionar; a matriz é a Task 2.

**Cuidado:** `to_dict()` sempre emite toda chave, e `in_scope` reprova valor vazio. Acrescentar `emr` significa que um futuro `runtime_scope: {emr: "*"}` falha fechado quando não há EMR — que é correto — mas **confirme que nenhuma regra existente passa a ser pulada**. `tests/test_rule_scope_by_nature.py::TestNoCatalogAreaVanishesEntirely` pega isso; rode-o.

- [ ] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_platform_divergence.py tests/test_runtime_detect.py tests/test_rule_scope_by_nature.py -q
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
git add sparkforge tests rules/catalog fixtures
git commit -m "feat(runtime): plataforma vira coisa rastreada, com regra propria"
```

---

## Task 2: `EMR_MATRIX` e o guard de drift

**Files:**
- Create: `knowledge/emr/runtime-matrix.md`
- Modify: `sparkforge/facts/runtime_detect.py`, `knowledge/sources.lock.json`
- Test: `tests/test_runtime_detect.py`

- [ ] **Step 1: O documento primeiro, o código depois**

`knowledge/emr/runtime-matrix.md`, no formato de `knowledge/glue/runtime-matrix.md` — **leia-o antes**. A tabela é release label → Spark, Python, Iceberg, Hadoop, com a URL oficial e a data de recuperação.

A pesquisa de fontes desta fase levantou a tabela e a página canônica. Use-a, mas **confirme cada linha contra a fonte** antes de escrever: matriz errada é bug de dado que se propaga para toda regra versionada.

- [ ] **Step 2: `EMR_MATRIX`**

No formato de `GLUE_MATRIX`, mesmo arquivo. Só releases que o documento sustenta.

- [ ] **Step 3: O guard de drift**

`tests/test_runtime_detect.py::test_matrix_matches_committed_knowledge` já faz isso para Glue — **leia-o e siga o mesmo mecanismo**, não invente outro. O teste tem que falhar se o código e o documento divergirem, em qualquer direção.

- [ ] **Step 4: Watchlist**

`knowledge/sources.lock.json` vigia fontes oficiais. Acrescente a página canônica da matriz EMR. Confirme como o `refresh_knowledge` consome esse arquivo antes de escrever a entrada — formato errado quebra o gate.

- [ ] **Step 5: `emr` observado e derivado**

`detect_runtime` passa a aceitar `emr_version`/`emr` como chave direta, e a derivar Spark/Python/Iceberg de `EMR_MATRIX` — do mesmo jeito que já faz com Glue. A origem derivada tem que carregar o sufixo `:matrix`, como a de Glue, senão `_resolve` a trata como observação direta.

- [ ] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_runtime_detect.py tests/test_runtime_inferred_from_facts.py -q
rtk proxy python -m pytest -q
git add sparkforge knowledge tests
git commit -m "feat(runtime): EMR_MATRIX, com guard de drift contra o knowledge"
```

---

## Task 3: O extrator de EMR on EC2

**Files:**
- Create: `sparkforge/facts/emr_cluster.py`, `tests/test_facts_emr_cluster.py`
- Modify: `sparkforge/collect/aws.py`, `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`

- [ ] **Step 1: Leia o análogo mais próximo**

`sparkforge/facts/athena_workgroup.py` é o modelo: lê dump JSON já coletado, **não coleta nada**, tem sentinela e `unresolved`, e o docstring documenta o shape esperado. `iceberg_metadata.py` é o segundo, para dump com várias seções opcionais.

A disciplina, e ela não é negociável: **entrada é artefato local, sem rede**. A coleta vive em `collect/aws.py`, atrás do extra `[aws]`.

- [ ] **Step 2: Feche os kinds**

O spec deixou os kinds em aberto. Decida-os a partir de **duas** restrições, e diga no relatório como cada uma pesou:

1. o que os dumps realmente devolvem — `describe-cluster`, `list-instance-groups`/`list-instance-fleets`, `list-bootstrap-actions`, `list-configurations`
2. o que as regras da Task 4 precisam julgar

Não emita kind que nenhuma regra consome: capacidade sem consumidor é mecanismo sem garantia declarada, que é exatamente o que o projeto recusa. E não emita um kind sentinela genérico como único gate de uma regra — foi assim que `SF-GLUE-002` sumia de findings **e** de skipped, e a Fase 5a teve que reancorá-la em `tf.resource`.

Obrigatórios: a sentinela `emr.analyzed` e o `emr.unresolved` para o que não deu para interpretar. Seção presente mas malformada vira `unresolved`, **não** silêncio.

- [ ] **Step 3: Instance groups e instance fleets**

São dois modelos alternativos e mutuamente exclusivos, com respostas de API de forma diferente. Um cluster tem um ou outro. Trate os dois, e **decida se viram o mesmo kind com um atributo discriminante ou kinds distintos** — justifique. Um dump com nenhum dos dois é dump incompleto, não cluster sem instâncias: isso é `unresolved`.

- [ ] **Step 4: Teste e fixture**

Fixture golden por caminho, seguindo `fixtures/` — leia um `meta.yaml` existente antes. Cubra: groups, fleets, seção ausente, seção malformada, e dump vazio.

- [ ] **Step 5: Verbo, tool e coleta**

`sparkforge analyze emr-cluster` e `sparkforge collect emr-cluster`, mais as tools MCP correspondentes. **Toda tool nova precisa ser alcançável a partir de um coordenador** — `tests/test_agent_coverage.py::test_no_tool_is_orphan` trava isso, e quem fecha é a Task 5. Se você acrescentar a tool antes do coordenador, o teste fica vermelho: isso é esperado, e some quando a Task 5 entrar. **Não contorne o teste.**

- [ ] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_facts_emr_cluster.py -q
rtk proxy python -m pytest -q
git add sparkforge tests fixtures
git commit -m "feat(facts): extrator de cluster EMR on EC2"
```

---

## Task 4: A área `SF-EMR`

**Files:**
- Create: `rules/catalog/emr-infra.yaml`, `knowledge/emr/*.md`, `fixtures/emr/*`

- [ ] **Step 1: Escolha as regras**

A pesquisa desta fase levantou candidatas com fonte, severidade, limiar e observabilidade no dump. **Não implemente todas por implementar**: cada regra precisa de fixture bidirecional, e regra fraca custa manutenção para sempre.

O critério de corte, e ele é do projeto: a regra tem que ser **observável no dump** e **julgável sem julgamento** — condição sobre fact, não impressão. Regra que exige informação que a API não devolve não pode existir; a pesquisa deve ter marcado quais são.

- [ ] **Step 2: Escreva-as**

Lendo `rules/catalog/README.md` e usando `rules/catalog/glue-infra.yaml` como modelo — é o análogo direto, regras de infraestrutura de job.

Obrigatório por regra: `sources` com URL e data, ou `origin: field-heuristic` declarado; `risks`, `tradeoffs`, `validation`, `rollback`; **sem percentual de ganho**.

O `runtime_scope` segue o critério que a Fase 5a fixou: **não-vazio só quando o gatilho genuinamente varia com a versão, e essa versão vem do runtime, não de um fact que a regra já lê**. Regra que lê release label do próprio dump **não** precisa de `runtime_scope` — o fact já prova a plataforma. Errar isso aqui é repetir exatamente o defeito que duas fases inteiras acabaram de corrigir.

- [ ] **Step 3: Conhecimento**

Regra com profundidade aponta para `knowledge/emr/`. Siga o formato de `knowledge/glue/workers-and-capacity.md`.

- [ ] **Step 4: Fixture bidirecional por regra**

Invariante da Fase 2: toda regra precisa de fixture que a faça disparar **e** de contraparte negativa. `tests/test_fixtures_kind_coverage.py` trava.

- [ ] **Step 5: Verifique e commite**

```bash
rtk proxy python -m pytest -q
python scripts/check_evals.py
git add rules/catalog knowledge fixtures tests
git commit -m "feat(rules): area SF-EMR, infraestrutura de cluster"
```

---

## Task 5: Coordenador e skill

Fecha o invariante de órfão que a Task 3 abriu de propósito.

**Files:**
- Create: `agents/emr-infra-reviewer.md`, `skills/review-emr-cluster/SKILL.md`

- [ ] **Step 1: A decisão, e ela já está tomada**

O spec deixou duas saídas: alargar `glue-infra-reviewer` ou criar um irmão. **Crie `emr-infra-reviewer`.**

A razão: `rule_areas` no frontmatter é contrato de roteamento, não rótulo. Um coordenador chamado `glue-infra-reviewer` declarando `SF-EMR` mente para quem lê a descrição — e a descrição é o gatilho de seleção do agente, como a Fase 5a.2 descobriu do jeito caro. A Fase 4 estabeleceu coordenadores por domínio; EMR é domínio.

Se ao escrever você concluir que a duplicação com `glue-infra-reviewer` é grande demais para justificar, **pare e relate** em vez de decidir sozinho.

- [ ] **Step 2: Escreva o coordenador**

Leia `agents/glue-infra-reviewer.md` inteiro — frontmatter (`name`, `description`, `tools`, `skills`, `rule_areas`, `executors`) e as seções de corpo. A `description` começa com "Use quando" e descreve o **gatilho**, não o que o agente faz.

`rule_areas` inclui `SF-EMR`. `executors` fecha a cadeia de handoff — `tests/test_agent_coverage.py` verifica que todo executor declarado existe.

- [ ] **Step 3: A skill**

`skills/review-emr-cluster/SKILL.md`, seguindo o padrão: seções `## Quando NÃO usar`, `## Referência rápida`, `## Red flags`, e `description` começando com "Use quando".

Duas coisas que a Fase 5a.2 travou com teste e você vai acertar de primeira lendo o que ela fez:
- **não negue capacidade que existe**, e não anuncie subcomando que o parser não aceita — o teste é derivado de `build_parser()`
- **runtime é opcional declarado**, não placeholder `<versão>`: `judge` infere dos facts, e a skill deve dizer de onde vem e o que fazer quando não vem

- [ ] **Step 4: Espelhos**

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
```

- [ ] **Step 5: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_agent_coverage.py tests/test_skill_content.py -q
rtk proxy python -m pytest -q
git add agents skills .claude .agents .github tests
git commit -m "feat(agents): emr-infra-reviewer, coordenador da area SF-EMR"
```

---

## Task 6: A prova do objetivo

O critério 8 e o último da tabela §5 do spec: **investigação sobre EMR produz achados de código, plano e armazenamento normalmente, e reporta as SF-GLUE como puladas em vez de sumirem em silêncio**.

**Files:**
- Modify: `tests/test_rule_scope_by_nature.py` ou módulo próprio

- [ ] **Step 1: O teste ponta a ponta**

Monte facts de um cenário EMR — cluster, código PySpark, e o que mais fizer sentido — e prove numa asserção só:

- as regras agnósticas disparam normalmente
- as `SF-EMR` disparam
- as `SF-GLUE` aparecem em `skipped`, com `reason`
- nenhuma área some em silêncio

`tests/test_rule_scope_by_nature.py` já tem `TestNoCatalogAreaVanishesEntirely` derivando runtimes de `GLUE_MATRIX`. Acrescente os runtimes EMR ao conjunto — derivados de `EMR_MATRIX`, não escritos à mão, para que release novo entre sozinho.

- [ ] **Step 2: Varredura**

```bash
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
python scripts/sync_skills.py --check
python scripts/gen_requirements.py --check
python scripts/check_evals.py
```

Prove com comando cada critério que esta fase fecha: **3, 4, 5, 6, 7, 8, 9, 12**.

- [ ] **Step 3: Docs — critério 14**

`README.md`, `AGENTS.md`, `STATUS.md`, `knowledge/`, as skills afetadas e o spec. Números medidos, não copiados. O spec sai de "implementado em parte" para implementado, e a 5b ganha seção própria em `STATUS.md` com o que ficou de fora.

**O que fica de fora, e deve ser escrito como dívida, não omitido:** EMR Serverless e EMR on EKS. Esta fase é EMR on EC2, por decisão registrada no spec.

- [ ] **Step 4: Commit**

```bash
git add docs knowledge README.md AGENTS.md
git commit -m "docs: fecha a Fase 5b"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Plataformas conhecidas pelo `RuntimeContext` | 1 (`glue`) | 2 (`glue`, `emr`) |
| Glue e EMR detectados juntos | passa mudo se as versões coincidem | `SF-ENV-005`, sempre |
| Extratores de facts | 13 | 14 |
| Áreas do catálogo | 9 | 10 |
| Coordenadores | 6 | 7 |
| Investigação sobre EMR | `SF-GLUE` avalia e nunca dispara | `SF-GLUE` pulada, com motivo |
