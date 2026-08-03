"""Extrator de Facts sobre VALIDACAO DE DADOS num modulo PySpark.

Modulo separado de `pyspark_ast.py` -- que ja tem 40 KB e 20 kinds -- porque
reconhecer validacao e responsabilidade propria, com frameworks proprios. O
custo aceito e caminhar a mesma AST duas vezes.

Este extrator DECIDE as correlacoes (posicao relativa ao write, persistencia do
alvo, numero de checks sobre o mesmo alvo) porque o motor de regras avalia um
fact por vez: `engine._condition_candidates` le o contexto de um unico fact e
`engine._absent_satisfied` compara so `kind`. E o mesmo padrao que `SF-EMR-008`
fixou na Fase 5b -- se a resposta depende de mais de uma propriedade, o extrator
decide e emite.

Nunca aplica limiar, nunca atribui severidade, nunca adivinha alvo: alvo nao
resolvido vira `dq.unresolved`, contado e nao presumido.

PROPRIEDADE DO MODULO: nome nu nao identifica objeto, e os QUATRO atributos de
correlacao tratam isso, cada um do jeito que o seu erro pede.

- Entre escopos, nome igual nao e o mesmo objeto: o indice e por escopo
  (`_ScopeIndex`), e nunca por modulo.
- Dentro de um escopo, religar o nome (`vendas = carrega(...)`) troca o objeto
  sem trocar o nome, entao evidencia de um lado da religacao nao vale do outro.
  `position_vs_write` OMITE a chave -- a regra nao deve opinar sobre ordem que
  nao existe --, enquanto `target_persisted` e `action_after_check` emitem
  `false`, porque `SF-DQ-003` dispara sobre esses dois valores e a ausencia
  CALARIA a regra: o rebind viraria um jeito de sumir com ela.

A escolha entre omitir e emitir `false` nao e estilo; e a direcao do erro. Um
atributo que erra para menos cala a regra e custa subnotificacao; um que erra
para mais faz o motor ACUSAR codigo correto. `action_after_check` e o unico dos
quatro do lado da acusacao, e por isso e o que mais precisa da guarda.
"""
from __future__ import annotations

import ast
import hashlib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, NamedTuple

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "data_quality@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "dq.check",
        "dq.enforcement",
        "dq.unresolved",
        "dq.module_analyzed",
    }
)

# `count` sobre uma cadeia que passou por um destes e a forma artesanal: filtra
# o que viola a regra e conta o que sobrou.
_HANDMADE_GATES = frozenset({"filter", "where"})

# Metodos que constroem um DataFrame A PARTIR da raiz da cadeia. Se um deles
# aparece na cadeia, a raiz e a sessao (ou o reader), NAO o dado validado: em
# `spark.table("t").filter(...).count()` o alvo do check e um DataFrame anonimo,
# e `spark` seria um alvo adivinhado -- `SF-DQ-001` passaria a comparar a linha
# deste check com o write de qualquer outro dado que tambem saia de `spark`, e
# afirmaria "validou depois de publicar" sobre dados que nunca se tocaram. Por
# isso a cadeia que passa por aqui vira `dq.unresolved`, contada, e nunca um
# `dq.check` com alvo errado.
#
# A presenca e testada em QUALQUER posicao, nao so no primeiro elo: `option`,
# `schema` e `format` configuram o reader antes do terminal, entao
# `spark.read.option("mergeSchema", "true").parquet(p)` empurra o terminal para
# fora da posicao 0. Testar so o primeiro elo deixava passar exatamente a forma
# canonica de leitura Delta/Iceberg/JDBC em job Glue real.
#
# Superconjunto de `_READ_TERMINALS` (`pyspark_ast.py:55`): os oito nomes de la
# estao todos aqui, `format` inclusive -- ele sozinho nao produz DataFrame, mas
# a presenca dele ja prova que a raiz da cadeia e um reader. Os quatro a mais
# (`range`, `createDataFrame`, `text`, `jdbc`) sao fabricas de DataFrame a
# partir da sessao: `pyspark_ast` nao precisa delas para classificar leitura, e
# aqui elas produziriam o mesmo alvo adivinhado que as outras.
_SOURCE_TERMINALS = frozenset(
    {
        "table",
        "sql",
        "range",
        "createDataFrame",
        "parquet",
        "csv",
        "json",
        "orc",
        "text",
        "jdbc",
        "load",
        "format",
    }
)


