# Fase 6a — grafo com Spark (`SF-GRAPH`): plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans para implementar tarefa a tarefa. Os passos usam checkbox (`- [ ]`).

**Goal:** Uma área `SF-GRAPH` que julga código PySpark que processa grafo com GraphFrames — como o grafo é processado, e se a biblioteca existe no runtime onde o job roda.

**Architecture:** Extrator novo (`sparkforge/facts/graph.py`) no padrão de `data_quality.py`: função pura sobre AST, correlação por escopo, `EMITTED_KINDS` fechado, sentinela sempre emitida, `unresolved` com vocabulário fechado. Catálogo próprio (`rules/catalog/graph.yaml`). Nenhuma mudança em `pyspark_ast.py`.

**Tech Stack:** Python 3, `ast` da stdlib, pytest, PyYAML. Sem dependência nova. Nenhuma chamada AWS.

**Spec:** [`../specs/2026-08-05-sparkforge-fase6a-graph-design.md`](../specs/2026-08-05-sparkforge-fase6a-graph-design.md)
**Branch:** `feat/fase6a-graph`

---

## Aviso a quem implementa — leia antes da Task 1

**Este plano erra sistematicamente onde eu escrevi código sem executar.** Nas Fases 4a, 4b, 4c e 5d os implementadores mediram entre 25 e 45 divergências por fase. Todas foram registradas como `D-*` e **todas as vezes a medição venceu**.

1. **Meça antes de copiar.** Se um trecho afirma que um arquivo tem tal função, assinatura ou linha, abra e confira. Divergiu? Registre como `D-6a-N` no fim deste arquivo e siga com a sua medição.
2. **Número no `STATUS.md` se mede, nunca se copia.** Rode e conte.
3. **Nada entra no catálogo sem fonte.** Regra sem `sources` com URL e `retrieved`, ou sem `origin: field-heuristic` com nota, não passa.
4. **Duas armadilhas que este repositório já pagou caro:**
   - `threshold` é **singular**. `thresholds` deixa a regra silenciosamente inerte — contexto vazio, `_expr_matches` engole o `ExprError`, ninguém nota.
   - Notação científica precisa de **ponto na mantissa**: `1.0e-9`, nunca `1e-9`. O segundo vira `str`, e `float > str` levanta `TypeError` que `_expr_matches` **não** engole — derruba o `judge` inteiro.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `knowledge/graph/graphframes-api.md` | algoritmos, `maxIter`, exigência de checkpoint — com fonte por afirmação | 1 |
| `knowledge/graph/availability.md` | matriz GraphFrames × Spark × Glue/EMR, e o que a AWS **não** documenta | 1 |
| `sparkforge/facts/graph.py` | extrator: AST → `Fact`s. Único lugar que conhece a API do GraphFrames | 2 |
| `tests/test_facts_graph.py` | testes de unidade do extrator | 2 |
| `sparkforge/adapters/_core.py` | verbo `analyze graph` | 3 |
| `sparkforge/adapters/cli.py` | sub-parser | 3 |
| `sparkforge/adapters/tools.py` | tool MCP | 3 |
| `sparkforge/collect/base.py` | `ARTIFACT_KINDS` — a sexta superfície | 3 |
| `parity.yaml`, `manifest.json` | superfícies declarativas | 3 |
| `fixtures/graph/*/` | golden bidirecional, domínio novo | 4 |
| `scripts/regen_fixtures.py` | regenerador do domínio novo | 4 |
| `rules/catalog/graph.yaml` | área `SF-GRAPH` | 5 |
| `knowledge/sources.lock.json` | URLs entram **aqui**, não na Task 1 | 5 |
| `tests/test_rules_graph_boundary.py` | fronteira nas três direções | 6 |
| `agents/*`, `skills/*`, docs | coordenador e fechamento | 7 |

---

## Task 1: A pesquisa, e as duas perguntas que decidem regra

**Nenhuma linha de código.** As Fases 5c e 5d provaram o padrão: a pesquisa vem antes e tem poder de **veto**.

**Files:**
- Create: `knowledge/graph/graphframes-api.md`
- Create: `knowledge/graph/availability.md`
- Modify: `knowledge/INDEX.md`

- [ ] **Step 1: Leia o formato antes de escrever um**

```bash
sed -n '1,40p' knowledge/emr/cluster-configuration.md
sed -n '225,246p' knowledge/emr/cluster-configuration.md
```

Três coisas que são o padrão: o link do espelho executável no topo; a seção `## Fontes` com `Título. URL (retrieved AAAA-MM-DD)`; e **os parágrafos finais que declaram o que a fonte NÃO sustenta**. Este último é o que mais importa — "não citar número" é frase que um arquivo destes pode e deve conter.

**Não toque em `knowledge/sources.lock.json`.** A Fase 5d mediu (`D-5d-2`) que ele é conferido contra uma watchlist derivada, e desde 2026-08-05 a watchlist tem **duas** origens — regras e blocos `Fontes` de `knowledge/**.md`. Meça como o teste se comporta hoje antes de decidir se o lock precisa mudar aqui ou na Task 5.

- [ ] **Step 2: Pergunta 1 — checkpoint é exigência ou recomendação?**

A documentação do GraphFrames **exige** `checkpointDir` em `connectedComponents`, ou recomenda? Registre a frase exata, com URL e data.

Exigir e recomendar dão severidades diferentes, e inventar a diferença é o defeito. Se a fonte disser que o algoritmo **falha** sem checkpoint, é P0; se disser que degrada, é P1 ou P2.

Meça também: a exigência vale para `connectedComponents` só, ou para outros algoritmos? Há `algorithm` alternativo (`graphframes` tem `graphx` e `graphframes` como implementações) que muda a resposta?

- [ ] **Step 3: Pergunta 2 — o default de `maxIter`**

Para cada algoritmo do vocabulário, qual o default de `maxIter`?

**Cuidado com o que decide a regra:** ausente pode significar *"roda até convergir"*, que é **diferente** de *"sem limite"*. `pageRank` tem duas formas — `maxIter` e `tol` —, e exigir `maxIter` de quem passou `tol` acusaria quem escreveu certo.

Se a fonte não fechar para algum algoritmo, escreva isso, e a regra correspondente não entra.

- [ ] **Step 4: Registre o vocabulário real da API**

Liste os algoritmos que o `GraphFrame` expõe, com assinatura. O spec chuta `connectedComponents`, `pageRank`, `shortestPaths`, `labelPropagation`, `triangleCount`, `bfs`, `aggregateMessages`, `pregel` — **confirme e corrija**. Um `frozenset` errado é silêncio no lugar de fact.

