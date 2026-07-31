"""Logica compartilhada entre a CLI (`cli.py`) e a superficie MCP (`tools.py`).

Adaptador fino: nenhuma funcao aqui decide limiar, severidade ou rota. Tudo
delega para `sparkforge.facts`, `sparkforge.rules`, `sparkforge.case` e
`sparkforge.findings`. Isto existe para que a CLI e o servidor MCP nunca
divirjam -- os dois chamam exatamente as mesmas funcoes deste modulo.

`AdapterError` e o unico tipo de erro que atravessa a fronteira do adaptador:
`cli.py` o traduz em (stderr, exit code); `tools.py` o traduz em um dict
`{"error": ...}`. Erros de baixo nivel (`CaseError`, `CatalogError`,
`ValidationFailed`) sao capturados aqui e reembalados, nunca vazam crus.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.case import router, store
from sparkforge.case.resume import render_handoff
from sparkforge.case.resume import resume as run_resume
from sparkforge.collect import aws as collect_aws
from sparkforge.collect.base import CollectorUnavailable, verify_all
from sparkforge.facts.athena_workgroup import (
    extract_athena_workgroup_path,
    extract_athena_workgroup_tree,
)
from sparkforge.facts.call_graph import build_call_graph
from sparkforge.facts.catalog_schema import (
    extract_catalog_schema_path,
    extract_catalog_schema_tree,
)
from sparkforge.facts.consumers import extract_consumers_path, extract_consumers_tree
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.fusion import fuse as run_fuse
from sparkforge.facts.iceberg_metadata import (
    extract_iceberg_metadata_path,
    extract_iceberg_metadata_tree,
)
from sparkforge.facts.pyspark_ast import extract_path, extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.s3_listing import extract_s3_listing_path, extract_s3_listing_tree
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.facts.sql_literal import extract_sql_from_pyspark, extract_sql_path
from sparkforge.facts.terraform import (
    extract_terraform_diff,
    extract_terraform_path,
    extract_terraform_tree,
)
from sparkforge.findings.models import Fact, RuntimeContext, sort_facts
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.rules.engine import judge as run_judge
from sparkforge.rules.loader import CatalogError, load_catalog

DEFAULT_LIMIT = 50


class AdapterError(Exception):
    """Erro acionavel de fronteira: mensagem pronta para stderr ou para um
    dict `{"error": ...}`, mais o exit code que a CLI deve devolver."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def _count_by(items: list[Any], keyfn: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = keyfn(item)
        counts[key] = counts.get(key, 0) + 1
    return counts


def paginate_items(
    items: list[Any], limit: int | None, cursor: str | None
) -> tuple[list[Any], str | None]:
    """Fatia `items` (ja filtrado) em uma pagina. `limit=None` devolve tudo.

    Cursor e um offset inteiro codificado como string -- suficiente porque a
    ordenacao upstream (sort_facts/sort_findings/ordem do catalogo) ja e
    deterministica, entao o mesmo cursor sempre reproduz a mesma pagina.
    """
    try:
        start = int(cursor) if cursor else 0
    except ValueError as exc:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2) from exc
    if start < 0:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2)

    if limit is None:
        return items[start:], None

    end = start + limit
    page = items[start:end]
    next_cursor = str(end) if end < len(items) else None
    return page, next_cursor


