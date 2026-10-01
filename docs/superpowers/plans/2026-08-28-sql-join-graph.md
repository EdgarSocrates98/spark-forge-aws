# Grafo de joins — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dizer **o que** está de cada lado de cada join — hoje `plan.join` diz que o build side é o esquerdo, e nada diz qual tabela é essa.

**Architecture:** Dois kinds novos em `sparkforge/facts/sql_metrics.py`, o módulo que já percorre o `sparkPlanInfo` do event log. `spark.sql.join` por nó de join, `spark.sql.join_input` por aresta `(join, relação, lado)` com `via_joins`. Nenhuma superfície nova: o extrator já é executado por `analyze sql-metrics` e pela tool que o expõe.

**Tech Stack:** Python 3, `pytest`. Spec: [`../specs/2026-08-28-sql-join-graph-design.md`](../specs/2026-08-28-sql-join-graph-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Fact nunca aplica limiar, nunca atribui severidade, nunca toca a rede.
- Todo fact declara `subject.type` do enum fechado. Aqui é sempre `plan_node`, via `_plan_node_subject`.
- Lint ruff `E,F,I,UP,B,S`, linha máxima 100.
- Todo comando com prefixo `rtk`. Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>`.
- Não rode a suíte inteira sem alvo (17 minutos), exceto onde a tarefa pedir.
- Não faça `git add` dos untracked pré-existentes na raiz. Cuidado com `git add .claude` — ele varre um `.bak`.

**Estado do módulo antes desta entrega** (leia antes de qualquer tarefa):

- `_walk(node, proximo)` percorre a árvore em preorder, numerando os nós; **não devolve pai nem filhos**.
- `_scan_of(node)` devolve `(scan_api, relation, format)` ou `None`.
- `_Execution` tem `nodes` (só os nós de scan), `nodes_total`, `accum`, `reassigned`, `values`, `ended`.
- `_Execution.absorb_plan(plano, source)` faz duas passadas de `_walk`: uma para os scans, outra para o mapa de acumuladores.
- `extract_sql_metrics(lines, path)` emite `spark.sql.scan`, `spark.sql.unresolved`, `spark.sql.execution`, `spark.sql.analyzed`.

---

## Estrutura de arquivos

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/facts/sql_metrics.py` | Conserto do AQE (Task 1), estrutura da árvore, `spark.sql.join` e `spark.sql.join_input` |
| `tests/test_facts_sql_metrics.py` | Casos do conserto e do grafo |
| `fixtures/sql_metrics/` | Quatro cenários novos |
| `tests/test_fixtures_golden_sql_metrics.py` | `REQUIRED_FIXTURES` e a garantia do corpus |
| `README.md`, `docs/superpowers/STATUS.md` | Números medidos e a fase |

**Não modificar:** `manifest.json`, `parity.yaml`, `tools.py`, `cli.py`, `_core.py`, `agents/`. Esta entrega não acrescenta superfície — ver §5 da spec.

---

## Task 1: O conserto do AQE que a entrega anterior deixou passar

**Files:**
- Modify: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

`absorb_plan` reseta `self.accum` a cada árvore absorvida, e `self.values` persiste. Sob AQE isso perde dado **em silêncio**: um valor publicado contra o plano inicial fica órfão quando a árvore é reposta, porque `measures_by_node` só itera `self.accum`. A spec de C1 (§3.5) manda o contrário — *"valores já acumulados continuam atribuídos ao nó que declarou aquele acumulador; eles foram medidos sob aquele plano"*.

Vem primeiro porque as Tasks 2-3 mexem no mesmo método, e consertar depois seria mexer duas vezes.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_sql_metrics.py`, na classe `TestAQE`:

```python
    def test_value_published_before_the_replan_is_not_lost(self):
        inicial = _scan_node(metrics=[_metric("number of files read", 11)])
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [
                _start(plan=inicial),
                _driver_update(0, [[11, 3]]),  # publicado ANTES da reposta
                _aqe(0, final),
                _end(0),
            ],
            "log.jsonl",
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # O valor foi medido sob o plano inicial, e o no continua sendo o mesmo
        # scan. Descarta-lo faria a extracao devolver menos bytes do que o
        # Spark publicou, sem dizer que descartou.
        assert scan.measures["files_read"] == 3

    def test_value_lost_to_a_replan_is_never_silent(self):
        """Se o no do acumulador antigo sumiu do plano novo, e lacuna.

        Nao ha nó a que atribuir, e o silencio faria a soma sair menor sem
        nenhum sinal.
        """
        inicial = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="FileScan parquet db.some[id#9]",
                    metrics=[_metric("number of files read", 12)],
                ),
            ],
        }
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [_start(plan=inicial), _driver_update(0, [[12, 5]]), _aqe(0, final), _end(0)],
            "log.jsonl",
        )
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "value_orphaned_by_replan"
        ]

        assert len(lacunas) == 1
        assert lacunas[0].attrs["accumulator_id"] == 12
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py::TestAQE -v
```

Esperado: FAIL nos dois casos novos — o valor some e nenhuma lacuna é emitida.

- [ ] **Step 3: Implementar**

Em `_Execution.__init__`, acrescente o histórico dos mapas já vistos:

```python
        # Mapa acumulado de TODAS as arvores desta execucao. `accum` guarda a
        # arvore corrente, que e quem define identidade de no; este guarda o
        # que ja foi declarado antes, para que um valor medido sob o plano
        # inicial nao evapore quando o AQE repoe a arvore.
        self.accum_historico: dict[int, tuple[int, str]] = {}
