"""Superficie de ferramentas MCP da Fase 0. Nao importa o SDK do MCP.

`mcp.py` e a unica camada que fala com o SDK; este modulo so declara os
contratos (`TOOLS`) e despacha (`call_tool`) para `sparkforge.adapters._core`
-- as mesmas funcoes que a CLI usa. Isto garante que a CLI e o cliente MCP
nunca podem discordar sobre o que uma analise ou um julgamento devolve.

`outputSchema` em toda ferramenta e o ponto: um cliente MCP le
`structuredContent` sem reparsear texto, entao o contrato e identico sob
qualquer LLM. `sparkforge_rules_lookup` e `sparkforge_validate_output` sao o
nucleo da independencia de modelo -- ver as descricoes abaixo.

Cada `outputSchema` abaixo e construido a partir do retorno real de
`sparkforge.adapters._core` (nao da descricao da ferramenta) e verificado
em `tests/test_adapters_tools.py::TestOutputSchemasAreReal` contra a saida
real de `call_tool`. Um `{"type": "object"}` generico passaria em qualquer
teste superficial e nao entregaria nada: o cliente voltaria a adivinhar a
forma, que e exatamente o problema que esta camada existe para evitar.

Nenhuma ferramenta da Fase 0 e destrutiva nem open-world: o nucleo e
offline, e coletores AWS ficam para a Fase 1. So `case_open` e `case_update`
escrevem em disco (`.sparkforge/case.yaml`); todas as outras sao read-only.
"""
from __future__ import annotations

from typing import Any

from sparkforge.adapters import _core

_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_WRITE_NOT_IDEMPOTENT = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": False,
}

_WRITE_IDEMPOTENT = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

# Os coletores AWS (`collect_*`, exceto `collect_verify`) sao as primeiras
# ferramentas deste projeto que tocam a rede: leem de S3/Glue/CloudWatch/Athena
# de verdade, nunca mudam estado do lado AWS (so `get_object`, `get_job`,
# `get_metric_data`, `SELECT`/`get_work_group` -- ver docstring de
# `sparkforge.collect.aws`), e por isso sao `readOnlyHint: True` e
# `openWorldHint: True` ao mesmo tempo -- leem, mas de fora do sandbox local.
# `collect_verify` fica de fora deste grupo: so le o manifesto e recalcula
# sha256 local, nunca toca rede (`openWorldHint: False`, ver `_READ_ONLY`).
_READ_ONLY_OPEN_WORLD = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

# --------------------------------------------------------------------------- #
# blocos de schema compartilhados -- ver `sparkforge/findings/models.py` e
# `sparkforge/findings/schemas/{fact,finding}.schema.json` para a autoridade
# sobre a forma de Fact e Finding; `_core.py` para a autoridade sobre o que
# cada funcao realmente devolve.
# --------------------------------------------------------------------------- #

_PAGE_PROPERTIES: dict[str, Any] = {
    "total_count": {
        "type": "integer",
        "description": "Tamanho do conjunto apos filtros, antes da paginacao.",
    },
    "returned_count": {
        "type": "integer",
        "description": "Quantos itens vieram nesta pagina (`len(items)`).",
    },
    "next_cursor": {
        "type": ["string", "null"],
        "description": (
            "Offset da proxima pagina, codificado como string decimal "
            "(nao inteiro: e o mesmo valor que `cursor` aceita de volta). "
            "`null` quando esta e a ultima pagina."
        ),
    },
}

_FACT_SUBJECT: dict[str, Any] = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {
            "type": "string",
            "enum": ["source_location", "stage", "task", "tf_resource", "table", "job_run"],
        },
        "file": {"type": "string"},
        "line": {"type": "integer"},
        "col": {"type": "integer"},
        "end_line": {"type": "integer"},
        "symbol": {"type": "string"},
        "snippet": {"type": "string"},
    },
}

_FACT_ITEM: dict[str, Any] = {
    "type": "object",
    "description": "Observacao deterministica ancorada; nunca contem juizo nem limiar.",
    "required": ["id", "schema_version", "kind", "subject", "measures", "attrs", "provenance"],
    "properties": {
        "id": {
            "type": "string",
            "pattern": "^f_[0-9a-f]{6}$",
            "description": "sha1[:6] de kind+subject+measures; identifica o que o fact afirma.",
        },
        "schema_version": {"type": "integer"},
        "kind": {"type": "string", "description": "Ex.: pyspark.partitioning, pyspark.unresolved."},
        "subject": _FACT_SUBJECT,
        "measures": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "Somente numerico; unidade no nome da chave.",
        },
        "attrs": {"type": "object", "description": "Atributos livres, nao numericos."},
        "provenance": {
            "type": "object",
            "properties": {
                "artifact": {"type": "string"},
                "artifact_sha256": {"type": "string"},
                "extractor": {"type": "string"},
            },
        },
    },
}

