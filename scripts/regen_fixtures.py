#!/usr/bin/env python3
"""Regenera os golden outputs das fixtures.

Rode SOMENTE quando a mudanca de comportamento for intencional, e revise o diff:
o golden e a defesa contra falso positivo, e regenerar sem ler o diff a destroi.

Uso:
    python scripts/regen_fixtures.py            # todas
    python scripts/regen_fixtures.py coalesce_one
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.facts.athena_workgroup import extract_athena_workgroup_path  # noqa: E402
from sparkforge.facts.call_graph import build_call_graph  # noqa: E402
from sparkforge.facts.catalog_schema import (  # noqa: E402
    extract_catalog_schema_path,
    extract_catalog_schema_tree,
)
from sparkforge.facts.consumers import extract_consumers_path  # noqa: E402
from sparkforge.facts.emr_cluster import extract_emr_cluster_path  # noqa: E402
from sparkforge.facts.event_log import extract_event_log_path  # noqa: E402
from sparkforge.facts.fusion import fuse  # noqa: E402
from sparkforge.facts.iceberg_metadata import (  # noqa: E402
    extract_iceberg_metadata_path,
    extract_iceberg_metadata_tree,
)
from sparkforge.facts.pyspark_ast import extract_tree  # noqa: E402
from sparkforge.facts.runtime_detect import detect_runtime  # noqa: E402
from sparkforge.facts.s3_listing import extract_s3_listing_path  # noqa: E402
from sparkforge.facts.spark_plan import extract_plan_path  # noqa: E402
from sparkforge.facts.sql_literal import extract_sql_path  # noqa: E402
from sparkforge.facts.terraform import (  # noqa: E402
    extract_terraform_diff,
    extract_terraform_tree,
)
from sparkforge.rules.engine import judge  # noqa: E402
from sparkforge.rules.loader import load_catalog  # noqa: E402

FIXTURES = ROOT / "fixtures" / "pyspark"
FIXTURES_EVENTLOG = ROOT / "fixtures" / "eventlog"
FIXTURES_TERRAFORM = ROOT / "fixtures" / "terraform"
FIXTURES_ICEBERG = ROOT / "fixtures" / "iceberg"
FIXTURES_SQL = ROOT / "fixtures" / "sql"
FIXTURES_FUSION = ROOT / "fixtures" / "fusion"
FIXTURES_CATALOG = ROOT / "fixtures" / "catalog"
FIXTURES_PLAN = ROOT / "fixtures" / "plan"
FIXTURES_ATHENA = ROOT / "fixtures" / "athena"
FIXTURES_EMR = ROOT / "fixtures" / "emr"
FIXTURES_RUNTIME = ROOT / "fixtures" / "runtime"
FIXTURES_CALLGRAPH = ROOT / "fixtures" / "callgraph"
FIXTURES_S3 = ROOT / "fixtures" / "s3"
FIXTURES_CONSUMERS = ROOT / "fixtures" / "consumers"
FIXTURES_TFDIFF = ROOT / "fixtures" / "tfdiff"
FIXTURES_INFRA_CODE = ROOT / "fixtures" / "infra_code"


def _write_expected(directory: Path, facts, findings) -> None:
    out = directory / "expected"
    out.mkdir(exist_ok=True)
    for name, payload in (
        ("facts.json", [f.to_dict() for f in facts]),
        ("findings.json", [f.to_dict() for f in findings]),
    ):
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        # newline="\n" força LF mesmo no Windows: sem isso, write_text() em
        # modo texto traduz para o newline nativo da plataforma (CRLF), e
        # todo golden já commitado (LF) vira diff espúrio de fim de linha.
        (out / name).write_text(text, encoding="utf-8", newline="\n")

    fired = ", ".join(sorted({f.rule_id for f in findings})) or "nenhum"
    print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings ({fired})")


def regen(directory: Path) -> None:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_eventlog(directory: Path) -> None:
    """Como `regen`, mas para fixtures de event log: uma unica *.jsonl sob
    input/, extraida com `extract_event_log_path` em vez de `extract_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    facts = []
    for jsonl in jsonl_files:
        facts.extend(extract_event_log_path(jsonl, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_terraform(directory: Path) -> None:
    """Como `regen`, mas para fixtures de Terraform: `*.tf` sob input/, extraida
    com `extract_terraform_tree` em vez de `extract_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_terraform_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_iceberg(directory: Path) -> None:
    """Como `regen`, mas para fixtures de metadata Iceberg: `*.json` sob
    input/, extraida com `extract_iceberg_metadata_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_iceberg_metadata_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_sql(directory: Path) -> None:
    """Como `regen_eventlog`, mas para fixtures de SQL: uma unica *.sql sob
    input/, extraida com `extract_sql_path`. Nao ha `extract_sql_tree` --
    mesma decisao de `event_log.py`, que tambem nao tem variante `_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for sql_file in sorted(input_dir.glob("*.sql")):
        facts.extend(extract_sql_path(sql_file, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_catalog(directory: Path) -> None:
    """Como `regen_iceberg`, mas para fixtures do extrator do Glue Data
    Catalog: `*.json` sob input/, extraida com `extract_catalog_schema_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_catalog_schema_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_callgraph(directory: Path) -> None:
    """Corpus de grafo de chamadas: `*.py` sob input/, extraidos por
    `extract_tree` e DERIVADOS por `build_call_graph`.

    O golden guarda so os facts derivados. Os de `pyspark_ast` que serviram de
    entrada ja tem o corpus `fixtures/pyspark/`; repeti-los aqui faria a mesma
    mudanca quebrar dois goldens pelo mesmo motivo, escondendo qual dos dois
    contratos regrediu.
    """
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    derived = build_call_graph(facts, path_hint=directory.name)
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    findings = judge(derived, load_catalog(), meta["runtime"])
    _write_expected(directory, derived, findings)