```

Em `absorb_plan`, antes de `self.accum = {}`, preserve o que existia:

```python
        self.accum_historico.update(self.accum)
```

E em `add_value`, aceite acumulador conhecido em qualquer das duas árvores:

```python
    def add_value(self, accum_id: int, valor: float) -> bool:
        """Soma um valor a um acumulador conhecido. Devolve se ele foi atribuido."""
        if accum_id in self.reassigned:
            return False
        if accum_id not in self.accum and accum_id not in self.accum_historico:
            return False
        self.values[accum_id] = self.values.get(accum_id, 0.0) + valor
        return True
```

Em `measures_by_node`, itere os dois mapas, com a árvore corrente vencendo, e devolva os órfãos:

```python
    def measures_by_node(
        self,
    ) -> tuple[dict[int, dict[str, Any]], list[tuple[int, str]], list[int]]:
        """`{node_id: {measure: valor}}`, os nomes fora do mapa, e os orfaos.

        Um acumulador declarado numa arvore anterior continua valendo se o
        `node_id` dele ainda existe no plano corrente: o valor foi medido, e o
        no e o mesmo. Se o no sumiu, o valor nao tem onde pousar -- e isso vira
        lacuna nomeada, nunca silencio.
        """
        conhecidos: dict[int, tuple[int, str]] = dict(self.accum_historico)
        conhecidos.update(self.accum)

        por_no: dict[int, dict[str, Any]] = {}
        desconhecidos: list[tuple[int, str]] = []
        orfaos: list[int] = []
        for accum_id, (node_id, nome) in sorted(conhecidos.items()):
            if accum_id not in self.values:
                # Metrica declarada no plano e nunca publicada. Ausencia, nao zero.
                continue
            if node_id not in self.nodes:
                orfaos.append(accum_id)
                continue
            measure = measure_for(nome)
            if measure is None:
                desconhecidos.append((node_id, nome))
                continue
            valor = self.values[accum_id]
            por_no.setdefault(node_id, {})[measure] = (
                int(valor) if float(valor).is_integer() else valor
            )
        return por_no, desconhecidos, orfaos
```

**Atenção à ordem das checagens:** `accum_id not in self.values` vem **antes** de tudo. Métrica declarada e nunca publicada não é órfã nem desconhecida — é ausência, e contá-la como lacuna encheria o relatório de ruído para todo plano que declara mais métricas do que publica, que é o caso comum.

No laço de emissão de `extract_sql_metrics`, ajuste o desempacotamento e emita a lacuna:

```python
        por_no, desconhecidos, orfaos = execucao.measures_by_node()