Registre também como se constrói um `GraphFrame` e quais são os nomes das colunas obrigatórias (`id`, `src`, `dst`), porque isso pode virar regra depois.

- [ ] **Step 5: A matriz de disponibilidade**

Confirme, com fonte datada, a medição de 2026-08-05:

- Última versão de GraphFrames e quais Spark ela suporta. Há **duas linhagens** — `graphframes` no spark-packages (legado, até 0.8.4) e `io.graphframes` no Maven Central (0.9.0+).
- Cruzando com `GLUE_MATRIX` e `EMR_MATRIX` em `sparkforge/facts/runtime_detect.py`: **quais releases não têm jar nenhum?** A medição diz Glue 4.0 e EMR 6.8.0–6.11.1, todos Spark 3.3.
- A AWS documenta GraphFrames em algum lugar? A medição diz **não** — não é aplicação do EMR, não é módulo do Glue, não há blog. **Isso sustenta a regra do IaC**: se a plataforma não instala, alguém precisa declarar.

Escreva a matriz e datar. Isso muda com um release, e é por isso que a data importa.

- [ ] **Step 6: Suíte e commit**

```bash
python -m pytest -q --no-header
git add knowledge/
git commit -m "docs(knowledge): GraphFrames, e as duas perguntas que decidem regra"
```

**Relate:** a resposta das duas perguntas com a frase que a sustenta; o vocabulário real e onde o spec errou; a matriz de disponibilidade; e o que a doc **não** respondeu.

---

## Task 2: O extrator

**Files:**
- Create: `sparkforge/facts/graph.py`
- Create: `tests/test_facts_graph.py`

- [x] **Step 1: Leia o precedente, e o que ele recusa**

```bash
sed -n '1,90p' sparkforge/facts/data_quality.py
sed -n '233,273p' sparkforge/facts/data_quality.py
sed -n '414,440p' sparkforge/facts/data_quality.py
sed -n '501,584p' sparkforge/facts/data_quality.py
```

Anote quatro mecanismos, porque você vai reusar a **forma** deles:

- `_ScopeIndex` — índice **por escopo**, não por módulo, porque *"nome nu não identifica objeto entre escopos"*.
- `_scopes` — worklist explícita, `FunctionDef` aninhado empurrado para `pending` e excluído de `own`. Não há `NodeVisitor`.
- `_rebind_lines` / `_rebound_between` — religação é **predicado consultado sob demanda**, não invalidação.
- `_chain_root` / `_chained_receivers` — cadeia fluente atribuída uma vez, por **identidade de nó**.

E a regra de governo de `data_quality.py:39-61`: **omitir chave × emitir `false` se decide pelo valor em que a regra consumidora dispara.** Se `false` e ausência calam a regra igualmente, emita o booleano; se `false` dispararia e a ausência é inerte, omita.

- [x] **Step 2: Escreva o teste que falha — a sentinela sai mesmo sem grafo**

```python
# tests/test_facts_graph.py
from sparkforge.facts.graph import extract_graph


def test_arquivo_sem_grafo_ainda_emite_sentinela():
    facts = extract_graph("x = 1\n", "sem_grafo.py")
    kinds = [f.kind for f in facts]
    assert "graph.module_analyzed" in kinds
    sentinela = next(f for f in facts if f.kind == "graph.module_analyzed")
    assert sentinela.measures["algorithm_count"] == 0
    assert sentinela.measures["import_count"] == 0
```

**Meça a assinatura antes de escrever.** A Fase 5d registrou `D-5d-12`: o plano assumiu `path_hint` e **nenhum extrator do repositório tem esse parâmetro**. Confira como `extract_data_quality` recebe o caminho e siga.

- [x] **Step 3: Rode e veja falhar**

```bash
python -m pytest tests/test_facts_graph.py -q
```

Esperado: `ModuleNotFoundError: No module named 'sparkforge.facts.graph'`.

- [x] **Step 4: O mínimo que passa**

Cabeçalho do módulo declarando, em prosa, três coisas — porque o próximo leitor vai perguntar as três:

1. **Por que vocabulário fechado aqui, quando `data_quality.py` o recusa.** A API do GraphFrames é finita; nome de check é aberto. É descrição do domínio, não atalho.
2. **Por que este módulo rastreia `import` quando nenhum outro rastreia.** A regra de disponibilidade afirma "este job usa GraphFrames", e a evidência honesta é o import — não a chamada, que um `getattr` esconde.
3. **O que o módulo não sabe.** Alias, import condicional, `importlib` — o que você decidir não seguir vira `unresolved` contado.

`EMITTED_KINDS` fechado, com guarda de namespace no fim (o padrão de `data_quality.py:1692-1694`, `raise AssertionError` se um kind escapar).

- [x] **Step 5: `graph.import`, com teste primeiro**

Meça o que o corpus real usa antes de decidir o alcance. Formas a considerar:

```python
from graphframes import GraphFrame          # from
import graphframes                          # plain
from graphframes import GraphFrame as GF    # alias
def f():
    from graphframes import GraphFrame      # dentro de função
```

Decida quais você lê e quais viram `graph.unresolved`, **escreva a razão**, e teste as duas listas. Não siga `importlib` — dinâmico é onde a análise estática mente.

- [x] **Step 6: `graph.algorithm` e `graph.construction`**

`GraphFrame(v, e)` é `ast.Call` com `func=ast.Name` — o filtro de `pyspark_ast.py:255` o descartaria, então **não copie aquele laço**.

Para cada algoritmo: `attrs.name`, o receptor, `inside_loop`, e o que a Task 1 mediu sobre limite de iteração. Se `pageRank` aceita `maxIter` **ou** `tol`, o fact precisa dizer qual veio — senão a regra acusa quem passou `tol`.

- [x] **Step 7: `graph.checkpoint_dir` e `graph.source_persisted`**

`setCheckpointDir` é chamado no `SparkContext`, não no grafo. Meça se ele aparece no mesmo escopo, no módulo, ou em qualquer lugar do arquivo — e decida o alcance com argumento.

Para persistência de vértices/arestas: a §9 do spec deixa em aberto se é kind próprio ou atributo. **Meça antes de separar** — a Fase 5d registrou (`D-5d-17`) que correlação entre dois kinds casa objeto errado quando há vários sujeitos no mesmo diretório, e a solução foi pôr a measure no mesmo fact.

- [x] **Step 8: Suíte, ruff, commit**

```bash
python -m pytest -q --no-header && ruff check .
git add sparkforge/facts/graph.py tests/test_facts_graph.py
git commit -m "feat(graph): o extrator do GraphFrames, e o import que vira evidencia"
```

