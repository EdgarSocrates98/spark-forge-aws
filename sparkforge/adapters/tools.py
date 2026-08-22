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

Nenhuma ferramenta e destrutiva. Os coletores AWS (`collect_*`, exceto
`collect_verify`) sao os unicos open-world -- leem de fora do sandbox local e
nunca escrevem do lado AWS. Escrevem em disco: `case_open` e `case_update`
(`.sparkforge/case.yaml`), `report_sign` (o bloco de assinatura, no lugar) e
`funcval_plan` (o plano, que `funcval_compare` rele como artefato); todas as
outras sao read-only. A lista literal correspondente vive em
`tests/test_adapters_tools.py::test_only_case_and_report_writers_are_not_read_only`.
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
            "enum": [
                "source_location",
                "stage",
                "task",
                "tf_resource",
                "table",
                "job_run",
                "plan_node",
            ],
        },
        "file": {"type": "string"},
        "line": {"type": "integer"},
        "col": {"type": "integer"},
        "end_line": {"type": "integer"},
        "symbol": {"type": "string"},
        "snippet": {"type": "string"},
        # `plan_node` (sparkforge/facts/spark_plan.py): um plano fisico nao tem
        # arquivo:linha de codigo-fonte, entao a entidade ancorada e o NO do
        # plano -- mesmo raciocinio de `stage`/`stage_id` no event log.
        "node_id": {"type": "integer"},
        "operator": {"type": "string"},
        "relation": {"type": "string"},
        "stage_id": {"type": "integer"},
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
        # `[A-Z][A-Z0-9]*` e nao `[A-Z]+`: a area pode ter digito no NOME
        # (`SF-SPARK4` fala do Apache Spark 4), e o digito ali nao e numeracao.
        # Tem que casar com `findings/schemas/finding.schema.json`.
        "rule_id": {"type": "string", "pattern": "^SF-[A-Z][A-Z0-9]*-[0-9]{3}$"},
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
    "required": [
        "glue",
        "emr",
        "spark",
        "python",
        "iceberg",
        "athena",
        "detected_from",
        "divergences",
    ],
    "properties": {
        "glue": {"type": "string"},
        # `emr` entrou em `RuntimeContext.to_dict()` na Task 1 da Fase 5b e nao
        # foi declarado aqui. Nao quebrava nada -- JSON Schema permite chave
        # extra por default --, mas o cliente MCP que le o schema nao ficava
        # sabendo que a plataforma existe no payload, e o campo so passa a ser
        # acionavel quando alguem sabe le-lo.
        "emr": {
            "type": "string",
            "description": (
                "Release label do EMR on EC2 ('emr-7.5.0'), vazio fora do EMR. "
                "Deriva spark/iceberg/python por EMR_MATRIX; ver "
                "knowledge/emr/runtime-matrix.md."
            ),
        },
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

# O espelho de ENTRADA do campo `emr` do contexto acima. As tools espelham as
# flags da CLI: deixar `--emr` so na CLI recriaria, um nivel acima, a mesma
# assimetria que a flag veio fechar -- um agente que fala MCP nao teria como
# declarar uma release que o operador conhece.
_EMR_INPUT: dict[str, Any] = {
    "type": "string",
    "description": (
        "Release do EMR on EC2, nas duas grafias ('emr-7.5.0' ou '7.5.0'). "
        "DECLARACAO, nao observacao: perde para o event log e para um dump de "
        "describe-cluster, e discordar de um deles vira divergencia reportada "
        "em `runtime.divergences`, nunca valor substituido em silencio."
    ),
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
        "recommended_agent",
        "recommended_agent_reason",
    ],
    "properties": {
        "phase": {
            "type": ["string", "null"],
            "description": (
                "Fase do case; null quando `next_step` roda sobre um case ausente "
                "(ex.: `sparkforge_playbook` sem case aberto -- ver `_PLAYBOOK_SCHEMA`)."
            ),
        },
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
        "recommended_agent": {
            "type": ["string", "null"],
            "description": (
                "Coordenador (agents/*.md) resolvido pelas rotas AGENT-* de "
                "routing.yaml a partir da fase e da area de achado dominante. "
                "`null` quando nenhuma rota de agente casa com o estado atual."
            ),
        },
        "recommended_agent_reason": {
            "type": ["string", "null"],
            "description": (
                "Motivo da rota AGENT-* escolhida, no mesmo formato de `reason` "
                "(prefixo `AGENT-NNN:`). `null` junto com `recommended_agent: null`."
            ),
        },
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

_GATE_OVERRIDE_LIST: dict[str, Any] = {
    "type": "array",
    "description": (
        "Historico de gates cobertos por override, em ordem de registro. E "
        "lista e nao mapa de proposito: dois overrides do mesmo gate em "
        "momentos diferentes sao dois fatos, e um mapa apagaria o primeiro "
        "motivo. Ausente em case aberto antes da Fase 4b."
    ),
    "items": {
        "type": "object",
        "required": ["gate", "reason", "at"],
        "properties": {
            "gate": {"type": "string", "enum": list(_GATE_NAMES)},
            "reason": {
                "type": "string",
                "description": "Nunca vazio: override sem motivo e recusado.",
            },
            "at": {
                "type": "string",
                "description": "Timestamp injetado por quem chamou; pode ser vazio.",
            },
        },
    },
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
        # Fora de `required` de proposito: case gravado antes da Fase 4b nao tem
        # estas duas chaves, e `case_get` devolve o que esta no disco. Exigi-las
        # faria a leitura de um case antigo falhar validacao por ausencia de um
        # campo cuja ausencia significa exatamente "modo advisory, como sempre".
        "strict_gates": {
            "type": "boolean",
            "description": (
                "Rigor de gate escolhido na abertura do case. Ligado, gate com "
                "produtor declarado bloqueia a transicao de fase; o booleano de "
                "`gates` nao destrava, so o fact produtor ou um override "
                "registrado. Ausente em case aberto antes da Fase 4b, e ausente "
                "significa desligado."
            ),
        },
        "gate_overrides": _GATE_OVERRIDE_LIST,
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
        "strict_gates",
        "gate_overrides",
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
        # Sempre presentes na retomada, mesmo em case antigo: `resume` normaliza
        # a ausencia para `false`/`[]`. Quem retoma noutra maquina precisa saber
        # que o case e estrito e que alguem passou por cima, sem abrir o YAML.
        "strict_gates": {"type": "boolean"},
        "gate_overrides": _GATE_OVERRIDE_LIST,
        "missing_artifacts": {"type": "array", "items": _ARTIFACT_ITEM},
        "next_step": _NEXT_STEP_SCHEMA,
        "in_flight": {"type": "string"},
        "coverage": _COVERAGE_SCHEMA,
        "skills_used": {"type": "array", "items": _SKILL_USE_ITEM},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}

_PLAYBOOK_STEP_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["order", "executor", "function", "does", "does_not"],
    "properties": {
        "order": {"type": "integer"},
        "executor": {"type": "string"},
        "function": {"type": "string"},
        "does": {"type": "string"},
        "does_not": {
            "type": "string",
            "description": "Vem da secao `## Não faz` do executor -- nunca reescrito.",
        },
    },
}

_PLAYBOOK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Decomposicao sequencial de um coordenador -- os mesmos passos que ele "
        "despacha como subagentes em Claude Code. E o piso das cinco plataformas: "
        "unico caminho em Codex e Copilot CI; o caminho nas tres quando o despacho "
        "esta desligado; e, no Devin, o caminho tambem quando ele esta ligado, "
        "porque um coordenador despachado como subagente nao gera subagente "
        "proprio por default e este repositorio nao declara `max-nesting`."
    ),
    "required": [
        "coordinator",
        "description",
        "rule_areas",
        "skills",
        "phase",
        "steps",
        "next_step",
        "note",
    ],
    "properties": {
        "coordinator": {"type": "string"},
        "description": {"type": "string"},
        "rule_areas": {"type": "array", "items": {"type": "string"}},
        "skills": {"type": "array", "items": {"type": "string"}},
        "phase": {
            "type": ["string", "null"],
            "description": "Fase do case quando um case existe; null se nenhum foi aberto.",
        },
        "steps": {"type": "array", "items": _PLAYBOOK_STEP_ITEM},
        "next_step": _NEXT_STEP_SCHEMA,
        "note": {"type": "string"},
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

# `benchmark_runs` tambem devolve o envelope com ponto cego, e por isso reusa o
# mesmo schema: `bench.unresolved` e ponto cego de verdade -- lado sem
# `spark.log_analyzed`, medida ausente ou parcial num lado, simbolo casado que
# perdeu a medida. Diferente de `analyze_call_graph`, que nao tem nenhum.
_BENCHMARK_SCHEMA = _ANALYZE_PYSPARK_SCHEMA

# Os dois verbos de `funcval` devolvem o mesmo envelope com ponto cego, pelo
# mesmo motivo: `funcval.unresolved` e ponto cego de verdade nos DOIS lados --
# alvo sem catalogo casado e tipo nao classificado no `plan`; check que veio de
# um lado so, check que rodou e nao deu, e os tres bloqueios de comparacao
# inteira no `compare`. Silencio ali seria indistinguivel de "nada divergiu".
_FUNCVAL_SCHEMA = _ANALYZE_PYSPARK_SCHEMA

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
        "runtime",
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
        "runtime": {
            **_RUNTIME_CONTEXT,
            "description": (
                "O runtime efetivamente usado para filtrar por versao -- derivado dos "
                "facts (tf.attribute glue_version, spark.runtime_version) e das flags. "
                "Explica por que uma regra versionada avaliou ou entrou em `skipped`, e "
                "carrega `divergences` quando flag e fact discordam."
            ),
        },
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
        # Mesma abertura de `rule_id` acima, pela mesma razao (`SF-SPARK4`).
        "id": {"type": "string", "pattern": "^SF-[A-Z][A-Z0-9]*-[0-9]{3}$"},
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
        "knowledge_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["ref", "path"],
                "properties": {
                    "ref": {"type": "string"},
                    "path": {"type": ["string", "null"]},
                },
            },
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