# `df.write`, `df.writeTo(...)` e `df.writeStream` sao ATRIBUTOS, nao chamadas:
# o metodo que termina a escrita (`parquet`, `save`, `append`, `start`) varia e
# nao e o que identifica a publicacao.
_WRITE_ATTRS = frozenset({"write", "writeTo", "writeStream"})

# Chamadas que disparam trabalho sobre o alvo. `save`/`saveAsTable` aparecem
# depois de `.write` -- estao aqui para o caso de a cadeia ser quebrada em duas
# linhas (`w = df.write` / `w.save(p)`), onde o atributo e a chamada nao
# compartilham linha.
_ACTION_METHODS = frozenset({"count", "collect", "show", "foreach", "save", "saveAsTable"})

_PERSIST_METHODS = frozenset({"cache", "persist"})
_UNPERSIST_METHODS = frozenset({"unpersist"})


class _ScopeIndex(NamedTuple):
    """Eventos que datam um check, por variavel-alvo, DENTRO DE UM ESCOPO.

    O motor de regras nao correlaciona dois facts -- `engine._condition_candidates`
    avalia um fact por vez e `engine._absent_satisfied` compara so `kind` -- entao
    quem enxerga o codigo inteiro e quem responde. Este indice e o que o extrator
    enxerga e o catalogo nao enxergaria.

    O indice e por escopo, e nao por modulo, porque nome nu nao identifica objeto
    entre escopos: `def a(vendas)` e `def b(vendas)` recebem dois DataFrames
    diferentes, e datar o check de `b` contra o write de `a` seria a mesma
    acusacao falsa que `_SOURCE_TERMINALS` evita do lado da cadeia.

    LIMITE conhecido: a separacao vale para `FunctionDef`/`AsyncFunctionDef`.
    `lambda` e corpo de `class` continuam no escopo que os contem, e um
    parametro de lambda homonimo ao alvo ainda colide -- forma rara, registrada
    e nao corrigida. O preco inverso tambem existe: funcao que le um DataFrame
    global perde a correlacao com o write feito no modulo, e sai
    `no_write_in_module`. E subnotificacao, nao acusacao.
    """

    writes: dict[str, set[int]]
    persists: dict[str, list[tuple[tuple[int, int], bool]]]
    actions: dict[str, set[int]]
    rebinds: dict[str, set[int]]


def _subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _unresolved(
    path: str, line: int, reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="dq.unresolved",
        subject=_subject(path, line),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _chain_root(node: ast.AST) -> tuple[str | None, list[str]]:
    """(nome da variavel raiz, metodos chamados na cadeia, da raiz para fora)."""
    methods: list[str] = []
    current = node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        methods.append(current.func.attr)
        current = current.func.value
    while isinstance(current, ast.Attribute):
        current = current.value
    methods.reverse()
    if isinstance(current, ast.Name):
        return current.id, methods
    return None, methods


def _chain_target(node: ast.AST) -> str | None:
    """Variavel-alvo da cadeia, ou None quando a raiz nao e o alvo.

    Reusa `_SOURCE_TERMINALS` pelo mesmo motivo que `_handmade_check`: a cadeia
    que passa por um reader tem raiz que e a sessao, e registrar a sessao como
    alvo faria dois dados que nunca se tocaram compartilharem a mesma linha de
    write -- um check seria datado contra a publicacao de outro dado.
    """
    root, methods = _chain_root(node)
    if root is None or any(m in _SOURCE_TERMINALS for m in methods):
        return None
    return root


def _scopes(tree: ast.AST) -> list[list[ast.AST]]:
    """Os nos de cada escopo de nome, cada escopo numa lista propria.

    Corpo do modulo e cada `FunctionDef`/`AsyncFunctionDef` sao escopos
    separados: dentro de um escopo, o mesmo nome e o mesmo objeto (a menos de
    rebind, que `_rebind_lines` apura); entre escopos, nao e.
    """
    scopes: list[list[ast.AST]] = []
    pending: list[ast.AST] = [tree]
    while pending:
        own: list[ast.AST] = []
        stack = list(ast.iter_child_nodes(pending.pop()))
        while stack:
            node = stack.pop()
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                pending.append(node)
                continue
            own.append(node)
            stack.extend(ast.iter_child_nodes(node))
        scopes.append(own)
    return scopes


def _lines_by_target(
    nodes: list[ast.AST], attrs: frozenset[str], methods: frozenset[str]
) -> dict[str, set[int]]:
    """Linhas em que cada variavel-alvo aparece na raiz de `df.<attr>` ou de
    `df....<method>()`.

    Guarda o CONJUNTO de linhas, nao a primeira encontrada: a travessia nao e
    por linha -- um write dentro de um laco e visitado depois de um write no
    corpo do modulo -- e "a primeira linha vista" nao e a primeira linha do
    arquivo. Quem consome escolhe o extremo que lhe interessa.

    LIMITE conhecido: alias nao e seguido. `df2 = vendas` seguido de
    `df2.write...` deixa o check sobre `vendas` como `no_write_in_module`. E
    subnotificacao -- o campo diz menos do que o arquivo contem -- e nunca
    acusacao falsa, que e o erro que esta fase recusa.
    """
    found: dict[str, set[int]] = {}
    for node in nodes:
        if isinstance(node, ast.Attribute) and node.attr in attrs:
            chain: ast.AST = node.value
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
        ):
            chain = node
        else:
            continue
        target = _chain_target(chain)
        if target is not None:
            found.setdefault(target, set()).add(node.lineno)
    return found