```

e, junto das outras lacunas da execução:

```python
        for accum_id in orfaos:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "value_orphaned_by_replan",
                        "accumulator_id": accum_id,
                        "detail": (
                            "Valor publicado contra um no que sumiu do plano corrente, "
                            "provavelmente numa reposta de AQE. O numero foi medido, mas "
                            "nao ha no a que atribui-lo; soma-lo a outro no poria bytes no "
                            "lugar errado."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
```

Atualize o docstring de `absorb_plan` para dizer o que ele preserva e por quê.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS, incluindo os dois casos novos. Reporte a contagem real.

- [ ] **Step 5: Conferir os goldens**

```bash
rtk pytest tests/test_fixtures_golden_sql_metrics.py -v
```

O cenário `aqe_replans_the_scan` pode mudar de saída — a mudança é o conserto aparecendo. Leia o diff, confirme que ele reflete o que o teste novo descreve, regrave e diga no relatório o que mudou.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py fixtures/sql_metrics
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `fix(facts): valor medido antes da reposta do AQE deixa de evaporar`

---

## Task 2: A estrutura da árvore

**Files:**
- Modify: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

Esta tarefa **não emite fact nenhum**. Ela dá ao módulo a estrutura que ele hoje joga fora, e é sobre ela que a Task 3 monta as arestas.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_sql_metrics.py`:

```python
class TestEstruturaDaArvore:
    def _tres_niveis(self):
        """(A join B) join C, com A/B/C sendo scans."""
        interno = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.a[id#1]"),
                _scan_node(simple="FileScan parquet db.b[id#2]"),
            ],
        }
        return {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#3], Inner",
            "metadata": {},
            "metrics": [],
            "children": [interno, _scan_node(simple="FileScan parquet db.c[id#3]")],
        }

    def test_children_of_each_node_are_recorded(self):
        from sparkforge.facts.sql_metrics import _estrutura

        filhos, profundidade = _estrutura(self._tres_niveis())

        # preorder: 0 SortMergeJoin, 1 BroadcastHashJoin, 2 db.a, 3 db.b, 4 db.c
        assert filhos[0] == [1, 4]
        assert filhos[1] == [2, 3]
        assert filhos[2] == []
        assert profundidade == 3

    def test_sources_below_a_node_carry_their_distance_in_joins(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = self._tres_niveis()
        # a partir do filho esquerdo da raiz (o join interno, node_id 1)
        fontes = _fontes_abaixo(arvore, 1)

        assert sorted((f["relation"], f["via_joins"]) for f in fontes) == [
            ("db.a", 0),
            ("db.b", 0),
        ]

    def test_distance_counts_the_joins_in_between(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = self._tres_niveis()
        fontes = _fontes_abaixo(arvore, 0)

        assert sorted((f["relation"], f["via_joins"]) for f in fontes) == [
            ("db.a", 1),
            ("db.b", 1),
            ("db.c", 0),
        ]

    def test_a_node_without_any_scan_below_reports_none(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [
                {
                    "nodeName": "Scan ExistingRDD",
                    "simpleString": "Scan ExistingRDD[id#1]",
                    "metadata": {},
                    "metrics": [],
                    "children": [],
                }
            ],
        }

        assert _fontes_abaixo(arvore, 0) == []
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py::TestEstruturaDaArvore -v
```

Esperado: FAIL com `ImportError: cannot import name '_estrutura'`.

- [ ] **Step 3: Implementar**

Acrescente, junto de `_walk`:

```python
# Teto de profundidade da arvore. `_walk` e recursivo, e um `sparkPlanInfo`
# suficientemente profundo estoura a pilha do Python antes de qualquer
# verificacao -- o extrator morreria com `RecursionError` no meio de uma
# extracao que ja produziu facts validos. Falha com nome e diagnostico; falha
# por estouro de pilha e acidente.
_TETO_DE_PROFUNDIDADE = 200

_JOIN_OPERADORES = frozenset(
    {
        "BroadcastHashJoin",
        "SortMergeJoin",
        "ShuffledHashJoin",
        "BroadcastNestedLoopJoin",
        "CartesianProduct",
    }
)

_BUILD_RE = re.compile(r"\bBuild(Left|Right)\b")


def _join_of(node: dict[str, Any]) -> tuple[str, str, str] | None:
    """Devolve `(strategy, join_type, build_side)` se o no e join, senao `None`.

    `build_side` sai `""` quando o operador nao publica lado de build --
    `SortMergeJoin` ordena e mescla os dois lados, e atribuir um lado a ele
    seria afirmar o que o plano nao diz.
    """
    operador = str(node.get("nodeName") or "").strip()
    if operador not in _JOIN_OPERADORES:
        return None
    texto = str(node.get("simpleString") or "")
    join_type = ""
    for candidato in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti"):
        if re.search(rf"\b{candidato}\b", texto):
            join_type = candidato
            break
    build = _BUILD_RE.search(texto)
    return operador, join_type, build.group(1).lower() if build else ""


def _estrutura(plano: dict[str, Any]) -> tuple[dict[int, list[int]], int]:
    """`{node_id: [ids dos filhos]}` e a profundidade maxima da arvore.

    Numeracao identica a de `_walk`: preorder, raiz = 0. Os dois precisam
    concordar, porque o `node_id` de um fact de scan e o de uma aresta tem que
    apontar para o mesmo no -- e e teste que garante isso, nao import.
    """
    filhos: dict[int, list[int]] = {}
    proximo = [0]
    profundidade_maxima = [0]

    def visita(node: dict[str, Any], nivel: int) -> int:
        meu = proximo[0]
        proximo[0] += 1
        profundidade_maxima[0] = max(profundidade_maxima[0], nivel + 1)
        meus_filhos: list[int] = []
        for filho in node.get("children") or []:
            meus_filhos.append(visita(filho, nivel + 1))
        filhos[meu] = meus_filhos
        return meu

    visita(plano, 0)
    return filhos, profundidade_maxima[0]


def _fontes_abaixo(plano: dict[str, Any], alvo: int) -> list[dict[str, Any]]:
    """As fontes alcancaveis abaixo de `alvo`, cada uma com `via_joins`.

    `via_joins` e quantos joins existem ENTRE o scan e `alvo`. Fonte que entra
    direto tem zero. Nao perde informacao e nao mente: quem quiser so o direto
    filtra por zero, quem quiser a arvore inteira soma tudo.
    """
    encontrados: list[dict[str, Any]] = []
    achou_alvo = [False]
    proximo = [0]

    def visita(node: dict[str, Any], dentro: bool, joins: int) -> None:
        meu = proximo[0]
        proximo[0] += 1
        aqui = dentro or meu == alvo
        if meu == alvo:
            achou_alvo[0] = True
        if aqui and meu != alvo:
            scan = _scan_of(node)
            if scan is not None:
                _, relation, _ = scan
                encontrados.append(
                    {"node_id": meu, "relation": relation, "via_joins": joins}
                )
        adiante = joins
        if aqui and meu != alvo and _join_of(node) is not None:
            adiante = joins + 1
        for filho in node.get("children") or []:
            visita(filho, aqui, adiante)

    visita(plano, False, 0)
    if not achou_alvo[0]:
        return []
    return encontrados
```

Acrescente `import re` ao topo se ele ainda não estiver lá.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS. Reporte a contagem real.

**Se `test_distance_counts_the_joins_in_between` falhar por um off-by-one:** a contagem é de joins **entre** o scan e o alvo, exclusive o alvo. No exemplo, `db.a` está sob o join interno, que está sob a raiz — então há **um** join no meio, e `via_joins` é 1. `db.c` é filho direto da raiz, sem join no meio: zero. Ajuste a implementação até a asserção do teste passar; ela é o contrato.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): a estrutura da arvore do plano, que o walk jogava fora`

---

## Task 3: As arestas

**Files:**
- Modify: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
class TestGrafoDeJoins:
    def _broadcast(self):
        return {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.pedidos[id#1]"),
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }

    def test_join_node_becomes_a_fact(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        join = [f for f in facts if f.kind == "spark.sql.join"][0]

        assert join.attrs["strategy"] == "BroadcastHashJoin"
        assert join.attrs["join_type"] == "Inner"
        assert join.attrs["build_side"] == "right"
        assert join.measures == {"inputs_left": 1, "inputs_right": 1}

    def test_each_source_becomes_an_edge_with_its_side(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        arestas = {
            f.attrs["relation"]: f.attrs for f in facts if f.kind == "spark.sql.join_input"
        }

        assert arestas["db.clientes"]["side"] == "build"
        assert arestas["db.clientes"]["position"] == "right"
        assert arestas["db.pedidos"]["side"] == "stream"
        assert arestas["db.pedidos"]["position"] == "left"

    def test_edges_are_anchored_on_the_join_not_on_the_scan(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        join = [f for f in facts if f.kind == "spark.sql.join"][0]
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert all(a.subject["node_id"] == join.subject["node_id"] for a in arestas)

    def test_sort_merge_join_has_no_build_side_and_says_so(self):
        plano = {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#2], Inner",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.pedidos[id#1]"),
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert len(arestas) == 2
        assert {a.attrs["side"] for a in arestas} == {"unknown"}
        assert {a.attrs["position"] for a in arestas} == {"left", "right"}

    def test_nested_join_carries_the_distance(self):
        interno = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.a[id#1]"),
                _scan_node(simple="FileScan parquet db.b[id#2]"),
            ],
        }
        plano = {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#3], Inner",
            "metadata": {},
            "metrics": [],
            "children": [interno, _scan_node(simple="FileScan parquet db.c[id#3]")],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        externo = [
            f
            for f in facts
            if f.kind == "spark.sql.join" and f.attrs["strategy"] == "SortMergeJoin"
        ][0]
        do_externo = {
            f.attrs["relation"]: f.measures["via_joins"]
            for f in facts
            if f.kind == "spark.sql.join_input"
            and f.subject["node_id"] == externo.subject["node_id"]
        }

        assert do_externo == {"db.a": 1, "db.b": 1, "db.c": 0}

    def test_side_without_a_named_source_is_a_gap_and_the_other_side_survives(self):
        plano = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                {
                    "nodeName": "Scan ExistingRDD",
                    "simpleString": "Scan ExistingRDD[id#1]",
                    "metadata": {},
                    "metrics": [],
                    "children": [],
                },
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "join_side_without_source"
        ]

        assert [a.attrs["relation"] for a in arestas] == ["db.clientes"]
        assert len(lacunas) == 1
        assert lacunas[0].attrs["position"] == "left"

    def test_a_plan_deeper_than_the_ceiling_is_a_named_gap(self):
        from sparkforge.facts.sql_metrics import _TETO_DE_PROFUNDIDADE

        no = _scan_node()
        for _ in range(_TETO_DE_PROFUNDIDADE + 5):
            no = {
                "nodeName": "Project",
                "simpleString": "Project",
                "metadata": {},
                "metrics": [],
                "children": [no],
            }
        facts = extract_sql_metrics([_start(plan=no)], "log.jsonl")
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved" and f.attrs["reason"] == "plan_too_deep"
        ]

        assert len(lacunas) == 1
        assert not [f for f in facts if f.kind == "spark.sql.join_input"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py::TestGrafoDeJoins -v
```

