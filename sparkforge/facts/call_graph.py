"""Construtor de grafo de chamadas a partir de Facts ja extraidos.

Consome os fatos `pyspark.callgraph_edge` (caller -> callee) e
`pyspark.function_def` (uma funcao definida, com ou sem chamada) que
`pyspark_ast.py` ja produz durante a extracao AST -- passe 2, funcoes
`_loop_and_callgraph_facts` e `_function_def_facts` -- mais os fatos de
trabalho Spark (leitura, action, write, cache, join, ...) que a mesma extracao
ja produz, e deriva: quais funcoes existem no grafo, quanto trabalho Spark cada
uma concentra, o que e alcancavel a partir de cada entrypoint e a que
profundidade minima, quais ciclos existem, quais simbolos ninguem referencia no
corpus, e um resumo do grafo inteiro.

Por que isto importa (ver `knowledge/spark/execution-model.md` secoes 6 e 7):
um `count()` dentro de um helper chamado tres niveis abaixo do entrypoint e
invisivel numa revisao de codigo que so olha o entrypoint, e obvio quando
plotado como profundidade de alcance. `min_depth == 0` esta na cara; `>= 2`
e o caso que passa despercebido.

Funcao pura sobre Facts: nunca le arquivo, nunca reexecuta `ast.parse`. A
extracao ja aconteceu em `pyspark_ast.py`; este modulo so deriva estrutura a
partir do que ja foi observado, o que mantem a fronteira entre "extrair" e
"derivar" -- extracao acontece uma vez, esta camada nunca reparseia fonte.

Determinismo: toda saida e ordenada (`sort_facts`) e toda travessia usa
pilha ou fila explicita, nunca recursao Python -- um grafo profundo ou
ciclico nao pode estourar a pilha do interpretador. A Fase 0 teve esse bug
duas vezes (`pyspark_ast._Context` e `_chain_methods`) e as duas foram
corrigidas trocando recursao por pilha/fila explicita; este modulo segue a
mesma convencao desde o primeiro commit.
"""
from __future__ import annotations

from collections import Counter, deque
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "call_graph@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "callgraph.function",
        "callgraph.reachable_spark_work",
        "callgraph.summary",
        "callgraph.cycle",
    }
)

# "Trabalho Spark": qualquer fato pyspark.* ancorado numa funcao, exceto os
# quatro que descrevem a propria extracao/grafo (a aresta em si, a definicao de
# funcao, o sentinela de modulo analisado, e o "nao consegui resolver") --
# nenhum dos quatro e trabalho que o Spark executa.
#
# `pyspark.function_def` PRECISA estar aqui: ele existe uma vez por funcao
# definida, entao conta-lo como trabalho daria `spark_work_count >= 1` a toda
# funcao do corpus e faria `callgraph.cycle.contains_spark_work` virar sempre
# verdadeiro -- SF-CG-001 (P1) passaria a disparar em qualquer recursao, com ou
# sem Spark dentro.
_NON_WORK_KINDS = frozenset(
    {
        "pyspark.callgraph_edge",
        "pyspark.function_def",
        "pyspark.module_analyzed",
        "pyspark.unresolved",
    }
)

# (file, symbol) identifica uma funcao. Arestas de `pyspark_ast` sao sempre
# intra-arquivo (callee precisa estar em `local_functions` do mesmo modulo),
# entao usar o `file` da propria aresta para caller e callee e correto -- os
# dois sempre estao no mesmo arquivo por construcao do extrator upstream.
NodeKey = tuple[str, str]


def _is_spark_work(kind: str) -> bool:
    return kind.startswith("pyspark.") and kind not in _NON_WORK_KINDS


