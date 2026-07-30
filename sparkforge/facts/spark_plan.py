"""Extrator de plano fisico Spark (`df.explain(...)` / `EXPLAIN`) em Facts.

A saida de `explain()` NAO e formato de maquina: e texto voltado para humano,
que varia entre versoes menores do Spark e entre modos. Este modulo suporta os
modos que consegue interpretar com confianca e REJEITA os demais em vez de
meio-parsear:

  formatted  -- `df.explain("formatted")` / `EXPLAIN FORMATTED`. Duas secoes:
                uma arvore compacta e, depois, um bloco de detalhe numerado por
                operador (`(1) Scan parquet db.tabela` seguido de `Output`,
                `ReadSchema`, `PartitionFilters`, `PushedFilters`,
                `DataFilters`, `Location`). E o modo preferido: os campos vem
                um por linha, sem ambiguidade de virgula.
  simple     -- `df.explain()` / `EXPLAIN`. Uma unica arvore; cada no cabe numa
                linha e carrega os metadados inline
                (`FileScan parquet db.t[a#1,b#2] Batched: true, DataFilters:
                [...], ..., ReadSchema: struct<...>`).
  extended   -- `df.explain(True)` / `EXPLAIN EXTENDED` / `EXPLAIN COST`. So a
                secao `== Physical Plan ==` e interpretada; as secoes logicas
                sao ignoradas de proposito (nao sao plano fisico) e contadas em
                `measures.skipped_logical_lines`, nunca em `unresolved` --
                ignorar de proposito e diferente de nao conseguir ler.
  codegen    -- `df.explain("codegen")`. REJEITADO: e codigo Java gerado, nao
                plano. Vira um unico `plan.unresolved` com
                `reason: unsupported_mode`.

Determinismo e disciplina de ponto cego, como em `pyspark_ast.py` e
`event_log.py`: nunca aplica limiar, nunca atribui severidade, nunca importa
nem executa nada. Tudo que o parser nao conseguiu interpretar vira um Fact
`plan.unresolved` contado -- um numero errado que parece certo e pior que um
ponto cego declarado, e `measures.read_schema_columns /
measures.referenced_columns` (SF-PQ-004) e uma RAZAO: uma lista de campos
truncada pelo Spark infla o numerador em silencio se o parser fingir que a
lista estava completa.

Ancoragem (`subject`): um plano nao tem arquivo:linha de codigo-fonte. Pelo
mesmo raciocinio de `event_log.py`, que ancora metrica em `{"type": "stage"}`
-- a entidade de dominio com identidade estavel dentro do artefato, nao o
byte offset -- aqui a entidade e o NO do plano: `{"type": "plan_node",
"symbol": "(1) Scan parquet db.tabela", "node_id": 1, ...}`. O operador age
sobre "a leitura de db.tabela no no 1", nao sobre "a linha 37 do arquivo de
texto"; `file`/`line` acompanham como procedencia, para o operador achar o
trecho, nunca como identidade.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "spark_plan@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "plan.file_scan",
        "plan.join",
        "plan.exchange",
        "plan.python_udf",
        "plan.operator",
        "plan.aqe",
        "plan.unresolved",
        "plan.analyzed",
    }
)

# Operadores de leitura. `FileScan <fmt>` e a forma do modo simple; `Scan <fmt>`
# e a do modo formatted (`nodeName` de FileSourceScanExec muda entre os dois).
# `BatchScan` e a API v2 (Iceberg, Delta): NAO tem `PartitionFilters` -- tratar
# os dois como a mesma coisa fabricaria falso positivo de SF-PQ-002.
# O token de formato precisa comecar em MINUSCULA. `Scan` tambem prefixa
# operadores que nao leem arquivo nenhum: `Scan ExistingRDD[...]`,
# `Scan In-memory table clientes` (InMemoryTableScanExec sobrescreve `nodeName`
# quando o cache tem nome), `Scan OneRowRelation`. Trata-los como FileScan
# produziria um `plan.file_scan` sem ReadSchema e um `partition_status_unknown`
# inventado para um cache em memoria.
_SCAN_V1_RE = re.compile(r"^(?:File)?Scan\s+([a-z][\w-]*)\b\s*(.*)$")
_SCAN_V2_RE = re.compile(r"^BatchScan\b\s*(.*)$")

# Cabecalhos que o AQE emite quando o plano corrente diverge do inicial
# (`AdaptiveSparkPlanExec.generateTreeStringWithHeader`, v3.3.0 e v3.5.6):
# `+- == Final Plan ==` / `+- == Current Plan ==` / `+- == Initial Plan ==`.
_AQE_SECTION_RE = re.compile(r"^[+\-\s]*==\s*(Final Plan|Current Plan|Initial Plan)\s*==\s*$")

_JOIN_OPERATORS = frozenset(
    {
        "BroadcastHashJoin",
        "SortMergeJoin",
        "ShuffledHashJoin",
        "BroadcastNestedLoopJoin",
        "CartesianProduct",
    }
)

_EXCHANGE_OPERATORS = frozenset({"Exchange", "BroadcastExchange", "ShuffleExchange"})

_PYTHON_UDF_OPERATORS = {
    "BatchEvalPython": "python",
    "ArrowEvalPython": "pandas",
    "AggregateInPandas": "pandas",
    "FlatMapGroupsInPandas": "pandas",
    "MapInPandas": "pandas",
    "WindowInPandas": "pandas",
}

# Operadores de custo que o `knowledge/spark/plan-reading.md` manda percorrer no
# checklist mas que nao merecem um kind proprio: um unico `plan.operator` com
# vocabulario FECHADO cobre todos, e continua sendo um vocabulario declarado,
# nao um catch-all que aceita qualquer texto.
_COST_OPERATORS = frozenset(
    {
        "Sort",
        "Window",
        "Generate",
        "HashAggregate",
        "ObjectHashAggregate",
        "SortAggregate",
        "ReusedExchange",
        "AQEShuffleRead",
        "CustomShuffleReader",
        "InMemoryTableScan",
        "Coalesce",
        "Union",
        "Expand",
        "TakeOrderedAndProject",
    }
)

# Operadores estruturais que nao geram fact proprio, mas cuja presenca PROVA
# que o texto e um plano fisico. Sem esta prova, `_parse_simple` aceitaria
# qualquer linha que comece com maiuscula (um README vira "plano" com um no
# chamado `Hello`), e o extrator reportaria facts sobre prosa.
_STRUCTURAL_OPERATORS = frozenset(
    {
        "Project",
        "Filter",
        "AdaptiveSparkPlan",
        "WholeStageCodegen",
        "ColumnarToRow",
        "InputAdapter",
        "LocalTableScan",
        "CommandResult",
        "SubqueryBroadcast",
        "ReusedSubquery",
        "Subquery",
        "SerializeFromObject",
        "DeserializeToObject",
        "MapPartitions",
        "Limit",
        "GlobalLimit",
        "LocalLimit",
        "Aggregate",
        "Scan",
        "FileScan",
        "BatchScan",
        "RowDataSourceScan",
    }
)

_KNOWN_OPERATOR_ROOTS = (
    _STRUCTURAL_OPERATORS
    | _JOIN_OPERATORS
    | _EXCHANGE_OPERATORS
    | _COST_OPERATORS
    | frozenset(_PYTHON_UDF_OPERATORS)
)

_SECTION_RE = re.compile(r"^==\s*(.+?)\s*==\s*$")
_NODE_HEADER_RE = re.compile(r"^\((\d+)\)\s+(\S.*)$")
_FIELD_RE = re.compile(r"^([A-Z][A-Za-z0-9 _/]*?)\s*(?:\[(\d+)\])?\s*:\s?(.*)$")
_ATTR_REF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)#(\d+)L?\b")
_FINAL_PLAN_RE = re.compile(r"isFinalPlan\s*=\s*(true|false)")
_MORE_FIELDS_RE = re.compile(r"\.\.\.\s*\d+\s*more field", re.IGNORECASE)
_CODEGEN_RE = re.compile(r"^(?:Found \d+ WholeStageCodegen subtrees\.|Generated code:)")

# Prefixo de desenho de arvore: conectores (`+-`, `:-`, `:`), recuo, e o marcador
# de whole-stage codegen (`*` ou `*(3)`).
_TREE_PREFIX_RE = re.compile(r"^[\s:+|\-]*(?:\*\s*(?:\(\d+\))?\s*)?")

# Campos cujo conteudo e PLUMBING, nao uso: `Input` de um no apenas repete o
# `Output` do filho. Contar `Input` como "coluna usada" faria toda coluna lida
# parecer referenciada, e a razao de SF-PQ-004 seria sempre ~1 -- a regra nunca
# dispararia. Ver `_referenced_expr_ids`.
_PLUMBING_FIELDS = frozenset({"Input"})

_NESTED_TYPE_WORDS = ("struct", "array", "map")


def split_top_level(text: str) -> list[str]:
    """Divide por virgula so no nivel de profundidade zero.

    Conta `[]`, `()` e -- condicionalmente -- `<>`. O angulo so abre quando o
    `<` vem logo depois de `struct`/`array`/`map`: em plano fisico `<` e `>`
    tambem aparecem como COMPARACAO (`(valor#11 > 100.0)`), e conta-los sempre
    deixaria a profundidade permanentemente aberta, corrompendo tudo depois no
    mesmo texto.

    Entrada desbalanceada (plano cortado no meio) nao levanta nem entra em
    laco: o que sobrou volta como um unico campo, e a deteccao de truncamento
    de `_scan_facts` cuida de marcar o ponto cego.
    """
    parts: list[str] = []
    depth = 0
    angle = 0
    current: list[str] = []
    word: list[str] = []

    for char in text:
        if char.isalpha():
            word.append(char)
        elif char != "<":
            word = []

        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        elif char == "<":
            if "".join(word[-6:]).lower().endswith(_NESTED_TYPE_WORDS):
                angle += 1
            word = []
        elif char == ">":
            if angle > 0:
                angle -= 1
        elif char == "," and depth == 0 and angle == 0:
            parts.append("".join(current).strip())
            current = []
            continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


def _bracketed(value: str) -> str:
    """Conteudo de `[...]` quando o valor inteiro e uma lista; senao o proprio."""
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip()
    return stripped


def _is_truncated(value: str) -> bool:
    stripped = value.strip()
    return bool(_MORE_FIELDS_RE.search(stripped)) or stripped.endswith("...")


def _column_names(refs: list[str]) -> list[str]:
    """`cliente_id#10` -> `cliente_id`; entradas sem `#` voltam como estao."""
    names = []
    for ref in refs:
        match = _ATTR_REF_RE.search(ref)
        names.append(match.group(1) if match else ref.strip())
    return names


def _expr_ids(text: str) -> set[str]:
    return {m.group(2) for m in _ATTR_REF_RE.finditer(text)}


def _read_schema_fields(value: str) -> tuple[list[str], bool]:
    """Nomes de coluna de `struct<a:int,b:struct<c:int>>` e se veio truncado."""
    stripped = value.strip()
    truncated = _is_truncated(stripped)
    lowered = stripped.lower()
    if lowered.startswith("struct<") and stripped.endswith(">"):
        inner = stripped[len("struct<") : -1]
    elif lowered.startswith("struct<"):
        inner = stripped[len("struct<") :]
        truncated = True
    else:
        inner = stripped
    names = [field.split(":", 1)[0].strip() for field in split_top_level(inner)]
    names = [n for n in names if n and not n.startswith("...")]
    return names, truncated


class _Node:
    """Um operador do plano, ja separado do desenho de arvore.

    `fields` so existe no modo formatted (um campo por linha); no modo simple o
    no inteiro cabe em `header`, e os metadados sao extraidos de la.
    """

    __slots__ = ("node_id", "operator", "header", "line", "fields", "text")

    def __init__(self, node_id: int, operator: str, header: str, line: int) -> None:
        self.node_id = node_id
        self.operator = operator
        self.header = header
        self.line = line
        self.fields: dict[str, tuple[str, int | None]] = {}
        self.text = header

    def field(self, name: str) -> str | None:
        entry = self.fields.get(name)
        return None if entry is None else entry[0]

    def declared_count(self, name: str) -> int | None:
        entry = self.fields.get(name)
        return None if entry is None else entry[1]


def _operator_of(header: str) -> str:
    """Nome do operador a partir do cabecalho do no.

    `Scan parquet db.t` -> `Scan parquet`; `Filter [codegen id : 1]` -> `Filter`;
    `Exchange hashpartitioning(...)` -> `Exchange`.
    """
    scan_v1 = _SCAN_V1_RE.match(header)
    if scan_v1:
        prefix = "FileScan" if header.startswith("FileScan") else "Scan"
        return f"{prefix} {scan_v1.group(1)}"
    if _SCAN_V2_RE.match(header):
        return "BatchScan"
    token = re.match(r"^([A-Za-z][A-Za-z0-9_]*)", header)
    return token.group(1) if token else ""


def _subject(path: str, node: _Node, relation: str = "") -> dict[str, Any]:
    label = f"({node.node_id}) {node.operator}" if node.node_id else node.operator
    if relation:
        label = f"{label} {relation}"
    return {
        "type": "plan_node",
        "file": path,
        "line": node.line,
        "symbol": label,
        "node_id": node.node_id,
        "operator": node.operator,
        "relation": relation,
    }


def _file_subject(path: str, line: int) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


class _Parser:
    def __init__(self, text: str, path: str) -> None:
        self.path = path
        self.lines = text.splitlines()
        self.provenance = {
            "artifact": path,
            "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "extractor": EXTRACTOR_ID,
        }
        self.facts: list[Fact] = []
        self.nodes: list[_Node] = []
        self.mode = "unknown"
        self.skipped_logical_lines = 0
        self.skipped_initial_plan_lines = 0
        self.aqe_sections: list[str] = []

    # -- infra ---------------------------------------------------------- #

    def unresolved(self, line: int, reason: str, detail: str = "", snippet: str = "") -> None:
        attrs: dict[str, Any] = {"reason": reason}
        if detail:
            attrs["detail"] = detail
        subject = _file_subject(self.path, line)
        if snippet:
            subject["snippet"] = snippet[:200]
        self.facts.append(
            Fact(
                kind="plan.unresolved",
                subject=subject,
                attrs=attrs,
                provenance=self.provenance,
            )
        )

    # -- fatiamento ------------------------------------------------------ #

    def _physical_slice(self) -> list[tuple[int, str]]:
        """Linhas (1-based) da secao de plano fisico.

        Sem marcador `== ... ==`, o arquivo inteiro e a secao. Com marcadores,
        so `== Physical Plan ==` entra; as secoes logicas de `explain(True)`
        sao puladas de proposito e contadas em `skipped_logical_lines`.
        """
        markers = [
            (i, _SECTION_RE.match(raw).group(1))  # type: ignore[union-attr]
            for i, raw in enumerate(self.lines)
            if _SECTION_RE.match(raw)
        ]
        if not markers:
            return [(i + 1, raw) for i, raw in enumerate(self.lines)]

        selected: list[tuple[int, str]] = []
        current_is_physical = False
        for i, raw in enumerate(self.lines):
            marker = _SECTION_RE.match(raw)
            if marker:
                current_is_physical = "physical plan" in marker.group(1).lower()
                continue
            if current_is_physical:
                selected.append((i + 1, raw))
            elif raw.strip():
                self.skipped_logical_lines += 1
        return selected

    # -- reconhecimento de modo ------------------------------------------ #

    def parse(self) -> None:
        if not self.lines or not any(raw.strip() for raw in self.lines):
            self.unresolved(0, "empty_input")
            return

        if any(_CODEGEN_RE.match(raw.strip()) for raw in self.lines):
            self.unresolved(
                0,
                "unsupported_mode",
                "explain(\"codegen\") devolve codigo Java gerado, nao plano fisico. "
                "Regere com df.explain(\"formatted\").",
            )
            return

        body = self._drop_superseded_plan(self._physical_slice())
        has_formatted_headers = any(_NODE_HEADER_RE.match(raw.strip()) for _, raw in body)
        has_logical_sections = self.skipped_logical_lines > 0

        if has_formatted_headers:
            self.mode = "formatted"
            self._parse_formatted(body)
        elif self._looks_like_plan(body):
            self.mode = "extended" if has_logical_sections else "simple"
            self._parse_simple(body)

        if not self.nodes:
            self.mode = "unknown"
            first = next((raw for _, raw in body if raw.strip()), "")
            self.unresolved(
                body[0][0] if body else 1,
                "not_a_plan",
                "nenhum operador de plano fisico reconhecido no texto.",
                first,
            )

    def _drop_superseded_plan(self, body: list[tuple[int, str]]) -> list[tuple[int, str]]:
        """Descarta a arvore `== Initial Plan ==` quando existe uma final.

        Com AQE, um `explain()` tirado apos a execucao traz DUAS arvores: a que
        de fato rodou (`Final Plan`, ou `Current Plan` se ainda executando) e a
        que o otimizador substituiu (`Initial Plan`). Extrair facts das duas
        produz o mesmo achado em duplicidade e, pior, um achado derivado de um
        plano que o AQE ja jogou fora -- uma acusacao sobre trabalho que nunca
        rodou. O descarte e CONTADO (`skipped_initial_plan_lines`) e as secoes
        vistas ficam na sentinela: silenciar metade do artefato sem dizer seria
        o mesmo ponto cego nao declarado que este projeto existe para evitar.
        """
        sections = [
            _AQE_SECTION_RE.match(raw.strip()).group(1)  # type: ignore[union-attr]
            for _n, raw in body
            if _AQE_SECTION_RE.match(raw.strip())
        ]
        self.aqe_sections = sections
        if "Initial Plan" not in sections or not (
            {"Final Plan", "Current Plan"} & set(sections)
        ):
            return body

        kept: list[tuple[int, str]] = []
        current = ""
        for line_no, raw in body:
            marker = _AQE_SECTION_RE.match(raw.strip())
            if marker:
                current = marker.group(1)
                continue
            if current == "Initial Plan":
                if raw.strip():
                    self.skipped_initial_plan_lines += 1
                continue
            kept.append((line_no, raw))
        return kept

    def _looks_like_plan(self, body: list[tuple[int, str]]) -> bool:
        """Prova de que o texto e um plano fisico, antes de extrair qualquer no.

        Sem esta porta, prosa qualquer que comece com maiuscula viraria "no de
        plano" e o extrator reportaria facts sobre um README. Duas provas
        aceitas: um conector de arvore (`+-`/`:-`/`*(1)`), ou uma linha cujo
        operador esta no vocabulario conhecido (um plano de um unico no nao tem
        conector nenhum).
        """
        for _line_no, raw in body:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith(("+-", ":-", ":+")):
                return True
            if re.match(r"^\*\s*\(?\d*\)?\s*\w", stripped):
                return True
            root = re.match(r"^([A-Za-z][A-Za-z0-9_]*)", _TREE_PREFIX_RE.sub("", stripped))
            if root and root.group(1) in _KNOWN_OPERATOR_ROOTS:
                return True
        return False

    def _parse_formatted(self, body: list[tuple[int, str]]) -> None:
        """Secao de arvore + blocos de detalhe numerados.

        So os blocos de detalhe viram nos: o mesmo operador aparece nas DUAS
        secoes, e emitir dos dois lados duplicaria cada fact.
        """
        current: _Node | None = None
        for line_no, raw in body:
            stripped = raw.strip()
            header = _NODE_HEADER_RE.match(stripped)
            if header:
                node_text = header.group(2)
                current = _Node(
                    int(header.group(1)), _operator_of(node_text), node_text, line_no
                )
                self.nodes.append(current)
                continue
            if current is None or not stripped:
                continue

            field = _FIELD_RE.match(stripped)
            if field:
                name = field.group(1).strip()
                declared = int(field.group(2)) if field.group(2) else None
                current.fields[name] = (field.group(3).strip(), declared)
                current.text += "\n" + stripped
            else:
                # Continuacao de um campo longo quebrado em varias linhas, ou
                # ruido. Anexa ao texto do no (para contagem de expr id) e
                # reporta, porque nao foi interpretado como campo.
                current.text += "\n" + stripped
                self.unresolved(line_no, "unparsed_node_field", "", stripped)

    def _parse_simple(self, body: list[tuple[int, str]]) -> None:
        for line_no, raw in body:
            stripped = raw.strip()
            if not stripped:
                continue
            header = _TREE_PREFIX_RE.sub("", stripped).strip()
            if not header:
                continue
            operator = _operator_of(header)
            if not operator or not operator[0].isupper():
                self.unresolved(line_no, "unparsed_plan_line", "", stripped)
                continue
            self.nodes.append(_Node(0, operator, header, line_no))

    # -- colunas referenciadas ------------------------------------------- #

    def _usage_expr_ids(self, exclude: _Node) -> set[str]:
        """Expr ids usados por QUALQUER outro no, em posicao de uso real.

        `Input` fica de fora (ver `_PLUMBING_FIELDS`). No modo simple nao ha
        campo `Input`: o texto inline do operador ja e a posicao de uso.
        """
        used: set[str] = set()
        for node in self.nodes:
            if node is exclude:
                continue
            if node.fields:
                used |= _expr_ids(node.header)
                for name, (value, _count) in node.fields.items():
                    if name in _PLUMBING_FIELDS:
                        continue
                    used |= _expr_ids(value)
            else:
                used |= _expr_ids(node.header)
        return used

    # -- facts ------------------------------------------------------------ #

    def emit(self) -> None:
        for node in self.nodes:
            if node.operator.startswith(("Scan ", "FileScan ")) or node.operator == "BatchScan":
                self._scan_fact(node)
            elif node.operator in _JOIN_OPERATORS:
                self._join_fact(node)
            elif node.operator in _EXCHANGE_OPERATORS:
                self._exchange_fact(node)
            elif node.operator in _PYTHON_UDF_OPERATORS:
                self._python_udf_fact(node)
            elif node.operator in _COST_OPERATORS:
                self._operator_fact(node)
            elif node.operator == "AdaptiveSparkPlan":
                self._aqe_fact(node)

            if node.operator != "AdaptiveSparkPlan" and _FINAL_PLAN_RE.search(node.text):
                self._aqe_fact(node)

    def _scan_metadata(self, node: _Node) -> tuple[str, str, str, dict[str, str], list[str], bool]:
        """(api, formato, relacao, metadados, refs de saida, saida truncada)."""
        if node.fields:
            return self._scan_metadata_formatted(node)
        return self._scan_metadata_simple(node)

    def _scan_metadata_formatted(
        self, node: _Node
    ) -> tuple[str, str, str, dict[str, str], list[str], bool]:
        api = "v2_batch_scan" if node.operator == "BatchScan" else "v1_file_scan"
        fmt = node.operator.split(" ", 1)[1] if " " in node.operator else ""
        scan_v1 = _SCAN_V1_RE.match(node.header)
        if scan_v1:
            relation = scan_v1.group(2).strip()
        elif node.operator == "BatchScan":
            relation = node.header[len("BatchScan") :].strip()
        else:
            relation = ""
        relation = re.sub(r"\s*\[codegen id : \d+\]\s*$", "", relation).strip()

        metadata = {name: value for name, (value, _c) in node.fields.items()}
        output_raw = node.field("Output")
        refs: list[str] = []
        truncated = False
        if output_raw is not None:
            refs = split_top_level(_bracketed(output_raw))
            declared = node.declared_count("Output")
            truncated = _is_truncated(output_raw) or (
                declared is not None and declared != len(refs)
            )
            refs = [r for r in refs if "#" in r]
        return api, fmt, relation, metadata, refs, truncated

    def _scan_metadata_simple(
        self, node: _Node
    ) -> tuple[str, str, str, dict[str, str], list[str], bool]:
        """`FileScan parquet db.t[a#1,b#2] Batched: true, DataFilters: [...], ...`"""
        header = node.header
        api = "v2_batch_scan" if node.operator == "BatchScan" else "v1_file_scan"
        fmt = node.operator.split(" ", 1)[1] if " " in node.operator else ""

        open_bracket = header.find("[")
        close_bracket = header.find("]", open_bracket + 1) if open_bracket >= 0 else -1
        if open_bracket < 0 or close_bracket < 0:
            relation = header.split(" ", 2)[-1].strip() if " " in header else ""
            return api, fmt, relation, {}, [], True

        prefix = header[:open_bracket]
        relation = prefix.split(" ", 2)[-1].strip() if " " in prefix else ""
        output_raw = header[open_bracket + 1 : close_bracket]
        refs = [r for r in split_top_level(output_raw) if "#" in r]
        truncated = _is_truncated(output_raw)

        metadata: dict[str, str] = {}
        for chunk in split_top_level(header[close_bracket + 1 :]):
            if ":" not in chunk:
                continue
            name, _, value = chunk.partition(":")
            metadata[name.strip()] = value.strip()
        return api, fmt, relation, metadata, refs, truncated

    def _scan_fact(self, node: _Node) -> None:
        api, fmt, relation, metadata, output_refs, output_truncated = self._scan_metadata(node)

        read_schema_raw = metadata.get("ReadSchema")
        read_schema_names: list[str] = []
        read_schema_truncated = False
        if read_schema_raw is not None:
            read_schema_names, read_schema_truncated = _read_schema_fields(read_schema_raw)

        # `Batched` so existe em FileSourceScanExec (v1). O `FileScan` v2 nunca
        # o emite, e no bloco FORMATTED de v1 o `Format` e sempre suprimido --
        # entao `Batched` e o unico discriminador confiavel de API ali dentro.
        is_v1 = "Batched" in metadata

        partition_raw = metadata.get("PartitionFilters")
        partition_present = partition_raw is not None
        partition_items = split_top_level(_bracketed(partition_raw)) if partition_present else []

        pushed_raw = metadata.get("PushedFilters")
        data_raw = metadata.get("DataFilters")

        # O modo FORMATTED DESCARTA metadado de valor `[]`
        # (`FileSourceScanLike.verboseStringWithOperatorId`, identico em v3.3.0
        # e v3.5.6). Num scan v1 formatado, portanto, a AUSENCIA de
        # `PartitionFilters` significa lista VAZIA, nao "nao sei" -- ler a
        # ausencia como desconhecida faria SF-PQ-002 nunca disparar justamente
        # no modo que a skill recomenda. Fora dessa combinacao (modo simple, ou
        # scan v2, ou linha truncada), ausencia continua sendo desconhecida.
        formatted_v1 = self.mode == "formatted" and is_v1

        # `PartitionFilters: []` NAO prova tabela particionada: uma tabela sem
        # particao nenhuma imprime exatamente a mesma coisa. Confundir os dois
        # fabrica um P0 falso. So evidencia POSITIVA marca `table_partitioned`:
        #   1. PartitionFilters nao vazio -- so tabela particionada tem filtro
        #      de particao (e nesse caso o pruning esta acontecendo);
        #   2. uma coluna no `Output` do scan que NAO esta no `ReadSchema` --
        #      assinatura estrutural de coluna de particao, que o Spark le do
        #      caminho e nunca do arquivo (FileSourceScanExec.output =
        #      requiredSchema ++ partitionSchema);
        #   3. um segmento `chave=valor` no `Location` -- diretorio de particao
        #      no estilo Hive.
        # Sem nenhuma das tres a resposta e "unknown", NAO `false`: o parser nao
        # sabe, e dizer `false` seria afirmar o que nao observou.
        partitioned: Any = "unknown"
        evidence = "none"
        location = metadata.get("Location", "")
        if partition_items:
            partitioned, evidence = True, "partition_filters"
        elif (
            output_refs
            and not output_truncated
            and read_schema_raw is not None
            and not read_schema_truncated
            and set(_column_names(output_refs)) - set(read_schema_names)
        ):
            partitioned, evidence = True, "output_minus_read_schema"
        elif re.search(r"[/\[][\w.-]+=", location):
            partitioned, evidence = True, "location_path"

        partition_filters_empty: Any = "unknown"
        if partition_present:
            partition_filters_empty = not partition_items
        elif formatted_v1:
            partition_filters_empty = True

        measures: dict[str, Any] = {}
        if read_schema_raw is not None and not read_schema_truncated:
            measures["read_schema_columns"] = len(read_schema_names)
        if output_refs and not output_truncated:
            measures["output_columns"] = len(output_refs)
            scan_ids = _expr_ids(",".join(output_refs))
            measures["referenced_columns"] = len(scan_ids & self._usage_expr_ids(node))
        if partition_present and not _is_truncated(partition_raw or ""):
            measures["partition_filter_count"] = len(partition_items)
        elif formatted_v1:
            measures["partition_filter_count"] = 0
        if pushed_raw is not None and not _is_truncated(pushed_raw):
            measures["pushed_filter_count"] = len(split_top_level(_bracketed(pushed_raw)))
        elif formatted_v1:
            measures["pushed_filter_count"] = 0
        if data_raw is not None and not _is_truncated(data_raw):
            measures["data_filter_count"] = len(split_top_level(_bracketed(data_raw)))

        attrs: dict[str, Any] = {
            "relation": relation,
            "format": (fmt or metadata.get("Format", "")).lower(),
            "scan_api": api,
            "table_partitioned": partitioned,
            "partitioned_evidence": evidence,
            "partition_filters_present": partition_present,
            "partition_filters_empty": partition_filters_empty,
            "output_truncated": output_truncated,
            "read_schema_truncated": read_schema_truncated,
        }

        self.facts.append(
            Fact(
                kind="plan.file_scan",
                subject=_subject(self.path, node, relation),
                measures=measures,
                attrs=attrs,
                provenance=self.provenance,
            )
        )

        if output_truncated or read_schema_truncated:
            self.unresolved(
                node.line,
                "truncated_field_list",
                f"lista de campos truncada pelo Spark no no {node.node_id or node.line}; "
                f"a razao de SF-PQ-004 nao pode ser calculada sobre contagem parcial.",
                node.header,
            )

        # Ponto cego que importa: `PartitionFilters: []` sem nenhuma evidencia de
        # particionamento e exatamente o caso em que SF-PQ-002 fica indecidivel.
        # Silenciar isso faria "sem achado" parecer "sem problema".
        if partition_filters_empty is True and partitioned == "unknown":
            self.unresolved(
                node.line,
                "partition_status_unknown",
                f"{relation or 'scan'}: PartitionFilters vazio, mas o plano nao prova se a "
                f"tabela e particionada. SF-PQ-002 fica indecidivel; confirme com "
                f"`sparkforge analyze catalog-schema`.",
                node.header,
            )

    def _join_fact(self, node: _Node) -> None:
        text = node.text
        join_type = ""
        for candidate in (
            "Inner",
            "LeftOuter",
            "RightOuter",
            "FullOuter",
            "LeftSemi",
            "LeftAnti",
            "Cross",
        ):
            if re.search(rf"\b{candidate}\b", text):
                join_type = candidate
                break
        build_side = ""
        build = re.search(r"\bBuild(Left|Right)\b", text)
        if build:
            build_side = build.group(1).lower()

        condition = node.field("Join condition")
        has_condition = bool(condition and condition.strip().lower() not in ("none", ""))
        if condition is None and not node.fields:
            has_condition = node.operator not in ("CartesianProduct",)

        self.facts.append(
            Fact(
                kind="plan.join",
                subject=_subject(self.path, node),
                attrs={
                    "strategy": node.operator,
                    "join_type": join_type,
                    "build_side": build_side,
                    "has_condition": has_condition,
                    "is_broadcast": node.operator == "BroadcastHashJoin",
                },
                provenance=self.provenance,
            )
        )

    def _exchange_fact(self, node: _Node) -> None:
        text = node.field("Arguments") or node.header
        partitioning = ""
        for candidate in (
            "hashpartitioning",
            "rangepartitioning",
            "RoundRobinPartitioning",
            "SinglePartition",
            "IdentityBroadcastMode",
            "HashedRelationBroadcastMode",
        ):
            if candidate in text:
                partitioning = candidate
                break
        if node.operator == "BroadcastExchange" and not partitioning:
            partitioning = "broadcast"

        self.facts.append(
            Fact(
                kind="plan.exchange",
                subject=_subject(self.path, node),
                attrs={
                    "operator": node.operator,
                    "partitioning": partitioning,
                    "is_broadcast": node.operator == "BroadcastExchange",
                },
                provenance=self.provenance,
            )
        )

    def _python_udf_fact(self, node: _Node) -> None:
        self.facts.append(
            Fact(
                kind="plan.python_udf",
                subject=_subject(self.path, node),
                attrs={
                    "operator": node.operator,
                    "udf_type": _PYTHON_UDF_OPERATORS[node.operator],
                },
                provenance=self.provenance,
            )
        )

    def _operator_fact(self, node: _Node) -> None:
        self.facts.append(
            Fact(
                kind="plan.operator",
                subject=_subject(self.path, node),
                attrs={"operator": node.operator},
                provenance=self.provenance,
            )
        )

    def _aqe_fact(self, node: _Node) -> None:
        match = _FINAL_PLAN_RE.search(node.text)
        is_final = match.group(1) == "true" if match else "unknown"
        self.facts.append(
            Fact(
                kind="plan.aqe",
                subject=_subject(self.path, node),
                attrs={"is_final_plan": is_final},
                provenance=self.provenance,
            )
        )

    # -- sentinela -------------------------------------------------------- #

    def sentinel(self) -> Fact:
        unresolved_count = sum(1 for f in self.facts if f.kind == "plan.unresolved")
        aqe = [f for f in self.facts if f.kind == "plan.aqe"]
        attrs: dict[str, Any] = {
            "mode": self.mode,
            "aqe_present": bool(aqe),
            # Um finding derivado de plano NAO final pode estar errado: o AQE
            # reescreve estrategia de join e particionamento depois de cada
            # shuffle. A sentinela carrega isso para quem le os facts poder
            # distinguir, em vez de tratar os dois planos como equivalentes.
            "aqe_final_plan": aqe[0].attrs["is_final_plan"] if aqe else "unknown",
            "aqe_sections_seen": list(self.aqe_sections),
        }
        return Fact(
            kind="plan.analyzed",
            subject=_file_subject(self.path, 0),
            measures={
                "line_count": len(self.lines),
                "node_count": len(self.nodes),
                "file_scan_count": sum(1 for f in self.facts if f.kind == "plan.file_scan"),
                "exchange_count": sum(1 for f in self.facts if f.kind == "plan.exchange"),
                "skipped_logical_lines": self.skipped_logical_lines,
                "skipped_initial_plan_lines": self.skipped_initial_plan_lines,
                "unresolved_count": unresolved_count,
            },
            attrs=attrs,
            provenance=self.provenance,
        )


def extract_plan(text: str, path: str) -> list[Fact]:
    """Extrai Facts do texto de um plano fisico. Nunca levanta.

    Qualquer falha inesperada vira um `plan.unresolved` com
    `reason: extraction_error` e a sentinela `plan.analyzed` continua sendo
    emitida -- pelo mesmo motivo de `pyspark_ast.extract_tree`: um insumo
    patologico nao pode apagar a analise nem derrubar quem chamou.
    """
    parser = _Parser(text, path)
    try:
        parser.parse()
        parser.emit()
    except Exception as exc:  # nenhum insumo pode derrubar quem chamou
        parser.unresolved(0, "extraction_error", f"{type(exc).__name__}: {exc}")

    facts = list(parser.facts)
    facts.append(parser.sentinel())

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    return sort_facts(facts)


def extract_plan_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo de plano, ancorando o path relativo a `repo_root`.

    `utf-8-sig` pela mesma razao de `pyspark_ast.extract_path`: um plano colado
    num arquivo salvo pelo Notepad do Windows chega com BOM, e sem isto a
    primeira linha nao casaria nenhum padrao e o plano inteiro viraria
    `not_a_plan`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [
            Fact(
                kind="plan.unresolved",
                subject=_file_subject(anchor, 0),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={
                    "artifact": anchor,
                    "artifact_sha256": "",
                    "extractor": EXTRACTOR_ID,
                },
            )
        ]
    return extract_plan(text, anchor)