Esperado: FAIL — nenhum fact `spark.sql.join` ou `spark.sql.join_input` é emitido.

- [ ] **Step 3: Implementar**

Acrescente os dois kinds a `EMITTED_KINDS`:

```python
        "spark.sql.join",
        "spark.sql.join_input",
```

Em `_Execution.__init__`, acrescente:

```python
        self.joins: dict[int, dict[str, Any]] = {}
        self.arestas: list[dict[str, Any]] = []
        self.lados_sem_fonte: list[dict[str, Any]] = []
        self.profundidade = 0
        self.plano_profundo_demais = False
```

Em `absorb_plan`, depois das duas passadas existentes:

```python
        self.joins = {}
        self.arestas = []
        self.lados_sem_fonte = []
        filhos, self.profundidade = _estrutura(plano)
        self.plano_profundo_demais = self.profundidade > _TETO_DE_PROFUNDIDADE
        if self.plano_profundo_demais:
            return

        for node_id, node in _walk(plano, [0]):
            join = _join_of(node)
            if join is None:
                continue
            strategy, join_type, build_side = join
            meus_filhos = filhos.get(node_id) or []
            if not meus_filhos:
                self.lados_sem_fonte.append(
                    {"node_id": node_id, "position": "", "reason": "join_without_children"}
                )
                continue

            # `children` vem em ordem: o primeiro e o lado esquerdo. `position`
            # e observacao; `side` e derivacao do token BuildLeft/BuildRight, e
            # so existe quando o operador o publica.
            contagem = {"left": 0, "right": 0}
            for indice, filho_id in enumerate(meus_filhos[:2]):
                position = "left" if indice == 0 else "right"
                if build_side:
                    side = "build" if position == build_side else "stream"
                else:
                    side = "unknown"
                fontes = _fontes_abaixo(plano, filho_id)
                # O proprio filho pode ser o scan, e `_fontes_abaixo` so olha
                # ABAIXO do alvo -- entao o alvo e conferido a parte.
                fontes = fontes + _fonte_do_proprio_no(plano, filho_id)
                if not fontes:
                    self.lados_sem_fonte.append(
                        {
                            "node_id": node_id,
                            "position": position,
                            "reason": "join_side_without_source",
                        }
                    )
                    continue
                contagem[position] = len(fontes)
                for fonte in fontes:
                    self.arestas.append(
                        {
                            "join_node_id": node_id,
                            "strategy": strategy,
                            "relation": fonte["relation"],
                            "position": position,
                            "side": side,
                            "via_joins": fonte["via_joins"],
                        }
                    )

            self.joins[node_id] = {
                "strategy": strategy,
                "join_type": join_type,
                "build_side": build_side,
                "inputs_left": contagem["left"],
                "inputs_right": contagem["right"],
            }
```