def _persist_events(nodes: list[ast.AST]) -> dict[str, list[tuple[tuple[int, int], bool]]]:
    """Eventos de persistencia por alvo, ordenados por posicao no arquivo.

    Guarda `cache`/`persist` E `unpersist`, porque `target_persisted` afirma
    ESTADO e nao ocorrencia. A posicao e (linha, coluna) para que dois eventos
    na mesma linha (`vendas.cache(); vendas.unpersist()`) ainda se ordenem.
    """
    events: dict[str, list[tuple[tuple[int, int], bool]]] = {}
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        if method not in _PERSIST_METHODS and method not in _UNPERSIST_METHODS:
            continue
        target = _chain_target(node)
        if target is not None:
            events.setdefault(target, []).append(
                ((node.lineno, node.col_offset), method in _PERSIST_METHODS)
            )
    for sequence in events.values():
        sequence.sort()
    return events


def _rebind_lines(nodes: list[ast.AST]) -> dict[str, set[int]]:
    """Linhas em que cada nome e ligado a outro objeto.

    Todo `ast.Name` em contexto `Store` conta, o que cobre de uma vez `Assign`,
    `AnnAssign`, `AugAssign`, alvo de `for` e `with ... as` -- e tambem alvo de
    comprehension e walrus, que ligam do mesmo jeito.
    """
    lines: dict[str, set[int]] = {}
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            lines.setdefault(node.id, set()).add(node.lineno)
    return lines


def _scope_index(nodes: list[ast.AST]) -> _ScopeIndex:
    return _ScopeIndex(
        writes=_lines_by_target(nodes, _WRITE_ATTRS, frozenset()),
        persists=_persist_events(nodes),
        # `.write` tambem e action: e o que dispara o trabalho de publicar.
        actions=_lines_by_target(nodes, _WRITE_ATTRS, _ACTION_METHODS),
        rebinds=_rebind_lines(nodes),
    )


def _rebound_between(target: str, low: int, high: int, index: _ScopeIndex) -> bool:
    """Ha religacao do nome ESTRITAMENTE entre duas linhas do mesmo escopo.

    Os tres atributos que correlacionam por nome fazem esta mesma pergunta, e o
    que muda entre eles nao e o predicado: e o que cada um FAZ com a resposta --
    omitir a chave, emitir `false`, ou descartar uma candidata. Manter o
    predicado em tres formas distintas garantiria divergencia na proxima
    mudanca, e divergencia aqui e falso positivo ou falso negativo, nunca so
    inconsistencia de estilo.
    """
    return any(low < rebind < high for rebind in index.rebinds.get(target, ()))