**Relate:** os kinds finais, quantos testes, o alcance que escolheu para `import` e `setCheckpointDir` com o argumento, e onde a Task 1 mudou o desenho.

---

## Task 3: O verbo, nas seis superfícies

**Files:**
- Modify: `sparkforge/adapters/{_core,cli,tools}.py`, `sparkforge/collect/base.py`, `parity.yaml`, `manifest.json`, `tests/test_adapters_*.py`

- [ ] **Step 1: Meça as listas antes de editar**

```bash
grep -n "EXTRACTORS" sparkforge/adapters/_core.py sparkforge/adapters/cli.py sparkforge/adapters/tools.py
grep -n "data-quality\|data_quality" sparkforge/adapters/*.py parity.yaml manifest.json
grep -n "ARTIFACT_KINDS" -A 15 sparkforge/collect/base.py
```

A Fase 5d confirmou **quatro** listas em `tests/test_adapters_tools.py` e achou a **sexta** superfície (`ARTIFACT_KINDS`, tupla fechada validada em `ArtifactEntry.__post_init__`, que levanta `ValueError` na escrita do manifesto — falha tarde). Confirme os números hoje.

`analyze data-quality` é o modelo mais próximo: mesmo artefato (`.py`), mesma forma de verbo.

- [ ] **Step 2: `analyze graph`, um adaptador por vez**

Rodando os testes de adaptador entre eles. `manifest.json` tem contagem de tools que precisa bater com `tools.py`.

- [ ] **Step 3: Rode a cadeia inteira na CLI**

A Fase 4c fechou com um verbo sem `--out` porque ninguém rodou a cadeia. A 5d mediu que a página default de 50 esconde metade da saída em artefato real.

As fixtures são a Task 4, então escreva um `.py` descartável no diretório de scratch — **não** dentro do repositório. Faça-o realista: import, construção, dois ou três algoritmos, um laço.

```bash
python -m sparkforge.adapters.cli analyze graph --path <o .py de scratch> --out facts_graph.json
python -m sparkforge.adapters.cli judge --facts facts_graph.json
```

Cole o resultado, incluindo `total_count` contra `returned_count`. `judge` vai achar zero — as regras são a Task 5 —, e é isso mesmo: aqui você está provando que o verbo produz artefato que o `judge` **aceita**, não que ele acusa algo. Se um arquivo de grafo realista estourar a página default, **escreva isso** — vai para a skill na Task 7.

- [ ] **Step 4: Fechamento**

```bash
python -m pytest -q --no-header && ruff check . && python scripts/sync_skills.py --check
git add -A && git commit -m "feat(graph): analyze graph nas seis superficies"
```

**Nota:** a Fase 5d mediu (`D-5d-21`) que tool nova é **órfã por construção** e `tests/test_agent_coverage.py` reprova no mesmo commit que a cria. Você vai precisar citá-la em algum agente para fechar verde. Se a decisão do coordenador ainda não estiver tomada (é Task 7), cite-a nos executores genéricos e **diga que é provisório**, como a 5d fez.

---

## Task 4: Fixtures

**Files:**
- Create: `fixtures/graph/*/`
- Modify: `scripts/regen_fixtures.py`, `tests/test_fixtures_kind_coverage.py`
- Create: `tests/test_fixtures_golden_graph.py`

- [ ] **Step 1: O regenerador antes das fixtures**

`regen_graph` em `scripts/regen_fixtures.py`, no padrão dos existentes. A Fase 4c teve sete goldens com campo vazio por alguém ter escrito à mão.

**Meça se o domínio tem um ou vários arquivos por fixture.** A 5d registrou (`D-5d-24`) que usar o laço por arquivo em vez da função `_tree` produz ordem que nenhuma superfície emite.

- [ ] **Step 2: As fixtures**

**As regras `SF-GRAPH` ainda não existem** — são a Task 5. Portanto os goldens de findings nascem **vazios**, e a Task 5 os regenera. Isso é esperado, não defeito, e a 5d registrou (`D-5d-28`) que `expects_rules` vazio é ordem do repositório nesta posição.

Mínimo, e ajuste conforme o que a Task 1 mediu:

| Fixture | O que exercita |
|---|---|
| `sem_grafo` | arquivo PySpark sem grafo — sentinela zerada, **nenhum achado** |
| `grafo_correto` | negativo de referência: checkpoint, `maxIter`, arestas persistidas |
| `connected_components_sem_checkpoint` | a regra de checkpoint |
| `algoritmo_sem_limite` | `maxIter` ausente onde a fonte o exige |
| `page_rank_com_tol` | **não acusa** — quem passou `tol` escreveu certo |
| `arestas_nao_persistidas` | a forma de `SF-DQ-003` com outro sujeito |
| `graphframe_em_laco` | construção por iteração |
| `import_sem_jar_no_iac` | a regra que cruza com `tf.attribute` |
| `import_dinamico` | `unresolved` contado, não silêncio |

- [ ] **Step 3: Registre o domínio nos testes de invariante**

```bash
grep -n "data_quality\|dq" tests/test_fixtures_kind_coverage.py | head
grep -n "areas\|SF-" tests/test_rules_catalog_reachability.py | head
```

`test_fixtures_kind_coverage.py` prova o critério 4 do spec. Extrator não registrado ali faz o critério passar **sem ser verificado**, que é pior que falhar.

- [ ] **Step 4: Suíte e commit**

```bash
python -m pytest -q --no-header
git add fixtures/graph/ scripts/regen_fixtures.py tests/
git commit -m "feat(graph): o corpus, e o arquivo sem grafo que continua contado"
```

---

## Task 5: A área `SF-GRAPH`

**Files:**
- Create: `rules/catalog/graph.yaml`
- Modify: `knowledge/sources.lock.json`, `rules/catalog/README.md`

- [ ] **Step 1: Leia o cabeçalho que é o modelo**

```bash
sed -n '1,150p' rules/catalog/emr-infra.yaml
sed -n '50,65p' rules/catalog/README.md
```

O cabeçalho carrega **os vetos** — o que foi considerado e recusado, com razão. Faça igual, incluindo o que a Task 1 vetou por falta de fonte.

- [ ] **Step 2: As regras que sobreviveram**

Uma por vez, cada uma com fixture pronta. `requires_facts` ancorado no fact que **prova a entidade** — nunca na sentinela (`emr-infra.yaml:474-480` registra a lição).

Para as regras de disponibilidade, `runtime_scope` é o mecanismo (D-4 do spec). Escreva o escopo que cobre as células sem jar e **confirme por medição** que uma regra fora do escopo aparece em `skipped` com `reason: runtime_scope`, não sumida.