E o auxiliar que faltava, junto de `_fontes_abaixo`:

```python
def _fonte_do_proprio_no(plano: dict[str, Any], alvo: int) -> list[dict[str, Any]]:
    """A fonte do PROPRIO no, quando o filho do join ja e um scan.

    `_fontes_abaixo` olha estritamente abaixo do alvo, porque `via_joins` conta
    o que ha ENTRE o scan e o join. O caso mais comum de todos -- join cujo
    filho e um scan direto -- cai fora daquela varredura, e sem este auxiliar
    sairia como lado sem fonte.
    """
    for node_id, node in _walk(plano, [0]):
        if node_id != alvo:
            continue
        scan = _scan_of(node)
        if scan is None:
            return []
        _, relation, _ = scan
        return [{"node_id": node_id, "relation": relation, "via_joins": 0}]
    return []
```

No laço de emissão de `extract_sql_metrics`, junto dos outros facts da execução:

```python
        for node_id, join in sorted(execucao.joins.items()):
            facts.append(
                Fact(
                    kind="spark.sql.join",
                    subject=_plan_node_subject(
                        execucao.execution_id, node_id, join["strategy"], ""
                    ),
                    attrs={
                        "strategy": join["strategy"],
                        "join_type": join["join_type"],
                        "build_side": join["build_side"],
                    },
                    measures={
                        "inputs_left": join["inputs_left"],
                        "inputs_right": join["inputs_right"],
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for aresta in execucao.arestas:
            facts.append(
                Fact(
                    kind="spark.sql.join_input",
                    subject=_plan_node_subject(
                        execucao.execution_id,
                        aresta["join_node_id"],
                        aresta["strategy"],
                        "",
                    ),
                    attrs={
                        "relation": aresta["relation"],
                        "position": aresta["position"],
                        "side": aresta["side"],
                        "strategy": aresta["strategy"],
                    },
                    measures={"via_joins": aresta["via_joins"]},
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for lado in execucao.lados_sem_fonte:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(
                        execucao.execution_id, lado["node_id"], "join", ""
                    ),
                    attrs={
                        "reason": lado["reason"],
                        "position": lado["position"],
                        "detail": (
                            "Lado do join sem nenhum scan nomeavel abaixo. Subquery, "
                            "relacao em cache e `Scan ExistingRDD` nao sao fonte que se "
                            "possa nomear, e inventar um nome seria pior que a lacuna."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        if execucao.plano_profundo_demais:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "plan_too_deep",
                        "detail": (
                            f"Arvore com profundidade {execucao.profundidade}, acima do teto "
                            f"de {_TETO_DE_PROFUNDIDADE}. O grafo nao e montado: percorrer "
                            f"recursivamente ate o fim estouraria a pilha no meio de uma "
                            f"extracao que ja produziu facts validos."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS. Reporte a contagem real.

**Cuidado com o custo:** `_fontes_abaixo` e `_fonte_do_proprio_no` percorrem a árvore inteira por chamada, e são chamados por lado de cada join. Numa árvore grande isso é quadrático. Se a suíte ficar lenta, meça antes de otimizar — e, se otimizar, faça a estrutura ser calculada uma vez em `_estrutura` e reusada, sem mudar o contrato que os testes fixam.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): qual fonte entra em qual join, de que lado e a que distancia`

