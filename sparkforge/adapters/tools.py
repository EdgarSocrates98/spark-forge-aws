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
        "outputSchema": _may_fail(_NEXT_STEP_SCHEMA, "Proximo passo, ou erro se o case nao existe."),
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
        "outputSchema": _may_fail(_RESUME_SCHEMA, "Payload de retomada, ou erro se o case nao existe."),
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
        "outputSchema": _may_fail(_ANALYZE_PYSPARK_SCHEMA, "Facts extraidos, ou erro se o path nao existe."),
        "annotations": _READ_ONLY,
    },
    "sparkforge_judge": {
        "description": (
            "Aplica o catalogo de regras versionado sobre facts ja extraidos, filtrado "
            "pelo runtime informado. Aceita `facts` inline ou `facts_path` (arquivo gerado "
            "por sparkforge_analyze_pyspark). Um `facts_path` ausente devolve um dict de "
            "erro com o comando de recoleta, nunca uma excecao. Regra fora de escopo de "
            "versao ou sem fact requerido aparece em `skipped` com o motivo, quando "
            "`show_skipped` e verdadeiro -- nunca descartada em silencio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": {"type": "object"}},
                "facts_path": {"type": "string"},
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


_HANDLERS = {
    "sparkforge_case_open": _h_case_open,
    "sparkforge_case_get": _h_case_get,
    "sparkforge_case_update": _h_case_update,
    "sparkforge_next_step": _h_next_step,
    "sparkforge_resume": _h_resume,
    "sparkforge_runtime_detect": _h_runtime_detect,
    "sparkforge_analyze_pyspark": _h_analyze_pyspark,
    "sparkforge_judge": _h_judge,
    "sparkforge_rules_lookup": _h_rules_lookup,
    "sparkforge_validate_output": _h_validate_output,
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