- [ ] **Step 3: `sources.lock.json`**

As URLs da Task 1 entram aqui, com os IDs das regras que as citam. Meça primeiro como a watchlist se comporta desde que ganhou a segunda origem em 2026-08-05.

- [ ] **Step 4: A verificação de apagabilidade**

Para **cada condição** de **cada regra**, **cada limiar** e **cada ramo de `severity_by`**: apague, rode, confirme vermelho, restaure.

A Fase 5d achou duas conjunções em que metade podia sumir sem nenhum golden reclamar — e era a metade mais cara das duas. Condição que some sem doer **não está testada**.

`test_every_severity_branch_has_a_golden_that_produces_it` já exige golden por ramo desde 2026-08-05; ele reprova sozinho se você esquecer, mas rode a perturbação mesmo assim, porque ele prova existência e não direção.

- [ ] **Step 5: Fechamento**

```bash
python -m pytest -q --no-header && ruff check .
git add rules/catalog/ knowledge/sources.lock.json
git commit -m "feat(rules): area SF-GRAPH, e os vetos que a pesquisa escreveu"
```

**Relate:** quantas regras entraram, quantas foram vetadas e o texto do veto, e o resultado da apagabilidade unidade a unidade.

---

## Task 6: A fronteira, nas três direções

**Files:**
- Create: `tests/test_rules_graph_boundary.py`

- [ ] **Step 1: Leia o precedente e a armadilha que ele resolveu**

```bash
sed -n '1,80p' tests/test_rules_emrs_boundary.py
```

A Fase 5d mediu duas coisas que você precisa:

1. **O `loader` NÃO propaga o `area:` do cabeçalho para dentro da regra.** Só `catalog_version` e `_source_file`. Comparar "pela área declarada" exige ler o documento — `rule["area"]` não existe.
2. Comparar por prefixo de id **passa vacuamente**: classificando por "primeiro prefixo que casa", `SF-EMR` ficava com 15 regras e `SF-EMRS` com zero.

Aqui os prefixos não colidem (`SF-GRAPH` × `SF-DQ` × `SF-PY`), mas o mecanismo de área continua sendo o certo — e reusar o helper que a 5d escreveu é melhor que escrever outro.

- [ ] **Step 2: O teste nas três direções**

Nenhuma regra `SF-GRAPH` dispara sobre golden de `fixtures/dq/` ou de `fixtures/pyspark/`; nenhuma `SF-DQ` ou `SF-PY` dispara sobre `fixtures/graph/`.

**Cuidado com o runtime:** a 5d mediu (`D-5d-39`) que corpora diferentes declaram runtimes diferentes nos `meta.yaml`. Julgue cada direção com o runtime da própria fixture, e inclua o guarda que a 5d escreveu — senão regra pulada por `runtime_scope` some do resultado e o teste fica **verde por skip**. Isso importa mais aqui do que lá, porque esta área **usa** `runtime_scope` de propósito.

- [ ] **Step 3: Desconfie se passar de primeira**

Quebre de propósito — mova uma regra `SF-GRAPH` para o arquivo do `SF-DQ`, ou troque um `requires_facts` para o kind do vizinho — e confirme vermelho **pela razão certa**, não por erro de carregamento. Use cópia do catálogo em scratch via `SPARKFORGE_CATALOG`, como a 5d fez, para não sujar a árvore.

- [ ] **Step 4: Commit**

```bash
python -m pytest -q --no-header
git add tests/test_rules_graph_boundary.py
git commit -m "test(graph): a fronteira com SF-DQ e SF-PY deixa de ser afirmacao"
```

---

## Task 7: Coordenador, docs, fechamento

**Files:**
- Modify: agentes e espelhos, skills, `STATUS.md`, `README.md`, `AGENTS.md`, `AGENT_PROTOCOL.md`, `GUIA_DE_USO.md`, o spec

- [ ] **Step 1: Veja o que o repositório cobra**

```bash
python -m pytest tests/test_agent_coverage.py -q
```

- [ ] **Step 2: A decisão do coordenador**

A §9 do spec deixou em aberto: `pyspark-code-reviewer` estendido ou próprio.

**O critério é o da Fase 4c, refinado pela 5d:** coordenador novo exige **fronteira de despacho** medida — e a 5d mediu que fronteira de **catálogo** não é fronteira de **despacho**. Lá o argumento decisivo foi que `_PLATFORM_KEYS` não tinha discriminador em dado para Serverless, então partir criaria o único par roteado por prosa.

Meça o equivalente aqui: **existe dado que diga, antes de ler o arquivo, que este é um job de grafo?** Se a resposta for "só o conteúdo do `.py`", isso é argumento — e diga para que lado.

Qualquer que seja a decisão, a `description` precisa dizer a verdade sobre o que o agente cobre. A 5d mediu que `description` é o **gatilho de seleção**, não decoração.

- [ ] **Step 3: Skill**

Se a fase ganhar skill própria ou entrar numa existente, ensine o verbo onde a skill ensina os outros. **Edite fonte, nunca espelho** — `scripts/sync_skills.py` é tradutor.

A 5d mediu (`D-5d-42`) que `description` de skill tem teto de 1024 e o orçamento restante pode ser de ~130 caracteres. Meça antes de escrever.

Se a Task 3 mediu que arquivo de grafo realista estoura a página default, **isso vai para a skill**, no ponto onde ela ensina o verbo.

- [ ] **Step 4: Meça os números**

```bash
python -c "import json;print(len(json.load(open('manifest.json'))['tools']))"
python -m pytest -q --no-header 2>&1 | tail -2
```

Regras, áreas, extratores, kinds, fixtures, domínios, tools, fontes vigiadas, testes. `README.md` e `STATUS.md` costumam estar certos, mas a revisão da 5d mediu **dois erros de contagem no próprio STATUS** — reconte tudo. `AGENTS.md` é o espelho em inglês que envelhece.

- [ ] **Step 5: A seção de desvios do spec**

O spec **não é reescrito**: ganha `## 11. Desvios` com os `D-6a-*` que **tornam o documento errado** — não todos, só os que contradizem o texto. O `Status:` deixa de dizer "não implementado".

- [ ] **Step 6: `STATUS.md`**

A linha `SF-GRAPH` do roadmap de bancos passa a apontar para esta fase como concluída. Registre as dívidas e limites que a fase abriu, **com a natureza de cada um** pelo critério de triagem: dívida é código que ninguém escreveu; fase é trabalho planejado; limite declarado é decisão registrada cujo custo já foi medido.

Recontagem por linha das três tabelas — **não some de cabeça**.

- [ ] **Step 7: Fechamento**