def _position_vs_write(target: str, line: int, index: _ScopeIndex) -> str | None:
    """Tres valores, nunca um booleano -- ou nenhum valor, quando nao da para saber.

    `no_write_in_module` e o modulo que valida e nao escreve -- uma biblioteca de
    validacao, um job de auditoria. Achatar isso em `before_write` afirmaria uma
    ordem que o arquivo nao contem.

    `None` (chave OMITIDA, nunca um quarto valor) e o nome religado entre o check
    e o write: em `vendas.write...` / `vendas = carrega(...)` / check, o alvo
    validado e um DataFrame que nunca foi escrito, e qualquer dos tres valores
    seria mentira. Chave ausente e a forma de dizer "nao sei" --
    `engine._where_matches` reprova caminho ausente e a regra nao avalia este
    check --, o mesmo mecanismo que o desvio D-5c-3 fixou para `shares_scan`.

    LIMITE conhecido: write e check na MESMA linha (`;`) caem em `before_write`,
    porque a comparacao e estrita e `lineno` nao tem sub-linha. Raro e de baixo
    impacto.
    """
    lines = index.writes.get(target)
    if not lines:
        return "no_write_in_module"
    write_line = min(lines)
    low, high = sorted((line, write_line))
    if _rebound_between(target, low, high, index):
        return None
    return "after_write" if line > write_line else "before_write"


def _target_persisted(target: str, line: int, index: _ScopeIndex) -> bool:
    """Estado no momento do check: o ULTIMO evento antes dele decide.

    `vendas.cache()` seguido de `vendas.unpersist()` deixa o alvo NAO persistido
    quando o check chega -- o campo afirma estado, nao que um `cache()` existiu
    em algum lugar do arquivo.

    Religar o nome entre o ultimo evento e o check tambem derruba a evidencia: em
    `vendas.cache()` / `vendas = carrega(...)` / check, o DataFrame validado nao e
    o que foi persistido. Aqui a chave NAO e omitida, ao contrario de
    `position_vs_write`: `SF-DQ-003` dispara sobre `target_persisted: false`, entao
    tanto o valor errado quanto a ausencia CALARIAM a regra sobre um DataFrame que
    de fato nao esta persistido -- e omitir faria do rebind um jeito de sumir com
    ela. `false` e a resposta honesta a "este DataFrame esta persistido quando o
    check roda", e um falso negativo silencioso e o pior modo de falha deste
    repositorio.
    """
    events = [event for event in index.persists.get(target, ()) if event[0][0] < line]
    if not events:
        return False
    (last_line, _), persisted = events[-1]
    if not persisted:
        return False
    return not _rebound_between(target, last_line, line, index)


def _action_after_check(target: str, line: int, index: _ScopeIndex) -> bool:
    """Ha action sobre o alvo depois do check, e sobre o MESMO objeto.

    Estritamente posterior: a linha do proprio check tem a action que o define
    -- o `count()` -- e o check nao e action depois de si.

    Religar o nome entre o check e uma action candidata invalida AQUELA action,
    nao o intervalo inteiro: se ha action em 3, religacao em 5 e action em 7, com
    o check em 2, a de 3 continua valendo e o atributo e `true`. Sao N candidatas,
    e cada uma responde por si.

    Este e o unico dos quatro atributos cujo erro cai do lado da ACUSACAO:
    `SF-DQ-003` dispara sobre `action_after_check: true`, entao afirmar reuso de
    um nome que ja aponta para outro objeto acusaria um check cujo DataFrame
    nunca foi reusado. Os outros tres erram para menos e calam a regra; este
    falaria de mais. Chave sempre presente, pelo mesmo argumento de
    `_target_persisted`: `false` e a resposta honesta.

    LIMITE conhecido: um check IRMAO sobre o mesmo alvo conta como action
    posterior, e e verdade -- sem cache, os dois recomputam o lineage --, mas
    quem ler o campo como "o dado e reusado" se engana: o reuso aqui e recomputo,
    nao releitura de algo materializado.
    """
    return any(
        action > line and not _rebound_between(target, line, action, index)
        for action in index.actions.get(target, ())
    )