def regen_runtime(directory: Path) -> None:
    """Corpus de deteccao de runtime. Unico que NAO julga com `meta["runtime"]`.

    Aqui o runtime nao e premissa da fixture, e o resultado dela: julgar com o
    runtime declarado no meta esconderia justamente o defeito que este corpus
    existe para pegar -- uma deteccao que resolve para a versao errada
    continuaria sendo julgada contra a versao certa, e a guarda
    `runtime_scope` das regras nunca reprovaria nada. O meta declara o runtime
    ESPERADO, e o golden test compara com o detectado.
    """
    input_dir = directory / "input"
    sources: dict = {}
    for source_file in sorted(input_dir.glob("*.json")):
        sources.update(json.loads(source_file.read_text(encoding="utf-8")))
    context, facts = detect_runtime(sources)
    findings = judge(facts, load_catalog(), context.to_dict())
    _write_expected(directory, facts, findings)


def regen_infra_code(directory: Path) -> None:
    """Terraform E codigo PySpark do MESMO job, no mesmo `input/`.

    Duas regras do catalogo cruzam infraestrutura com codigo e nao podem ser
    provadas por nenhum corpus de fonte unica: SF-ENV-003 (argumento de
    observabilidade ligado sem `GlueContext` no codigo) e SF-GLUE-004
    (`max_retries` com escrita `append`, que a retentativa duplica).
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = list(extract_terraform_tree(input_dir, repo_root=input_dir))
    facts.extend(extract_tree(input_dir, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_s3(directory: Path) -> None:
    """Listagem S3, e opcionalmente o dump de catalogo que ela precisa.

    `input/*.json` sao listagens; `input/catalog/*.json`, quando existe, e o
    dump do Glue Data Catalog. SF-PQ-005 e a razao do segundo: ela correlaciona
    o que esta no armazenamento com a cardinalidade de particao declarada no
    catalogo, e nenhuma das duas fontes responde sozinha.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for listing in sorted(input_dir.glob("*.json")):
        facts.extend(extract_s3_listing_path(listing, repo_root=input_dir))
    catalog_dir_path = input_dir / "catalog"
    if catalog_dir_path.is_dir():
        facts.extend(extract_catalog_schema_tree(catalog_dir_path, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_consumers(directory: Path) -> None:
    """Inventario declarado de consumidores, e o dump Iceberg da tabela.

    SF-ENV-002 so existe na interseccao: a tabela em format V3 vem do metadata
    Iceberg, e quem a consome vem do inventario. Uma fixture com so uma das
    metades nao prova nada sobre a regra.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for inventory in sorted(input_dir.glob("*.yaml")):
        facts.extend(extract_consumers_path(inventory, repo_root=input_dir))
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_iceberg_metadata_path(dump, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_tfdiff(directory: Path) -> None:
    """Diff de Terraform (`input/before/` e `input/after/`) mais o event log.

    SF-GLUE-005 pergunta se alguem aumentou o worker SEM evidencia de pressao
    de memoria: a mudanca vem do diff, e a evidencia (ou a falta dela) vem do
    event log. As duas fontes na mesma fixture, porque a regra so faz sentido
    com as duas.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = list(
        extract_terraform_diff(input_dir / "before", input_dir / "after", repo_root=input_dir)
    )
    for log in sorted(input_dir.glob("*.jsonl")):
        facts.extend(extract_event_log_path(log, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_athena(directory: Path) -> None:
    """Como `regen_catalog`, mas para dumps de workgroup do Athena: `*.json`
    sob input/, extraidos com `extract_athena_workgroup_path`. Nao ha variante
    `_tree` neste extrator -- um dump ja descreve varios workgroups."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_athena_workgroup_path(dump, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_emr(directory: Path) -> None:
    """Como `regen_athena`, mas para dumps de cluster EMR on EC2: `*.json` sob
    input/, extraidos com `extract_emr_cluster_path`. Um dump ja e a uniao dos
    seis subcomandos de um cluster, entao nao ha variante `_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_emr_cluster_path(dump, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_plan(directory: Path) -> None:
    """Como `regen_eventlog`, mas para fixtures de plano fisico: `*.txt` sob
    input/ (a saida colada de `explain("formatted")`), extraida com
    `extract_plan_path`. Um plano e um arquivo de texto, nao uma arvore de
    codigo, entao nao ha variante `_tree` -- mesma decisao de `event_log.py`
    e `sql_literal.py`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for plan_file in sorted(input_dir.glob("*.txt")):
        facts.extend(extract_plan_path(plan_file, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_fusion(directory: Path) -> None:
    """Como `regen_sql`, mas o corpus de fusao: `*.sql` E `*.json` sob
    input/ na MESMA fixture (a query e o dump de catalogo que ela precisa
    correlacionar). Extrai as duas fontes, roda `fuse` sobre a uniao, e SO
    ENTAO julga -- provando as regras SF-ATH-* desbloqueadas disparando (ou
    corretamente nao disparando) a partir de facts fundidos de verdade, nao
    so unitariamente."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = []
    for sql_file in sorted(input_dir.glob("*.sql")):
        facts.extend(extract_sql_path(sql_file, repo_root=input_dir))
    for json_file in sorted(input_dir.glob("*.json")):
        facts.extend(extract_catalog_schema_path(json_file, repo_root=input_dir))
    fused = fuse(facts)
    findings = judge(fused, load_catalog(), meta["runtime"])
    _write_expected(directory, fused, findings)


def main() -> int:
    targets = sys.argv[1:]

    if targets:
        for name in targets:
            # Um nome pode existir em mais de um corpus (ex.: "clean_job" em
            # fixtures/pyspark E fixtures/terraform -- e o nome mais comum de
            # fixture do repo, cada corpus tem o seu). Regenerar so o
            # primeiro achado regeneraria o corpus errado em silencio;
            # regenerar todos os que casam o nome e a unica opcao segura.
            matches = [
                (FIXTURES / name, regen),
                (FIXTURES_EVENTLOG / name, regen_eventlog),
                (FIXTURES_TERRAFORM / name, regen_terraform),
                (FIXTURES_ICEBERG / name, regen_iceberg),
                (FIXTURES_SQL / name, regen_sql),
                (FIXTURES_FUSION / name, regen_fusion),
                (FIXTURES_CATALOG / name, regen_catalog),
                (FIXTURES_PLAN / name, regen_plan),
                (FIXTURES_ATHENA / name, regen_athena),
                (FIXTURES_EMR / name, regen_emr),
                (FIXTURES_RUNTIME / name, regen_runtime),
                (FIXTURES_CALLGRAPH / name, regen_callgraph),
                (FIXTURES_S3 / name, regen_s3),
                (FIXTURES_CONSUMERS / name, regen_consumers),
                (FIXTURES_TFDIFF / name, regen_tfdiff),
                (FIXTURES_INFRA_CODE / name, regen_infra_code),
            ]
            found = [(path, fn) for path, fn in matches if path.is_dir()]
            if not found:
                print(f"fixture nao encontrada: {name}", file=sys.stderr)
                return 1
            if len(found) > 1:
                corpora = ", ".join(path.parent.name for path, _ in found)
                print(f"{name}: nome ambiguo, regenerando em todos os corpus ({corpora})")
            for path, fn in found:
                fn(path)
        return 0

    for directory in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        regen(directory)
    for directory in sorted(p for p in FIXTURES_EVENTLOG.iterdir() if p.is_dir()):
        regen_eventlog(directory)
    for directory in sorted(p for p in FIXTURES_TERRAFORM.iterdir() if p.is_dir()):
        regen_terraform(directory)
    for directory in sorted(p for p in FIXTURES_ICEBERG.iterdir() if p.is_dir()):
        regen_iceberg(directory)
    for directory in sorted(p for p in FIXTURES_SQL.iterdir() if p.is_dir()):
        regen_sql(directory)
    for directory in sorted(p for p in FIXTURES_FUSION.iterdir() if p.is_dir()):
        regen_fusion(directory)
    for directory in sorted(p for p in FIXTURES_CATALOG.iterdir() if p.is_dir()):
        regen_catalog(directory)
    for directory in sorted(p for p in FIXTURES_PLAN.iterdir() if p.is_dir()):
        regen_plan(directory)
    for directory in sorted(p for p in FIXTURES_ATHENA.iterdir() if p.is_dir()):
        regen_athena(directory)
    for directory in sorted(p for p in FIXTURES_EMR.iterdir() if p.is_dir()):
        regen_emr(directory)
    for directory in sorted(p for p in FIXTURES_RUNTIME.iterdir() if p.is_dir()):
        regen_runtime(directory)
    for directory in sorted(p for p in FIXTURES_CALLGRAPH.iterdir() if p.is_dir()):
        regen_callgraph(directory)
    for directory in sorted(p for p in FIXTURES_S3.iterdir() if p.is_dir()):
        regen_s3(directory)
    for directory in sorted(p for p in FIXTURES_CONSUMERS.iterdir() if p.is_dir()):
        regen_consumers(directory)
    for directory in sorted(p for p in FIXTURES_TFDIFF.iterdir() if p.is_dir()):
        regen_tfdiff(directory)
    for directory in sorted(p for p in FIXTURES_INFRA_CODE.iterdir() if p.is_dir()):
        regen_infra_code(directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