```bash
python -m pytest -q --no-header && ruff check . && python scripts/sync_skills.py --check
git add -A && git commit -m "docs(fase6a): SF-GRAPH ganha coordenador, e o roadmap de bancos abre"
```

**Relate:** a decisão do coordenador com o argumento medido; cada número medido e quais estavam errados; as dívidas registradas; e onde o plano não sobreviveu.

---

## Desvios (`D-6a-*`)

Registre aqui cada ponto em que a medição contrariou este plano. Formato: `**D-6a-N** — o que o plano dizia; o que a medição mostrou, com `arquivo:linha`; o que você fez.`

**D-6a-1 — "não toque em `sources.lock.json`" e "suíte verde" são incompatíveis nesta task.**
O plano (Step 1) manda não tocar no lock e deixar a decisão para a Task 5; o Step 6
exige `pytest -q` verde. Medido: `tests/test_refresh_knowledge.py:271` exige
`set(lock["sources"]) == set(watchlist())`, igualdade **exata**, e
`scripts/refresh_knowledge.py:195` deriva URLs de **todo** bloco `## Fontes` de
`knowledge/**.md`. Escrever qualquer página de knowledge com fonte datada —
que é o padrão do repositório e o objetivo desta task — quebra esse teste por
construção. Baseline: watchlist 109 = lock 109. Depois das duas páginas:
watchlist **131**, lock 109, **22 novas, 0 sumidas**. Resolvi pelo mecanismo que
o próprio repositório declara para este caso: `python scripts/refresh_knowledge.py
--update --offline`. `sync_metadata` (`refresh_knowledge.py:370-384`) existe
literalmente porque *"uma regra nova ou uma pagina de knowledge nova mudam o lock
sem que nada tenha sido conferido"*, e **nunca inventa `sha256` nem `checked_at`**
— as 22 entradas ficaram sem hash, com `rules: []` e o back-link `docs` derivado.
A Task 5 re-roda quando as regras citarem as URLs, e aí o `rules` se preenche
sozinho. O que a Task 5 **não** herda pronto é decisão nenhuma: o conjunto é
derivado, não escolhido.

**D-6a-2 — uma URL do bloco `Fontes` teria virado alarme permanente.**
A primeira redação citava `https://repos.spark-packages.org/graphframes/graphframes/`
como base das medições por artefato. Essa URL responde `NoSuchKey`/404 (o bucket
não serve listagem), e entraria na watchlist como fonte móvel ilegível para
sempre. Pus a base em crase, que é exatamente a convenção que
`refresh_knowledge.py:210-214` documenta para padrão-de-caminho, e a contagem
caiu de 23 para 22 novas. Sem isso a fase entregaria um `unreachable` eterno.

**D-6a-3 — o vocabulário do spec está incompleto, e um item dele não é chamada.**
O spec (§5 e §6) chuta oito nomes. Os oito existem, mas `pregel` é `@property` nas
duas linhagens, assim como `triplets`, `degrees`, `inDegrees` e `outDegrees` — um
`frozenset` casado só contra `ast.Call` **não emite fact para o Pregel**, que é o
único algoritmo cujo limite de iteração o usuário controla de fato. Faltam ainda
`stronglyConnectedComponents`, `parallelPersonalizedPageRank`, `svdPlusPlus` e
`find` já na 0.8.3, mais treze nomes acrescentados de 0.9.0 a 0.12.0 — em
`snake_case`, convivendo com o `camelCase` antigo no mesmo objeto. Detalhe em
`knowledge/graph/graphframes-api.md` §3.

**D-6a-4 — a regra "algoritmo iterativo sem `maxIter`" não entra, e não é por falta de fonte.**
O plano (Step 3) previa que a fonte pudesse não fechar. Fechou, e no sentido
oposto: em nenhum dos dezesseis algoritmos com noção de iteração "ausente" é
defeito. Em seis é `TypeError`/`AssertionError` — código que não roda; em três é
default documentado (2, 10, 3); em `pageRank` é o modo `tol`, oficial e
recomendado; e em `connectedComponents` a doc diz textualmente *"Default is
`Integer.MAX_VALUE` (unlimited). It is generally not recommended to change this
value."* A fixture `algoritmo_sem_limite` da Task 4 **não tem regra para
exercitar** e precisa ser repensada ou removida. Ver `graphframes-api.md` §5.

**D-6a-5 — a exigência de checkpoint tem três saídas no `.py` e uma quarta fora dele.**
O plano (Step 2) pergunta se é exigência ou recomendação. É exigência e o
algoritmo **falha** (`throw new IOException`), o que autoriza P0 — mas
`algorithm="graphx"`, `checkpointInterval<=0` e `use_local_checkpoints=True`
tornam a exigência inaplicável, e a conf `spark.checkpoint.dir` (0.9.3+) a
satisfaz **de fora do artefato**. A regra da Task 5 precisa das três negações e
da ressalva escrita dentro do achado, no padrão de `V-AS-2`. E os valores de
`algorithm` que o plano supõe (`graphx`/`graphframes`) estão desatualizados:
hoje são `graphx`, `two_phase`, `randomized_contraction`, com `graphframes` como
**alias depreciado**.

**D-6a-6 — a hipótese da matriz de disponibilidade se confirma, e por um motivo mais forte.**
O plano diz que Glue 4.0 e EMR 6.8.0–6.11.1 não têm jar. Medido: **9 das 34
células**, exatamente essas. Mas a razão não é "a versão é antiga": é que
**nenhum artefato foi publicado para Spark 3.3 em linhagem nenhuma** — `0.8.2`
para em 3.2, `0.8.3` começa em 3.4, e `io.graphframes` compila contra 3.5. A
release note da `0.8.3` afirma *"Support Spark 3.3 / Scala 2.12"* e o jar
`0.8.3-spark3.3-s_2.12` responde **404**. Consequência de desenho: o
`runtime_scope` da Task 5 deve ser escrito por **Spark 3.3.x**, não por lista de
release — cobre as nove de uma vez e não envelhece a cada release nova de EMR.

**D-6a-7 — `graph.source_persisted` não existe: virou atributo, e a §9 do spec previa a pergunta.**
O spec (§4) lista o kind na tabela de facts. Medido: um kind separado precisaria
ser reunido ao `graph.construction` **por nome de variável**, que é exatamente a
correlação que `D-5d-17` mostrou casar objeto errado — e dois `GraphFrame(...)`
no mesmo arquivo são o caso literal. `vertices_persisted` e `edges_persisted`
são atributos do próprio `graph.construction`. Fica **6 kinds**, não 7. A §9 do
spec autorizava a decisão ("medir antes de separar"); a §4 é que fica errada.