def _node_subject(node: NodeKey, line: int) -> dict[str, Any]:
    file, symbol = node
    return {
        "type": "source_location",
        "file": file,
        "line": line,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _canonical_rotation(cycle: list[NodeKey]) -> list[NodeKey]:
    """Rotaciona o ciclo para comecar no membro lexicograficamente menor.

    Sem isto, o mesmo ciclo fisico (f -> g -> f) produziria fatos diferentes
    dependendo de qual funcao a travessia visitou primeiro -- que por sua vez
    depende so da ordem de insercao dos fatos de entrada, nao de nada
    estrutural do ciclo. A rotacao canonica remove essa dependencia de ordem
    e garante que o mesmo ciclo sempre produz o mesmo fato.
    """
    if not cycle:
        return cycle
    min_index = min(range(len(cycle)), key=lambda i: cycle[i])
    return cycle[min_index:] + cycle[:min_index]


def _find_cycles(
    nodes: list[NodeKey], callees: dict[NodeKey, list[NodeKey]]
) -> list[list[NodeKey]]:
    """DFS iterativo (pilha explicita, sem recursao Python) para achar ciclos.

    Um back-edge -- uma aresta para um no que ainda esta na pilha da
    travessia atual -- fecha um ciclo: o segmento do caminho corrente desde
    aquele no ate o topo da pilha, mais a aresta de volta. Isto acha um
    ciclo representativo por regiao fortemente conectada, nao enumera todo
    ciclo elementar de grafos com ciclos sobrepostos -- o que basta para o
    proposito aqui, que e sinalizar recursao/recursao mutua, nao listar
    exaustivamente cada rota possivel.
    """
    visited: set[NodeKey] = set()
    cycles: list[list[NodeKey]] = []
    seen_keys: set[tuple[NodeKey, ...]] = set()

    for start in nodes:
        if start in visited:
            continue
        stack: list[NodeKey] = [start]
        child_index: list[int] = [0]
        on_stack: set[NodeKey] = {start}
        path: list[NodeKey] = [start]

        while stack:
            current = stack[-1]
            children = callees.get(current, [])
            idx = child_index[-1]
            if idx < len(children):
                child_index[-1] += 1
                nxt = children[idx]
                if nxt in on_stack:
                    start_index = path.index(nxt)
                    canon = _canonical_rotation(path[start_index:])
                    key = tuple(canon)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        cycles.append(canon)
                elif nxt not in visited:
                    stack.append(nxt)
                    child_index.append(0)
                    on_stack.add(nxt)
                    path.append(nxt)
            else:
                visited.add(current)
                stack.pop()
                child_index.pop()
                on_stack.discard(current)
                path.pop()

    return cycles


def _bfs(
    entrypoint: NodeKey, callees: dict[NodeKey, list[NodeKey]]
) -> dict[NodeKey, tuple[int, list[NodeKey]]]:
    """BFS com fila explicita: profundidade + rota mais curta de
    `entrypoint` para cada no alcancavel. `visited` bloqueia ciclos -- um
    no ja descoberto nunca e reenfileirado, entao um grafo ciclico nao trava
    a travessia."""
    visited: dict[NodeKey, tuple[int, list[NodeKey]]] = {entrypoint: (0, [entrypoint])}
    queue: deque[NodeKey] = deque([entrypoint])
    while queue:
        current = queue.popleft()
        depth, path = visited[current]
        for nxt in callees.get(current, []):
            if nxt not in visited:
                visited[nxt] = (depth + 1, path + [nxt])
                queue.append(nxt)
    return visited


def build_call_graph(facts: Sequence[Fact], path_hint: str = "") -> list[Fact]:
    """Deriva Facts de grafo de chamadas a partir de Facts ja extraidos.

    `facts` normalmente vem de `pyspark_ast.extract_tree`/`extract_source`:
    precisa conter `pyspark.callgraph_edge` para que qualquer no exista, e os
    fatos de trabalho Spark (`pyspark.read`, `.action`, `.driver_collect`,
    etc.) para que `spark_work_count`/`callgraph.reachable_spark_work` nao
    fiquem vazios. `path_hint` ancora o fato `callgraph.summary` quando
    `facts` cobre uma arvore inteira (varios arquivos) em vez de um unico.

    Ha um no por funcao DEFINIDA (`pyspark.function_def`), com ou sem aresta,
    mais qualquer ponta de aresta que apareca sem definicao. Ate a Fase 5b os
    nos vinham SO das arestas, e uma funcao definida e nunca chamada nao existia
    no grafo -- ver a secao sobre `unreferenced_function_count` abaixo.

    Quando `facts` nao traz nenhum `pyspark.function_def` (entrada sintetica, ou
    facts de uma versao anterior do extrator), o grafo degrada para o
    comportamento antigo: so os nos das arestas, `defined_function_count` zero e
    `unreferenced_function_count` zero. Zero por ausencia de definicao,
    nao por ausencia de orfa -- a diferenca esta em `defined_function_count`.
    """
    provenance = {"artifact": path_hint, "artifact_sha256": "", "extractor": EXTRACTOR_ID}

    edges: set[tuple[NodeKey, NodeKey]] = set()
    facts_by_node: dict[NodeKey, list[Fact]] = {}
    definitions: dict[NodeKey, Fact] = {}
    definition_counts: dict[NodeKey, int] = {}
    referenced_names: dict[str, set[str]] = {}
    dynamic_dispatch = False

    for fact in facts:
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        file = subject.get("file", "")
        symbol = subject.get("symbol", "")
        if symbol:
            facts_by_node.setdefault((file, symbol), []).append(fact)

        if fact.kind == "pyspark.callgraph_edge":
            caller = fact.attrs.get("caller")
            callee = fact.attrs.get("callee")
            if caller and callee:
                edges.add(((file, caller), (file, callee)))

        elif fact.kind == "pyspark.function_def" and symbol:
            node = (file, symbol)
            definition_counts[node] = definition_counts.get(node, 0) + 1
            # Dois `def` com o mesmo nome no mesmo arquivo (metodos homonimos em
            # classes diferentes, redefinicao condicional) colapsam num no so --
            # a chave do grafo e (arquivo, nome), como a aresta. Vence a
            # definicao de menor linha, criterio deterministico, e
            # `definition_count` deixa a colisao VISIVEL em vez de silenciosa.
            current = definitions.get(node)
            if current is None or subject.get("line", 0) < current.subject.get("line", 0):
                definitions[node] = fact

        elif fact.kind == "pyspark.module_analyzed":
            names = fact.attrs.get("referenced_names")
            if isinstance(names, list):
                referenced_names.setdefault(file, set()).update(str(n) for n in names)

        elif fact.kind == "pyspark.unresolved" and fact.attrs.get("reason") == "getattr":
            dynamic_dispatch = True

    nodes: set[NodeKey] = set(definitions)
    callers: dict[NodeKey, set[NodeKey]] = {}
    for caller_node, callee_node in edges:
        nodes.add(caller_node)
        nodes.add(callee_node)
        callers.setdefault(callee_node, set()).add(caller_node)

    callees: dict[NodeKey, list[NodeKey]] = {}
    for caller_node, callee_node in sorted(edges):
        callees.setdefault(caller_node, []).append(callee_node)
    for node in nodes:
        callees.setdefault(node, [])
        callers.setdefault(node, set())

    sorted_nodes = sorted(nodes)

    work_counters: dict[NodeKey, Counter[str]] = {}
    anchor_lines: dict[NodeKey, int] = {}
    for node in sorted_nodes:
        node_facts = facts_by_node.get(node, [])
        counter: Counter[str] = Counter()
        for f in node_facts:
            if _is_spark_work(f.kind):
                counter[f.kind] += 1
        work_counters[node] = counter
        lines = [f.subject.get("line", 0) for f in node_facts if isinstance(f.subject, dict)]
        anchor_lines[node] = min(lines) if lines else 0

    out: list[Fact] = []

    # callgraph.function -----------------------------------------------
    #
    # `caller_visibility` responde a pergunta que decide se a AUSENCIA de
    # chamador significa alguma coisa:
    #
    #   resolvable -- funcao de nivel de modulo ou aninhada, sem decorator e
    #                 fora de `__all__`. Todo uso dela passa por uma leitura do
    #                 nome -- chamada, callback, entrada de dicionario, retorno
    #                 de fechamento -- e leitura de nome e observavel. Aqui, e
    #                 so aqui, "ninguem chama" e observacao sobre o CODIGO.
    #   opaque     -- metodo (invocado por `self.x()`/`obj.x()`, que e
    #                 `ast.Attribute` e nunca vira aresta nem leitura do nome
    #                 da funcao), decorada (o framework que registrou pode
    #                 invocar) ou exportada em `__all__` (o chamador esta fora
    #                 do corpus por definicao). "Ninguem chama" aqui e
    #                 propriedade do EXTRATOR, nao do codigo.
    #   unknown    -- no que so existe porque uma aresta o citou; nenhuma
    #                 definicao foi observada.
    #
    # Sem essa separacao, listar "funcao sem chamador" num corpus de biblioteca
    # devolveria a API publica inteira como achado.
    unreferenced: list[NodeKey] = []
    opaque_nodes: list[NodeKey] = []
    for node in sorted_nodes:
        file, symbol = node
        fan_out = len(callees.get(node, []))
        fan_in = len(callers.get(node, set()))
        definition = definitions.get(node)

        if definition is None:
            def_kind = ""
            visibility = "unknown"
            local_references = 0
        else:
            def_kind = str(definition.attrs.get("def_kind", ""))
            local_references = int(definition.measures.get("name_reference_count", 0))
            opaque = (
                def_kind == "method"
                or bool(definition.attrs.get("decorators"))
                or bool(definition.attrs.get("exported"))
            )
            visibility = "opaque" if opaque else "resolvable"

        # Referencia ao nome em OUTRO arquivo do corpus: `from lib import f` +
        # `f(df)`, ou `lib.f(df)`. Nao vira aresta (as arestas sao intra-arquivo)
        # e sem esta consulta toda funcao usada entre modulos pareceria orfa.
        referenced_elsewhere = any(
            symbol in names for other, names in referenced_names.items() if other != file
        )
        is_referenced = fan_in > 0 or local_references > 0 or referenced_elsewhere
        is_unreferenced = visibility == "resolvable" and not is_referenced

        if is_unreferenced:
            unreferenced.append(node)
        if visibility == "opaque":
            opaque_nodes.append(node)

        out.append(
            Fact(
                kind="callgraph.function",
                subject=_node_subject(node, anchor_lines[node]),
                measures={
                    "fan_out": fan_out,
                    "fan_in": fan_in,
                    "spark_work_count": sum(work_counters[node].values()),
                    "definition_count": definition_counts.get(node, 0),
                    "name_reference_count": local_references,
                },
                attrs={
                    "is_entrypoint": fan_in == 0,
                    "is_leaf": fan_out == 0,
                    "is_defined": definition is not None,
                    "def_kind": def_kind,
                    "caller_visibility": visibility,
                    "referenced_in_other_module": referenced_elsewhere,
                    "is_unreferenced": is_unreferenced,
                },
                provenance=provenance,
            )
        )

    entrypoints = [n for n in sorted_nodes if len(callers.get(n, set())) == 0]

    # callgraph.reachable_spark_work + acumulo de alcance para o summary ---
    reachable_all: dict[NodeKey, int] = {}
    for entrypoint in entrypoints:
        visited = _bfs(entrypoint, callees)
        for node, (depth, _path) in visited.items():
            if node not in reachable_all or depth < reachable_all[node]:
                reachable_all[node] = depth

        kinds_present: set[str] = set()
        for node in visited:
            kinds_present.update(work_counters[node].keys())

        for kind in sorted(kinds_present):
            candidate_nodes = [node for node in visited if kind in work_counters[node]]
            min_depth = min(visited[node][0] for node in candidate_nodes)
            # Desempate deterministico: entre as funcoes que atingem a
            # profundidade minima, a chave (file, symbol) lexicograficamente
            # menor vence, independente da ordem de descoberta do BFS.
            best_node = min(
                (node for node in candidate_nodes if visited[node][0] == min_depth),
            )
            occurrence_count = sum(work_counters[node][kind] for node in candidate_nodes)

            out.append(
                Fact(
                    kind="callgraph.reachable_spark_work",
                    subject=_node_subject(entrypoint, anchor_lines[entrypoint]),
                    measures={"min_depth": min_depth, "occurrence_count": occurrence_count},
                    attrs={
                        "entrypoint": entrypoint[1],
                        "work_kind": kind,
                        "via": [step[1] for step in visited[best_node][1]],
                    },
                    provenance=provenance,
                )
            )

    # callgraph.cycle -----------------------------------------------------
    cycles = _find_cycles(sorted_nodes, callees)
    for cycle in cycles:
        spark_work_total = sum(sum(work_counters[n].values()) for n in cycle)
        out.append(
            Fact(
                kind="callgraph.cycle",
                subject=_node_subject(cycle[0], anchor_lines[cycle[0]]),
                measures={"length": len(cycle), "spark_work_count": spark_work_total},
                attrs={
                    "functions": [n[1] for n in cycle],
                    "contains_spark_work": spark_work_total > 0,
                },
                provenance=provenance,
            )
        )

    # callgraph.summary -----------------------------------------------------
    #
    # `unreachable_from_entrypoint_count` era `unreachable_function_count` ate a
    # Fase 5b. A conta e a mesma -- nos que nenhum BFS alcancou -- mas o nome
    # prometia deteccao de codigo morto e entregava outra coisa: como todo no
    # sem chamador vira entrypoint, e todo entrypoint se alcanca a si mesmo com
    # profundidade zero, o unico jeito de um no nao ser alcancado e estar num
    # componente ciclico sem entrada. Funcao definida e nunca chamada dava ZERO,
    # e zero e indistinguivel de "nao ha codigo morto". O nome novo diz o que a
    # conta faz.
    #
    # `unreferenced_function_count` e a medida que responde de verdade, e ela
    # afirma exatamente isto e nada alem: funcao definida (nivel de modulo ou
    # aninhada), sem decorator, fora de `__all__`, que nenhuma outra funcao
    # deste corpus chama e cujo nome nao e lido em nenhum arquivo deste corpus.
    # Nao afirma "codigo morto": a chamada pode vir de fora do corpus (aplicacao
    # que importa a biblioteca), de string (`getattr`, tabela por nome, entry
    # point de pacote) ou de framework. `attrs.dynamic_dispatch_present` marca
    # quando o proprio corpus tem `getattr` -- nesse caso a lista e ainda mais
    # fraca, e o consumidor tem que saber disso pelo fact.
    unreachable = len(nodes) - len(reachable_all)
    max_depth = max(reachable_all.values()) if reachable_all else 0
    out.append(
        Fact(
            kind="callgraph.summary",
            subject={
                "type": "source_location",
                "file": path_hint,
                "line": 0,
                "col": 0,
                "symbol": "",
                "snippet": "",
            },
            measures={
                "function_count": len(nodes),
                "defined_function_count": len(definitions),
                "edge_count": len(edges),
                "entrypoint_count": len(entrypoints),
                "max_depth": max_depth,
                "unreachable_from_entrypoint_count": unreachable,
                "unreferenced_function_count": len(unreferenced),
                "opaque_caller_function_count": len(opaque_nodes),
            },
            attrs={
                "entrypoints": [n[1] for n in entrypoints],
                "has_cycle": bool(cycles),
                # A lista, nao so a contagem: contagem sem nome nao e
                # acionavel, e o operador nao consegue verificar uma afirmacao
                # cujo sujeito ele nao conhece.
                "unreferenced_functions": [n[1] for n in unreferenced],
                "dynamic_dispatch_present": dynamic_dispatch,
            },
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)