def _handmade_check(
    node: ast.Call, path: str, index: _ScopeIndex, provenance: dict[str, Any]
) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "count":
        return None
    target, methods = _chain_root(node)
    if not any(m in _HANDMADE_GATES for m in methods):
        return None
    if target is None or any(m in _SOURCE_TERMINALS for m in methods):
        return _unresolved(
            path, node.lineno, "unresolved_target", provenance, check_type="count_of_violations"
        )
    line = node.lineno
    attrs: dict[str, Any] = {
        "framework": "handmade",
        "check_type": "count_of_violations",
        "target": target,
        "target_persisted": _target_persisted(target, line, index),
        "action_after_check": _action_after_check(target, line, index),
        # Todo check artesanal paga varredura propria: cada `count()` e uma
        # passada sobre o alvo, sem compartilhamento com os outros checks do
        # modulo. So a `VerificationSuite` do Deequ agrupa agregacoes
        # (knowledge/dq/validation-frameworks.md, §2.3).
        "shares_scan": False,
    }
    position = _position_vs_write(target, line, index)
    if position is not None:
        attrs["position_vs_write"] = position
    return Fact(
        kind="dq.check",
        subject=_subject(path, line),
        measures={"line": line},
        attrs=attrs,
        provenance=provenance,
    )


def extract_data_quality(tree: ast.AST, path: str, artifact_sha256: str = "") -> list[Fact]:
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    for nodes in _scopes(tree):
        index = _scope_index(nodes)
        found: list[Fact] = []
        for node in nodes:
            if isinstance(node, ast.Call):
                fact = _handmade_check(node, path, index, provenance)
                if fact is not None:
                    found.append(fact)

        # Segundo passe: quantos checks ha sobre o mesmo alvo so e conhecido
        # depois de a travessia terminar. Por escopo, pelo mesmo motivo que o
        # indice: dois checks sobre `vendas` em duas funcoes diferentes nao sao
        # dois checks sobre o mesmo alvo.
        per_target = Counter(f.attrs["target"] for f in found if f.kind == "dq.check")
        facts.extend(
            replace(f, measures={**f.measures, "checks_on_target": per_target[f.attrs["target"]]})
            if f.kind == "dq.check"
            else f
            for f in found
        )

    check_count = sum(1 for f in facts if f.kind == "dq.check")
    unresolved_count = sum(1 for f in facts if f.kind == "dq.unresolved")
    facts.append(
        Fact(
            kind="dq.module_analyzed",
            subject=_subject(path),
            measures={"check_count": check_count, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_data_quality_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.py`, ancorando o path relativo a `repo_root`.

    Mesma convencao de `athena_workgroup.extract_athena_workgroup_path`: falha
    ao abrir o arquivo vira um unico Fact `dq.unresolved` com reason
    "read_error"; fonte que nao compila vira "syntax_error". Nunca uma excecao
    que derruba quem chamou -- um arquivo ilegivel e um ponto cego CONTADO, e
    nao o fim da varredura.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [_unresolved(anchor, 0, "read_error", empty, detail=str(exc))]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance_sha = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            _unresolved(
                anchor, exc.lineno or 0, "syntax_error", provenance_sha, detail=str(exc.msg)
            )
        ]
    return extract_data_quality(tree, anchor, artifact_sha256=sha)


def extract_data_quality_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.py` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um `.py` problematico vira `dq.unresolved`
    para aquele arquivo e a travessia continua -- mesma convencao de
    `athena_workgroup.extract_athena_workgroup_tree`.
    """
    facts: list[Fact] = []
    for py_file in sorted(root.rglob("*.py")):
        rel = str(py_file.relative_to(repo_root)) if repo_root else str(py_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_data_quality_path(py_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            # Um `.py` que nao decodifica levanta UnicodeDecodeError -- um
            # ValueError, nao um OSError -- e escaparia da guarda estreita de
            # `extract_data_quality_path`. Aqui a guarda e larga de proposito:
            # um arquivo ilegivel custa um fact contado, nunca a varredura
            # inteira.
            facts.append(
                _unresolved(
                    anchor,
                    0,
                    "read_error",
                    {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                    detail=str(exc),
                )
            )
    return sort_facts(facts)