def build_runtime_context(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> RuntimeContext:
    raw = {
        "glue_version": glue,
        "spark_version": spark,
        "python_version": python,
        "iceberg_version": iceberg,
        "athena_version": athena,
    }
    cleaned = {k: v for k, v in raw.items() if v}
    sources = {"cli": cleaned} if cleaned else {}
    context, _facts = detect_runtime(sources)
    return context


# --------------------------------------------------------------------------- #
# analyze pyspark
# --------------------------------------------------------------------------- #


def _extract_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        # Erro traz causa E o comando que resolve. Dizer so o que esta errado
        # deixa o operador (ou o agente) adivinhando o proximo passo, que e a
        # forma mais barata de fazer uma ferramenta parecer quebrada.
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio da biblioteca ou para um arquivo .py:\n"
            f"    sparkforge analyze pyspark --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_tree(target, repo_root=target)
    return extract_path(target, repo_root=target.parent)


def analyze_pyspark(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    # `unresolved` e contado sobre `facts`, nao sobre `filtered`: um filtro por
    # kind nao pode fazer o ponto cego desaparecer do relatorio. A regra 7 do
    # AGENT_PROTOCOL.md exige reportar sempre — no nao resolvido e ponto cego,
    # nao ausencia de problema, e omiti-lo deixa o operador confundir "nao achei"
    # com "nao ha".
    unresolved = sum(1 for f in facts if f.kind == "pyspark.unresolved")
    unresolved_at = [
        {
            "file": f.subject.get("file", ""),
            "line": f.subject.get("line", 0),
            "reason": f.attrs.get("reason", ""),
        }
        for f in facts
        if f.kind == "pyspark.unresolved"
    ]

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "unresolved": unresolved,
        "unresolved_at": unresolved_at,
        "items": page,
    }


# --------------------------------------------------------------------------- #
# analyze catalog-schema
# --------------------------------------------------------------------------- #


def _extract_catalog_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps do Glue Data Catalog ou para um "
            f"arquivo .json:\n"
            f"    sparkforge analyze catalog-schema --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_catalog.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_catalog_schema_tree(target, repo_root=target)
    return extract_catalog_schema_path(target, repo_root=target.parent)


def analyze_catalog_schema(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_catalog_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    # Mesmo raciocinio de `analyze_pyspark`: `unresolved` conta sobre `facts`,
    # nao sobre `filtered`, para um filtro por kind nao esconder o ponto cego.
    unresolved = sum(1 for f in facts if f.kind == "catalog.unresolved")
    unresolved_at = [
        {"file": f.subject.get("file", ""), "reason": f.attrs.get("reason", "")}
        for f in facts
        if f.kind == "catalog.unresolved"
    ]

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "unresolved": unresolved,
        "unresolved_at": unresolved_at,
        "items": page,
    }


def _facts_page(
    facts: list[Fact],
    unresolved_kind: str | None,
    kind: list[str] | None,
    limit: int | None,
    cursor: str | None,
) -> dict[str, Any]:
    """Pagina uma lista de Facts ja extraida, no mesmo shape de
    `analyze_pyspark`/`analyze_catalog_schema`: total/pagina/by_kind, mais
    `unresolved`/`unresolved_at` quando `unresolved_kind` e informado.

    `unresolved_kind` e `None` para extratores derivados que nao tem ponto
    cego proprio (`analyze_call_graph`: deriva de Facts ja resolvidos por
    `pyspark_ast`, nunca falha em interpretar algo por si so) -- as duas
    chaves ficam simplesmente ausentes do resultado, em vez de zeradas, para
    nao alegar uma garantia que o extrator nao da.

    Compartilhado pelos extratores adicionados apos `analyze_pyspark`/
    `analyze_catalog_schema` (que ja tinham a logica inline antes deste
    helper existir e continuam como estao, para nao arriscar o golden test
    dos dois por um refactor que nao muda comportamento).
    """
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    result: dict[str, Any] = {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "items": page,
    }

    if unresolved_kind is not None:
        # Mesmo raciocinio de `analyze_pyspark`/`analyze_catalog_schema`:
        # contado sobre `facts` (o conjunto completo), nao sobre `filtered`,
        # para um filtro por kind nao fazer o ponto cego desaparecer do
        # relatorio. Regra 7 do AGENT_PROTOCOL.md.
        unresolved = sum(1 for f in facts if f.kind == unresolved_kind)
        unresolved_at = [
            {
                "file": f.subject.get("file", ""),
                "line": f.subject.get("line", 0),
                "reason": f.attrs.get("reason", ""),
            }
            for f in facts
            if f.kind == unresolved_kind
        ]
        result["unresolved"] = unresolved
        result["unresolved_at"] = unresolved_at

    return result


# --------------------------------------------------------------------------- #
# analyze event-log
# --------------------------------------------------------------------------- #


def _extract_event_log_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o arquivo de Spark event log (.jsonl):\n"
            f"    sparkforge analyze event-log --path <arquivo> "
            f"--out .sparkforge/facts_eventlog.json",
            exit_code=2,
        )
    return extract_event_log_path(target, repo_root=target.parent)