_FINDING_ITEM: dict[str, Any] = {
    "type": "object",
    "description": "Juizo sobre o sistema analisado; sempre lastreado por ao menos um Fact.",
    "required": [
        "rule_id",
        "schema_version",
        "catalog_version",
        "title",
        "severity",
        "confidence",
        "status",
        "subject",
        "evidence",
        "measured",
        "threshold",
        "runtime_scope",
        "explanation",
        "proposed_change",
        "expected_effect",
        "benchmark_ref",
        "risks",
        "tradeoffs",
        "validation",
        "rollback",
        "sources",
    ],
    "properties": {
        "rule_id": {"type": "string", "pattern": "^SF-[A-Z]+-[0-9]{3}$"},
        "schema_version": {"type": "integer"},
        "catalog_version": {"type": "integer"},
        "title": {"type": "string"},
        "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "P4"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "status": {"type": "string", "enum": ["structural", "confirmed"]},
        "subject": {"type": "object"},
        "evidence": {
            "type": "array",
            "items": {"type": "string", "pattern": "^f_[0-9a-f]{6}$"},
            "minItems": 1,
            "description": "IDs de Fact que sustentam o finding. Finding sem Fact e invalido.",
        },
        "measured": {"type": "object"},
        "threshold": {"type": "object"},
        "runtime_scope": {"type": "object"},
        "explanation": {"type": "string"},
        "proposed_change": {"type": "array", "items": {"type": "string"}},
        "expected_effect": {"type": "string"},
        "benchmark_ref": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "tradeoffs": {"type": "array", "items": {"type": "string"}},
        "validation": {"type": "array", "items": {"type": "string"}},
        "rollback": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "object"}},
    },
}

_RUNTIME_CONTEXT: dict[str, Any] = {
    "type": "object",
    "required": ["glue", "spark", "python", "iceberg", "athena", "detected_from", "divergences"],
    "properties": {
        "glue": {"type": "string"},
        "spark": {"type": "string"},
        "python": {"type": "string"},
        "iceberg": {"type": "string"},
        "athena": {"type": "string"},
        "detected_from": {"type": "array", "items": {"type": "string"}},
        "divergences": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Divergencia entre fontes de versao nao e resolvida escolhendo uma; "
                "e reportada aqui em vez de descartada em silencio."
            ),
        },
    },
}

_ALTERNATIVE_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["rank", "rule_id", "recommended_skill", "reason"],
    "properties": {
        "rank": {"type": "integer"},
        "rule_id": {"type": "string"},
        "recommended_skill": {"type": "string"},
        "reason": {"type": "string"},
    },
}

_NEXT_STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "phase",
        "recommended_skill",
        "reason",
        "evidence",
        "missing_artifacts",
        "collect_commands",
        "blocked_by",
        "alternatives",
    ],
    "properties": {
        "phase": {"type": "string"},
        "recommended_skill": {"type": "string"},
        "reason": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "missing_artifacts": {"type": "array", "items": {"type": "string"}},
        "collect_commands": {"type": "array", "items": {"type": "string"}},
        "blocked_by": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Gates nao satisfeitos; advisory, nao impede a rota.",
        },
        "alternatives": {"type": "array", "items": _ALTERNATIVE_ITEM},
        "note": {
            "type": "string",
            "description": "So presente quando a regra de routing.yaml que casou declara `note`.",
        },
    },
}

_GATE_NAMES = (
    "baseline_captured",
    "dominant_bottleneck_identified",
    "functional_validation_defined",
    "flows_mapped",
)

_GATES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": list(_GATE_NAMES),
    "properties": {gate: {"type": "boolean"} for gate in _GATE_NAMES},
}

_SKILL_USE_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["skill", "at", "outcome"],
    "properties": {
        "skill": {"type": "string"},
        "at": {"type": "string"},
        "outcome": {"type": "string"},
    },
}

_HYPOTHESIS_ITEM: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "statement": {"type": "string"},
        "prediction": {"type": "string"},
        "experiment": {"type": "string"},
        "status": {"type": "string"},
    },
}

_ARTIFACT_ITEM: dict[str, Any] = {
    "type": "object",
    "description": (
        "Artefato coletado (Fase 1); a forma completa ainda nao esta estabilizada "
        "pelos coletores AWS, que ainda nao existem neste repositorio."
    ),
    "properties": {
        "kind": {"type": "string"},
        "path": {"type": "string"},
        "present": {"type": "boolean"},
        "collect_command": {"type": "string"},
    },
}

_CASE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Estado completo de .sparkforge/case.yaml -- barramento de handoff.",
    "required": [
        "schema_version",
        "case_id",
        "created_at",
        "runtime",
        "scope",
        "phase",
        "artifacts",
        "facts_index",
        "findings_index",
        "baseline",
        "hypotheses",
        "gates",
        "skills_used",
        "open_questions",
    ],
    "properties": {
        "schema_version": {"type": "integer"},
        "case_id": {"type": "string"},
        "created_at": {
            "type": "string",
            "description": "Timestamp ISO 8601 injetado por quem chama.",
        },
        "runtime": _RUNTIME_CONTEXT,
        "scope": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "entrypoints": {"type": "array", "items": {"type": "string"}},
                "job_names": {"type": "array", "items": {"type": "string"}},
                "consumers": {"type": "array", "items": {"type": "string"}},
            },
        },
        "phase": {
            "type": "string",
            "enum": [
                "intake",
                "inventory",
                "facts",
                "diagnosis",
                "hypothesis",
                "experiment",
                "validation",
                "report",
            ],
        },
        "artifacts": {"type": "array", "items": _ARTIFACT_ITEM},
        "facts_index": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "count": {"type": "integer"},
                "by_kind": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
        },
        "findings_index": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "count": {"type": "integer"},
                "by_severity": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
        },
        "baseline": {
            "type": ["object", "null"],
            "description": "`null` ate a metrica de baseline ser capturada.",
        },
        "hypotheses": {"type": "array", "items": _HYPOTHESIS_ITEM},
        "gates": _GATES_SCHEMA,
        "skills_used": {"type": "array", "items": _SKILL_USE_ITEM},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}

_COVERAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["facts", "findings", "unresolved"],
    "properties": {
        "facts": {"type": "integer"},
        "findings": {"type": "integer"},
        "unresolved": {
            "type": "integer",
            "description": (
                "Nos que o extrator nao conseguiu resolver estaticamente; ponto cego, "
                "nao ausencia de problema. Nunca deve ser lido como 'sem achados'."
            ),
        },
    },
}