_REPORT_SIGN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "report",
        "findings",
        "signature",
        "fact_ids",
        "rule_ids",
        "catalog_version",
        "schema_version",
        "proves",
    ],
    "properties": {
        "report": {"type": "string"},
        "findings": {"type": "string"},
        "signature": {"type": "string", "pattern": "^sig_[0-9a-f]{64}$"},
        "fact_ids": {"type": "array", "items": {"type": "string"}},
        "rule_ids": {"type": "array", "items": {"type": "string"}},
        "catalog_version": {"type": "integer"},
        "schema_version": {"type": "integer"},
        "proves": {
            "type": "string",
            "description": (
                "O limite da assinatura, no proprio payload e nao so na documentacao: "
                "ela prova correspondencia, nunca autoria."
            ),
        },
    },
}

_REPORT_CHECK_ITEM: dict[str, Any] = {
    "type": "object",
    "required": ["ok", "detail"],
    "properties": {"ok": {"type": "boolean"}, "detail": {"type": "string"}},
}

_REPORT_VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "report",
        "findings",
        "valid",
        "status",
        "signature",
        "expected_signature",
        "diverged",
        "checks",
        "reason",
    ],
    "properties": {
        "report": {"type": "string"},
        "findings": {"type": "string"},
        "valid": {"type": "boolean"},
        "status": {
            "type": "string",
            "enum": [
                "signed",
                "diverged",
                "version_mismatch",
                "missing_block",
                "malformed_block",
            ],
        },
        "signature": {"type": ["string", "null"]},
        "expected_signature": {"type": ["string", "null"]},
        "diverged": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["version", "evidence", "catalog", "body"],
            },
            "description": (
                "Quais das QUATRO partes nao bateram. Vazio com `valid` falso "
                "significa que nao houve o que comparar -- bloco ausente ou "
                "malformado. Com `version` na lista, `body` fica de fora mesmo com "
                "`checks.body.ok` falso: a regra de normalizacao mudou entre a "
                "assinatura e esta build, e atribuir a diferenca ao corpo seria "
                "chamar de adulteracao o que e mudanca de regra."
            ),
        },
        "checks": {
            "type": "object",
            "required": ["version", "evidence", "catalog", "body"],
            "properties": {
                "version": _REPORT_CHECK_ITEM,
                "evidence": _REPORT_CHECK_ITEM,
                "catalog": _REPORT_CHECK_ITEM,
                "body": _REPORT_CHECK_ITEM,
            },
        },
        "reason": {"type": "string"},
    },
}