**D-6a-8 — a assinatura do extrator é `(source, path)`, não `(tree, path, sha)`.**
O plano (Step 2) escreve `extract_graph("x = 1\n", "sem_grafo.py")` e manda
medir. Medido: `extract_data_quality(tree, path, artifact_sha256="")`
(`data_quality.py:1627`) recebe **árvore**; `extract_source(source, path)`
(`pyspark_ast.py:200`) recebe **texto**. O modelo certo é o segundo, e não por
gosto: a sentinela e o `graph.unresolved` de `syntax_error` só existem se o
próprio extrator tentar o parse, e quem recebe árvore pronta nunca vê o
`SyntaxError`. O teste do plano já assumia isso sem dizer.

**D-6a-9 — o motor não sabe dizer "a chave não está lá", e isso decidiu o desenho do fact.**
O plano (Step 7) trata a exigência de checkpoint como correlação entre facts.
Medido: `engine._where_matches` (`rules/engine.py:31-37`) compara por
**igualdade** e reprova caminho ausente, e `_expr_matches` engole o `ExprError`
devolvendo `False` — então `attrs.algorithm_arg != "graphx"` é **falso quando a
chave não existe**, que é o caso comum. Nenhuma regra consegue exprimir "o
código não declarou saída nenhuma". Logo quem enxerga as três saídas de uma vez
é o extrator, e ele emite `checkpoint_required` **já decidido**, mais
`checkpoint_configured_in_module` no mesmo fact. É o padrão que `SF-EMR-008`
fixou e que `data_quality.py:6-12` declara — não juízo: severidade e limiar
continuam no catálogo.

**D-6a-10 — o `pregel` foi resolvido por `ast.Attribute` mais travessia para FORA, e não por `ast.Call`.**
`D-6a-3` avisou que um `frozenset` casado contra `ast.Call` não emite fact para o
Pregel. A solução: `pregel`, `triplets`, `inDegrees`, `outDegrees` (e `degrees`,
ver `D-6a-11`) são casados como `ast.Attribute` em contexto `Load` que **não é o
`func` de uma `Call`**; a partir desse nó a cadeia é percorrida **para fora**
pelo mapa de pais, o que recupera `setMaxIter(10)` de
`g.pregel.setMaxIter(10)...run()`. Todos os outros extratores caminham só para
dentro (da chamada para a raiz) e por isso nunca precisaram de mapa de pais —
este é o primeiro que precisa, e a razão está no `_pregel_chain`.

**D-6a-11 — o vocabulário tem DOIS níveis, e três nomes da API ficaram de fora.**
O plano e o spec supõem um `frozenset` único. Medido contra o risco de homônimo:
`find` é método de `str`, e `validate`/`degrees` são identificadores que
qualquer objeto de usuário pode ter — casá-los sempre produziria `graph.algorithm`
sobre `"abc".find("b")`, que é **acusação falsa**, o pior modo de falha desta
área. Eles são lidos **só quando o módulo importa GraphFrames**, que é a
evidência independente que o `D-3` do spec justifica. E `cache`, `persist` e
`unpersist` — que a API do `GraphFrame` de fato expõe — ficam **fora do
vocabulário de algoritmo**: `pyspark.cache` já os emite sobre o mesmo artefato,
e reemiti-los duplicaria o sujeito de `SF-PY-008` e apagaria justamente a
fronteira que a Task 6 tem de provar. Entram só como evidência de persistência.

**D-6a-12 — a conf de checkpoint às vezes ESTÁ no `.py`, e ignorá-la seria um P0 falso.**
A pesquisa (§8) trata `spark.checkpoint.dir` e
`spark.graphframes.useLocalCheckpoints` como saídas **fora do artefato**. Verdade
quando vêm do IaC ou do `--conf` — mas `spark.conf.set("spark.checkpoint.dir",
...)` dentro do próprio job é forma corrente, e não lê-la faria a regra P0
disparar sobre código que configurou o checkpoint na linha de cima. O extrator lê
as duas confs e as emite como `graph.checkpoint_dir` com `form`
(`set_checkpoint_dir`, `conf_checkpoint_dir`, `conf_local_checkpoints`). A
ressalva da regra continua valendo para o que vem de fora — o alcance do módulo
não mudou, só deixou de ser cego ao que está dentro.

**D-6a-13 — o alcance de `setCheckpointDir` é o ARQUIVO, e o argumento é o objeto.**
O plano (Step 7) pede a decisão entre escopo, módulo e arquivo. `setCheckpointDir`
é chamado no `SparkContext`, que é **singleton do processo**: o diretório vale
para a aplicação inteira, não para um escopo de nome. A forma canônica de job
Glue/EMR configura a sessão num `build_spark()` e roda o algoritmo noutra função
— correlacionar por escopo produziria P0 sobre exatamente essa forma correta. O
inverso continua valendo para nome de **dado**: vértices e arestas são apurados
**por escopo**, porque ali dois nomes iguais são dois objetos. Não há dois
`SparkContext`.

**D-6a-14 — `v = vertices.cache()` teria saído como "não persistido".**
Medição durante a implementação, e é acusação falsa sobre a forma mais comum de
persistir em job real: `_persist_events` casando só a **raiz da cadeia** registra
o evento em `vertices` e não em `v`, e `GraphFrame(v, e)` saía com
`vertices_persisted: false`. A correção registra o evento nos **dois** nomes —
raiz da cadeia e alvo da atribuição. `data_quality._persist_events` tem o mesmo
recorte e o mesmo furo, mas lá o alvo do check é o nome da raiz, então ele não
aparece; aqui aparece porque o sujeito é o argumento do construtor.

**D-6a-15 — o `_SOURCE_TERMINALS` de `data_quality.py` é necessário aqui pelo mesmo motivo.**
Nem o plano nem o spec o mencionam para esta fase. Medido:
`GraphFrame(spark.read.parquet(p), e)` fazia `vertices_ref` sair como `"spark"` —
a raiz da cadeia é a **sessão**, não o dado — e a persistência passaria a ser
apurada sobre a sessão. A lista é a mesma de `data_quality.py:161`, e o
`_data_root` que a consome é o análogo de `_chain_target`.

**D-6a-16 — um ponto cego por chamada, porque `Fact.id` deixa `attrs` de fora.**
`Fact.id` é sha de `kind + subject + measures` (`findings/models.py:41-55`), e
`graph.unresolved` não tem measures. Dois `unresolved` sobre o **mesmo nó** —
`g.connectedComponents("graphx", algorithm=x)` produz `positional_argument` e
`non_literal_argument` — sairiam com **id idêntico**, e o `fact_id` que um
Finding cita deixaria de identificar evidência. Decidido: no máximo um
`graph.unresolved` por chamada de algoritmo, com precedência argumento antes de
receptor, porque é o argumento que suprime a decisão de checkpoint. Há teste de
unicidade de id sobre arquivo denso.