_RESUME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "case_id",
        "phase",
        "created_at",
        "runtime",
        "baseline",
        "top_findings",
        "open_hypotheses",
        "gates",
        "unsatisfied_gates",
        "missing_artifacts",
        "next_step",
        "in_flight",
        "coverage",
        "skills_used",
        "open_questions",
    ],
    "properties": {
        "case_id": {"type": "string"},
        "phase": {"type": "string"},
        "created_at": {"type": "string"},
        "runtime": _RUNTIME_CONTEXT,
        "baseline": {
            "type": ["string", "object"],
            "description": "Literal 'ausente' quando o case nao tem baseline; senao o dict salvo.",
        },
        "top_findings": {
            "type": "array",
            "maxItems": 10,
            "items": {"type": "object"},
            "description": (
                "Ate 10 findings de `findings` (parametro de entrada), ordenados por "
                "severidade. Forma livre: quem chama decide o shape de cada finding, "
                "a ferramenta so ordena e corta."
            ),
        },
        "open_hypotheses": {"type": "array", "items": _HYPOTHESIS_ITEM},
        "gates": _GATES_SCHEMA,
        "unsatisfied_gates": {"type": "array", "items": {"type": "string"}},
        "missing_artifacts": {"type": "array", "items": _ARTIFACT_ITEM},
        "next_step": _NEXT_STEP_SCHEMA,
        "in_flight": {"type": "string"},
        "coverage": _COVERAGE_SCHEMA,
        "skills_used": {"type": "array", "items": _SKILL_USE_ITEM},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}

_ANALYZE_PYSPARK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "total_count",
        "returned_count",
        "next_cursor",
        "filters_applied",
        "by_kind",
        "unresolved",
        "unresolved_at",
        "items",
    ],
    "properties": {
        **_PAGE_PROPERTIES,
        "filters_applied": {
            "type": "object",
            "properties": {
                "kind": {"type": ["array", "null"], "items": {"type": "string"}},
                "limit": {"type": ["integer", "null"]},
                "cursor": {"type": ["string", "null"]},
            },
        },
        "by_kind": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
            "description": "Contagem sobre o conjunto completo apos filtros, nao so a pagina.",
        },
        "unresolved": {
            "type": "integer",
            "description": (
                "Contagem sobre TODOS os facts extraidos, nao so os filtrados por `kind`: "
                "um filtro nao pode fazer o ponto cego desaparecer do relatorio. E sinal "
                "de ponto cego, nao ausencia de problema."
            ),
        },
        "unresolved_at": {
            "type": "array",
            "description": "Onde cada no nao resolvido estaticamente ocorre.",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "reason": {"type": "string"},
                },
            },
        },
        "items": {"type": "array", "items": _FACT_ITEM},
    },
}

# Shape compartilhado por TODOS os extratores de arquivo/diretorio que
# reportam ponto cego: `analyze_pyspark`, `analyze_catalog_schema`,
# `analyze_event_log`, `analyze_terraform`, `analyze_iceberg`, `analyze_sql`,
# `analyze_athena_workgroup` (`sparkforge/adapters/_core.py::_facts_page`).
# Reaproveitado por identidade (nao uma copia com outro nome): a forma e
# genuinamente identica, entao um schema por tool so duplicaria texto sem
# testar nada a mais -- `TestOutputSchemasAreReal` ainda valida a saida REAL
# de cada tool contra este schema compartilhado.
_ANALYZE_FACTS_SCHEMA = _ANALYZE_PYSPARK_SCHEMA

# `analyze_call_graph` deriva de Facts ja resolvidos (nunca reparseia fonte,
# ver `sparkforge.facts.call_graph`): sem `unresolved`/`unresolved_at`
# proprios -- as duas chaves ficam ausentes, nunca zeradas, porque a tool nao
# tem ponto cego para reportar.
_ANALYZE_CALL_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "total_count",
        "returned_count",
        "next_cursor",
        "filters_applied",
        "by_kind",
        "items",
    ],
    "properties": {
        **_PAGE_PROPERTIES,
        "filters_applied": {
            "type": "object",
            "properties": {
                "kind": {"type": ["array", "null"], "items": {"type": "string"}},
                "limit": {"type": ["integer", "null"]},
                "cursor": {"type": ["string", "null"]},
            },
        },
        "by_kind": {"type": "object", "additionalProperties": {"type": "integer"}},
        "items": {"type": "array", "items": _FACT_ITEM},
    },
}

# `fuse_facts` (`sparkforge/adapters/_core.py`) devolve o mesmo envelope
# paginado, mais `summary`: o fact `fusion.summary` (ou `null` quando a fusao
# nao produziu nenhum, o que nunca acontece na pratica -- `fuse` sempre emite
# a sentinela -- mas o tipo fica honesto sobre a possibilidade).
_FUSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "total_count",
        "returned_count",
        "next_cursor",
        "filters_applied",
        "by_kind",
        "summary",
        "items",
    ],
    "properties": {
        **_PAGE_PROPERTIES,
        "filters_applied": {
            "type": "object",
            "properties": {
                "kind": {"type": ["array", "null"], "items": {"type": "string"}},
                "limit": {"type": ["integer", "null"]},
                "cursor": {"type": ["string", "null"]},
            },
        },
        "by_kind": {"type": "object", "additionalProperties": {"type": "integer"}},
        "summary": {"type": ["object", "null"]},
        "items": {"type": "array", "items": _FACT_ITEM},
    },
}