TOOLS: dict[str, dict[str, Any]] = {
    "sparkforge_case_open": {
        "description": (
            "Cria um case novo em .sparkforge/case.yaml, detectando o runtime "
            "Glue/EMR/Spark/Python/Iceberg a partir dos parametros informados. E o barramento "
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
                "emr": _EMR_INPUT,
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
                "facts_path": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": (
                        "Facts ja extraidos: o runtime do case sai do que os "
                        "extratores observaram, nao so das flags."
                    ),
                },
                "strict_gates": {
                    "type": "boolean",
                    "description": (
                        "Grava no case que gate com produtor declarado bloqueia "
                        "a transicao de fase. A escolha e do case, nao da "
                        "chamada: vale pela investigacao inteira, e quem retoma "
                        "noutra sessao herda o rigor de quem abriu. Omitido, o "
                        "comportamento e o de sempre (gate advisory)."
                    ),
                },
                "reopen": {
                    "type": "boolean",
                    "description": (
                        "Recomeca do zero por cima de um case que ja existe. "
                        "Omitido, abrir sobre um case existente e RECUSADO: "
                        "sobrescrever apagaria fase, rigor e overrides "
                        "gravados. O `strict_gates` do case atual e herdado -- "
                        "`strict_gates` sobe o rigor, e nada o baixa por "
                        "omissao."
                    ),
                },
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
            "dominio conhecido (PHASES, GATES) -- nunca um valor livre. Num case aberto "
            "com `strict_gates`, `gate_value` NAO destrava a transicao de fase: destrava "
            "o fact produtor (informe `facts_path`) ou um `override_gate` com `reason`."
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
                "override_gate": {
                    "type": "string",
                    "enum": list(_GATE_NAMES),
                    "description": (
                        "Passa por cima deste gate num case estrito, quando o "
                        "dado genuinamente nao existe (job descontinuado, "
                        "ambiente que sumiu). Exige `reason`."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Motivo do `override_gate`. Sem ele o override e "
                        "recusado -- override anonimo nao se distingue de gate "
                        "esquecido."
                    ),
                },
                "facts_path": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": (
                        "Facts que comprovam os gates da fase pedida. Num case "
                        "estrito, e daqui que sai a evidencia que destrava "
                        "`phase`."
                    ),
                },
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
    "sparkforge_playbook": {
        "description": (
            "Decomposicao de um coordenador (agents/*.md) em passos sequenciais -- o "
            "PISO de orquestracao das cinco plataformas. Tres despacham subagente "
            "(Claude Code, Devin CLI e o Devin Local agent do Devin Desktop, sob o "
            "toggle Subagents (Preview)); esta tool e o unico caminho em Codex e "
            "Copilot CI, onde nenhuma pesquisa mediu despacho, e continua sendo o "
            "caminho nas tres quando o despacho esta desligado -- por escolha do "
            "usuario (subagents_enabled) ou do admin da organizacao (Default subagent "
            "model: None). No Devin ela e o caminho tambem com o despacho LIGADO: um "
            "coordenador despachado como subagente nao gera subagente proprio por "
            "default, e este repositorio nao declara max-nesting em perfil nenhum. "
            "Le os arquivos de agents/ e agents/executors/ em vez de "
            "repetir a lista: uma copia divergiria do coordenador na primeira mudanca. "
            "`does_not` de cada passo vem da secao `## Não faz` do executor, nunca "
            "reescrito aqui. Case ausente nao e erro -- os passos saem com `phase: null`. "
            "Traz tambem o `next_step` do case (mesmo calculo de sparkforge_next_step), "
            "incluindo `recommended_agent` -- ver secao 4.5 da spec de Fase 4."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["coordinator"],
            "properties": {
                "coordinator": {
                    "type": "string",
                    "description": (
                        "Nome do arquivo em agents/ (sem .md), ex.: glue-infra-reviewer."
                    ),
                },
                "repo": {"type": "string", "description": "Raiz do repositorio analisado."},
                "findings": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Findings atuais, usados para resolver o `next_step` embutido "
                        "(so `rule_id` importa)."
                    ),
                },
            },
        },
        "outputSchema": _may_fail(
            _PLAYBOOK_SCHEMA,
            "Passos do coordenador, ou erro se o coordenador nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_runtime_detect": {
        "description": (
            "Deriva glue/emr/spark/python/iceberg/athena dos facts ja extraidos e dos "
            "parametros informados, usando as matrizes oficiais de compatibilidade do "
            "Glue e do EMR. "
            "Com `facts_path`, a versao OBSERVADA pelos extratores (`tf.attribute` "
            "glue_version, `spark.runtime_version`, `emr.cluster`) alimenta a deteccao -- ninguem "
            "precisa saber a versao de cor. Divergencia entre fontes nao e resolvida "
            "escolhendo uma: e reportada em `divergences`, porque aplicar limiar ou API "
            "da versao errada invalida qualquer recomendacao seguinte."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "glue": {"type": "string"},
                "emr": _EMR_INPUT,
                "spark": {"type": "string"},
                "python": {"type": "string"},
                "iceberg": {"type": "string"},
                "athena": {"type": "string"},
                "facts_path": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "description": (
                        "Um caminho, ou varios: os facts sao unidos e deduplicados "
                        "antes de derivar as fontes de versao."
                    ),
                },
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
    "sparkforge_analyze_plan": {
        "description": (
            "Extrai facts do TEXTO de um plano fisico ja salvo em disco: a saida de "
            "`df.explain(\"formatted\")`, `df.explain()`, `df.explain(True)` ou "
            "`EXPLAIN [FORMATTED]`. Devolve `plan.file_scan` (relacao, formato, "
            "PartitionFilters, PushedFilters, contagem de coluna de ReadSchema contra "
            "colunas realmente referenciadas acima no plano), `plan.join`, "
            "`plan.exchange`, `plan.python_udf`, `plan.operator`, `plan.aqe`. E o unico "
            "caminho para SF-PQ-002 (pruning de particao ausente) e SF-PQ-004 (pruning de "
            "coluna ausente). NAO executa Spark nem gera o plano: quem chama cola a saida "
            "de explain num arquivo. `explain(\"codegen\")` e REJEITADO com "
            "`reason: unsupported_mode` -- e codigo Java, nao plano. Lista de campos "
            "truncada pelo Spark (`... N more fields`) vira `plan.unresolved` e a razao de "
            "SF-PQ-004 NAO e calculada: SF-PQ-004 e uma razao, e contar uma lista parcial "
            "infla o numerador em silencio. `PartitionFilters` vazio sem evidencia de "
            "particionamento devolve `table_partitioned: \"unknown\"`, nunca `false`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo de texto com a saida de explain (um plano).",
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
    "sparkforge_analyze_emr_cluster": {
        "description": (
            "Extrai facts de um dump JSON de cluster EMR on EC2 (`describe-cluster` mais "
            "`list-instance-groups`/`list-instance-fleets`/`list-bootstrap-actions`/"
            "`get-managed-scaling-policy`/`get-auto-termination-policy`): release, "
            "aplicacoes com a versao observada, capacidade por papel (Spot/On-Demand, "
            "grupo OU fleet no mesmo kind), configuracoes nos DOIS niveis (cluster e "
            "grupo, com quem sobrepoe quem), bootstrap actions e a politica de managed "
            "scaling. NAO chama a API do EMR -- so le o JSON ja salvo em disco "
            "(`sparkforge_collect_emr_cluster` ou `aws emr ...` a mao fazem isso). "
            "Grupo cujo `Configurations` diverge de `LastSuccessfullyAppliedConfigurations` "
            "vira `emr.configuration.unapplied`: a reconfiguracao foi pedida e NAO "
            "aplicada, entao o cluster nao roda com o que o dump aparenta dizer, e toda "
            "regra que le configuracao daquele grupo precisa desse fact como guarda. "
            "Emite tambem um unico fact DERIVADO, `emr.yarn.am_node_label`, que decide a "
            "partir do `yarn-site` se o ApplicationMaster -- que em deploy-mode cluster E "
            "o driver -- esta preso a um rotulo de no seguro; ele so aparece quando o AM "
            "NAO esta provadamente solto, e e o guarda de SF-EMR-008."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo ou diretorio com dumps de cluster EMR.",
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
    "sparkforge_analyze_emr_serverless": {
        "description": (
            "Extrai facts de um dump JSON de application Amazon EMR Serverless "
            "(`get-application`): release, estado, arquitetura, capacidade pre-inicializada "
            "por worker type (`emrs.initial_capacity`), teto de recursos, propriedades de "
            "`runtimeConfiguration` (`emrs.configuration`) e destinos de log "
            "(`emrs.monitoring`). NAO chama a API do EMR Serverless -- so le o JSON ja "
            "salvo em disco (`sparkforge_collect_emr_serverless` ou "
            "`aws emr-serverless get-application` a mao fazem isso). "
            "LIMITE QUE VALE PARA TODO FACT DAQUI: `get-application` descreve o PADRAO da "
            "application, nao o que um job rodou -- a AWS declara que as configuracoes de "
            "`StartJobRun` sobrepoem as do nivel da application, inclusive removendo "
            "classificacao e destino de log. Nenhum achado desta area pode ser redigido "
            "como afirmacao sobre execucao. "
            "`emrs.monitoring` e o unico fact do modulo que aplica default documentado, e "
            "por necessidade: managed persistence tem default `true` e CloudWatch tem "
            "default `false`, entao `*_declared` acompanha cada destino para distinguir o "
            "que foi lido do que foi presumido. Auto-stop faz o oposto -- o default da AWS "
            "e o estado SEGURO, entao o campo ausente NAO e materializado e "
            "`auto_stop_declared` responde sobre o payload. Unidade de capacidade fora do "
            "conjunto documentado vira `emrs.unresolved` contado, nunca numero adivinhado."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo ou diretorio com dumps de application.",
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
    "sparkforge_analyze_data_quality": {
        "description": (
            "Extrai facts de VALIDACAO DE DADO do proprio codigo PySpark (`.py` do "
            "repositorio, nunca API da AWS): onde cada check roda, o que ele custa e "
            "se ele tem consequencia. Reconhece tres formas pela FORMA do codigo, "
            "nunca por lista de nomes -- o check artesanal (`df.filter(...).count()`), "
            "a `VerificationSuite` do PyDeequ e a validacao do Great Expectations. "
            "`dq.check` carrega framework, tipo, alvo, `position_vs_write` (a "
            "validacao roda antes ou depois de o dado ser publicado), "
            "`target_persisted`, `action_after_check` e quantos checks incidem sobre o "
            "mesmo alvo; `dq.enforcement` so aparece quando a consequencia esta "
            "PROVADA (`raise`, `sys.exit`, `assert`) -- no escopo do check, ou UM "
            "salto adiante no corpo de um helper do mesmo modulo, e ai `attrs.via` "
            "nomeia o helper --, e a AUSENCIA "
            "dele e o sinal de validacao sem dente; `dq.module_analyzed` prova que o "
            "modulo foi lido, para que 'nenhum check' nao se confunda com 'nao "
            "analisei'. NAO JULGA O DADO: nao diz se a tabela esta correta, se um "
            "check reprovaria, nem quantas linhas violam a regra -- isso e trabalho "
            "da ferramenta de DQ em execucao. Diz apenas ONDE a validacao esta no "
            "codigo, o que ela alcanca e o que ela deixa passar. Nao aplica limiar, "
            "nao atribui severidade e nao adivinha alvo: alvo que a AST nao resolve "
            "(DataFrame anonimo, helper que monta a cadeia a partir do nome da "
            "tabela) e cadeia de consequencia mais longa que um salto viram "
            "`dq.unresolved` com `reason`, contados como ponto cego em vez de "
            "presumidos resolvidos."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo .py ou diretorio com codigo PySpark.",
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
    "sparkforge_analyze_graph": {
        "description": (
            "Extrai facts de PROCESSAMENTO DE GRAFO com GraphFrames do proprio codigo "
            "PySpark (`.py` do repositorio, nunca API da AWS). Emite `graph.import` "
            "(a evidencia honesta de que o job usa GraphFrames, com `scope` e "
            "`guarded` para o import dentro de funcao ou sob `try`), "
            "`graph.construction` (o `GraphFrame(v, e)` com `vertices_persisted` e "
            "`edges_persisted`, porque um grafo cujos dois DataFrames nao estao "
            "persistidos e recomputado a cada iteracao), `graph.algorithm` (o "
            "algoritmo chamado, seus argumentos literais, `inside_loop`, "
            "`iteration_arg` quando o codigo passou algum, e `checkpoint_required` JA "
            "DECIDIDO), `graph.checkpoint_dir` (`setCheckpointDir`, "
            "`spark.checkpoint.dir` e `spark.graphframes.useLocalCheckpoints` lidos "
            "DENTRO do arquivo) e `graph.module_analyzed`, que prova que o modulo foi "
            "lido para que 'nenhum grafo' nao se confunda com 'nao analisei'. "
            "NAO AFIRMA VERSAO: `from graphframes import GraphFrame` e identico em "
            "0.8.2 e em 0.12.1, e nenhum fact daqui diz qual linhagem esta instalada. "
            "NAO JULGA: nao aplica limiar, nao atribui severidade e nao diz se o grafo "
            "cabe na memoria. Nao adivinha: despacho dinamico (`getattr`), import "
            "montado em runtime, argumento posicional de `connectedComponents` e "
            "vertice que chega por parametro viram `graph.unresolved` com `reason`, "
            "contados como ponto cego em vez de presumidos resolvidos."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo .py ou diretorio com codigo PySpark.",
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
    "sparkforge_analyze_s3_listing": {
        "description": (
            "Extrai facts de um dump de `aws s3api list-objects-v2`: contagem, media, "
            "p95 e maximo de bytes por prefixo, agrupados por (formato, compressao). "
            "NAO chama a API da AWS -- so le o JSON ja salvo em disco. Desbloqueia "
            "SF-PQ-001 (small files), SF-PQ-003 (texto gzip nao splitavel) e, junto "
            "com `sparkforge_analyze_catalog_schema`, SF-PQ-005 (cardinalidade de "
            "particao). Listagem com `IsTruncated: true` NAO produz sumario: os "
            "numeros seriam de uma pagina apresentada como total, entao vira "
            "`s3.unresolved` com `reason: truncated_listing`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo .json ou diretorio com paginas da listagem.",
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
    "sparkforge_analyze_consumers": {
        "description": (
            "Extrai facts do inventario DECLARADO de consumidores de tabela "
            "(`.sparkforge/consumers.yaml`, versionado com o repositorio). Unico "
            "extrator do pacote que le um arquivo escrito por uma pessoa, e de "
            "proposito: quem consome uma tabela nao esta no codigo, no plano nem no "
            "event log -- e conhecimento da organizacao. Desbloqueia SF-ENV-002 (a "
            "tabela Iceberg em format V3 que o Athena nao le). Tabela ausente do "
            "inventario nao produz fact: ausencia de declaracao nao e declaracao de "
            "ausencia."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo .yaml do inventario, ou diretorio com varios.",
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
    "sparkforge_analyze_terraform_diff": {
        "description": (
            "Compara dois estados de um modulo Terraform (dois checkouts, dois "
            "`git worktree`, o main e o branch do PR) e devolve os facts do lado "
            "DEPOIS, com `attrs.changed` e `attrs.previous_value` no que mudou. Nao "
            "roda terraform: le o HCL, que e o que o revisor do PR ve. Desbloqueia "
            "SF-GLUE-005, que pergunta se alguem aumentou o worker sem evidencia de "
            "pressao de memoria -- e por isso exige tambem o event log do run."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["before", "after"],
            "properties": {
                "before": {"type": "string", "description": "Diretorio do estado anterior."},
                "after": {"type": "string", "description": "Diretorio do estado proposto."},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts do lado depois, anotados com o que mudou, ou erro se um path nao existe.",
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
    "sparkforge_benchmark": {
        "description": (
            "Compara DUAS execucoes a partir dos facts de event log de cada uma "
            "(`sparkforge_analyze_event_log` gravado em disco), e emite `bench.run_delta`, "
            "`bench.stage_delta`, `bench.unmatched`, `bench.analyzed` e `bench.unresolved`. "
            "Verbo de topo, nao um `analyze`: nao extrai nada de artefato, compara dois "
            "conjuntos ja extraidos. "
            "O QUE ELE RECUSA AFIRMAR, e isso importa mais que o que ele afirma: "
            "(1) `total_task_ms` e TEMPO DE TASK SOMADO (`mean_ms * task_count` sobre os "
            "stages) -- e trabalho, NAO tempo de relogio; o event log nao carrega duracao "
            "wall-clock, e um job pode terminar antes no relogio somando MAIS tempo de task "
            "ao paralelizar melhor, entao uma alta aqui pede confirmacao no relogio antes de "
            "reverter qualquer coisa. (2) Esta ferramenta NAO EXECUTA NADA: nao roda Spark, "
            "nao chama AWS, nao mede; ela le dois conjuntos de facts que alguem ja coletou. "
            "(3) O casamento de stage e por `symbol` IDENTICO -- `stage_id` nao e estavel "
            "entre execucoes --, e o que nao casa nao e silenciado: vira `bench.unmatched` e "
            "entra em `unmatched_stage_count`. (4) Uma chave `*_delta_pct` AUSENTE significa "
            "\"nao sei\", nunca \"zero\": ela e omitida quando o lado antes e zero, quando a "
            "medida falta ou esta incompleta de um lado, ou quando a populacao de stages "
            "mudou -- casos em que o percentual seria inventado. Os totais observados ficam; "
            "o que cai e a razao entre eles."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["before_path", "after_path"],
            "properties": {
                "before_path": {
                    "type": "string",
                    "description": (
                        "Arquivo de facts da execucao ANTES, gerado por "
                        "`sparkforge_analyze_event_log`."
                    ),
                },
                "after_path": {
                    "type": "string",
                    "description": (
                        "Arquivo de facts da execucao DEPOIS, gerado por "
                        "`sparkforge_analyze_event_log`."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _BENCHMARK_SCHEMA,
            "Comparacao das duas execucoes, ou erro se um dos arquivos nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_funcval_plan": {
        "description": (
            "Deriva O QUE MEDIR nos dois lados de uma mudanca, a partir de facts JA "
            "extraidos (`sparkforge_analyze_pyspark` e `sparkforge_analyze_catalog_schema` "
            "gravados em disco), e GRAVA o plano em `out_path` -- o artefato que "
            "`sparkforge_funcval_compare` rele. Emite `funcval.plan` (um por alvo "
            "distinto) e `funcval.unresolved`. Verbo de topo, nao um `analyze`: nao "
            "extrai nada de artefato. "
            "O QUE ELE RECUSA AFIRMAR, e isso importa mais que o que ele afirma: "
            "(1) Os quatro eixos sao PROXIES. Contagem, schema, chaves e agregados "
            "iguais NAO provam que o dado e o mesmo -- duas linhas podem trocar valores "
            "entre si e os quatro passam; a fase afirma 'nenhum dos quatro proxies "
            "detectou divergencia', nunca 'o resultado e identico'. (2) Ele NAO MEDE "
            "NADA: nao executa consulta, nao le a tabela, nao chama AWS. Os valores vem "
            "do resultado que VOCE produz em cada lado. (3) CHAVE DE NEGOCIO NAO E "
            "DERIVAVEL: nenhum kind que os extratores emitem a nomeia (`pyspark.join` "
            "da o NUMERO de colunas do `on`, `pyspark.dedup` e `pyspark.window` dao "
            "booleanos, particao como proxy foi medida e rejeitada). Ela so entra por "
            "`keys`, com `origin: declared` e `derived_from: []` -- e chave declarada "
            "errada produz P0 em dado correto, com a diferenca de que fica gravado quem "
            "afirmou. Sem `keys`, o eixo sai ESCRITO como ausente em `undeclared_axes`, "
            "nunca calado. (4) O catalogo diz QUAIS colunas e tipos existem, e nada "
            "mais: o check de `schema` NAO carrega o mapa coluna->tipo, porque a "
            "comparacao e sempre antes contra depois -- observado contra declarado e "
            "asserção absoluta sobre o dado, que e pergunta de SF-DQ. (5) Alvo que nao "
            "casa por string identica com um simbolo do catalogo vira "
            "`funcval.unresolved`, nunca alvo adivinhado por sufixo."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["facts_paths", "out_path"],
            "properties": {
                "facts_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": (
                        "Arquivos de facts (JSON) de `sparkforge_analyze_pyspark` e "
                        "`sparkforge_analyze_catalog_schema`. Repetivel, e precisa ser: "
                        "o alvo vem do `pyspark.write` e o schema/os agregados vem do "
                        "`catalog.table_schema`, que nenhum verbo produz no mesmo arquivo."
                    ),
                },
                "out_path": {
                    "type": "string",
                    "description": (
                        "Onde gravar o plano. Obrigatorio: o plano e a entrada de "
                        "`sparkforge_funcval_compare` e a evidencia do gate, nao uma "
                        "conveniencia de saida."
                    ),
                },
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Chaves de negocio DECLARADAS por voce. Cada elemento e uma "
                        "chave; virgula dentro dele faz chave COMPOSTA "
                        "(`\"loja_id,pedido_id\"` e uma chave de duas colunas). Omitir "
                        "nao e erro: o eixo sai escrito como ausente."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _FUNCVAL_SCHEMA,
            "O plano derivado (e gravado em out_path), ou erro se um arquivo nao existe.",
        ),
        "annotations": _WRITE_IDEMPOTENT,
    },
    "sparkforge_funcval_compare": {
        "description": (
            "Compara os DOIS resultados que VOCE mediu contra o plano de "
            "`sparkforge_funcval_plan`, e emite `funcval.check_delta`, a sentinela "
            "`funcval.analyzed` e `funcval.unresolved`. Funcao pura sobre valores ja "
            "medidos: nao executa consulta e nao mede nada. Com `out_path`, GRAVA a "
            "comparacao COMPLETA no arquivo que `sparkforge_judge` le -- sem ele o passo "
            "seguinte exige extrair `items` do envelope a mao, e o envelope PAGINA. "
            "O QUE ELE RECUSA AFIRMAR: "
            "(1) Os quatro eixos sao PROXIES -- contagem, schema, chaves e agregados "
            "iguais NAO provam que o dado e o mesmo. A sentinela carrega esse limite em "
            "`attrs`, e nao so nesta descricao. (2) A comparacao e SEMPRE antes contra "
            "depois, NUNCA resultado contra catalogo: o schema declarado serviu para "
            "saber quais colunas existem, e conferir o observado contra ele seria "
            "asserção absoluta sobre o dado -- pergunta de SF-DQ, nao desta fase. "
            "(3) COMPARACAO RELATIVA NAO DECIDE `diverged`. Para ponto flutuante o fact "
            "sai com `measures.relative_delta` e SEM `diverged`, com "
            "`diverged_omitted_reason` dizendo por que: o numero que separa reassociacao "
            "de divergencia real e heuristica de campo, e heuristica de campo mora no "
            "catalogo (SF-FVAL-004, `threshold.relative_tolerance`), nunca em Python -- "
            "um Fact nunca contem limiar. Quem julga e a regra. A comparacao exata "
            "mantem o `diverged` no fact, porque 'os dois valores nao sao identicos' e "
            "observacao e nao limiar. (4) O MODO DE COMPARACAO VEM DO PLANO, nunca do "
            "resultado: senao o operador escolheria se o proprio numero dele e julgado "
            "exato ou com tolerancia. O `type` do resultado so e lido para check que o "
            "plano NAO pediu. (5) Tres estados de cobertura continuam DISTINTOS: check "
            "com valor entra na comparacao; `value: null` com `unavailable_reason` vira "
            "`unresolved` e NAO conta como reportado; chave ausente de `checks` e "
            "cobertura faltante. 'Nao medi' nunca vira zero. (6) Divergencia dentro da "
            "tolerancia nao e prova de igualdade: e ausencia de prova de diferenca."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["plan_path", "before_path", "after_path"],
            "properties": {
                "plan_path": {
                    "type": "string",
                    "description": "Arquivo gravado por `sparkforge_funcval_plan`.",
                },
                "before_path": {
                    "type": "string",
                    "description": (
                        "Resultado medido ANTES: JSON `{\"target\", \"checks\"}`, cada "
                        "check um objeto `{\"value\": <numero|mapa|null>}`. "
                        "`value: null` exige `unavailable_reason`; check nao medido fica "
                        "AUSENTE de `checks`, nunca zero."
                    ),
                },
                "after_path": {
                    "type": "string",
                    "description": "Resultado medido DEPOIS, no mesmo contrato.",
                },
                "out_path": {
                    "type": "string",
                    "description": (
                        "Onde gravar a comparacao (JSON de facts), que e o que "
                        "`sparkforge_judge` le como `facts`. OPCIONAL, ao contrario do "
                        "`out_path` do plano: o plano e a entrada do proximo verbo, esta "
                        "e uma saida terminal. O arquivo traz a lista COMPLETA e nunca a "
                        "pagina -- `limit` corta o `structuredContent`, nao o arquivo, e "
                        "julgar a primeira pagina como se fosse a comparacao e o defeito "
                        "que a SF-FVAL-005 acusa no dado do operador."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            _FUNCVAL_SCHEMA,
            "A comparacao antes/depois (e gravada em out_path, quando pedido), ou erro "
            "se o plano/os resultados nao servem.",
        ),
        "annotations": _WRITE_IDEMPOTENT,
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
            "pelo runtime -- que sai dos PROPRIOS facts quando eles o carregam "
            "(`tf.attribute` glue_version, `spark.runtime_version`), e so entao das "
            "flags: nao e preciso saber a versao de cor para as regras versionadas "
            "avaliarem. O runtime usado volta em `runtime`, com `divergences`. "
            "Aceita `facts` inline ou `facts_path` (arquivo gerado "
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
                "emr": _EMR_INPUT,
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
    "sparkforge_knowledge_path": {
        "description": (
            "Resolve a raiz dos arquivos de conhecimento versionado e, "
            "opcionalmente, um arquivo dentro dela. Use antes de tentar LER "
            "knowledge: num pacote instalado por pip o caminho fica dentro do "
            "site-packages e nao e adivinhavel."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Caminho relativo, ex.: glue/runtime-matrix.md",
                }
            },
        },
        "outputSchema": {
            "type": "object",
            "required": ["root", "available"],
            "properties": {
                "root": {"type": "string"},
                "file": {"type": ["string", "null"]},
                "available": {"type": "array", "items": {"type": "string"}},
            },
        },
        "annotations": _READ_ONLY,
    },
    "sparkforge_validate_output": {
        "description": (
            "Valida um finding proposto contra o JSON Schema e contra a regra de ganho sem "
            "benchmark_ref antes de aceita-lo. Este e o outro pilar da independencia de "
            "modelo: um LLM diferente pode redigir o finding de outra forma, mas so passa "
            "se for logicamente consistente com o catalogo -- a validacao decide o que e "
            "aceitavel, nao o modelo que escreveu. `benchmark_ref` cita o `fact_id` de um "
            "`bench.run_delta` (`sparkforge_benchmark`), nao texto livre; informando "
            "`facts_path` o id citado passa a precisar existir naquele conjunto."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["finding"],
            "properties": {
                "finding": {"type": "object"},
                "facts_path": {
                    "type": "string",
                    "description": (
                        "Opcional. Caminho de um arquivo de facts. Sem ele, "
                        "`benchmark_ref` so e cobrado na FORMA (`f_` + 6 hex); com "
                        "ele, o `fact_id` citado precisa estar no conjunto."
                    ),
                },
            },
        },
        "outputSchema": _VALIDATE_OUTPUT_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_report_sign": {
        "description": (
            "Escreve, no fim do relatorio, o bloco que prova CORRESPONDENCIA entre o "
            "texto, a evidencia e o catalogo que o produziram -- nunca autoria: nao ha "
            "chave e nao ha segredo, e qualquer um com os mesmos findings produz a mesma "
            "assinatura. O limite vai escrito dentro do bloco, porque bloco que sugira "
            "autoridade mente por omissao. O corpo assinado e tudo que vem ANTES do "
            "delimitador de abertura, entao o bloco nunca entra no hash que carrega. Os "
            "quatro campos nao-corpo saem do arquivo de FINDINGS, e nao do de facts: so "
            "o finding carrega `evidence` (os fact_id citados), `rule_id`, "
            "`catalog_version` e `schema_version`. Reassinar e barato e idempotente."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["report_path", "findings_path"],
            "properties": {
                "report_path": {
                    "type": "string",
                    "description": "Markdown do relatorio. E reescrito no lugar.",
                },
                "findings_path": {
                    "type": "string",
                    "description": "Findings (JSON) gerados por `sparkforge judge --out`.",
                },
            },
        },
        "outputSchema": _may_fail(
            _REPORT_SIGN_SCHEMA,
            "O que foi assinado, ou erro se o relatorio/findings nao servem.",
        ),
        "annotations": _WRITE_IDEMPOTENT,
    },
    "sparkforge_report_verify": {
        "description": (
            "Confere a assinatura de um relatorio e diz QUAL das tres partes divergiu -- "
            "evidencia, catalogo ou corpo --, em vez de devolver apenas 'invalido'. "
            "Cobre tambem bloco ausente e bloco malformado, que sao estados diferentes "
            "de 'nao corresponde': relatorio sem bloco nao e relatorio adulterado, e "
            "confundir os dois faria o leitor desconfiar do texto errado."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["report_path", "findings_path"],
            "properties": {
                "report_path": {"type": "string"},
                "findings_path": {
                    "type": "string",
                    "description": (
                        "O mesmo arquivo de findings contra o qual o relatorio foi "
                        "assinado."
                    ),
                },
            },
        },
        "outputSchema": _may_fail(
            _REPORT_VERIFY_SCHEMA,
            "O veredito por parte, ou erro se o relatorio/findings nao existem.",
        ),
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
    "sparkforge_collect_emr_cluster": {
        "description": (
            "Baixa os seis dumps de um cluster EMR on EC2 (`describe_cluster`, grupos OU "
            "fleets, bootstrap actions, managed scaling e auto termination) e registra a "
            "uniao deles no manifesto, no mesmo shape PascalCase que `aws emr ...` "
            "devolve -- coleta manual e automatica produzem o mesmo arquivo. Secao que "
            "nao se aplica ao cluster (fleets num cluster de grupos, politica nao "
            "configurada) e OMITIDA, nunca gravada vazia. Mesma politica offline-first "
            "de `sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "cluster_id", "now"],
            "properties": {
                "repo": {"type": "string"},
                "cluster_id": {"type": "string", "description": "j-XXXXXXXXXXXXX"},
                "now": {"type": "string", "description": "Timestamp ISO 8601."},
            },
        },
        "outputSchema": _may_fail(
            _COLLECT_ARTIFACT_SCHEMA,
            "Artefato coletado (ou cache hit local), ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY_OPEN_WORLD,
    },
    "sparkforge_collect_emr_serverless": {
        "description": (
            "Baixa `get-application` de uma application Amazon EMR Serverless e registra a "
            "resposta no manifesto, no mesmo shape camelCase que "
            "`aws emr-serverless get-application` devolve -- coleta manual e automatica "
            "produzem o mesmo arquivo, que e o que `sparkforge_analyze_emr_serverless` le. "
            "UMA chamada, nao seis como no EMR on EC2: capacidade inicial e maxima, "
            "auto-start/stop, `runtimeConfiguration` e `monitoringConfiguration` chegam "
            "todos dentro do mesmo objeto. Job runs ficam FORA por escopo. "
            "Exige `application_id`, nunca nome: `name` e opcional na API e nenhuma fonte "
            "o declara unico, entao resolver id por nome escolheria uma entre homonimas em "
            "silencio. Mesma politica offline-first de `sparkforge_collect_event_log`."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "application_id", "now"],
            "properties": {
                "repo": {"type": "string"},
                "application_id": {"type": "string", "description": "00fXXXXXXXXXXXXX"},
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
        emr=args.get("emr"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
        facts_path=args.get("facts_path"),
        strict_gates=bool(args.get("strict_gates", False)),
        reopen=bool(args.get("reopen", False)),
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
        override_gate=args.get("override_gate"),
        reason=args.get("reason"),
        facts_path=args.get("facts_path"),
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


def _h_playbook(args: dict[str, Any]) -> dict[str, Any]:
    return _core.playbook(
        args["coordinator"], repo=args.get("repo", "."), findings=args.get("findings") or []
    )


def _h_runtime_detect(args: dict[str, Any]) -> dict[str, Any]:
    return _core.runtime_detect(
        glue=args.get("glue"),
        emr=args.get("emr"),
        spark=args.get("spark"),
        python=args.get("python"),
        iceberg=args.get("iceberg"),
        athena=args.get("athena"),
        facts_path=args.get("facts_path"),
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
        emr=args.get("emr"),
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


def _h_knowledge_path(args: dict[str, Any]) -> dict[str, Any]:
    return _core.knowledge_path(file=args.get("file"))


def _h_validate_output(args: dict[str, Any]) -> dict[str, Any]:
    return _core.validate_output(args["finding"], facts_path=args.get("facts_path"))


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


def _h_analyze_plan(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_plan(
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


def _h_analyze_s3_listing(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_s3_listing(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_consumers(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_consumers(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_terraform_diff(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_terraform_diff(
        args["before"],
        args["after"],
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


def _h_analyze_emr_cluster(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_emr_cluster(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_emr_serverless(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_emr_serverless(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_data_quality(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_data_quality(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_analyze_graph(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_graph(
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


def _h_benchmark(args: dict[str, Any]) -> dict[str, Any]:
    return _core.benchmark_runs(
        args["before_path"],
        args["after_path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_funcval_plan(args: dict[str, Any]) -> dict[str, Any]:
    return _core.funcval_plan(
        args.get("facts_paths"),
        args["out_path"],
        keys=args.get("keys"),
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
    )


def _h_funcval_compare(args: dict[str, Any]) -> dict[str, Any]:
    return _core.funcval_compare(
        args["plan_path"],
        args["before_path"],
        args["after_path"],
        out_path=args.get("out_path"),
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


def _h_report_sign(args: dict[str, Any]) -> dict[str, Any]:
    return _core.report_sign(args["report_path"], args["findings_path"])


def _h_report_verify(args: dict[str, Any]) -> dict[str, Any]:
    return _core.report_verify(args["report_path"], args["findings_path"])


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


def _h_collect_emr_cluster(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_emr_cluster(
        args["repo"], cluster_id=args["cluster_id"], now=args["now"]
    )


def _h_collect_emr_serverless(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_emr_serverless(
        args["repo"], application_id=args["application_id"], now=args["now"]
    )


def _h_collect_verify(args: dict[str, Any]) -> dict[str, Any]:
    return _core.collect_verify(args["repo"])


_HANDLERS = {
    "sparkforge_case_open": _h_case_open,
    "sparkforge_case_get": _h_case_get,
    "sparkforge_case_update": _h_case_update,
    "sparkforge_next_step": _h_next_step,
    "sparkforge_resume": _h_resume,
    "sparkforge_playbook": _h_playbook,
    "sparkforge_runtime_detect": _h_runtime_detect,
    "sparkforge_knowledge_path": _h_knowledge_path,
    "sparkforge_analyze_pyspark": _h_analyze_pyspark,
    "sparkforge_analyze_catalog_schema": _h_analyze_catalog_schema,
    "sparkforge_analyze_event_log": _h_analyze_event_log,
    "sparkforge_analyze_plan": _h_analyze_plan,
    "sparkforge_analyze_terraform": _h_analyze_terraform,
    "sparkforge_analyze_iceberg": _h_analyze_iceberg,
    "sparkforge_analyze_sql": _h_analyze_sql,
    "sparkforge_analyze_athena_workgroup": _h_analyze_athena_workgroup,
    "sparkforge_analyze_emr_cluster": _h_analyze_emr_cluster,
    "sparkforge_analyze_emr_serverless": _h_analyze_emr_serverless,
    "sparkforge_analyze_data_quality": _h_analyze_data_quality,
    "sparkforge_analyze_graph": _h_analyze_graph,
    "sparkforge_analyze_s3_listing": _h_analyze_s3_listing,
    "sparkforge_analyze_consumers": _h_analyze_consumers,
    "sparkforge_analyze_terraform_diff": _h_analyze_terraform_diff,
    "sparkforge_analyze_call_graph": _h_analyze_call_graph,
    "sparkforge_benchmark": _h_benchmark,
    "sparkforge_funcval_plan": _h_funcval_plan,
    "sparkforge_funcval_compare": _h_funcval_compare,
    "sparkforge_fuse": _h_fuse,
    "sparkforge_judge": _h_judge,
    "sparkforge_rules_lookup": _h_rules_lookup,
    "sparkforge_validate_output": _h_validate_output,
    "sparkforge_report_sign": _h_report_sign,
    "sparkforge_report_verify": _h_report_verify,
    "sparkforge_collect_event_log": _h_collect_event_log,
    "sparkforge_collect_glue_job": _h_collect_glue_job,
    "sparkforge_collect_cloudwatch": _h_collect_cloudwatch,
    "sparkforge_collect_iceberg_metadata": _h_collect_iceberg_metadata,
    "sparkforge_collect_athena_workgroup": _h_collect_athena_workgroup,
    "sparkforge_collect_emr_cluster": _h_collect_emr_cluster,
    "sparkforge_collect_emr_serverless": _h_collect_emr_serverless,
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