**D-6a-17 — as referências de linha do plano e do spec envelheceram.**
`pyspark_ast.py:255` (o filtro que descarta o que não é `ast.Attribute`, citado
no plano Step 6 e na §1 do spec) está hoje em **`pyspark_ast.py:264`**. A guarda
de namespace citada como `data_quality.py:1692-1694` está em **1692-1694** —
essa confere. Nenhuma das duas muda decisão; ficam registradas porque o próximo
leitor vai conferir.

**D-6a-18 — a sexta superfície não tem entrada nova a fazer, e a medição por falha é que provou.**
O Step 1 manda conferir `ARTIFACT_KINDS` (`sparkforge/collect/base.py:29`), a
tupla fechada que a Fase 5d achou tarde. Medido: `analyze graph` lê o mesmo
artefato de `analyze data-quality` — um `.py` do repositório —, cujo `kind` é
`"source"`, **já declarado** em `collect/base.py:38`. A tupla é o vocabulário de
artefato **coletado** (`ArtifactEntry`, escrito por `collect/aws.py:162,185`), e
verbo que lê arquivo local do repo não cria linha de manifesto. Com o verbo
inteiro implementado e nenhuma das seis superfícies declarativas atualizada, a
suíte reprovou **6 testes em 4 arquivos** e **nenhum** deles em
`tests/test_collect_base.py`. A sexta superfície continua sendo real; ela só não
é atravessada por esta fase. Ela volta a valer se a Fase 6a ganhar coletor.

**D-6a-19 — "quatro listas em `test_adapters_tools.py`" era para tool de COLETA; para tool de análise é uma.**
O Step 1 repassa o número que a 5d confirmou. Medido por falha, com o verbo
implementado e os testes intocados, as coleções que reprovam são:
`tests/test_adapters_tools.py::TestToolSurface::test_the_full_tool_surface_is_declared`
(o `set(TOOLS)` literal, linha 30) e a cadeia `if name == ...` de
`_real_output_for` (linha 988, que **não é lista** e reprova como
`test_real_output_matches_declared_schema[sparkforge_analyze_graph]`);
`tests/test_capability_parity.py` **duas** vezes
(`test_every_phase_zero_tool_appears_in_some_capability` e
`test_every_cli_verb_has_an_mcp_tool_or_a_declared_reason` — esta última cita o
verbo por nome: `['analyze graph']`); `tests/test_docs_coverage.py::TestManifest::test_tools_list_equals_the_real_tools_keys`
(que é onde mora a "contagem de tools" do `manifest.json` — não existe campo
`tool_count`, o invariante é `len(manifest["tools"]) == len(TOOLS)`, linha 227);
e `tests/test_agent_coverage.py::test_no_tool_is_orphan`. As outras **três**
listas manuais daquela classe — `open_world`, os não-`readOnly` e a de
`test_only_case_and_report_writers_are_not_read_only` — só mudam para tool que
toca rede ou escreve, que é o caso de `collect_emr_serverless` da 5d, não o de um
`analyze_*`. `FAILABLE` (linha 1282) confirmou o outro lado do que a 5d
registrou: **nenhum teste a deriva de `TOOLS`**, ela ficou silenciosa, e a
entrada foi acrescentada mesmo assim — uma tool de fronteira sem caso de erro
declarado é schema de sucesso prometido como total.

**D-6a-20 — a tool órfã foi fechada no executor genérico, e é provisório.**
`test_no_tool_is_orphan` reprovou no mesmo commit que criou a tool
(`1 de 41 tools nao sao alcancaveis`), exatamente como `D-5d-21` previu. Citada
em `agents/executors/sf-extractor.md`, na tabela artefato→tool, que é onde a 5d
pôs `sparkforge_analyze_emr_serverless`. **Provisório de propósito**: nenhum
coordenador temático cita `sparkforge_analyze_graph`, porque a `description` do
coordenador é o **gatilho de seleção** e citar área que a Task 7 ainda não
decidiu afirmaria cobertura que não existe. A Task 7 decide se `SF-GRAPH` ganha
coordenador próprio ou entra em `pyspark-code-reviewer`.

**D-6a-21 — arquivo de grafo realista NÃO estoura a página default.**
O Step 3 manda escrever se estourar, porque a 5d mediu que 50 esconde metade da
saída em artefato real. Medido sobre um `.py` de 71 linhas com dois imports,
duas construções, cinco algoritmos (`connectedComponents`, `pageRank`,
`triangleCount`, `aggregateMessages` dentro de um `for`, e `pregel` como
`@property`) e um `setCheckpointDir` noutra função: **`total_count` 11,
`returned_count` 11, `next_cursor: null`, `unresolved: 0`**. A razão é de
desenho e não de tamanho do arquivo: este extrator emite **um fact por evento de
grafo**, não um por linha de código nem um por partição — `emrs.*` e `emr.*`
emitem por propriedade de configuração, e é por isso que eles enchem a página.
Um diretório inteiro multiplica pelo número de módulos **que usam grafo**, e o
`graph.module_analyzed` por `.py` é o único termo que cresce com a árvore. A
skill da Task 7 não precisa de aviso de paginação para arquivo único; precisa
dele para `--path src/`.

**D-6a-22 — as duas fixtures que o plano lista para a regra de `maxIter` saíram, e uma virou asserção.**
A tabela do Step 2 pede `algoritmo_sem_limite` e `page_rank_com_tol`. Com a regra
vetada por `D-6a-4`, a primeira **não tem nada para exercitar**: uma fixture cujo
único propósito é uma regra vetada é a regra vetada entrando pela porta dos
fundos, e ela seria o corpus que alguém citaria para reabrir a discussão. Saiu.
A segunda foi **dobrada dentro de `grafo_correto`** — `pageRank(tol=0.01)` no
mesmo job correto —, porque o que ela prova não é uma regra e sim a **forma do
fact**: `iteration_arg` nomeia o parâmetro que veio, e sem ele uma regra sobre
"limite de iteração" não distinguiria `maxIter` de `tol`. O veto ganhou teste
próprio no lugar da fixture:
`test_no_fact_claims_a_missing_iteration_limit` varre o corpus inteiro e reprova
se qualquer fact passar a carregar `has_max_iter`, `max_iter_missing`,
`iteration_limited`, `unbounded` ou `has_iteration_limit` — bastaria um deles
para alguém escrever `where: {attrs.has_max_iter: false}`.

