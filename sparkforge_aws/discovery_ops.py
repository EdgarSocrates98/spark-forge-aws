# sparkforge_aws/discovery_ops.py
"""Mapa ops conceituais do install-2.0 (§6.2) -> verbos REAIS do sparkforge-aws.

Fonte unica do mapeamento: o manifesto `forge/context/v1`
(`install/lifecycle.py::_context_manifest`) e o verbo
`sparkforge-aws capabilities` emitem o MESMO mapa daqui — a tabela nao vive
copiada em dois lugares para nunca divergir em silencio.

Cada entrada liga o op conceitual (chave de `discovery.ops` no manifesto) ao
comando declarado: `id` (o id do discovery command), `argv` (o que vai depois
do nome do CLI — `{placeholder}` e slot do consumidor, nunca preenchido aqui),
`mode` (o enum COMMAND_MODES do contrato) e `description`.
"""

from __future__ import annotations

from typing import Any

CLI = "sparkforge-aws"

# Dominios publicados do forge — os MESMOS nomes do campo `domains` do
# manifesto forge/context/v1 (`install/lifecycle.py::_AWS_DOMAINS`). O
# consumidor le `domains` do manifesto e passa um deles em
# `context pack --domain`/`knowledge search --domain`; `DOMAIN_PREFIXES`
# traduz cada nome publicado nos prefixos nativos (categorias de regra e
# segmentos do knowledge) que o matching mecanico resolve.
DOMAINS: tuple[str, ...] = (
    "pyspark",
    "aws-glue",
    "amazon-emr",
    "amazon-athena",
    "apache-iceberg",
    "spark-streaming",
    "terraform",
    "data-quality",
)

# Nome publicado -> prefixos nativos. Um nome NAO listado aqui casa como
# prefixo literal dele mesmo — `glue`, `emr-eks`, `spark-plan` e os prefixos
# de `known_domains` (em `capabilities`) funcionam sem registro.
DOMAIN_PREFIXES: dict[str, tuple[str, ...]] = {
    "pyspark": ("pyspark", "spark"),
    "aws-glue": ("glue",),
    "amazon-emr": ("emr",),
    "amazon-athena": ("athena",),
    "apache-iceberg": ("iceberg",),
    "spark-streaming": ("streaming",),
    "terraform": ("terraform",),
    "data-quality": ("data-quality", "dq"),
}


def domain_prefixes(domain: str) -> tuple[str, ...]:
    """Os prefixos nativos de um dominio — o nome publicado resolve pela
    tabela; qualquer outro valor casa como prefixo literal (normalizado)."""
    norm = domain.strip().lower().replace("_", "-")
    return DOMAIN_PREFIXES.get(norm, (norm,))


PROTOCOLS: tuple[dict[str, str], ...] = (
    {"id": "forge/v1", "version": "1"},
    {"id": "forge/context/v1", "version": "1"},
    {"id": "forge/context-registry/v1", "version": "1"},
)

MCP_INTERFACE: dict[str, Any] = {
    "server_name": "sparkforge-aws",
    "command": [CLI, "mcp", "serve"],
    "verify_tool": "sparkforge_aws_runtime_detect",
}

OPS: dict[str, dict[str, Any]] = {
    "capabilities.list": {
        "id": "capabilities",
        "argv": ["capabilities"],
        "mode": "direct-capability",
        "description": (
            "capabilities.list (§6.2) — o que este forge instalado consegue "
            "fazer: contagens reais, areas de regra, protocolos e este mapa"
        ),
    },
    "protocol.describe": {
        "id": "capabilities",
        "argv": ["capabilities"],
        "mode": "direct-capability",
        "description": (
            "protocol.describe (§6.2) — secoes `protocols`+`interfaces` do "
            "mesmo verbo `capabilities`"
        ),
    },
    "rules.search": {
        "id": "rules-search",
        "argv": [
            "rules",
            "lookup",
            "--query",
            "{term}",
            "--category",
            "{category}",
            "--severity",
            "{severity}",
            "--runtime",
            "{runtime}",
            "--limit",
            "{limit}",
            "--cursor",
            "{cursor}",
        ],
        "mode": "direct-capability",
        "description": (
            "rules.search (§6.2) — catalogo filtrado por palavra-chave, "
            "categoria, severidade, runtime; paginado, campos §6.4 completos"
        ),
    },
    "rules.get": {
        "id": "rules-get",
        "argv": ["rules", "lookup", "--id", "{rule_id}"],
        "mode": "direct-capability",
        "description": (
            "rules.get (§6.2) — uma regra pelo id, em `rules[0]`; vazio "
            "significa ausente, nunca inventada"
        ),
    },
    "knowledge.search": {
        "id": "knowledge-search",
        "argv": [
            "knowledge",
            "search",
            "{term}",
            "--domain",
            "{domain}",
            "--limit",
            "{limit}",
            "--cursor",
            "{cursor}",
        ],
        "mode": "direct-capability",
        "description": (
            "knowledge.search (§6.2) — busca textual offline com filtro de "
            "dominio, paginacao e sha256 por documento"
        ),
    },
    "knowledge.get": {
        "id": "knowledge-get",
        "argv": ["knowledge", "path", "--file", "{file}"],
        "mode": "direct-capability",
        "description": (
            "knowledge.get (§6.2) — resolve o caminho absoluto do documento "
            "no pacote instalado, com sha256 e proveniencia"
        ),
    },
    "context.build": {
        "id": "context-pack",
        "argv": ["context", "pack", "--domain", "{domain}"],
        "mode": "direct-capability",
        "description": (
            "context.build (§6.2) — Context Pack limitado por dominio: "
            "regras aplicaveis + knowledge + protocolos + hash"
        ),
    },
    "health.check": {
        "id": "doctor",
        "argv": ["doctor"],
        "mode": "diagnostic-only",
        "description": "health.check (§6.2) — ambiente, pacote e catalogos",
    },
}


def commands() -> list[dict[str, Any]]:
    """Os `discovery.commands` do manifesto — um comando por id declarado,
    na ordem estavel das OPS (ids unicos preservados)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in OPS.values():
        if entry["id"] in seen:
            continue
        seen.add(entry["id"])
        out.append(
            {
                "id": entry["id"],
                "argv": [CLI, *entry["argv"]],
                "mode": entry["mode"],
                "read_only": True,
                "description": entry["description"],
            }
        )
    return out


def ops() -> dict[str, str]:
    """O `discovery.ops` do manifesto: op conceitual -> id do comando."""
    return {op: entry["id"] for op, entry in OPS.items()}


def ops_expanded() -> dict[str, dict[str, Any]]:
    """O mapa materializado para `capabilities`: op -> comando + argv real."""
    return {
        op: {"command": entry["id"], "argv": [CLI, *entry["argv"]]} for op, entry in OPS.items()
    }