def analyze_event_log(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_event_log_facts(path)
    return _facts_page(facts, "spark.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze plan
# --------------------------------------------------------------------------- #


def _extract_plan_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um arquivo de texto com a saida de "
            f"`df.explain(\"formatted\")` (um plano por arquivo):\n"
            f"    sparkforge analyze plan --path <arquivo> "
            f"--out .sparkforge/facts_plan.json",
            exit_code=2,
        )
    return extract_plan_path(target, repo_root=target.parent)


def analyze_plan(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Extrai Facts do texto de um plano fisico ja salvo em disco.

    Um arquivo por chamada, nunca um diretorio: cada arquivo e UM plano, e
    concatenar planos de queries diferentes na mesma analise misturaria nos com
    a mesma numeracao `(N)` vindos de arvores distintas.
    """
    facts = _extract_plan_facts(path)
    return _facts_page(facts, "plan.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze terraform
# --------------------------------------------------------------------------- #


def _extract_terraform_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com arquivos .tf ou para um arquivo .tf:\n"
            f"    sparkforge analyze terraform --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_terraform.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_terraform_tree(target, repo_root=target)
    return extract_terraform_path(target, repo_root=target.parent)


def analyze_terraform(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_terraform_facts(path)
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze iceberg
# --------------------------------------------------------------------------- #


def _extract_iceberg_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps das metadata tables Iceberg ou para "
            f"um arquivo .json:\n"
            f"    sparkforge analyze iceberg --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_iceberg.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_iceberg_metadata_tree(target, repo_root=target)
    return extract_iceberg_metadata_path(target, repo_root=target.parent)


def analyze_iceberg(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_iceberg_facts(path)
    return _facts_page(facts, "iceberg.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze sql
# --------------------------------------------------------------------------- #


def _extract_sql_facts(path: str | None, from_pyspark: str | None) -> list[Fact]:
    if from_pyspark:
        target = Path(from_pyspark)
        if not target.is_file():
            raise AdapterError(
                f"Caminho nao encontrado para analise: {from_pyspark}\n"
                f'  Aponte para um arquivo .py com chamadas spark.sql("..."):\n'
                f"    sparkforge analyze sql --from-pyspark <arquivo> "
                f"--out .sparkforge/facts_sql.json",
                exit_code=2,
            )
        try:
            source = target.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise AdapterError(f"{from_pyspark}: erro de leitura: {exc}", exit_code=2) from exc
        return extract_sql_from_pyspark(source, target.name)

    if not path:
        raise AdapterError(
            "informe --path <arquivo.sql> ou --from-pyspark <arquivo.py>.",
            exit_code=2,
        )
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um arquivo .sql:\n"
            f"    sparkforge analyze sql --path <arquivo> --out .sparkforge/facts_sql.json",
            exit_code=2,
        )
    return extract_sql_path(target, repo_root=target.parent)


def analyze_sql(
    path: str | None = None,
    from_pyspark: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_sql_facts(path, from_pyspark)
    return _facts_page(facts, "sql.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze athena-workgroup
# --------------------------------------------------------------------------- #


def _extract_athena_workgroup_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de workgroups do Athena ou para um "
            f"arquivo .json:\n"
            f"    sparkforge analyze athena-workgroup --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_athena.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_athena_workgroup_tree(target, repo_root=target)
    return extract_athena_workgroup_path(target, repo_root=target.parent)


def analyze_athena_workgroup(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_athena_workgroup_facts(path)
    return _facts_page(facts, "athena.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze s3-listing
# --------------------------------------------------------------------------- #


def _extract_s3_listing_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com paginas de listagem ou para um arquivo .json:\n"
            f"    aws s3api list-objects-v2 --bucket <b> --prefix <p> > listing.json\n"
            f"    sparkforge analyze s3-listing --path listing.json "
            f"--out .sparkforge/facts_s3.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_s3_listing_tree(target, repo_root=target)
    return extract_s3_listing_path(target, repo_root=target.parent)


def analyze_s3_listing(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_s3_listing_facts(path)
    return _facts_page(facts, "s3.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze consumers
# --------------------------------------------------------------------------- #


def _extract_consumers_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o inventario declarado de consumidores:\n"
            f"    sparkforge analyze consumers --path .sparkforge/consumers.yaml "
            f"--out .sparkforge/facts_consumers.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_consumers_tree(target, repo_root=target)
    return extract_consumers_path(target, repo_root=target.parent)


def analyze_consumers(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    facts = _extract_consumers_facts(path)
    return _facts_page(facts, "env.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze terraform-diff
# --------------------------------------------------------------------------- #


def analyze_terraform_diff(
    before: str,
    after: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    before_path = Path(before)
    after_path = Path(after)
    for label, target in (("--before", before_path), ("--after", after_path)):
        if not target.is_dir():
            raise AdapterError(
                f"Diretorio nao encontrado para {label}: {target}\n"
                f"  Aponte para dois estados do mesmo modulo Terraform (dois checkouts,\n"
                f"  dois `git worktree`, o main e o branch do PR):\n"
                f"    sparkforge analyze terraform-diff --before ./infra-main "
                f"--after ./infra-pr",
                exit_code=2,
            )
    facts = extract_terraform_diff(before_path, after_path, repo_root=after_path)
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze call-graph
# --------------------------------------------------------------------------- #


def analyze_call_graph(
    facts_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Deriva Facts de grafo de chamadas a partir de um arquivo de facts ja
    extraido (tipicamente `analyze pyspark --out`). Funcao pura sobre Facts:
    nunca reparseia fonte -- ver docstring de `sparkforge.facts.call_graph`.
    Sem `unresolved` proprio: o grafo so deriva do que `pyspark_ast` ja
    resolveu, nunca falha em interpretar algo por si so.
    """
    fact_list = _load_facts_file(facts_path)
    derived = build_call_graph(fact_list, path_hint=facts_path)
    return _facts_page(derived, None, kind, limit, cursor)


# --------------------------------------------------------------------------- #
# fuse
# --------------------------------------------------------------------------- #


def fuse_facts(
    facts_paths: list[str] | None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Combina um ou mais arquivos de facts (`analyze pyspark --out`,
    `analyze catalog-schema --out`, ou qualquer outro produtor de facts) e
    roda `sparkforge.facts.fusion.fuse` sobre a uniao.

    `--facts` e repetivel de proposito: fusao so tem o que correlacionar
    quando ve facts de mais de uma fonte na MESMA chamada (texto SQL de um
    lado, schema do catalogo do outro) -- diferente de `judge --facts`, que
    aceita um unico arquivo porque so julga o que ja esta combinado. A saida
    de `fuse` (facts originais + `.enriched` + `fusion.summary`, ver docstring
    de `sparkforge/facts/fusion.py`) e desenhada para alimentar `judge --facts`
    direto, sem outro passo de combinacao no meio.
    """
    if not facts_paths:
        raise AdapterError(
            "informe ao menos um --facts (arquivo gerado por `analyze pyspark --out` "
            "ou `analyze catalog-schema --out`). Repetivel para combinar as fontes "
            "que a fusao precisa correlacionar.",
            exit_code=2,
        )

    combined: list[Fact] = []
    for facts_path in facts_paths:
        combined.extend(_load_facts_file(facts_path))

    fused = run_fuse(combined)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in fused if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    summary = next((f for f in fused if f.kind == "fusion.summary"), None)

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "summary": summary.to_dict() if summary is not None else None,
        "items": page,
    }


# --------------------------------------------------------------------------- #
# judge
# --------------------------------------------------------------------------- #


def _facts_from_dicts(payload: Any) -> list[Fact]:
    if not isinstance(payload, list):
        raise AdapterError("facts precisa ser uma lista de objetos fact.", exit_code=2)

    facts: list[Fact] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise AdapterError(f"facts[{index}] nao e um objeto.", exit_code=2)
        try:
            kwargs: dict[str, Any] = {"kind": entry["kind"], "subject": entry["subject"]}
        except KeyError as exc:
            raise AdapterError(
                f"facts[{index}] esta sem o campo obrigatorio {exc}. O arquivo de facts "
                "pode ter sido gerado por uma versao antiga do schema. Rode "
                "`sparkforge analyze pyspark --path <dir> --out <arquivo>` novamente.",
                exit_code=2,
            ) from exc
        for optional in ("measures", "attrs", "provenance", "schema_version"):
            if optional in entry:
                kwargs[optional] = entry[optional]
        facts.append(Fact(**kwargs))
    return facts


def _load_facts_file(facts_path: str) -> list[Fact]:
    path = Path(facts_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de facts nao encontrado: {facts_path}. Rode "
            f"`sparkforge analyze pyspark --path <dir> --out {facts_path}` para gera-lo.",
            exit_code=2,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{facts_path}: JSON invalido: {exc}", exit_code=2) from exc
    return _facts_from_dicts(raw)


def _merge_facts_files(facts_paths: list[str]) -> list[Fact]:
    """Une varios arquivos de facts numa lista unica, sem duplicata e ordenada.

    `judge` correlaciona facts de extratores diferentes (`SF-GLUE-004` cruza
    `tf.attribute` com `pyspark.write`), e cada extrator escreve o seu proprio
    arquivo. Sem uniao aqui, avaliar essa classe de regra exigia concatenar
    dois arrays JSON na mao -- passo manual que, quando ninguem faz, apenas
    faz a regra nunca disparar.

    A deduplicacao e por conteudo do que o fact AFIRMA (kind + subject +
    measures + attrs), nao por provenance: dois arquivos que se sobrepoem
    descrevem a mesma observacao uma vez so. Sem isso, o mesmo fact viraria
    duas entradas em `Finding.evidence` e o achado pareceria duas vezes mais
    sustentado do que e. `sort_facts` no fim e a mesma normalizacao que
    `judge` ja aplica -- a ordem passa a depender do conteudo, nunca da ordem
    em que os arquivos foram informados na linha de comando.
    """
    seen: set[str] = set()
    merged: list[Fact] = []
    for facts_path in facts_paths:
        for fact in _load_facts_file(facts_path):
            key = json.dumps(
                {
                    "kind": fact.kind,
                    "subject": fact.subject,
                    "measures": fact.measures,
                    "attrs": fact.attrs,
                },
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(fact)
    return sort_facts(merged)


def judge_findings(
    facts: list[dict[str, Any]] | None = None,
    facts_path: str | list[str] | None = None,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    severity: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    show_skipped: bool = False,
) -> dict[str, Any]:
    if facts is not None:
        fact_list = _facts_from_dicts(facts)
    elif facts_path is not None:
        # `facts_path` aceita um caminho ou uma lista deles: uma regra pode
        # exigir facts de mais de um extrator (SF-GLUE-004) e cada extrator
        # escreve o seu arquivo. Um caminho unico continua valendo -- e a forma
        # que toda skill documenta.
        paths = [facts_path] if isinstance(facts_path, str) else list(facts_path)
        if not paths:
            raise AdapterError(
                "informe ao menos um `facts_path` (arquivo gerado por "
                "`sparkforge analyze pyspark --out <arquivo>`).",
                exit_code=2,
            )
        fact_list = _merge_facts_files(paths)
    else:
        raise AdapterError(
            "informe `facts` (lista inline de facts) ou `facts_path` (arquivo gerado por "
            "`sparkforge analyze pyspark --out <arquivo>`).",
            exit_code=2,
        )

    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    context = build_runtime_context(glue, spark, python, iceberg, athena)
    runtime = context.to_dict()

    findings, skipped = run_judge(fact_list, rules, runtime, return_skipped=True)
    finding_dicts = [f.to_dict() for f in findings]

    if severity:
        wanted = set(severity)
        finding_dicts = [f for f in finding_dicts if f["severity"] in wanted]

    by_severity = _count_by(finding_dicts, lambda f: f["severity"])
    page, next_cursor = paginate_items(finding_dicts, limit, cursor)

    result: dict[str, Any] = {
        "total_count": len(finding_dicts),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "severity": list(severity) if severity else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_severity": by_severity,
        "items": page,
    }
    if show_skipped:
        result["skipped"] = skipped
    return result


# --------------------------------------------------------------------------- #
# runtime detect
# --------------------------------------------------------------------------- #


def runtime_detect(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> dict[str, Any]:
    return build_runtime_context(glue, spark, python, iceberg, athena).to_dict()


# --------------------------------------------------------------------------- #
# rules lookup
# --------------------------------------------------------------------------- #


def rules_lookup(
    id: list[str] | None = None,  # noqa: A002 -- nome do parametro espelha o flag --id
    category: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    filtered = rules
    if id:
        wanted_ids = set(id)
        filtered = [r for r in filtered if r["id"] in wanted_ids]
    if category:
        filtered = [r for r in filtered if r.get("category") == category]

    by_category = _count_by(filtered, lambda r: r.get("category", ""))
    clean = [{k: v for k, v in r.items() if k != "_source_file"} for r in filtered]
    page, next_cursor = paginate_items(clean, limit, cursor)

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "id": list(id) if id else None,
            "category": category,
            "limit": limit,
            "cursor": cursor,
        },
        "by_category": by_category,
        "rules": page,
    }


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #


def validate_output(finding: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_finding(finding)
        return {"valid": True, "errors": []}
    except ValidationFailed as exc:
        return {"valid": False, "errors": [str(exc)]}


# --------------------------------------------------------------------------- #
# case lifecycle
# --------------------------------------------------------------------------- #


def case_open(
    repo: str,
    case_id: str,
    now: str,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
) -> dict[str, Any]:
    context = build_runtime_context(glue, spark, python, iceberg, athena)
    case = store.new_case(case_id, now, context.to_dict(), repo=repo)
    store.save_case(case, root=repo)
    return case


def case_get(repo: str) -> dict[str, Any]:
    try:
        return store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def case_update(
    repo: str,
    phase: str | None = None,
    gate: str | None = None,
    gate_value: bool = True,
    skill: str | None = None,
    now: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
        if phase is not None:
            case = store.set_phase(case, phase)
        if gate is not None:
            case = store.set_gate(case, gate, bool(gate_value))
        if skill is not None:
            case = store.record_skill_use(case, skill, now or "", outcome or "")
        store.save_case(case, root=repo)
        return case
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def next_step(repo: str, findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    finding_ids = [
        f.get("rule_id") for f in (findings or []) if isinstance(f, dict) and f.get("rule_id")
    ]
    try:
        return router.next_step(case, finding_ids)
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def resume_case(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    try:
        return run_resume(
            case, findings or [], unresolved_count=unresolved, in_flight=in_flight, root=root
        )
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def handoff(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    payload = resume_case(repo, findings, unresolved, in_flight, root=root)
    markdown = render_handoff(payload)
    path = Path(repo) / ".sparkforge" / "handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    result = dict(payload)
    result["handoff_path"] = str(path)
    return result


# --------------------------------------------------------------------------- #
# collect (coletores AWS)
# --------------------------------------------------------------------------- #


def _collect_error(exc: Exception, repo: str, rel_path: str) -> AdapterError:
    """Reembala falha de coleta com o caminho exato onde o artefato coletado
    manualmente precisa ficar -- sem isto, "colete manualmente e registre"
    (a mensagem generica de `require_boto3`) deixa o operador adivinhando
    onde. Perder acesso a AWS nao pode deixar a ferramenta inutilizavel."""
    message = str(exc)
    if isinstance(exc, CollectorUnavailable):
        expected = Path(repo) / rel_path
        message += (
            f"\n  Alternativa manual: baixe o artefato (AWS CLI ou console), salve em "
            f"{expected}, e registre com `sparkforge.collect.register_artifact` "
            f"(kind, sha256, source e o collect_command acima)."
        )
    return AdapterError(message, exit_code=2)


def _collect_payload(entry: Any, now: str) -> dict[str, Any]:
    payload = entry.to_dict()
    # `collected_at != now` prova que a chamada foi um cache hit local (o
    # sha256 ja batia) -- nenhuma rede, nenhuma credencial AWS tocada. Sem
    # este campo, "no-op" e um fato que so existe nos logs internos do
    # coletor, invisivel para quem le a saida da CLI/MCP.
    payload["cache_hit"] = entry.collected_at != now
    return payload


def collect_event_log(
    repo: str, *, job_run_id: str, bucket: str, prefix: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.event_log_path(job_run_id)
    try:
        entry = collect_aws.collect_event_log(
            job_run_id, Path(repo), bucket=bucket, prefix=prefix, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_glue_job(repo: str, *, job_name: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.glue_job_path(job_name)
    try:
        entry = collect_aws.collect_glue_job(job_name, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_cloudwatch(
    repo: str, *, job_name: str, job_run_id: str, start: str, end: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.cloudwatch_path(job_name, job_run_id)
    try:
        entry = collect_aws.collect_cloudwatch(
            job_name, job_run_id, Path(repo), now=now, start=start, end=end
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_iceberg_metadata(
    repo: str, *, table: str, workgroup: str, output_location: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.iceberg_metadata_path(table)
    try:
        entry = collect_aws.collect_iceberg_metadata(
            table, Path(repo), workgroup=workgroup, output_location=output_location, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_athena_workgroup(repo: str, *, workgroup: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.athena_workgroup_path(workgroup)
    try:
        entry = collect_aws.collect_athena_workgroup(workgroup, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_verify(repo: str) -> dict[str, Any]:
    results = verify_all(repo)
    missing = [r for r in results if not r["present"]]
    mismatched = [r for r in results if r["present"] and not r["hash_matches"]]
    ok = [r for r in results if r["present"] and r["hash_matches"]]
    return {
        "total_count": len(results),
        "ok_count": len(ok),
        "missing_count": len(missing),
        "mismatched_count": len(mismatched),
        "artifacts": results,
    }