# Shape de `_core._collect_payload`: o manifesto (`ArtifactEntry.to_dict()`)
# mais `cache_hit`, que prova se a chamada tocou a rede AWS ou foi um no-op
# local (sha256 ja batia) -- ver docstring de `_core._collect_payload`.
_COLLECT_ARTIFACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "kind",
        "path",
        "sha256",
        "source",
        "collect_command",
        "collected_at",
        "cache_hit",
    ],
    "properties": {
        "kind": {"type": "string"},
        "path": {"type": "string"},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "source": {"type": "string"},
        "collect_command": {"type": "string"},
        "collected_at": {"type": "string"},
        "cache_hit": {
            "type": "boolean",
            "description": (
                "True quando `collected_at != now`: cache hit local, nenhuma rede "
                "nem credencial AWS tocada nesta chamada."
            ),
        },
    },
}

_VERIFY_ARTIFACT_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["kind", "path", "present", "hash_matches", "collect_command", "source"],
    "properties": {
        "kind": {"type": ["string", "null"]},
        "path": {"type": "string"},
        "present": {"type": "boolean"},
        "hash_matches": {"type": "boolean"},
        "collect_command": {"type": ["string", "null"]},
        "source": {"type": ["string", "null"]},
    },
}

_COLLECT_VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["total_count", "ok_count", "missing_count", "mismatched_count", "artifacts"],
    "properties": {
        "total_count": {"type": "integer"},
        "ok_count": {"type": "integer"},
        "missing_count": {"type": "integer"},
        "mismatched_count": {"type": "integer"},
        "artifacts": {"type": "array", "items": _VERIFY_ARTIFACT_ITEM},
    },
}

_JUDGE_SKIPPED_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["rule_id", "reason"],
    "properties": {
        "rule_id": {"type": "string"},
        "reason": {
            "type": "string",
            "enum": ["runtime_scope", "blocked_on", "requires_facts"],
            "description": (
                "runtime_scope: regra fora do runtime informado. blocked_on: "
                "capacidade ainda nao implementada (ver campo `blocked_on`). "
                "requires_facts: fact exigido nao foi extraido (ver campo `missing`)."
            ),
        },
        "scope": {"type": "object", "description": "Presente quando reason=runtime_scope."},
        "blocked_on": {"type": "string", "description": "Presente quando reason=blocked_on."},
        "missing": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Kinds de fact ausentes; presente quando reason=requires_facts.",
        },
    },
}

_JUDGE_SUCCESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "total_count",
        "returned_count",
        "next_cursor",
        "filters_applied",
        "by_severity",
        "items",
    ],
    "properties": {
        **_PAGE_PROPERTIES,
        "filters_applied": {
            "type": "object",
            "properties": {
                "severity": {"type": ["array", "null"], "items": {"type": "string"}},
                "limit": {"type": ["integer", "null"]},
                "cursor": {"type": ["string", "null"]},
            },
        },
        "by_severity": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
            "description": "Contagem sobre o conjunto completo apos filtro de severidade.",
        },
        "items": {"type": "array", "items": _FINDING_ITEM},
        "skipped": {
            "type": "array",
            "items": _JUDGE_SKIPPED_ITEM,
            "description": (
                "Regra fora de escopo de versao, bloqueada por capacidade ausente, ou "
                "sem fact requerido -- explicada aqui, nunca descartada em silencio. "
                "So aparece quando `show_skipped` e verdadeiro."
            ),
        },
    },
}

_ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Forma de erro de fronteira (`_core.AdapterError`), devolvida em vez de uma "
        "excecao -- ex.: `facts_path` ausente no disco. `error` traz o comando de "
        "recoleta pronto para copiar."
    ),
    "required": ["error", "exit_code"],
    "properties": {
        "error": {"type": "string"},
        "exit_code": {"type": "integer"},
    },
}

def _may_fail(success: dict[str, Any], why: str) -> dict[str, Any]:
    """Declara as DUAS formas que a tool pode devolver: sucesso ou erro de fronteira.

    `call_tool` converte `_core.AdapterError` em `{"error", "exit_code"}` em vez de
    propagar excecao. Um schema so-de-sucesso e uma promessa falsa: o cliente que
    validar uma resposta de "case nao existe" recebe falha de validacao em cima de
    um erro que a tool ja tratou corretamente. As duas formas nao compartilham
    nenhuma chave, entao `oneOf` casa exatamente um ramo.
    """
    return {"description": why, "oneOf": [success, _ERROR_SCHEMA]}


_JUDGE_SCHEMA: dict[str, Any] = {
    "description": (
        "Sucesso (paginado, com findings) OU erro de fronteira quando `facts_path` "
        "nao existe no disco -- ver `_JUDGE_SUCCESS_SCHEMA` e `_ERROR_SCHEMA`."
    ),
    "oneOf": [_JUDGE_SUCCESS_SCHEMA, _ERROR_SCHEMA],
}

_SEVERITY_BRANCH_ITEM: dict[str, Any] = {
    "type": "object",
    "properties": {
        "when": {"type": "string"},
        "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "P4"]},
    },
}

_RULE_SOURCE_ITEM: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "origin": {"type": "string"},
        "title": {"type": "string"},
        "note": {"type": "string"},
        "retrieved": {"type": "string", "description": "ISO 8601."},
    },
}