---

## Task 4: Fixtures e a garantia do corpus

**Files:**
- Create: quatro cenários em `fixtures/sql_metrics/`
- Modify: `tests/test_fixtures_golden_sql_metrics.py`

- [ ] **Step 1: Criar os cenários**

Leia um cenário existente de `fixtures/sql_metrics/` para a forma exata de `meta.yaml` e `expected/`. Nada de nome, número ou particularidade de ambiente real.

| Cenário | Prova |
|---|---|
| `join_broadcast_build_side` | a fonte nomeada do lado de build, com `side: build` |
| `join_nested_via_joins` | `(A join B) join C`: `via_joins` correto nos dois níveis |
| `join_sort_merge_without_build` | `side: unknown` nos dois lados, `position` preenchido |
| `join_side_without_source` | lado lendo de `ExistingRDD`: lacuna nomeada, e o outro lado com a aresta |

Acrescente os quatro a `REQUIRED_FIXTURES` e o kind novo a cada `meta.yaml` que o produzir.

- [ ] **Step 2: A garantia sobre o corpus inteiro**

Acrescente a `tests/test_fixtures_golden_sql_metrics.py`:

```python
    def test_every_edge_points_at_a_real_join_and_a_real_relation(self):
        """Aresta que aponta para o nada e pior que aresta ausente.

        Ela parece grafo. Verificada sobre o corpus INTEIRO: um erro de indice
        na numeracao de preorder passaria em cada cenario isolado e quebraria
        aqui, porque so um corpus com arvores de formatos diferentes cobre as
        duas numeracoes ao mesmo tempo.
        """
        for directory in fixture_dirs():
            facts = _extract(directory)
            joins = {
                (f.subject["execution_id"], f.subject["node_id"])
                for f in facts
                if f.kind == "spark.sql.join"
            }
            relacoes = {
                (f.subject["execution_id"], f.subject["relation"])
                for f in facts
                if f.kind == "spark.sql.scan"
            }
            for aresta in (f for f in facts if f.kind == "spark.sql.join_input"):
                chave = (aresta.subject["execution_id"], aresta.subject["node_id"])
                assert chave in joins, (directory.name, chave)
                relacao = (aresta.subject["execution_id"], aresta.attrs["relation"])
                assert relacao in relacoes, (directory.name, relacao)
```

