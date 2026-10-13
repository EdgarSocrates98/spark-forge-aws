"""Extracao textual de arestas de lineage -- caminho S3 e nome de tabela.

Leitura lexica, nao parse: serve para orientar a investigacao, e por isso cada
aresta carrega o `offset` que ancora o achado na linha real do fonte. Nao
substitui `analyze_pyspark`, que le AST.
"""
import re

_S3_RE = re.compile(r"s3://[^\s\"`,)]+")
_TABLE_RE = re.compile(
    r"(?:from|into|join|table)\s+([A-Za-z_][\w.-]*(?:\.[A-Za-z_][\w.-]*)?)",
    re.I,
)


def extract_lineage_edges(text):
    edges = []
    for m in _S3_RE.finditer(text):
        edges.append(
            {"kind": "s3", "name": m.group(0), "direction": "read", "offset": m.start()}
        )
    for m in _TABLE_RE.finditer(text):
        direction = "read" if m.group(0).lower().startswith(("from", "join")) else "write"
        edges.append(
            {"kind": "table", "name": m.group(1), "direction": direction, "offset": m.start()}
        )
    deduped = {(e["kind"], e["name"], e["direction"]): e for e in edges}
    return sorted(deduped.values(), key=lambda e: (e["kind"], e["name"]))