_RULE_ITEM: dict[str, Any] = {
    "type": "object",
    "required": [
        "id",
        "category",
        "title",
        "requires_facts",
        "when",
        "status",
        "runtime_scope",
        "sources",
        "catalog_version",
    ],
    "properties": {
        "id": {"type": "string", "pattern": "^SF-[A-Z]+-[0-9]{3}$"},
        "category": {"type": "string"},
        "title": {"type": "string"},
        "requires_facts": {"type": "array", "items": {"type": "string"}},
        "when": {"type": "object"},
        "status": {"type": "string", "enum": ["structural", "confirmed"]},
        "runtime_scope": {"type": "object"},
        "sources": {"type": "array", "items": _RULE_SOURCE_ITEM},
        "catalog_version": {"type": "integer"},
        "threshold": {"type": "object"},
        "severity_default": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "P4"]},
        "severity_by": {"type": "array", "items": _SEVERITY_BRANCH_ITEM},
        "explanation": {"type": "string"},
        "proposed_change": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "tradeoffs": {"type": "array", "items": {"type": "string"}},
        "validation": {"type": "array", "items": {"type": "string"}},
        "rollback": {"type": "array", "items": {"type": "string"}},
        "blocked_on": {
            "type": "string",
            "description": "Capacidade ainda nao implementada que bloqueia esta regra.",
        },
    },
}

_RULES_LOOKUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "total_count",
        "returned_count",
        "next_cursor",
        "filters_applied",
        "by_category",
        "rules",
    ],
    "properties": {
        **_PAGE_PROPERTIES,
        "filters_applied": {
            "type": "object",
            "properties": {
                "id": {"type": ["array", "null"], "items": {"type": "string"}},
                "category": {"type": ["string", "null"]},
                "limit": {"type": ["integer", "null"]},
                "cursor": {"type": ["string", "null"]},
            },
        },
        "by_category": {"type": "object", "additionalProperties": {"type": "integer"}},
        "rules": {"type": "array", "items": _RULE_ITEM},
    },
}

_VALIDATE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["valid", "errors"],
    "properties": {
        "valid": {"type": "boolean"},
        "errors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Vazio quando `valid` e verdadeiro.",
        },
    },
}