- [ ] **Step 3: Rodar**

```bash
rtk pytest tests/test_fixtures_golden_sql_metrics.py tests/test_fixtures_kind_coverage.py -q
```

Grave os goldens com a saída real e **leia** cada um antes de commitar. Golden gravado sem leitura trava o defeito junto com o comportamento.

- [ ] **Step 4: Commit**

```bash
rtk git add fixtures/sql_metrics tests/test_fixtures_golden_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `test(fixtures): quatro cenarios de grafo de join, e a aresta que nao aponta para o nada`

---

## Task 5: Documentação e os gates

**Files:**
- Modify: `README.md`, `docs/superpowers/STATUS.md`, possivelmente `docs/harness/*.md` e `docs/claims.lock.json`

- [ ] **Step 1: Rodar a suíte inteira**

```bash
rtk pytest -q
```

Cerca de 17 minutos. Qualquer falha é regressão desta entrega.

- [ ] **Step 2: README**

Atualize os números de extratores e kinds, **medidos**:

```bash
rtk python -c "
import importlib, pkgutil
import sparkforge.facts as F
mods, kinds = [], set()
for m in pkgutil.iter_modules(F.__path__):
    mod = importlib.import_module(f'sparkforge.facts.{m.name}')
    ek = getattr(mod, 'EMITTED_KINDS', None)
    if ek:
        mods.append(m.name); kinds |= set(ek)
print(len(mods), 'extratores,', len(kinds), 'kinds')
"
```

Há **dois** lugares no README com contagem de kinds — o da seção de extração e o do parágrafo sobre chave de negócio derivável. Confira os dois: um deles já envelheceu trinta kinds em silêncio por não ser coberto por gate nenhum.

Nenhum verbo novo a documentar: esta entrega não acrescenta superfície.

- [ ] **Step 3: STATUS**

Registre a fase: os dois kinds novos, o conserto do AQE da Task 1, o número de testes acrescentados (meça), a faixa de commits, a referência à spec, e o que ficou de fora com a razão — volume propagado até o join (exigiria cardinalidade que o plano não publica), ordem dos joins como julgamento, `reuse_count` por fonte (recorte irmão), nenhuma regra nova e nenhum eixo novo no fingerprint.

Registre também, explicitamente, que **a superfície não mudou** e por quê: estender o extrator existente estende a tool existente.

- [ ] **Step 4: Gate de números**

```bash
rtk python scripts/check_vnext_claims.py
```

Para cada divergência o gate imprime `esperado X, obtido Y`: corrija o texto para **Y** e ajuste `docs/claims.lock.json`. Itere até `0 divergencia(s).`

```bash
rtk pytest tests/test_docs_coverage.py -q
```

- [ ] **Step 5: Commit e prova final**

```bash
rtk git add README.md docs/superpowers/STATUS.md docs/claims.lock.json docs/harness docs/vnext
rtk git commit -F <arquivo com a mensagem>
rtk pytest -q
```

Mensagem: `docs: o grafo de joins, a fase e o que ficou de fora`

Esperado: 0 failed.

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §3.1 arestas em `sql_metrics.py` | 2, 3 |
| §3.2 toda fonte com `via_joins` | 2, 3 |
| §3.3 `position` observado, `side` derivado | 3 |
| §3.4 teto de profundidade | 2, 3 |
| §4.1 `spark.sql.join` | 3 |
| §4.2 `spark.sql.join_input` | 3 |
| §4.3 razões novas de `unresolved` | 1, 3 |
| §5 nenhuma superfície nova | — (nada a fazer, e o STATUS declara) |
| §6 erros, cada um com o seu nome | 1, 3 |
| §7.1 cenários no domínio existente | 4 |
| §7.2 a garantia sobre o corpus | 4 |
| §8 documentação | 5 |
| §9 critérios de aceite 1–6 | 2, 3, 4 |
| §9 critério de aceite 7 | 4, 5 |