**D-6a-23 — o corpus tem 19 fixtures, e as 4 saídas do checkpoint viraram 5.**
A tabela do plano lista 9. Medido: `D-6a-12` diz que a conf de checkpoint tem
**duas grafias** (`spark.checkpoint.dir` e
`spark.graphframes.useLocalCheckpoints`), e elas são caminhos diferentes em
`_checkpoint_facts` — a primeira só lê o literal, a segunda passa por `_truthy` e
pode virar `unreadable`. Uma fixture por caminho:
`saida_graphx`, `saida_intervalo_nao_positivo`, `saida_local_checkpoints`,
`conf_checkpoint_dir_no_job`, `conf_local_checkpoints_no_job`. Mais
`conf_local_checkpoints_ilegivel`, que é o **sexto** estado e o único em que a
decisão some do fact: `checkpoint_required` **ausente**, ponto cego contado.
Sete das dezenove existem só para provar que o motor cala.

**D-6a-24 — `regen_graph` usa a função `_tree`, e a fixture que torna isso mediável precisou ser construída de propósito.**
O Step 1 manda medir qual forma o adaptador usa. Medido:
`adapters/_core.py:943` chama `extract_graph_tree`, que termina em `sort_facts`
— ordem **global** por (kind, subject, id) — enquanto um laço por arquivo
concatena blocos já ordenados por arquivo. Mas a diferença **não aparece
sozinha**: na primeira redação de `fonte_que_nao_compila` o arquivo quebrado se
chamava `quebrado.py`, e como o único fact dele é um `graph.unresolved` — que
ordena por último no alfabeto de kinds de qualquer jeito — as duas ordens
**coincidiram** e o teste passou vazio. Renomeado para `carga_quebrada.py`
(`c` < `j`), o laço põe o `unresolved` na frente e a divergência fica real.
`test_the_tree_order_is_the_one_the_product_emits` afirma as três coisas:
as ordens divergem, a diferença é **só** de ordem, e o golden é a da `_tree`.
Sem a renomeação, D-5d-24 continuaria sendo convenção repetida em vez de
medição.

**D-6a-25 — o corpus de grafo carrega Terraform, e é a única forma de a regra de disponibilidade ter metade negativa.**
Nem o plano nem `regen_dq` preveem fonte mista neste domínio. Medido: a regra do
IaC (`availability.md` §5) afirma "a plataforma não instala, então alguém
precisou declarar o jar", e sem os `tf.attribute` do mesmo job ela acusaria
**todo** job de grafo em Spark 3.3 — inclusive quem resolveu o problema.
`regen_graph` estende `regen_infra_code`/`regen_s3`: extrai Terraform quando há
`*.tf` sob `input/`. O par `import_sem_jar_no_iac` × `import_com_jar_declarado`
compartilha o `.py` **byte a byte** e difere só no `--extra-jars`, e os dois
declaram `runtime` Glue 4.0 / Spark 3.3.0 — o resto do corpus é 5.0 / 3.5.4.
Efeito colateral medido e corrigido: com o `.tf` escrito no molde de
`fixtures/infra_code/`, **SF-GLUE-002 disparava** (P1, observabilidade ausente),
e um golden de findings não vazio nesta posição esconderia a primeira regra
`SF-GRAPH` que aparecer. Os dois `.tf` ganharam `--enable-spark-ui` e
`--spark-event-logs-path`; `--enable-observability-metrics` ficou **de fora de
propósito**, porque `pyspark.glue_context_init` não é emitido neste corpus e o
`absent:` de SF-ENV-003 seria vacuamente verdadeiro.

**D-6a-26 — o golden de `syntax_error` é contrato com o interpretador, e foi medido nas três versões.**
`fonte_que_nao_compila` é a primeira fixture do repositório a exercitar
`syntax_error`, e `detail=str(exc.msg)` põe a **mensagem do CPython** dentro do
golden — em corpus que o CI roda em 3.10 **e** 3.11
(`.github/workflows/ci.yml:21`). Medido antes de commitar, com o mesmo arquivo:
CPython 3.10.20, 3.11.15 e 3.14.6 devolvem `'(' was never closed`, linha 5,
coluna 16 — idênticos. O corpus `graph` inteiro foi reproduzido byte a byte nas
três. A asserção da mensagem está no teste adversarial, com o porquê escrito ao
lado: se um interpretador futuro reescrever a frase, o teste falha **com nome**
em vez de virar diff mudo no golden. Nenhuma fixture cobre `read_error`, e a
razão é declarada: ele exige arquivo ilegível pelo sistema de arquivos, que não
se versiona de forma portável entre Windows e Linux.

**D-6a-27 — o extrator NÃO emite sentinela para arquivo que não compila, e o corpus fixa isso.**
O cabeçalho de `graph.py` diz "sentinela sempre emitida"; medido, `extract_graph`
retorna **antes** dela quando o `ast.parse` levanta (`graph.py:1103-1120`), e o
arquivo sai com um `graph.unresolved` e nada mais. Não é defeito — o
`unresolved` já responde "não consegui ler", que é a pergunta que a sentinela
existe para separar de "não há grafo" —, mas **muda o invariante**: a versão do
`dq` (`sum(module.measures[...]) == len(facts)`) esconderia o arquivo que ficou
de fora da contagem. Aqui a conferência é **por arquivo**, e
`test_a_file_that_does_not_compile_has_no_sentinel_and_stops_nothing` fixa que
os `graph.module_analyzed` do diretório são `{job.py}` e não `{job.py,
carga_quebrada.py}`.

**D-6a-28 — os três contrafactuais do registro de domínio, medidos um a um.**
O Step 3 manda registrar e medir. Registrado em `test_fixtures_kind_coverage.py`
(dicionário `EXTRACTORS`) e em `test_rules_catalog_reachability.py` (tupla
`EXTRACTORS`). Medido tirando cada peça:
(1) sem `"graph": graph` no dicionário,
`test_no_golden_carries_a_kind_that_no_extractor_declares` reprova **nomeando os
seis** `graph.*` — e é essa direção que pega o esquecimento, não a que o Step 3
cita;
(2) com um sétimo kind declarado que nenhum golden produz,
`test_every_kind_of_every_extractor_appears_in_some_golden[graph]` reprova
nomeando o kind;
(3) sem `tests/test_fixtures_golden_graph.py`,
`test_every_fixture_domain_has_a_golden_module` reprova com
`dominios de fixture sem modulo golden: ['graph']`.
A terceira lista é a que o plano não menciona e é a mais fácil de perder: o gate
de `verify_wheel.py` roda **módulos**, não diretórios.