TOOLS: dict[str, dict[str, Any]] = {
    "sparkforge_case_open": {
        "description": (
            "Cria um case novo em .sparkforge/case.yaml, detectando o runtime "
            "Glue/Spark/Python/Iceberg a partir dos parametros informados. E o barramento "
            "de handoff entre sessoes (Devin, Claude Code): sem case, next-step e resume "
            "nao tem estado sobre o qual operar. `now` e obrigatorio e nunca lido do relogio "
            "pela ferramenta -- quem chama fornece o timestamp."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "case_id", "now"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio analisado."},
                "case_id": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(_CASE_SCHEMA, "Case carregado, ou erro se ausente."),
        "annotations": _WRITE_IDEMPOTENT,
    },
    "sparkforge_case_get": {
        "description": (
            "Le o estado atual do case (.sparkforge/case.yaml): fase, gates, runtime "
            "detectado, indices de facts e findings. Falha com um erro que nomeia "
            "`sparkforge case open` quando nenhum case existe ainda no repositorio."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
        "outputSchema": _may_fail(_CASE_SCHEMA, "Case carregado, ou erro se ausente."),
        "annotations": _READ_ONLY,
    },
    "sparkforge_case_update": {
        "description": (
            "Atualiza a fase, um gate booleano, ou registra o uso de uma skill no case "
            "atual. Cada mutacao e uma transicao de estado explicita e validada contra o "
            "dominio conhecido (PHASES, GATES) -- nunca um valor livre."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "phase": {"type": "string"},
                "gate": {"type": "string"},
                "gate_value": {"type": "boolean"},
                "skill": {"type": "string"},
                "now": {"type": "string"},
                "outcome": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(_CASE_SCHEMA, "Case carregado, ou erro se ausente."),
        "annotations": _WRITE_NOT_IDEMPOTENT,
    },
    "sparkforge_next_step": {
        "description": (
            "Decide o proximo passo (skill recomendada) a partir de routing.yaml -- o mesmo "
            "motor declarativo de sparkforge.rules.engine, mas sobre o estado do case e os "
            "achados atuais, nunca sobre o julgamento livre do agente. `blocked_by` e "
            "advisory: informa gates pendentes sem impedir a chamada."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Findings atuais, usados para casar condicoes de roteamento.",
                },
            },
        },
        "outputSchema": _may_fail(
            _NEXT_STEP_SCHEMA,
            "Proximo passo, ou erro se o case nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_resume": {
        "description": (
            "Monta o payload de rehidratacao de um case: onde parou, runtime, baseline, "
            "achados principais, hipoteses abertas, gates, artefatos ausentes e proximo "
            "passo. `coverage.unresolved` e um sinal de ponto cego, nao de ausencia de "
            "problema -- um no nao resolvido nunca deve ser lido como 'sem achados'."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "unresolved": {"type": "integer"},
                "in_flight": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _RESUME_SCHEMA,
            "Payload de retomada, ou erro se o case nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_runtime_detect": {
        "description": (
            "Deriva glue/spark/python/iceberg/athena a partir dos parametros informados, "
            "usando a matriz oficial de compatibilidade do Glue. Divergencia entre fontes "
            "nao e resolvida escolhendo uma: e reportada em `divergences`, porque aplicar "
            "limiar ou API da versao errada invalida qualquer recomendacao seguinte."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
            },
        },
        "outputSchema": _RUNTIME_CONTEXT,
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_pyspark": {
        "description": (
            "Extrai facts deterministicos de codigo PySpark via AST estatico -- nunca "
            "importa nem executa o codigo analisado. So observa (particionamento, joins, "
            "UDFs, cache, acoes no driver, etc.); nao atribui severidade nem limiar. "
            "Paginado: `total_count`/`by_kind` refletem o conjunto completo apos filtros, "
            "nao so a pagina devolvida em `items`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Arquivo ou diretorio a analisar."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_PYSPARK_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_catalog_schema": {
        "description": (
            "Extrai facts de um dump JSON ja coletado do Glue Data Catalog "
            "(`GetTables`/`GetTable`): schema, colunas, chaves de particao, contagem de "
            "particoes e table properties. NAO chama a API do Glue -- so le o JSON ja "
            "salvo em disco. Correlacionar isso com texto SQL (`sql.projection`/"
            "`sql.predicate`) e trabalho de `sparkforge_fuse`, nao desta ferramenta."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo ou diretorio com dumps do catalogo.",
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_event_log": {
        "description": (
            "Extrai facts de um Spark event log (.jsonl) ja coletado: duracao/skew de "
            "task por stage, spill, GC, contagem de tasks, cores do cluster, executor "
            "perdido. NAO baixa o log de S3 -- so le o arquivo ja presente em disco "
            "(`sparkforge_collect_event_log` ou coleta manual fazem isso). Um unico "
            "arquivo por chamada, nunca um diretorio."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Arquivo de event log (.jsonl)."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_terraform": {
        "description": (
            "Extrai facts de blocos `resource \"aws_glue_job\"` em HCL Terraform: "
            "glue_version, worker_type, number_of_workers, default_arguments, "
            "observabilidade do Spark UI. Parser de linha limitado (nao uma gramatica HCL "
            "geral) -- construcoes nao suportadas (interpolacao, heredoc, dynamic, "
            "for_each) viram `tf.unresolved` com reason especifico, nunca um valor "
            "adivinhado. Ver `sparkforge.facts.terraform` para o vocabulario completo."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Arquivo ou diretorio .tf."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_iceberg": {
        "description": (
            "Extrai facts de um dump JSON das cinco metadata tables Iceberg (`.files`, "
            "`.delete_files`, `.snapshots`, `.manifests`, `.partitions`): small files, "
            "delete files, cadencia de snapshot, tamanho de manifesto, skew de particao. "
            "NAO consulta Athena -- so le o JSON ja salvo em disco "
            "(`sparkforge_collect_iceberg_metadata` ou coleta manual fazem isso)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo ou diretorio com dumps das metadata tables.",
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_sql": {
        "description": (
            "Extrai facts de texto SQL por regex/varredura de token (nunca uma gramatica "
            "SQL completa): projecao (`SELECT *` vs. colunas explicitas), predicados de "
            "WHERE, uso de LIMIT. Dois modos, mutuamente exclusivos: `path` le um arquivo "
            ".sql; `from_pyspark` varre um arquivo .py via AST e extrai o literal de cada "
            "chamada `spark.sql(\"...\")` (argumento nao-literal vira `sql.unresolved` com "
            "reason `non_literal_sql`, nunca uma referencia seguida). NAO sabe se uma "
            "coluna e de particao nem seu tipo declarado -- isso exige `sparkforge_fuse` "
            "correlacionando com `sparkforge_analyze_catalog_schema`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Arquivo .sql a analisar."},
                "from_pyspark": {
                    "type": "string",
                    "description": (
                        "Arquivo .py: extrai texto de chamadas spark.sql(\"...\") em vez "
                        "de ler `path`. Mutuamente exclusivo com `path`."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se nem path nem from_pyspark existem/foram informados.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_athena_workgroup": {
        "description": (
            "Extrai facts de um dump JSON de workgroups do Athena (`get_work_group`): "
            "engine version efetiva, state, bytes_scanned_cutoff. NAO chama a API do "
            "Athena -- so le o JSON ja salvo em disco (`sparkforge_collect_athena_workgroup` "
            "ou coleta manual fazem isso). Uma `effective_engine_version` sem inteiro "
            "reconhecivel (`\"AUTO\"`, string vazia) NUNCA vira `athena.workgroup` com "
            "valor adivinhado: vira `athena.unresolved` com "
            "`reason: unparseable_engine_version`, unico fact que desbloqueia SF-ATH-004."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo ou diretorio com dumps de workgroups.",
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_call_graph": {
        "description": (
            "Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts JA "
            "extraidos (tipicamente `sparkforge_analyze_pyspark` gravado em disco via "
            "`--out`) -- funcao pura sobre Facts, nunca reparseia codigo-fonte. Revela "
            "trabalho Spark (`count()`, `write`, `collect`) escondido dentro de um helper "
            "chamado varios niveis abaixo do entrypoint, invisivel numa revisao que so olha "
            "o entrypoint. Sem `unresolved` proprio: so deriva do que ja foi resolvido."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["facts_path"],
            "properties": {
                "facts_path": {
                    "type": "string",
                    "description": "Arquivo de facts gerado por `sparkforge_analyze_pyspark`.",
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_CALL_GRAPH_SCHEMA,
            "Grafo de chamadas derivado, ou erro se facts_path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_fuse": {
        "description": (
            "Correlaciona facts de fontes diferentes (texto SQL de "
            "`sparkforge_analyze_sql` com schema de `sparkforge_analyze_catalog_schema`) "
            "pelo nome da tabela, e produz facts `.enriched` (`sql.projection.enriched`, "
            "`sql.predicate.enriched`) que carregam attrs das duas fontes NO MESMO fact -- "
            "o que desbloqueia SF-ATH-001, SF-ATH-002 e SF-ATH-005. `facts_paths` e "
            "repetivel de proposito: a fusao so tem o que correlacionar quando ve as duas "
            "fontes na MESMA chamada. A saida (facts originais + `.enriched` + "
            "`fusion.summary`) alimenta `sparkforge_judge` direto, sem outro passo no meio."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["facts_paths"],
            "properties": {
                "facts_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": (
                        "Arquivos de facts (JSON) gerados por `sparkforge_analyze_*`. "
                        "Repetivel: informe todas as fontes a correlacionar na mesma chamada."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _FUSE_SCHEMA,
            "Facts fundidos, ou erro se facts_paths esta vazio ou algum arquivo nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_judge": {
        "description": (
            "Aplica o catalogo de regras versionado sobre facts ja extraidos, filtrado "
            "pelo runtime informado. Aceita `facts` inline ou `facts_path` (arquivo gerado "
            "por sparkforge_analyze_pyspark). `facts_path` aceita tambem uma LISTA de "
            "caminhos, unidos e deduplicados antes do julgamento: regra que correlaciona "
            "extratores diferentes (SF-GLUE-004 cruza `tf.attribute` com `pyspark.write`) "
            "so dispara com as duas fontes na mesma chamada. Um `facts_path` ausente devolve "
            "um dict de erro com o comando de recoleta, nunca uma excecao. Regra fora de escopo de "
            "versao ou sem fact requerido aparece em `skipped` com o motivo, quando "
            "`show_skipped` e verdadeiro -- nunca descartada em silencio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": {"type": "object"}},
                "facts_path": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": (
                        "Um caminho, ou varios: os facts sao unidos e deduplicados antes "
                        "de julgar."
                    ),
                },
                "glue": {"type": "string"},
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
                "severity": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "show_skipped": {"type": "boolean"},
            },
        },
        "outputSchema": _JUDGE_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_rules_lookup": {
        "description": (
            "Consulta o catalogo de regras determinístico por id ou categoria, devolvendo "
            "threshold, runtime_scope e fontes completas. Este e o nucleo da independencia "
            "de modelo: o LLM nao precisa saber de cor o limiar ou a severidade de uma "
            "regra -- ele consulta o catalogo versionado e recebe sempre a mesma resposta, "
            "qualquer que seja o modelo por tras da chamada."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "array", "items": {"type": "string"}},
                "category": {"type": "string"},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _RULES_LOOKUP_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_validate_output": {
        "description": (
            "Valida um finding proposto contra o JSON Schema e contra a regra de ganho sem "
            "benchmark_ref antes de aceita-lo. Este e o outro pilar da independencia de "
            "modelo: um LLM diferente pode redigir o finding de outra forma, mas so passa "
            "se for logicamente consistente com o catalogo -- a validacao decide o que e "
            "aceitavel, nao o modelo que escreveu."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["finding"],
            "properties": {"finding": {"type": "object"}},
        },
        "outputSchema": _VALIDATE_OUTPUT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_collect_event_log": {
        "description": (
            "Baixa o Spark event log de um job run via `s3.list_objects_v2`/`get_object` "
            "e registra no manifesto (`.sparkforge/artifacts/manifest.json`). Le, nunca "
            "grava nada do lado AWS. Offline-first: uma segunda chamada com o mesmo "
            "artefato ja presente e integro localmente (`cache_hit: true`) nao toca rede "
            "nem credenciais. boto3 ausente devolve um erro com o comando `pip install` E "
            "o caminho exato para registrar uma coleta manual -- nunca deixa a ferramenta "
            "inutilizavel. NAO interpreta o log; use `sparkforge_analyze_event_log` depois."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "job_run_id", "bucket", "prefix", "now"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio analisado."},
                "job_run_id": {"type": "string"},
                "bucket": {"type": "string"},
                "prefix": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_glue_job": {
        "description": (
            "Baixa a definicao de um job via `glue.get_job` e registra no manifesto. Le o "
            "job tal como esta *implantado*, nao o que o `.tf` fonte declara -- os dois "
            "podem divergir. Mesma politica offline-first e mensagem de boto3 ausente que "
            "`sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "job_name", "now"],
            "properties": {
                "repo": {"type": "string"},
                "job_name": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_cloudwatch": {
        "description": (
            "Baixa as metricas de observabilidade Glue via `cloudwatch.get_metric_data` "
            "(skewness, uso de heap, bytes/records lidos e escritos, sucesso/erro) e "
            "registra no manifesto. Requer `--enable-observability-metrics=true` no job; "
            "sem isso o CloudWatch simplesmente nao tem as series, e a chamada grava o que "
            "veio de volta sem adivinhar. Mesma politica offline-first de "
            "`sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "job_name", "job_run_id", "start", "end", "now"],
            "properties": {
                "repo": {"type": "string"},
                "job_name": {"type": "string"},
                "job_run_id": {"type": "string"},
                "start": {"type": "string", "description": "Inicio ISO 8601."},
                "end": {"type": "string", "description": "Fim ISO 8601."},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_iceberg_metadata": {
        "description": (
            "Consulta as cinco metadata tables Iceberg de uma tabela via Athena "
            "(`SELECT * FROM \"db\".\"tabela$secao\"`) e registra no manifesto. "
            "AccessDeniedException numa metadata table quase sempre e Lake Formation "
            "(filtro de linha/celula), nao IAM -- o erro aponta para o lugar certo. Mesma "
            "politica offline-first de `sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "table", "workgroup", "output_location", "now"],
            "properties": {
                "repo": {"type": "string"},
                "table": {"type": "string", "description": "db.tabela"},
                "workgroup": {"type": "string"},
                "output_location": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_athena_workgroup": {
        "description": (
            "Baixa a configuracao de um workgroup via `athena.get_work_group` (engine "
            "version efetiva/selecionada, state, bytes_scanned_cutoff, output_location) e "
            "registra no manifesto, ja no shape que `sparkforge_analyze_athena_workgroup` "
            "le. Mesma politica offline-first de `sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "workgroup", "now"],
            "properties": {
                "repo": {"type": "string"},
                "workgroup": {"type": "string"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_verify": {
        "description": (
            "Verifica presenca e integridade (sha256 recalculado) de todos os artefatos "
            "registrados no manifesto local. So le disco -- nunca toca a rede, ao contrario "
            "dos outros `collect_*` -- entao serve para checar o que falta ou foi corrompido "
            "sem gastar uma chamada AWS. Um artefato ausente aparece com seu "
            "`collect_command` pronto para copiar."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string"}},
        },
        "outputSchema": _COLLECT_VERIFY_SCHEMA,
        "annotations": _READ_ONLY,
    },
}


def _h_case_open(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_open(
        args["repo"],
        args["case_id"],
        args["now"],
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
    )


def _h_case_get(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_get(args["repo"])


def _h_case_update(args: dict[str, Any]) -> dict[str, Any]:
    return _core.case_update(
        args["repo"],
        phase=args.get("phase"),
        gate=args.get("gate"),
        gate_value=args.get("gate_value", True),
        skill=args.get("skill"),
        now=args.get("now"),
        outcome=args.get("outcome"),
    )


def _h_next_step(args: dict[str, Any]) -> dict[str, Any]:
    return _core.next_step(args["repo"], args.get("findings") or [])


def _h_resume(args: dict[str, Any]) -> dict[str, Any]:
    return _core.resume_case(
        args["repo"],
        args.get("findings") or [],
        unresolved=args.get("unresolved", 0),
        in_flight=args.get("in_flight", ""),
    )


def _h_runtime_detect(args: dict[str, Any]) -> dict[str, Any]:
    return _core.runtime_detect(
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
    )


def _h_analyze_pyspark(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_pyspark(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_judge(args: dict[str, Any]) -> dict[str, Any]:
    return _core.judge_findings(
        facts=args.get("facts"),
        facts_path=args.get("facts_path"),
        glue=args.get("glue"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
        severity=args.get("severity"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        show_skipped=args.get("show_skipped", False),
    )


def _h_rules_lookup(args: dict[str, Any]) -> dict[str, Any]:
    return _core.rules_lookup(
        id=args.get("id"),
        category=args.get("category"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_validate_output(args: dict[str, Any]) -> dict[str, Any]:
    return _core.validate_output(args["finding"])


def _h_analyze_catalog_schema(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_catalog_schema(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_event_log(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_event_log(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_terraform(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_terraform(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_iceberg(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_iceberg(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_sql(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_sql(
        path=args.get("path"),
        from_pyspark=args.get("from_pyspark"),
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_athena_workgroup(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_athena_workgroup(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_call_graph(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_call_graph(
        args["facts_path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_fuse(args: dict[str, Any]) -> dict[str, Any]:
    return _core.fuse_facts(
        args.get("facts_paths"),
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_collect_event_log(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_event_log(
        args["repo"],
        job_run_id=args["job_run_id"],
        bucket=args["bucket"],
        prefix=args["prefix"],
        now=args["now"],
    )


def _h_collect_glue_job(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_glue_job(args["repo"], job_name=args["job_name"], now=args["now"])


def _h_collect_cloudwatch(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_cloudwatch(
        args["repo"],
        job_name=args["job_name"],
        job_run_id=args["job_run_id"],
        start=args["start"],
        end=args["end"],
        now=args["now"],
    )


def _h_collect_iceberg_metadata(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_iceberg_metadata(
        args["repo"],
        table=args["table"],
        workgroup=args["workgroup"],
        output_location=args["output_location"],
        now=args["now"],
    )


def _h_collect_athena_workgroup(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_athena_workgroup(
        args["repo"], workgroup=args["workgroup"], now=args["now"]
    )


def _h_collect_verify(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_verify(args["repo"])


_HANDLERS = {
    "sparkforge_case_open": _h_case_open,
    "sparkforge_case_get": _h_case_get,
    "sparkforge_case_update": _h_case_update,
    "sparkforge_next_step": _h_next_step,
    "sparkforge_resume": _h_resume,
    "sparkforge_runtime_detect": _h_runtime_detect,
    "sparkforge_analyze_pyspark": _h_analyze_pyspark,
    "sparkforge_analyze_catalog_schema": _h_analyze_catalog_schema,
    "sparkforge_analyze_event_log": _h_analyze_event_log,
    "sparkforge_analyze_terraform": _h_analyze_terraform,
    "sparkforge_analyze_iceberg": _h_analyze_iceberg,
    "sparkforge_analyze_sql": _h_analyze_sql,
    "sparkforge_analyze_athena_workgroup": _h_analyze_athena_workgroup,
    "sparkforge_analyze_call_graph": _h_analyze_call_graph,
    "sparkforge_fuse": _h_fuse,
    "sparkforge_judge": _h_judge,
    "sparkforge_rules_lookup": _h_rules_lookup,
    "sparkforge_validate_output": _h_validate_output,
    "sparkforge_collect_event_log": _h_collect_event_log,
    "sparkforge_collect_glue_job": _h_collect_glue_job,
    "sparkforge_collect_cloudwatch": _h_collect_cloudwatch,
    "sparkforge_collect_iceberg_metadata": _h_collect_iceberg_metadata,
    "sparkforge_collect_athena_workgroup": _h_collect_athena_workgroup,
    "sparkforge_collect_verify": _h_collect_verify,
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Despacha para o handler de `name`. Nome desconhecido: KeyError com as validas.

    Erros de fronteira (`_core.AdapterError`) nunca propagam como excecao: viram
    `{"error": ..., "exit_code": ...}`, para que um cliente MCP sempre receba um
    resultado estruturado, mesmo em falha.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        valid = ", ".join(sorted(TOOLS))
        raise KeyError(f"ferramenta desconhecida: {name!r}. Validas: {valid}")

    try:
        return handler(arguments or {})
    except _core.AdapterError as exc:
        return {"error": exc.message, "exit_code": exc.exit_code}
